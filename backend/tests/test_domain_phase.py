"""Tests unitaires de l'agrégat `Phase` (E01US009 / ADR-0011, E01US015) — domaine pur, sans base."""

from __future__ import annotations

import pytest

from domain.bareme import BaremeQualification
from domain.erreurs import (
    CadenceValidationSuperieureAuBareme,
    EffectifIncompatible,
    EffectifPhaseInvalide,
    GrainIncompatibleAvecTypePhase,
    PhaseQualificationIncomplete,
    PhaseSansClassementPrelevee,
    PlageSourceVide,
    RangSourceInvalide,
    RangsSourceInexistants,
    SequenceOrdreInvalide,
    SeuilDeBarrageInvalide,
    SourceApresPhase,
    SourceIntrouvable,
)
from domain.grain_validation import GrainValidation, TypeGrain
from domain.phase import (
    IssueTour,
    Phase,
    SequencePhases,
    SourcePhase,
    StatutPhase,
    TypePhase,
    grain_par_defaut,
    produit_un_classement,
)


def _phase(
    bareme: BaremeQualification | None = None,
    validation: GrainValidation | None = None,
) -> Phase:
    """Une phase de qualification persistée (id=3), valeurs par défaut surchargeables."""
    return Phase(
        depart_id=7,
        ordre=1,
        type=TypePhase.QUALIFICATION,
        bareme=bareme or BaremeQualification.creer(20, 3),
        validation=validation or GrainValidation.fin_de_serie(),
        statut=StatutPhase.A_VENIR,
        id=3,
    )


def test_qualification_cree_la_premiere_phase() -> None:
    """`qualification` crée une phase qualification, ordre 1, statut à venir, non persistée."""
    bareme = BaremeQualification.preset_ffta_18m()
    phase = Phase.qualification(depart_id=7, bareme=bareme)
    assert phase.depart_id == 7
    assert phase.ordre == 1
    assert phase.type is TypePhase.QUALIFICATION
    assert phase.statut is StatutPhase.A_VENIR
    assert phase.bareme == bareme
    assert phase.id is None


def test_qualification_applique_le_preset_fin_de_serie_par_defaut() -> None:
    """Sans grain explicite, la qualification valide en fin de série (`D-11`)."""
    phase = Phase.qualification(depart_id=7, bareme=BaremeQualification.preset_ffta_18m())

    assert phase.validation == GrainValidation.fin_de_serie()


def test_qualification_accepte_un_grain_explicite() -> None:
    phase = Phase.qualification(
        depart_id=7,
        bareme=BaremeQualification.preset_ffta_18m(),
        validation=GrainValidation.toutes_les_n_volees(2),
    )

    assert phase.validation == GrainValidation.toutes_les_n_volees(2)


def test_grain_par_defaut_de_la_qualification_est_fin_de_serie() -> None:
    assert grain_par_defaut(TypePhase.QUALIFICATION) == GrainValidation.fin_de_serie()


def test_grain_par_defaut_de_l_elimination_directe_est_fin_de_duel() -> None:
    """E04US013/ADR-0049 §5 : une phase à duels se valide **en fin de duel** (FFTA B.6.1.1)."""
    assert grain_par_defaut(TypePhase.ELIMINATION_DIRECTE) == GrainValidation.fin_de_duel()


def test_elimination_directe_accepte_le_grain_fin_de_duel() -> None:
    """Le grain `fin de duel` est **admis** pour l'élimination directe (E04US013)."""
    phase = Phase.creer(depart_id=7, ordre=2, type=TypePhase.ELIMINATION_DIRECTE)
    modifiee = phase.avec_validation(GrainValidation.fin_de_duel())
    assert modifiee.validation == GrainValidation.fin_de_duel()


def test_elimination_directe_refuse_un_grain_de_serie() -> None:
    """« Fin de série » n'a pas de sens pour un duel : seul `fin de duel` est admis (E04US013)."""
    phase = Phase.creer(depart_id=7, ordre=2, type=TypePhase.ELIMINATION_DIRECTE)
    with pytest.raises(GrainIncompatibleAvecTypePhase):
        phase.avec_validation(GrainValidation.fin_de_serie())


