"""Tests unitaires de la **projection d'un déroulé** (E01US024) — domaine pur, sans base.

Écrits **depuis le CA** de `stories/E01-configuration.md` (règle 9), avant l'implémentation. Les
puces couvertes, dans l'ordre :

- « **le schéma à braquets** » — chaque bloc répond à quatre questions : *qui est là* (combien, et
  quelle tranche de rangs), *ce qu'on leur demande*, *où ils vont après* (une flèche par sortie),
  *combien de tours* ; « plusieurs flèches peuvent **entrer** dans un bloc » ;
- « **les braquets** » — à chaque tour, les perdants forment une tranche de rangs (Règle R de
  `moteur-placement-lucky-loser.md`) ;
- « **effectif simulé** » — sans effectif un format reste abstrait, avec il devient calculable ;
- « **le schéma EST le contrôle de validité** » — un archer sans destination est un trou visible ;
- « **l'ajustement d'effectif** » — simuler à 120 puis à 82 sans retoucher le format.

La ligne de partage des gravités, tranchée dans cette US et consignée à l'ADR-0063 : **ce qui est
faux quel que soit l'effectif bloque ; ce qui n'est faux qu'à *cet* effectif avertit.**
"""

from __future__ import annotations

from domain.anomalie import Gravite
from domain.bareme import BaremeQualification
from domain.deroule import projeter
from domain.format_tournoi import ModelePhase
from domain.phase import IssueTour, NatureSource, SourcePhase, TypePhase
from domain.poule import ReglageDePoules


def _qualification(ordre: int = 1, effectif: int | None = None) -> ModelePhase:
    return ModelePhase.qualification(
        BaremeQualification.preset_ffta_18m(), ordre=ordre, effectif=effectif
    )


def _tableau(
    ordre: int, sources: tuple[SourcePhase, ...], effectif: int | None = None
) -> ModelePhase:
    return ModelePhase(
        ordre=ordre, type=TypePhase.ELIMINATION_DIRECTE, sources=sources, effectif=effectif
    )


def _codes(anomalies: object) -> list[str]:
    assert isinstance(anomalies, tuple)
    return [anomalie.code for anomalie in anomalies]


# --- CA « effectif simulé » : sans N, le format reste abstrait ; avec N, il devient calculable ----


def test_sans_effectif_le_premier_bloc_ne_sait_pas_combien_darchers_il_accueille() -> None:
    projection = projeter([_qualification()])

    assert projection.effectif is None
    assert projection.blocs[0].effectif is None
    assert projection.blocs[0].tranche is None


def test_avec_effectif_le_premier_bloc_accueille_tout_le_monde() -> None:
    projection = projeter([_qualification()], effectif=120)

    bloc = projection.blocs[0]
    assert bloc.effectif == 120
    assert bloc.tranche == (1, 120)


def test_un_effectif_declare_sur_la_phase_prime_sur_leffectif_simule() -> None:
    """Une phase qui *déclare* son effectif ne s'étire pas à N — c'est une contrainte du format."""
    projection = projeter([_qualification(effectif=60)], effectif=120)

    assert projection.blocs[0].effectif == 60


# --- CA « le schéma à braquets » : qui est là, ce qu'on demande, où ils vont, combien de tours ----


def test_un_bloc_porte_ce_quon_demande_aux_archers() -> None:
    projection = projeter([_qualification()], effectif=120)

    bloc = projection.blocs[0]
    assert bloc.nb_volees == 20
    assert bloc.nb_fleches_par_volee == 3


def test_une_sortie_par_prelevement_aval_et_une_entree_par_prelevement_amont() -> None:
    """« Une flèche par sortie » — et le même prélèvement est l'entrée du bloc d'en face."""
    etapes = [_qualification(), _tableau(2, (SourcePhase.par_rangs(1, 1, 32),))]

    projection = projeter(etapes, effectif=120)

    qualif, tableau = projection.blocs
    assert len(qualif.sorties) == 1
    assert qualif.sorties[0].ordre_cible == 2
    assert qualif.sorties[0].effectif == 32
    assert len(tableau.entrees) == 1
    assert tableau.entrees[0].ordre_source == 1
    assert tableau.entrees[0].effectif == 32


