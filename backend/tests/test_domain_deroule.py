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
from domain.poule import ModeDeComposition, ReglageDePoules


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
    paire (rang 7, rang 10), tous deux de la poule 1.

    ⚠️ La *raison* n'est pas celle que le CA avançait. Ce ne sont pas les byes : à nombre **pair**
    de poules, l'effectif a beau ne pas être une puissance de 2, le serpent sépare toujours (le
    tableau apparie `r` et `M+1-r` avec `M` pair, donc l'écart entre deux adversaires est impair et
    n'est jamais divisible par un `P` pair). C'est l'**imparité de `P`** qui casse la séparation —
    ici `P = 3`. Le cas du CA reste vrai, son explication était fausse.

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


def test_une_phase_de_poules_non_reglee_avertit_plutot_que_de_se_taire() -> None:
    """Sans réglage, le nombre de poules ne se calcule pas : on ne peut pas prouver l'innocuité.

    Un avertissement de trop coûte une lecture ; un avertissement manquant coûte un tournoi mal
    apparié. Le CA demande de ne pas mentir, pas d'être fin.

    ⚠️ L'effectif **déclaré**, lui, ne manque presque jamais : la projection résout l'effectif de
    chaque phase et le signal lit désormais ce résolu. Une version antérieure lisait le seul
    déclaré — champ facultatif que le formulaire laisse vide par défaut —, si bien qu'elle
    s'allumait sur **tout** tableau nourri par des poules. Un signal permanent est ce qui fait
    ignorer les vrais.
    """
    etapes = [
        _qualification(),
        ModelePhase(ordre=2, type=TypePhase.POULES, sources=(SourcePhase.par_rangs(1, 1, 16),)),
        _tableau(3, (SourcePhase.par_rangs(2, 1, 16),)),
    ]

    assert "choc_de_poule_possible" in _codes(projeter(etapes, effectif=120).anomalies)


def test_le_departage_inter_poules_rend_l_appariement_indemontrable() -> None:
    """⚠️ Le réglage qui invalide l'arithmétique — et que le produit **recommande**.

    `classement_de_poules` trie chaque bloc de niveau indépendamment quand le départage est actif :
    la position d'une poule change alors d'un bloc à l'autre, et « le membre `k` occupe les rangs
    `k, k+P, …` » cesse d'être vrai. Or c'est précisément le geste que l'outil conseille quand un
    prélèvement coupe un bloc (ADR-0081). Le signal doit donc s'allumer **même à `P` pair**, où
    l'arithmétique conclurait à tort à l'innocuité.
    """
    etapes = [
        _qualification(),
        _poules(2, (SourcePhase.par_rangs(1, 1, 24),), effectif=24, taille_visee=4),  # P = 6, pair
        _tableau(3, (SourcePhase.par_rangs(2, 1, 16),)),
    ]
    sans_departage = _codes(projeter(etapes, effectif=120).anomalies)
    assert "choc_de_poule_possible" not in sans_departage

    etapes[1] = ModelePhase(
        ordre=2,
        type=TypePhase.POULES,
        sources=(SourcePhase.par_rangs(1, 1, 24),),
        effectif=24,
        poules=ReglageDePoules(taille_visee=4, nb_qualifies=4, departage_inter_poules=True),
    )

    assert "choc_de_poule_possible" in _codes(projeter(etapes, effectif=120).anomalies)


def test_un_nombre_impair_de_poules_ne_suffit_pas_si_le_prelevement_est_trop_court() -> None:
    """L'imparité ne suffit pas : encore faut-il que la paire fautive tombe dans le prélèvement.

    9 poules et un tableau de 8 : les 8 têtes viennent de 8 poules distinctes, aucun choc n'est
    possible. La version précédente avertissait — elle testait `P` impair sans vérifier que la
    solution de `2r ≡ M+1 (mod P)` tombe dans `[1, N]`. Un signal qui s'allume sur un format sain
    est un signal qu'on apprend à ignorer.
    """
    etapes = [
        _qualification(),
        _poules(2, (SourcePhase.par_rangs(1, 1, 36),), effectif=36, taille_visee=4),  # P = 9
        _tableau(3, (SourcePhase.par_rangs(2, 1, 8),)),
    ]

    assert "choc_de_poule_possible" not in _codes(projeter(etapes, effectif=120).anomalies)


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


# --- E05US029 : « averti s'il compose une 2ᵉ phase de poules au serpent » -------------------------
#
# Tests écrits depuis le CA, avant l'implémentation (règle 9). L'oracle est la puce « **CA —
# l'organisateur est averti s'il compose une 2ᵉ phase de poules au serpent** » de
# `stories/E05-moteur-phases.md` § E05US029, et l'arbitrage du cadrage du 21/08/2026 qui a tranché
# la **fermeté** : refus, levé par une dérogation explicite — et non simple bandeau.


def _poules_de_niveau(
    ordre: int,
    sources: tuple[SourcePhase, ...] = (),
    effectif: int | None = None,
    taille_visee: int = 4,
) -> ModelePhase:
    """Une phase de poules composée **par niveau** — le mode que cette US ouvre."""
    return ModelePhase(
        ordre=ordre,
        type=TypePhase.POULES,
        sources=sources,
        effectif=effectif,
        poules=ReglageDePoules(
            taille_visee=taille_visee, nb_qualifies=4, mode=ModeDeComposition.PAR_NIVEAU
        ),
    )