def test_avec_bareme_remplace_le_bareme_et_preserve_le_reste() -> None:
    """`avec_bareme` met à jour le barème et conserve id/tournoi/ordre/statut/type/grain."""
    phase = _phase(bareme=BaremeQualification.creer(20, 3))
    modifiee = phase.avec_bareme(BaremeQualification.creer(10, 3))
    assert modifiee.id == 3
    assert modifiee.depart_id == 7
    assert modifiee.ordre == 1
    assert modifiee.type is TypePhase.QUALIFICATION
    assert modifiee.statut is StatutPhase.A_VENIR
    assert modifiee.validation == GrainValidation.fin_de_serie()
    assert modifiee.bareme is not None and modifiee.bareme.nb_volees == 10
    # L'agrégat est gelé : l'original n'est pas muté.
    assert phase.bareme is not None and phase.bareme.nb_volees == 20


def test_avec_validation_remplace_le_grain_et_preserve_le_reste() -> None:
    phase = _phase(validation=GrainValidation.fin_de_serie())

    modifiee = phase.avec_validation(GrainValidation.toutes_les_n_volees(4))

    assert modifiee.id == 3
    assert modifiee.depart_id == 7
    assert modifiee.ordre == 1
    assert modifiee.type is TypePhase.QUALIFICATION
    assert modifiee.statut is StatutPhase.A_VENIR
    assert modifiee.bareme == phase.bareme
    assert modifiee.validation == GrainValidation.toutes_les_n_volees(4)
    # L'agrégat est gelé : l'original n'est pas muté.
    assert phase.validation == GrainValidation.fin_de_serie()


def test_une_qualification_refuse_le_grain_fin_de_duel() -> None:
    """Une qualification se tire en séries : « fin de duel » n'y a pas de sens (`D-11`)."""
    with pytest.raises(GrainIncompatibleAvecTypePhase):
        Phase.qualification(
            depart_id=7,
            bareme=BaremeQualification.preset_ffta_18m(),
            validation=GrainValidation.fin_de_duel(),
        )


def test_avec_validation_refuse_un_grain_hors_du_type_de_phase() -> None:
    with pytest.raises(GrainIncompatibleAvecTypePhase):
        _phase().avec_validation(GrainValidation.fin_de_duel())


def test_une_cadence_superieure_au_bareme_est_refusee() -> None:
    """Valider toutes les 30 volées sur un barème de 20, c'est ne jamais valider."""
    with pytest.raises(CadenceValidationSuperieureAuBareme):
        _phase(
            bareme=BaremeQualification.creer(20, 3),
            validation=GrainValidation.toutes_les_n_volees(30),
        )


def test_une_cadence_egale_au_bareme_est_admise() -> None:
    """Cas limite : valider toutes les 20 volées d'un barème de 20 = une validation, à la fin."""
    phase = _phase(
        bareme=BaremeQualification.creer(20, 3),
        validation=GrainValidation.toutes_les_n_volees(20),
    )

    assert phase.validation is not None and phase.validation.n_volees == 20


def test_reduire_le_bareme_sous_la_cadence_en_place_est_refuse() -> None:
    """Le barème et le grain vivent sur la même phase : leur cohérence se vérifie des deux côtés.

    Conséquence assumée (E01US015) : l'endpoint barème (E01US009) peut désormais refuser une
    réduction — l'admin doit d'abord élargir son grain.
    """
    phase = _phase(
        bareme=BaremeQualification.creer(20, 3),
        validation=GrainValidation.toutes_les_n_volees(10),
    )

    with pytest.raises(CadenceValidationSuperieureAuBareme):
        phase.avec_bareme(BaremeQualification.creer(5, 3))


def test_reduire_le_bareme_sous_un_grain_de_fin_reste_possible() -> None:
    """Un grain de fin n'a pas de cadence : aucun couplage avec le barème."""
    phase = _phase(
        bareme=BaremeQualification.creer(20, 3),
        validation=GrainValidation.fin_de_serie(),
    )

    modifiee = phase.avec_bareme(BaremeQualification.creer(5, 3))

    assert modifiee.bareme is not None and modifiee.bareme.nb_volees == 5