def test_plusieurs_fleches_peuvent_entrer_dans_un_bloc() -> None:
    """Le cas du commanditaire : « les demi-finalistes du principal **et** le gagnant du
    secondaire »."""
    etapes = [
        _qualification(),
        _tableau(2, (SourcePhase.par_rangs(1, 1, 32),)),
        _tableau(3, (SourcePhase.par_rangs(1, 33, 64),)),
        _tableau(
            4,
            (
                SourcePhase.par_issue_de_tour(2, tour=4, issue=IssueTour.GAGNANTS),
                SourcePhase.par_issue_de_tour(3, tour=5, issue=IssueTour.GAGNANTS),
            ),
        ),
    ]

    projection = projeter(etapes, effectif=120)

    finale = projection.blocs[3]
    assert len(finale.entrees) == 2
    assert {flux.ordre_source for flux in finale.entrees} == {2, 3}


def test_le_bloc_dune_phase_alimentee_par_rangs_porte_sa_tranche() -> None:
    """« Qui est là » = combien **et quelle tranche de rangs** — c'est le braquet du bloc."""
    etapes = [_qualification(), _tableau(2, (SourcePhase.par_rangs(1, 33, 64),))]

    projection = projeter(etapes, effectif=120)

    assert projection.blocs[1].tranche == (33, 64)
    assert projection.blocs[1].effectif == 32


# --- CA « les braquets » : Règle R rendue visible -------------------------------------------------


def test_un_tableau_de_32_se_deroule_en_cinq_tours() -> None:
    etapes = [_qualification(), _tableau(2, (SourcePhase.par_rangs(1, 1, 32),))]

    projection = projeter(etapes, effectif=120)

    assert len(projection.blocs[1].tours) == 5


def test_a_chaque_tour_les_perdants_forment_la_moitie_basse_de_la_plage() -> None:
    """Règle R : les perdants du tour *t* prennent la tranche de rangs basse encore ouverte."""
    etapes = [_qualification(), _tableau(2, (SourcePhase.par_rangs(1, 1, 32),))]

    tours = projeter(etapes, effectif=120).blocs[1].tours

    assert tours[0].plage_perdants == (17, 32)
    assert tours[0].plage_gagnants == (1, 16)
    assert tours[1].plage_perdants == (9, 16)
    assert tours[2].plage_perdants == (5, 8)
    assert tours[3].plage_perdants == (3, 4)
    assert tours[4].plage_perdants == (2, 2)
    assert tours[4].plage_gagnants == (1, 1)


def test_les_braquets_sont_decales_quand_le_tableau_part_dun_rang_intermediaire() -> None:
    """Un tableau des rangs 33-64 rend des rangs 33-64, pas 1-32 : le braquet est **absolu**."""
    etapes = [_qualification(), _tableau(2, (SourcePhase.par_rangs(1, 33, 64),))]

    tours = projeter(etapes, effectif=120).blocs[1].tours

    assert tours[0].plage_gagnants == (33, 48)
    assert tours[0].plage_perdants == (49, 64)


def test_un_tableau_incomplet_joue_moins_de_duels_au_premier_tour_les_byes() -> None:
    """24 duellistes dans un tableau de 32 : 8 duels au tour 1, 8 exemptés — puis 8 duels."""
    etapes = [_qualification(), _tableau(2, (SourcePhase.par_rangs(1, 1, 24),))]

    tours = projeter(etapes, effectif=120).blocs[1].tours

    assert [tour.duels for tour in tours] == [8, 8, 4, 2, 1]
    assert sum(tour.duels for tour in tours) == 23


def test_un_bloc_sans_effectif_connu_ne_pretend_pas_compter_ses_tours() -> None:
    etapes = [_qualification(), _tableau(2, (SourcePhase.le_reste(1),))]

    projection = projeter(etapes)

    assert projection.blocs[1].effectif is None
    assert projection.blocs[1].tours == ()