def test_une_deuxieme_phase_de_poules_au_serpent_est_refusee() -> None:
    """Le cas où le défaut est presque sûrement le mauvais choix.

    Une phase de poules qui prélève dans une **autre phase de poules** dispose déjà des niveaux :
    les composer au serpent éparpillerait les six têtes dans les six groupes, soit l'inverse exact
    de ce que l'organisateur croit régler. Le refus est **bloquant** — arbitrage du cadrage — parce
    que le défaut ne se voit qu'en salle, une fois les groupes affichés.
    """
    etapes = [
        _qualification(),
        _poules(2, (SourcePhase.par_rangs(1, 1, 36),), effectif=36, taille_visee=6),
        _poules(3, (SourcePhase.par_rangs(2, 1, 36),), effectif=36, taille_visee=6),
    ]

    projection = projeter(etapes, effectif=120)

    assert "serpent_apres_des_poules" in _codes(projection.anomalies)
    assert not projection.est_applicable


def test_le_refus_se_colle_a_la_phase_mal_reglee() -> None:
    """C'est la phase **avale** que l'organisateur doit retoucher, pas sa source : le mode est un
    réglage de la phase qui compose. L'accrocher à la phase 2 enverrait corriger au mauvais
    endroit — le même soin que `choc_de_poule_possible` prend déjà."""
    etapes = [
        _qualification(),
        _poules(2, (SourcePhase.par_rangs(1, 1, 36),), effectif=36, taille_visee=6),
        _poules(3, (SourcePhase.par_rangs(2, 1, 36),), effectif=36, taille_visee=6),
    ]

    projection = projeter(etapes, effectif=120)

    assert [
        anomalie.ordre
        for anomalie in projection.anomalies
        if anomalie.code == "serpent_apres_des_poules"
    ] == [3]


def test_la_derogation_leve_le_refus() -> None:
    """« Refus avec dérogation à cocher » : le serpent en 2ᵉ phase reste **légitime** quand il est
    voulu — rebrasser volontairement les groupes est un choix d'organisateur, pas une faute.

    Ce que la dérogation achète n'est pas le droit de se tromper : c'est la preuve que le choix a
    été posé. Sans elle, on ne peut pas distinguer « voulu » de « pas vu ».
    """
    etapes = [
        _qualification(),
        _poules(2, (SourcePhase.par_rangs(1, 1, 36),), effectif=36, taille_visee=6),
        ModelePhase(
            ordre=3,
            type=TypePhase.POULES,
            sources=(SourcePhase.par_rangs(2, 1, 36),),
            effectif=36,
            poules=ReglageDePoules(taille_visee=6, nb_qualifies=4, serpent_assume=True),
        ),
    ]

    projection = projeter(etapes, effectif=120)

    assert "serpent_apres_des_poules" not in _codes(projection.anomalies)
    assert projection.est_applicable


def test_des_poules_de_niveau_ne_declenchent_aucun_refus() -> None:
    """Le chemin nominal du format visé : la 2ᵉ phase est composée **par niveau**, donc le
    garde-fou n'a rien à dire. C'est même tout son objet — il pousse vers ce réglage-là."""
    etapes = [
        _qualification(),
        _poules(2, (SourcePhase.par_rangs(1, 1, 36),), effectif=36, taille_visee=6),
        _poules_de_niveau(3, (SourcePhase.par_rangs(2, 1, 36),), effectif=36, taille_visee=6),
    ]

    projection = projeter(etapes, effectif=120)

    assert "serpent_apres_des_poules" not in _codes(projection.anomalies)
    assert projection.est_applicable


def test_une_premiere_phase_de_poules_au_serpent_ne_declenche_rien() -> None:
    """⚠️ Le prédicat porte sur la **source**, pas sur la position dans le déroulé.

    Le serpent est *juste* quand personne ne connaît encore les niveaux — c'est l'arbitrage du
    31/07/2026 qui l'a mis par défaut. Une phase de poules nourrie par la qualification est dans ce
    cas, qu'elle soit la 1ʳᵉ ou la 5ᵉ étape du déroulé : ce qui compte est d'où viennent les
    niveaux, pas le numéro d'ordre.
    """
    etapes = [
        _qualification(),
        _poules(2, (SourcePhase.par_rangs(1, 1, 36),), effectif=36, taille_visee=6),
    ]

    assert "serpent_apres_des_poules" not in _codes(projeter(etapes, effectif=120).anomalies)


def test_une_phase_de_poules_sans_source_declaree_ne_declenche_rien() -> None:
    """Le même prédicat, sur le cas qui aurait pu passer au travers d'une lecture « 2ᵉ phase de
    poules du déroulé ».

    Sans source déclarée, une phase est alimentée par le classement du **départ** (ADR-0068) — donc
    par la qualification, et non par les poules qui la précèdent dans le déroulé. Les niveaux n'en
    viennent pas : le serpent y reste légitime, et refuser serait un faux positif systématique.
    """
    etapes = [
        _qualification(),
        _poules(2, (SourcePhase.par_rangs(1, 1, 36),), effectif=36, taille_visee=6),
        _poules(3, effectif=36, taille_visee=6),
    ]

    assert "serpent_apres_des_poules" not in _codes(projeter(etapes, effectif=120).anomalies)