def test_le_grain_fin_de_duel_reste_declare_pour_le_moteur() -> None:
    """`FIN_DE_DUEL` existe dans le domaine (choix cible, `D-11`) même si aucune phase actuelle ne
    l'accepte : EPIC-05 introduira les phases à duels, dont il sera le preset."""
    assert TypeGrain.FIN_DE_DUEL.value == "fin_de_duel"


# --- E05US001 : typage, phase générique, effectif (ADR-0045 §2) --------------------------------


def test_creer_une_phase_generique_sans_bareme() -> None:
    """Une phase d'élimination directe n'a **pas** de barème de qualification (ADR-0045 §2)."""
    phase = Phase.creer(depart_id=7, ordre=2, type=TypePhase.ELIMINATION_DIRECTE)

    assert phase.type is TypePhase.ELIMINATION_DIRECTE
    assert phase.ordre == 2
    assert phase.statut is StatutPhase.A_VENIR
    assert phase.bareme is None
    assert phase.validation is None
    assert phase.sources == ()
    assert phase.id is None


def test_les_types_placement_et_elimination_directe_existent() -> None:
    assert TypePhase.ELIMINATION_DIRECTE.value == "elimination_directe"
    assert TypePhase.PLACEMENT.value == "placement"


def test_une_qualification_sans_bareme_est_refusee() -> None:
    """L'invariant « qualification ⇒ barème + grain » ferme le seul cas dangereux du barème
    facultatif (ADR-0045 §2)."""
    with pytest.raises(PhaseQualificationIncomplete):
        Phase(depart_id=7, ordre=1, type=TypePhase.QUALIFICATION)


def test_un_effectif_nul_ou_negatif_est_refuse() -> None:
    with pytest.raises(EffectifPhaseInvalide):
        Phase.creer(depart_id=7, ordre=2, type=TypePhase.PLACEMENT, effectif=0)


def test_un_effectif_declare_est_conserve() -> None:
    phase = Phase.creer(depart_id=7, ordre=2, type=TypePhase.PLACEMENT, effectif=16)

    assert phase.effectif == 16


# --- E05US001 : cycle de vie d'une phase (ADR-0045 §1) -----------------------------------------


def test_transitions_de_statut_enchainent_a_venir_en_cours_terminee() -> None:
    """Les transitions sont **pures** : chacune renvoie une copie au nouveau statut."""
    phase = Phase.creer(depart_id=7, ordre=1, type=TypePhase.PLACEMENT)

    en_cours = phase.demarrer()
    assert en_cours.statut is StatutPhase.EN_COURS
    assert phase.statut is StatutPhase.A_VENIR  # l'original n'est pas muté (gelé)

    assert en_cours.terminer().statut is StatutPhase.TERMINEE


def test_mettre_en_pause_puis_reprendre_est_reversible() -> None:
    """`en_pause` gèle la phase (ADR-0045 §1) ; `reprendre` la ramène `en_cours`, sans perte."""
    en_cours = Phase.creer(depart_id=7, ordre=1, type=TypePhase.PLACEMENT).demarrer()

    en_pause = en_cours.mettre_en_pause()
    assert en_pause.statut is StatutPhase.EN_PAUSE

    assert en_pause.reprendre().statut is StatutPhase.EN_COURS


def test_le_statut_en_pause_de_phase_existe() -> None:
    assert StatutPhase.EN_PAUSE.value == "en_pause"


# --- E05US001 : source de peuplement — value object (ADR-0045 §3) ------------------------------


def test_une_source_prelève_une_plage_de_rangs() -> None:
    source = SourcePhase(ordre_source=1, rang_debut=1, rang_fin=16)

    assert source.effectif_selectionne == 16


def test_une_plage_de_rangs_vide_est_refusee() -> None:
    """« source vide » du CA : des rangs 8 à 4 ne prélèvent personne."""
    with pytest.raises(PlageSourceVide):
        SourcePhase(ordre_source=1, rang_debut=8, rang_fin=4)


def test_un_rang_de_debut_inferieur_a_un_est_refuse() -> None:
    """« rangs inexistants » (volet indépendant de la séquence) : le premier rang est 1."""
    with pytest.raises(RangSourceInvalide):
        SourcePhase(ordre_source=1, rang_debut=0, rang_fin=16)