# --- CA « le schéma EST le contrôle de validité » : le trou se voit ------------------------------


def test_les_archers_quaucune_phase_ne_reprend_sont_comptes_sans_suite() -> None:
    """120 qualifiés, 32 partent au tableau : les 88 autres n'ont pas de suite — c'est visible."""
    etapes = [_qualification(), _tableau(2, (SourcePhase.par_rangs(1, 1, 32),))]

    projection = projeter(etapes, effectif=120)

    assert projection.blocs[0].sans_suite == 88
    assert projection.blocs[1].sans_suite == 32


def test_une_phase_que_personne_natteint_est_une_anomalie_visible() -> None:
    """Un bloc vide est un trou dans le dessin : il s'affiche, et il s'explique."""
    etapes = [_qualification(effectif=16), _tableau(2, (SourcePhase.par_rangs(1, 17, 32),))]

    projection = projeter(etapes, effectif=16)

    assert projection.blocs[1].effectif == 0
    assert "phase_sans_participant" in _codes(projection.blocs[1].anomalies)


def test_une_anomalie_est_rattachee_au_bloc_quelle_concerne() -> None:
    """« Pas un message d'erreur abstrait » : l'anomalie sait de quelle phase elle parle."""
    etapes = [_qualification(effectif=16), _tableau(2, (SourcePhase.par_rangs(1, 17, 32),))]

    projection = projeter(etapes, effectif=16)

    ordres = {anomalie.ordre for anomalie in projection.anomalies}
    assert ordres == {2}


# --- CA « l'ajustement d'effectif » : 120 puis 82, sans retoucher le format ----------------------


def _format_relatif() -> list[ModelePhase]:
    """Qualification, tableau des 32 premiers, et « le reste » en tableau secondaire."""
    return [
        _qualification(),
        _tableau(2, (SourcePhase.par_rangs(1, 1, 32),)),
        _tableau(3, (SourcePhase.par_rangs(1, 33, None),)),
    ]


def test_un_format_a_plage_relative_sajuste_a_120() -> None:
    projection = projeter(_format_relatif(), effectif=120)

    assert projection.blocs[2].effectif == 88
    assert projection.blocs[2].tranche == (33, 120)
    assert projection.est_applicable


def test_le_meme_format_sajuste_a_82_sans_etre_retouche() -> None:
    projection = projeter(_format_relatif(), effectif=82)

    assert projection.blocs[2].effectif == 50
    assert projection.blocs[2].tranche == (33, 82)
    assert projection.est_applicable


def test_une_plage_fermee_qui_deborde_a_effectif_reduit_avertit_sans_bloquer() -> None:
    """« Les rangs 33 à 120 » sur 82 inscrits : le format n'est pas faux — il ne tient pas ici."""
    etapes = [_qualification(), _tableau(2, (SourcePhase.par_rangs(1, 33, 120),))]

    projection = projeter(etapes, effectif=82)

    assert "rangs_source_inexistants" in _codes(projection.blocs[1].anomalies)
    assert all(
        anomalie.gravite is Gravite.AVERTISSEMENT
        for anomalie in projection.blocs[1].anomalies
        if anomalie.code == "rangs_source_inexistants"
    )
    assert projection.est_applicable
    assert projection.blocs[1].effectif == 50


def test_une_incoherence_structurelle_bloque_quel_que_soit_leffectif() -> None:
    """Une source postérieure est fausse à 120 comme à 82 : elle interdit l'application."""
    etapes = [_qualification(), _tableau(2, (SourcePhase.par_rangs(3, 1, 8),)), _tableau(3, ())]

    projection = projeter(etapes, effectif=120)

    assert "source_apres_phase" in _codes(projection.anomalies)
    assert not projection.est_applicable


def test_une_qualification_sans_bareme_bloque() -> None:
    """Invariant d'étape (`verifier_coherence_etape`) : il remonte comme anomalie bloquante."""
    etapes = [ModelePhase(ordre=1, type=TypePhase.QUALIFICATION)]

    projection = projeter(etapes, effectif=120)

    assert "phase_qualification_incomplete" in _codes(projection.anomalies)
    assert not projection.est_applicable