# --- E05US001 : cohérence de la séquence (ADR-0045 §3) -----------------------------------------


def _qualification(effectif: int | None = None) -> Phase:
    """Une qualification (ordre 1) éventuellement dotée d'un effectif déclaré."""
    return Phase(
        depart_id=7,
        ordre=1,
        type=TypePhase.QUALIFICATION,
        bareme=BaremeQualification.preset_ffta_18m(),
        validation=GrainValidation.fin_de_serie(),
        effectif=effectif,
    )


def test_une_sequence_vide_est_valide() -> None:
    """Un tournoi peut n'avoir encore composé aucune phase."""
    assert SequencePhases(phases=()).phases == ()


def test_une_sequence_ordonnee_et_bien_sourcee_est_valide() -> None:
    """Qualification (40) → élimination directe (16) alimentée par les 16 premiers : cohérent."""
    qualif = _qualification(effectif=40)
    elim = Phase.creer(
        depart_id=7,
        ordre=2,
        type=TypePhase.ELIMINATION_DIRECTE,
        sources=(SourcePhase(ordre_source=1, rang_debut=1, rang_fin=16),),
        effectif=16,
    )

    sequence = SequencePhases(phases=(qualif, elim))

    assert len(sequence.phases) == 2


def test_un_trou_dans_les_ordres_est_refuse() -> None:
    qualif = _qualification()
    elim = Phase.creer(depart_id=7, ordre=3, type=TypePhase.ELIMINATION_DIRECTE)

    with pytest.raises(SequenceOrdreInvalide):
        SequencePhases(phases=(qualif, elim))


def test_un_doublon_dans_les_ordres_est_refuse() -> None:
    qualif = _qualification()
    autre = Phase.creer(depart_id=7, ordre=1, type=TypePhase.PLACEMENT)

    with pytest.raises(SequenceOrdreInvalide):
        SequencePhases(phases=(qualif, autre))


def test_une_source_vers_une_phase_inexistante_est_refusee() -> None:
    qualif = _qualification()
    elim = Phase.creer(
        depart_id=7,
        ordre=2,
        type=TypePhase.ELIMINATION_DIRECTE,
        sources=(SourcePhase(ordre_source=5, rang_debut=1, rang_fin=8),),
    )

    with pytest.raises(SourceIntrouvable):
        SequencePhases(phases=(qualif, elim))


def test_une_source_vers_une_phase_non_anterieure_est_refusee() -> None:
    """Une phase ne peut se nourrir que d'une phase d'ordre strictement inférieur."""
    qualif = _qualification()
    elim = Phase.creer(
        depart_id=7,
        ordre=2,
        type=TypePhase.ELIMINATION_DIRECTE,
        sources=(SourcePhase(ordre_source=2, rang_debut=1, rang_fin=8),),
    )

    with pytest.raises(SourceApresPhase):
        SequencePhases(phases=(qualif, elim))


def test_prelever_au_dela_de_l_effectif_de_la_source_est_refuse() -> None:
    """« rangs inexistants » (volet séquence) : prendre 40 rangs d'une phase qui en classe 32."""
    qualif = _qualification(effectif=32)
    elim = Phase.creer(
        depart_id=7,
        ordre=2,
        type=TypePhase.ELIMINATION_DIRECTE,
        sources=(SourcePhase(ordre_source=1, rang_debut=1, rang_fin=40),),
    )

    with pytest.raises(RangsSourceInexistants):
        SequencePhases(phases=(qualif, elim))


def test_un_effectif_consommateur_incompatible_avec_la_source_est_refuse() -> None:
    """« effectif incompatible » : une phase déclarée pour 16 mais dont la source prélève 8."""
    qualif = _qualification(effectif=40)
    elim = Phase.creer(
        depart_id=7,
        ordre=2,
        type=TypePhase.ELIMINATION_DIRECTE,
        sources=(SourcePhase(ordre_source=1, rang_debut=1, rang_fin=8),),
        effectif=16,
    )

    with pytest.raises(EffectifIncompatible):
        SequencePhases(phases=(qualif, elim))