def test_un_format_vide_ne_projette_aucun_bloc_et_reste_inapplicable() -> None:
    projection = projeter([], effectif=120)

    assert projection.blocs == ()
    assert not projection.est_applicable


# --- Résolution des natures de prélèvement -------------------------------------------------------


def test_le_reste_prend_ce_quaucune_autre_source_na_pris() -> None:
    etapes = [
        _qualification(),
        _tableau(2, (SourcePhase.par_rangs(1, 1, 32),)),
        _tableau(3, (SourcePhase.le_reste(1),)),
    ]

    projection = projeter(etapes, effectif=120)

    assert projection.blocs[2].effectif == 88
    assert projection.blocs[2].entrees[0].nature is NatureSource.RESTE


def test_les_gagnants_dun_tour_se_comptent_depuis_la_taille_du_tableau() -> None:
    """32 duellistes : 16 gagnants au tour 1, 8 au tour 2 — et 16 perdants au tour 1."""
    etapes = [
        _qualification(),
        _tableau(2, (SourcePhase.par_rangs(1, 1, 32),)),
        _tableau(3, (SourcePhase.par_issue_de_tour(2, tour=2, issue=IssueTour.GAGNANTS),)),
        _tableau(4, (SourcePhase.par_issue_de_tour(2, tour=1, issue=IssueTour.PERDANTS),)),
    ]

    projection = projeter(etapes, effectif=120)

    assert projection.blocs[2].effectif == 8
    assert projection.blocs[3].effectif == 16


# --- Trous fermés en revue (E01US024) -----------------------------------------------------------


def test_une_phase_qui_ne_dit_pas_dou_viennent_ses_archers_est_signalee_sans_bloquer() -> None:
    """Le bloc se **montre**, mais le format reste applicable — et c'est délibéré.

    Le schéma dessinait un rectangle isolé « effectif inconnu / suite inconnue » sous un verdict
    « tient debout » : il fallait le signaler. Mais le **bloquer** serait une régression, relevée en
    revue : `docs/fonctionnel/E05US015.md` décrit « échauffement puis élimination directe **sans
    source** » comme un déroulé accepté, et le peuplement ensemence de toute façon tous les archers
    en lice (`# DETTE-028`) — « personne ne peut l'atteindre » serait faux.
    """
    etapes = [_qualification(), _tableau(2, ())]

    projection = projeter(etapes, effectif=120)

    assert "phase_sans_source" in _codes(projection.anomalies)
    assert projection.est_applicable
    assert all(
        anomalie.gravite is Gravite.AVERTISSEMENT
        for anomalie in projection.anomalies
        if anomalie.code == "phase_sans_source"
    )


def test_un_deroule_echauffement_puis_tableau_reste_applicable() -> None:
    """Non-régression explicite du déroulé d'E05US015 : il ne doit pas cesser de fonctionner."""
    etapes = [
        ModelePhase(ordre=1, type=TypePhase.ECHAUFFEMENT),
        ModelePhase(ordre=2, type=TypePhase.ELIMINATION_DIRECTE),
    ]

    assert projeter(etapes, effectif=32).est_applicable


def test_la_premiere_phase_na_pas_besoin_de_source() -> None:
    """Elle se peuple des inscrits — son absence de prélèvement est le cas normal."""
    assert projeter([_qualification()], effectif=120).est_applicable


def test_deux_phases_avales_qui_se_disputent_les_memes_rangs_sont_signalees() -> None:
    """« Rangs 1 à 32 » puis « rangs 32 à 64 » — l'erreur de borne d'un rang.

    `_anomalies_recoupements` compare les prélèvements **d'une même phase cible** : deux phases
    avales différentes puisant dans la même source ne se croisaient jamais, et `max(0, …)` écrasait
    le négatif de `sans_suite`. Le format passait au vert.
    """
    etapes = [
        _qualification(),
        _tableau(2, (SourcePhase.par_rangs(1, 1, 32),)),
        _tableau(3, (SourcePhase.par_rangs(1, 32, 64),)),
    ]

    projection = projeter(etapes, effectif=64)

    assert "sources_qui_se_recoupent" in _codes(projection.anomalies)
    assert projection.blocs[0].sans_suite == -1