def test_prelever_plus_que_l_effectif_declare_est_aussi_refuse() -> None:
    """« effectif incompatible » dans l'**autre** sens : la source prélève 20 (rangs 1..20, dans les
    40 de la source, donc rangs valides) pour une phase qui n'en attend que 16."""
    qualif = _qualification(effectif=40)
    elim = Phase.creer(
        depart_id=7,
        ordre=2,
        type=TypePhase.ELIMINATION_DIRECTE,
        sources=(SourcePhase(ordre_source=1, rang_debut=1, rang_fin=20),),
        effectif=16,
    )

    with pytest.raises(EffectifIncompatible):
        SequencePhases(phases=(qualif, elim))


def test_sans_effectif_declare_la_source_ne_declenche_pas_de_controle_d_effectif() -> None:
    """Les contrôles d'effectif sont silencieux quand l'effectif n'est pas déclaré (ADR-0045 §3)."""
    qualif = _qualification()  # pas d'effectif
    elim = Phase.creer(
        depart_id=7,
        ordre=2,
        type=TypePhase.ELIMINATION_DIRECTE,
        sources=(SourcePhase(ordre_source=1, rang_debut=1, rang_fin=999),),
    )

    assert len(SequencePhases(phases=(qualif, elim)).phases) == 2


# --- E05US025 : plusieurs qualifications dans un même déroulé -------------------------------------
#
# Dérivés du CA de `stories/E05-moteur-phases.md` § E05US025, sur l'exemple de référence du
# commanditaire (arbitrage du 09/08/2026) : 120 archers en 3x20, coupés en une *haute* (rangs 1..60)
# et une *basse* (rangs 61..120) à 3x15. L'invariant d'unicité qu'E05US021 avait posé — « une
# séquence ne porte qu'une phase de qualification » — se décrivait lui-même comme « supposé partout
# et vérifié nulle part », posé pour fermer un bug de lecteurs plutôt que pour dire une règle du tir
# à l'arc. Il disparaît ici. Les effectifs sont divisés par 10 : la règle de séquence ne dépend pas
# de la taille.


def _qualification_sourcee(
    ordre: int, rang_debut: int, rang_fin: int, effectif: int | None = None
) -> Phase:
    """Une qualification d'ordre `ordre`, peuplée d'un prélèvement par rangs dans l'ordre 1."""
    return Phase(
        depart_id=7,
        ordre=ordre,
        type=TypePhase.QUALIFICATION,
        bareme=BaremeQualification.creer(15, 3),
        validation=GrainValidation.fin_de_serie(),
        sources=(SourcePhase(ordre_source=1, rang_debut=rang_debut, rang_fin=rang_fin),),
        effectif=effectif,
    )


def test_deux_qualifications_coexistent_dans_une_sequence() -> None:
    """CA « deux qualifications coexistent » : plus d'anomalie d'unicité.

    Le cas minimal : une qualification de tête, puis une seconde qui prélève dans son classement.
    C'est exactement ce que le commanditaire demandait le 08/08/2026 (« pourquoi on ne peut pas
    faire plusieurs phases de qualification ? »), et qui levait `PlusieursQualifications`.
    """
    qualif = _qualification(effectif=12)
    seconde = _qualification_sourcee(ordre=2, rang_debut=1, rang_fin=6, effectif=6)

    sequence = SequencePhases(phases=(qualif, seconde))

    assert len(sequence.phases) == 2


def test_une_fourche_de_deux_qualifications_est_valide() -> None:
    """CA « fourche » : haute et basse puisent toutes deux dans la même phase amont.

    L'`ordre` d'une phase est **topologique** — il dit qui peut alimenter qui, pas qui passe avant
    qui sur le pas de tir. La haute (ordre 2) et la basse (ordre 3) se jouent en même temps ; leurs
    numéros se suivent uniquement parce que `_anomalies_ordres` exige la suite 1..N.

    Le contrôle de non-recoupement des rangs ne joue **qu'entre les sources d'une même phase** : que
    la haute prenne 1..6 et la basse 7..12 dans le même classement n'est donc pas un conflit, c'est
    une partition.
    """
    qualif = _qualification(effectif=12)
    haute = _qualification_sourcee(ordre=2, rang_debut=1, rang_fin=6, effectif=6)
    basse = _qualification_sourcee(ordre=3, rang_debut=7, rang_fin=12, effectif=6)

    sequence = SequencePhases(phases=(qualif, haute, basse))

    assert [phase.ordre for phase in sequence.phases] == [1, 2, 3]