def test_un_effectif_declare_deja_juge_par_le_domaine_nest_pas_signale_deux_fois() -> None:
    """Prélèvements tous dénombrables : `_anomalies_somme` tranche seule, en bloquant.

    Sans cette garde, le même défaut remontait deux fois — une bloquante et un avertissement, même
    code, messages quasi identiques.
    """
    etapes = [
        _qualification(),
        ModelePhase(
            ordre=2,
            type=TypePhase.ELIMINATION_DIRECTE,
            sources=(SourcePhase.par_rangs(1, 1, 16),),
            effectif=32,
        ),
    ]

    codes = [anomalie.code for anomalie in projeter(etapes, effectif=120).anomalies]

    assert codes.count("effectif_incompatible") == 1


def test_un_effectif_declare_que_les_prelevements_ne_remplissent_pas_est_signale() -> None:
    """Une flèche « 120 » entrant dans un bloc « 16 archers » ne doit pas passer au vert.

    Le contrôle de somme du domaine abandonne l'égalité dès qu'un prélèvement est relatif ; la
    projection, elle, sait le résoudre — conjoncturel, donc avertissement.
    """
    etapes = [
        _qualification(),
        ModelePhase(
            ordre=2,
            type=TypePhase.ELIMINATION_DIRECTE,
            sources=(SourcePhase.le_reste(1),),
            effectif=16,
        ),
    ]

    projection = projeter(etapes, effectif=120)

    assert "effectif_incompatible" in _codes(projection.blocs[1].anomalies)
    assert projection.est_applicable


# --- CA E05US023 : le choc de poule est signalé à l'atelier, jamais corrigé en douce -------------


def _poules(
    ordre: int,
    sources: tuple[SourcePhase, ...] = (),
    effectif: int | None = None,
    taille_visee: int = 4,
) -> ModelePhase:
    """Une phase de poules. `effectif` et `taille_visee` fixent **P**, le nombre de poules.

    Les deux sont paramétrables depuis le correctif de revue : c'est P — et sa parité — qui décide
    si le serpent peut réunir deux membres d'une même poule, et sans lui le signal ne peut rien
    prouver.
    """
    return ModelePhase(
        ordre=ordre,
        type=TypePhase.POULES,
        sources=sources,
        effectif=effectif,
        poules=ReglageDePoules(taille_visee=taille_visee, nb_qualifies=4),
    )


def test_un_tableau_nourri_par_des_poules_hors_puissance_de_deux_avertit() -> None:
    """CA E05US023 — « À **signaler à l'atelier** plutôt qu'à corriger en douce ».

    L'exemple est celui du CA, verbatim : **3 poules x 4 qualifiés = 12 archers**, qui produit la
    paire (rang 7, rang 10), tous deux de la poule 1. Les byes décalent les appariements dès que
    l'effectif du tableau n'est pas une puissance de 2 ; le serpent ne sépare plus les membres d'un
    même groupe.

    Avertissement, **jamais bloquant** : le format reste applicable. Corriger demanderait une
    politique de croisement, donc une règle métier que personne n'a demandée.
    """
    etapes = [
        _qualification(),
        _poules(2, (SourcePhase.par_rangs(1, 1, 12),)),
        _tableau(3, (SourcePhase.par_rangs(2, 1, 12),)),
    ]

    projection = projeter(etapes, effectif=120)

    assert "choc_de_poule_possible" in _codes(projection.blocs[2].anomalies)
    assert projection.est_applicable