def test_chaque_qualification_porte_son_propre_bareme() -> None:
    """CA « le barème se règle par qualification » : 3x20 en tête, 3x15 ensuite.

    L'invariant interne d'une qualification (barème **et** grain obligatoires) vaut pour chacune,
    indépendamment. Rien n'oblige deux qualifications d'un même déroulé à tirer le même nombre de
    flèches — c'est même le cœur de l'exemple.
    """
    qualif = _qualification(effectif=12)
    haute = _qualification_sourcee(ordre=2, rang_debut=1, rang_fin=6, effectif=6)

    sequence = SequencePhases(phases=(qualif, haute))

    baremes = [phase.bareme for phase in sequence.phases]
    assert baremes[0] is not None and baremes[0].nb_volees == 20
    assert baremes[1] is not None and baremes[1].nb_volees == 15


def test_une_seconde_qualification_sans_bareme_reste_refusee() -> None:
    """Non-régression : lever l'unicité ne lève pas l'invariant **interne** de la qualification.

    Une qualification porte barème et grain — la seconde comme la première. C'est le contrôle que
    l'US ne doit surtout pas emporter avec l'unicité en retirant `_anomalies_unicite_qualification`
    de la liste des invariants collectifs.
    """
    qualif = _qualification(effectif=12)

    with pytest.raises(PhaseQualificationIncomplete):
        SequencePhases(
            phases=(
                qualif,
                Phase(
                    depart_id=7,
                    ordre=2,
                    type=TypePhase.QUALIFICATION,
                    sources=(SourcePhase(ordre_source=1, rang_debut=1, rang_fin=6),),
                ),
            )
        )


# --- E05US015 : le catalogue de types de phase ---------------------------------------------------


def test_le_catalogue_porte_les_six_types_de_e05us015() -> None:
    """Chacun vient avec son moteur (ADR-0045 §2 : « on n'offre pas un type qu'aucun moteur ne sait
    dérouler ») — sauf l'échauffement, dont l'absence de moteur *est* le contenu."""
    assert TypePhase.ECHAUFFEMENT.value == "echauffement"
    assert TypePhase.BARRAGE.value == "barrage"
    assert TypePhase.POULES.value == "poules"
    assert TypePhase.BIG_SHOOT_OFF.value == "big_shoot_off"
    assert TypePhase.SUISSE.value == "suisse"
    assert TypePhase.COLLINE.value == "colline"


def test_les_types_a_duels_se_valident_en_fin_de_duel() -> None:
    """Ce qui se joue en duels (barrage, poules, suisse, colline) suit l'élimination directe."""
    a_duels = (TypePhase.BARRAGE, TypePhase.POULES, TypePhase.SUISSE, TypePhase.COLLINE)
    for type_phase in a_duels:
        assert grain_par_defaut(type_phase) == GrainValidation.fin_de_duel()


def test_le_big_shoot_off_se_valide_comme_une_serie() -> None:
    """Il fait tirer des **volées en parallèle**, pas des duels : son grain est celui d'une
    série."""
    assert grain_par_defaut(TypePhase.BIG_SHOOT_OFF) == GrainValidation.fin_de_serie()


def test_l_echauffement_n_admet_aucun_grain_de_validation() -> None:
    """« Sans point et sans classement » : il n'attribue rien, donc il n'y a **rien à valider**.

    Un grain déclaré sur un échauffement est une incohérence, pas un réglage inutile toléré.
    """
    with pytest.raises(GrainIncompatibleAvecTypePhase):
        grain_par_defaut(TypePhase.ECHAUFFEMENT)
    with pytest.raises(GrainIncompatibleAvecTypePhase):
        Phase.creer(depart_id=7, ordre=2, type=TypePhase.ECHAUFFEMENT).avec_validation(
            GrainValidation.fin_de_serie()
        )