def test_un_tableau_nourri_par_un_nombre_pair_de_poules_sans_bye_navertit_pas() -> None:
    """CA E05US023, l'autre versant : « le serpent sépare naturellement » — mais **à P pair**.

    Le membre `k` d'une poule occupe les rangs `k, k+P, k+2P…`, et le serpent apparie `r` contre
    `N+1-r`. Deux membres se croisent donc quand `2r ≡ N+1 (mod P)` a une solution. À **P pair** et
    sans bye, il n'y en a pas : 16 archers en 4 poules ne produisent aucun choc, et avertir ici
    serait du bruit — le bruit est ce qui fait ignorer les vrais signaux.
    """
    etapes = [
        _qualification(),
        _poules(2, (SourcePhase.par_rangs(1, 1, 16),), effectif=16, taille_visee=4),  # P = 4
        _tableau(3, (SourcePhase.par_rangs(2, 1, 16),)),
    ]

    assert "choc_de_poule_possible" not in _codes(projeter(etapes, effectif=120).anomalies)


def test_un_nombre_impair_de_poules_avertit_meme_a_effectif_puissance_de_deux() -> None:
    """⚠️ Le contre-exemple qui invalide l'oracle « puissance de 2 ⇒ pas de choc ».

    24 archers en poules de 8 font **3** poules ; un tableau de 16 y prélève les rangs 1 à 16. Le
    serpent apparie alors (1, 16), (4, 13) et (7, 10) — **trois** paires de la poule 1, dont le n° 1
    du tableau contre un membre de son propre groupe **en match d'ouverture**. L'effectif est
    pourtant une puissance de 2, donc l'ancienne règle ne disait rien.

    Le test est écrit depuis le CA (« signaler à l'atelier plutôt que corriger en douce ») et non
    depuis le code : c'est l'arithmétique du serpent qui l'établit, vérifiable à la main.
    """
    etapes = [
        _qualification(),
        _poules(2, (SourcePhase.par_rangs(1, 1, 24),), effectif=24, taille_visee=8),  # P = 3
        _tableau(3, (SourcePhase.par_rangs(2, 1, 16),)),
    ]

    assert "choc_de_poule_possible" in _codes(projeter(etapes, effectif=120).anomalies)


def test_un_nombre_de_poules_indeterminable_avertit_plutot_que_de_se_taire() -> None:
    """Sans effectif déclaré à l'amont, on ne peut pas prouver l'innocuité — donc on signale.

    Un avertissement de trop coûte une lecture ; un avertissement manquant coûte un tournoi mal
    apparié. Le CA demande de ne pas mentir, pas d'être fin.
    """
    etapes = [
        _qualification(),
        _poules(2, (SourcePhase.par_rangs(1, 1, 16),)),  # effectif non déclaré → P inconnu
        _tableau(3, (SourcePhase.par_rangs(2, 1, 16),)),
    ]

    assert "choc_de_poule_possible" in _codes(projeter(etapes, effectif=120).anomalies)


def test_un_tableau_nourri_par_une_qualification_navertit_jamais() -> None:
    """Le signal vise le **format poules**, pas l'imparité d'un tableau.

    Un tableau de 12 issu d'une qualification a les mêmes byes, et aucun choc de poule possible :
    il n'y a pas de poule. Sans cette borne, l'avertissement se déclencherait sur la majorité des
    déroulés existants et ne dirait plus rien.
    """
    etapes = [_qualification(), _tableau(2, (SourcePhase.par_rangs(1, 1, 12),))]

    assert "choc_de_poule_possible" not in _codes(projeter(etapes, effectif=120).anomalies)


def test_la_phase_de_poules_elle_meme_nest_pas_signalee() -> None:
    """Le choc est un défaut d'**appariement de tableau** : il se colle au bloc qui apparie.

    Le rattacher à la phase de poules le montrerait sur le bloc amont, où l'organisateur n'a rien à
    corriger — c'est le nombre de qualifiés ou la taille du tableau qu'il ajusterait, pas la poule.
    """
    etapes = [
        _qualification(),
        _poules(2, (SourcePhase.par_rangs(1, 1, 12),)),
        _tableau(3, (SourcePhase.par_rangs(2, 1, 12),)),
    ]

    projection = projeter(etapes, effectif=120)

    assert "choc_de_poule_possible" not in _codes(projection.blocs[1].anomalies)
    assert [
        anomalie.ordre
        for anomalie in projection.anomalies
        if anomalie.code == "choc_de_poule_possible"
    ] == [3]