def test_seul_l_echauffement_ne_produit_pas_de_classement() -> None:
    """La table est écrite **en négatif** pour qu'un type ajouté demain soit classant par défaut :
    l'oubli le plus probable est d'ajouter un vrai format, pas un second échauffement."""
    assert not produit_un_classement(TypePhase.ECHAUFFEMENT)
    for type_phase in TypePhase:
        if type_phase is not TypePhase.ECHAUFFEMENT:
            assert produit_un_classement(type_phase)


def test_on_ne_preleve_pas_de_rangs_dans_un_echauffement() -> None:
    """L'invariant le plus intéressant du lot (CA E05US015) : « les rangs 1 à 32 de l'échauffement »
    ne désigne aucun ensemble, puisque rien n'y est ordonné."""
    with pytest.raises(PhaseSansClassementPrelevee):
        SequencePhases(
            (
                Phase.creer(depart_id=7, ordre=1, type=TypePhase.ECHAUFFEMENT),
                Phase.creer(
                    depart_id=7,
                    ordre=2,
                    type=TypePhase.ELIMINATION_DIRECTE,
                    sources=(SourcePhase.par_rangs(1, 1, 8),),
                ),
            )
        )


def test_succeder_a_un_echauffement_par_le_reste_est_licite() -> None:
    """« Les mêmes archers, sans ordre » est la seule succession possible — et elle doit marcher,
    sans quoi une phase d'échauffement serait un cul-de-sac dans le déroulé."""
    sequence = SequencePhases(
        (
            Phase.creer(depart_id=7, ordre=1, type=TypePhase.ECHAUFFEMENT),
            Phase(
                depart_id=7,
                ordre=2,
                type=TypePhase.QUALIFICATION,
                sources=(SourcePhase.le_reste(1),),
                bareme=BaremeQualification(nb_volees=5, nb_fleches_par_volee=3),
                validation=GrainValidation.fin_de_serie(),
            ),
        )
    )
    assert sequence.phases[1].sources[0].ordre_source == 1


def test_preleve_des_rangs_dans_un_type_classant_reste_licite() -> None:
    """Le nouveau contrôle ne doit pas déborder sur les types qui, eux, classent bien."""
    sequence = SequencePhases(
        (
            Phase.creer(depart_id=7, ordre=1, type=TypePhase.POULES, effectif=16),
            Phase.creer(
                depart_id=7,
                ordre=2,
                type=TypePhase.ELIMINATION_DIRECTE,
                sources=(SourcePhase.par_rangs(1, 1, 8),),
            ),
        )
    )
    assert sequence.phases[1].sources[0].rang_fin == 8


def test_on_ne_preleve_pas_non_plus_une_issue_de_tour_dans_un_echauffement() -> None:
    """⚠️ **La nature que le premier jet laissait passer.**

    Le garde-fou ne refusait que `RANGS` — or « les gagnants du tour 1 de l'échauffement » est
    exactement aussi vide : un échauffement n'a ni tour ni duel. Le trou était d'autant plus
    invisible que les deux tests encadrants couvraient `RANGS` (refusé) et `RESTE` (accepté),
    laissant la troisième nature dans l'angle mort — le patron du « cas limite jamais exercé ».
    """
    with pytest.raises(PhaseSansClassementPrelevee):
        SequencePhases(
            (
                Phase.creer(depart_id=7, ordre=1, type=TypePhase.ECHAUFFEMENT),
                Phase.creer(
                    depart_id=7,
                    ordre=2,
                    type=TypePhase.ELIMINATION_DIRECTE,
                    sources=(SourcePhase.par_issue_de_tour(1, tour=1, issue=IssueTour.GAGNANTS),),
                ),
            )
        )


def test_un_seuil_de_barrage_nul_est_refuse() -> None:
    """« Aucun barrage » se dit en ne réglant rien ; un 0 accepté laisserait croire à l'organisateur
    qu'il a désactivé une option qu'il vient en fait de régler (E06US003)."""
    with pytest.raises(SeuilDeBarrageInvalide):
        Phase.creer(1, ordre=2, type=TypePhase.ELIMINATION_DIRECTE, barrage_jusqu_au=0)


def test_un_seuil_de_barrage_positif_est_conserve() -> None:
    phase = Phase.creer(1, ordre=2, type=TypePhase.ELIMINATION_DIRECTE, barrage_jusqu_au=8)
    assert phase.barrage_jusqu_au == 8
