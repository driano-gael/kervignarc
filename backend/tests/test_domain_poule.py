"""Tests du moteur de **poules** (E05US015).

**Dérivés du CA**, pas du code (règle 9) : la source est la règle donnée verbatim par le
commanditaire le 31/07/2026 (`stories/E05-moteur-phases.md`, CA « poules », reprise au référentiel
§10.1) et les arbitrages tranchés avec lui au cadrage — composition serpent, round-robin complet par
défaut, barème 3/1/0, nombre de qualifiés non pré-rempli.

Chaque test nomme le fragment de règle qu'il éprouve ; un test qui ne saurait pas le citer serait le
signe qu'il décrit l'implémentation.
"""

from __future__ import annotations

import pytest

from domain.erreurs import BarrageRequisAvantQualification, ConfigurationPouleInvalide
from domain.participant import Participant
from domain.poule import (
    BaremePoule,
    ConfigurationPoules,
    Poule,
    ResultatRencontre,
    classement_de_poule,
    composer_poules,
    qualifies_de_poule,
    rencontres_de_poule,
)


def archers(nombre: int) -> list[Participant]:
    """`nombre` participants individuels, **ordonnés par rang** de la phase source (1 = premier)."""
    return [Participant.individuel(rang) for rang in range(1, nombre + 1)]


# --- composition : « les archers sont regroupés en poules » --------------------------------------


def test_composition_serpent_equilibre_les_poules() -> None:
    """Serpent (arbitrage 31/07) : 1→A, 2→B, 3→C puis **retour** 4→C, 5→B, 6→A.

    C'est le cœur de l'équilibrage : sans le retour, la poule A prendrait 1, 2, 3 — tous les
    favoris dans le même groupe.
    """
    poules = composer_poules(archers(6), ConfigurationPoules(nb_poules=3))
    assert [[p.ref_id for p in poule.membres] for poule in poules] == [[1, 6], [2, 5], [3, 4]]


def test_composition_accepte_des_poules_de_tailles_inegales() -> None:
    """7 archers en 3 poules : les tailles diffèrent d'une unité, chaque poule étant classée
    séparément (aucun invariant ne l'interdit)."""
    poules = composer_poules(archers(7), ConfigurationPoules(nb_poules=3))
    assert sorted(len(poule.membres) for poule in poules) == [2, 2, 3]


def test_composition_refuse_plus_de_poules_que_de_participants() -> None:
    """Une poule vide n'est pas un groupe : on refuse à la composition."""
    with pytest.raises(ConfigurationPouleInvalide):
        composer_poules(archers(3), ConfigurationPoules(nb_poules=4))


# --- rencontres : « chaque archer rencontre tout ou partie des autres archers de sa poule » -------


def test_round_robin_complet_fait_se_rencontrer_tout_le_monde_une_fois() -> None:
    """« Tout » : dans une poule de 4, les 6 paires sont disputées, chacune une seule fois."""
    poule = Poule(numero=1, membres=tuple(archers(4)))
    rencontres = rencontres_de_poule(poule, ConfigurationPoules(nb_poules=1))
    paires = {frozenset((r.a.ref_id, r.b.ref_id)) for r in rencontres}
    assert len(rencontres) == 6
    assert len(paires) == 6


def test_un_archer_ne_figure_jamais_deux_fois_dans_le_meme_tour() -> None:
    """Condition pour tirer les rencontres d'un tour **en parallèle** sur plusieurs cibles."""
    poule = Poule(numero=1, membres=tuple(archers(6)))
    rencontres = rencontres_de_poule(poule, ConfigurationPoules(nb_poules=1))
    for tour in {r.tour for r in rencontres}:
        du_tour = [r for r in rencontres if r.tour == tour]
        engages = [r.a for r in du_tour] + [r.b for r in du_tour]
        assert len(engages) == len(set(engages))


def test_effectif_impair_fait_reposer_un_membre_par_tour() -> None:
    """À 5 membres, chacun rencontre bien ses 4 adversaires — un tour sur cinq il se repose."""
    poule = Poule(numero=1, membres=tuple(archers(5)))
    rencontres = rencontres_de_poule(poule, ConfigurationPoules(nb_poules=1))
    assert len(rencontres) == 10
    for membre in poule.membres:
        assert sum(1 for r in rencontres if membre in (r.a, r.b)) == 4


def test_round_robin_partiel_est_un_reglage_pas_un_autre_moteur() -> None:
    """« Ou partie » : 2 rencontres par archer dans une poule de 4 — le cercle est tronqué."""
    poule = Poule(numero=1, membres=tuple(archers(4)))
    configuration = ConfigurationPoules(nb_poules=1, rencontres_par_archer=2)
    rencontres = rencontres_de_poule(poule, configuration)
    for membre in poule.membres:
        assert sum(1 for r in rencontres if membre in (r.a, r.b)) == 2


def test_round_robin_partiel_refuse_plus_que_le_nombre_d_adversaires() -> None:
    """Dans une poule de 4, nul ne peut disputer 4 rencontres : il n'a que 3 adversaires.

    ⚠️ Le plafond est le nombre d'**adversaires**, pas le nombre de tours du cercle — à effectif
    impair le cercle compte un tour de plus (celui du repos).
    """
    poule = Poule(numero=1, membres=tuple(archers(4)))
    with pytest.raises(ConfigurationPouleInvalide):
        rencontres_de_poule(poule, ConfigurationPoules(nb_poules=1, rencontres_par_archer=4))


# --- barème : « un barème de points attribue les victoires, nuls et défaites » --------------------


def test_bareme_par_defaut_est_3_1_0() -> None:
    """Arbitrage du commanditaire (31/07/2026), qui a écarté le 2/1/0 initialement proposé."""
    bareme = BaremePoule()
    assert (bareme.victoire, bareme.nul, bareme.defaite) == (3, 1, 0)


def test_bareme_refuse_de_recompenser_la_defaite() -> None:
    """Un barème où perdre rapporte plus que gagner produirait un classement cohérent et absurde :
    on le refuse à la composition, seul endroit où l'anomalie est encore visible."""
    with pytest.raises(ConfigurationPouleInvalide):
        BaremePoule(victoire=1, nul=2, defaite=0)


# --- classement : « le classement de poule détermine les qualifiés » ------------------------------


def test_classement_ordonne_par_points_de_match() -> None:
    """Premier critère du départage §10.1. A gagne deux fois, B une, C aucune."""
    poule = Poule(numero=1, membres=tuple(archers(3)))
    a, b, c = poule.membres
    resultats = [
        ResultatRencontre(a=a, b=b, sets_a=6, sets_b=2),
        ResultatRencontre(a=a, b=c, sets_a=6, sets_b=0),
        ResultatRencontre(a=b, b=c, sets_a=6, sets_b=4),
    ]
    classement = classement_de_poule(poule, resultats, ConfigurationPoules(nb_poules=1))
    assert [ligne.participant for ligne in classement] == [a, b, c]
    assert [ligne.decompte.points_match for ligne in classement] == [6, 3, 0]


def test_un_nul_rapporte_a_chacun_les_points_du_nul() -> None:
    """Égalité de sets = nul (le barème distingue bien trois issues, pas deux)."""
    poule = Poule(numero=1, membres=tuple(archers(2)))
    a, b = poule.membres
    classement = classement_de_poule(
        poule,
        [ResultatRencontre(a=a, b=b, sets_a=5, sets_b=5)],
        ConfigurationPoules(nb_poules=1),
    )
    assert {ligne.decompte.points_match for ligne in classement} == {1}


def test_departage_suit_l_ordre_a_cinq_criteres_de_la_regle() -> None:
    """À points égaux, c'est la **différence de sets** qui tranche — deuxième critère (§10.1).

    ⚠️ Cet ordre **diffère** de celui de la qualification (§8.1, qui s'arrête aux 10 puis aux 9) :
    le référentiel avertit de ne pas confondre les deux.
    """
    poule = Poule(numero=1, membres=tuple(archers(3)))
    a, b, c = poule.membres
    resultats = [
        # A et B gagnent chacun une rencontre et en perdent une : même nombre de points.
        ResultatRencontre(a=a, b=b, sets_a=6, sets_b=0),
        ResultatRencontre(a=b, b=c, sets_a=6, sets_b=5),
        ResultatRencontre(a=c, b=a, sets_a=6, sets_b=5),
    ]
    classement = classement_de_poule(poule, resultats, ConfigurationPoules(nb_poules=1))
    assert [ligne.decompte.points_match for ligne in classement] == [3, 3, 3]
    # Diffs de sets : A = +6 -1 = +5, C = -1 +1 = 0, B = -6 +1 = -5.
    assert [ligne.participant for ligne in classement] == [a, c, b]


def test_ex_aequo_est_signale_et_non_arbitre() -> None:
    """« Barrage si nécessaire » : les cinq critères épuisés, le moteur **signale** l'ex æquo.

    Un comparateur pur ne fait pas tirer de flèches ; décider du barrage appartient au service.
    """
    poule = Poule(numero=1, membres=tuple(archers(2)))
    a, b = poule.membres
    classement = classement_de_poule(
        poule,
        [ResultatRencontre(a=a, b=b, sets_a=5, sets_b=5, score_a=140, score_b=140)],
        ConfigurationPoules(nb_poules=1),
    )
    assert [ligne.rang for ligne in classement] == [1, 1]
    assert all(ligne.ex_aequo for ligne in classement)


def test_un_membre_sans_rencontre_figure_au_classement() -> None:
    """Un archer présent doit apparaître, même si aucune de ses rencontres n'a encore été saisie :
    le faire disparaître serait pire que de l'afficher à zéro."""
    poule = Poule(numero=1, membres=tuple(archers(3)))
    a, b, c = poule.membres
    classement = classement_de_poule(
        poule, [ResultatRencontre(a=a, b=b, sets_a=6, sets_b=0)], ConfigurationPoules(nb_poules=1)
    )
    assert c in [ligne.participant for ligne in classement]


def test_resultat_etranger_a_la_poule_est_ignore() -> None:
    """Le service passe volontiers tous les résultats de la phase ; filtrer ici lui évite un
    découpage préalable."""
    poule = Poule(numero=1, membres=tuple(archers(2)))
    a, b = poule.membres
    etranger = Participant.individuel(99)
    classement = classement_de_poule(
        poule,
        [
            ResultatRencontre(a=a, b=b, sets_a=6, sets_b=0),
            ResultatRencontre(a=a, b=etranger, sets_a=6, sets_b=0),
        ],
        ConfigurationPoules(nb_poules=1),
    )
    assert classement[0].decompte.points_match == 3


# --- qualification -------------------------------------------------------------------------------


def test_aucun_qualifie_par_defaut() -> None:
    """Arbitrage du 31/07 : pas de valeur pré-remplie — le nombre de qualifiés dépend de ce que la
    phase suivante attend, pas du format de poule."""
    assert ConfigurationPoules(nb_poules=2).nb_qualifies is None


def test_les_qualifies_sont_les_premiers_du_classement() -> None:
    poule = Poule(numero=1, membres=tuple(archers(3)))
    a, b, c = poule.membres
    resultats = [
        ResultatRencontre(a=a, b=b, sets_a=6, sets_b=2),
        ResultatRencontre(a=a, b=c, sets_a=6, sets_b=0),
        ResultatRencontre(a=b, b=c, sets_a=6, sets_b=4),
    ]
    configuration = ConfigurationPoules(nb_poules=1, nb_qualifies=2)
    classement = classement_de_poule(poule, resultats, configuration)
    assert qualifies_de_poule(classement, configuration) == (a, b)


def test_ex_aequo_sur_la_barre_refuse_de_qualifier() -> None:
    """Qualifier « les deux premiers » quand les rangs 2 et 3 sont à égalité reviendrait à
    qualifier sur l'ordre d'affichage — c'est-à-dire sur le rang d'origine, qui n'a plus cours en
    poule. C'est exactement le « barrage si nécessaire » de la règle."""
    poule = Poule(numero=1, membres=tuple(archers(3)))
    a, b, c = poule.membres
    resultats = [
        ResultatRencontre(a=a, b=b, sets_a=6, sets_b=0, score_a=150, score_b=100),
        ResultatRencontre(a=a, b=c, sets_a=6, sets_b=0, score_a=150, score_b=100),
        ResultatRencontre(a=b, b=c, sets_a=5, sets_b=5, score_a=120, score_b=120),
    ]
    configuration = ConfigurationPoules(nb_poules=1, nb_qualifies=2)
    classement = classement_de_poule(poule, resultats, configuration)
    # Code **distinct** de `configuration_poule_invalide` : ce n'est pas un format mal réglé, c'est
    # une action à proposer à l'organisateur (« barrage si nécessaire », dernier terme de la règle).
    with pytest.raises(BarrageRequisAvantQualification):
        qualifies_de_poule(classement, configuration)


def test_la_difference_de_score_est_le_troisieme_critere() -> None:
    """3ᵉ critère de §10.1, qui n'était éprouvé nulle part — ni ici ni sur `TiebreakPoules`.

    A et B ont mêmes points **et** même différence de sets ; seul le score les sépare.
    """
    poule = Poule(numero=1, membres=tuple(archers(3)))
    a, b, c = poule.membres
    resultats = [
        ResultatRencontre(a=a, b=c, sets_a=6, sets_b=0, score_a=150, score_b=100),
        ResultatRencontre(a=b, b=c, sets_a=6, sets_b=0, score_a=140, score_b=100),
    ]
    classement = classement_de_poule(poule, resultats, ConfigurationPoules(nb_poules=1))
    par_participant = {ligne.participant: ligne for ligne in classement}
    assert par_participant[a].decompte.points_match == par_participant[b].decompte.points_match
    assert par_participant[a].decompte.diff_sets == par_participant[b].decompte.diff_sets
    assert par_participant[a].rang < par_participant[b].rang
    assert not par_participant[a].ex_aequo


def test_demander_autant_de_rencontres_que_d_adversaires_donne_le_round_robin_complet() -> None:
    """⚠️ Le piège d'effectif impair, **figé** au lieu d'être seulement documenté.

    « Je veux que chacun rencontre ses 4 adversaires » dans une poule de 5 : sans traitement, la
    troncature du cercle en donnait 4 à un seul archer et 3 aux quatre autres — l'écart touchait
    donc 4 membres sur 5, pas « un archer » comme la note le laissait entendre.
    """
    poule = Poule(numero=1, membres=tuple(archers(5)))
    configuration = ConfigurationPoules(nb_poules=1, rencontres_par_archer=4)
    rencontres = rencontres_de_poule(poule, configuration)
    for membre in poule.membres:
        assert sum(1 for r in rencontres if membre in (r.a, r.b)) == 4


def test_une_rencontre_fournie_deux_fois_est_refusee() -> None:
    """Un double envoi compterait les points deux fois et laisserait un classement parfaitement
    cohérent — simplement faux. C'est le genre d'erreur qui ne se voit jamais."""
    poule = Poule(numero=1, membres=tuple(archers(2)))
    a, b = poule.membres
    with pytest.raises(ConfigurationPouleInvalide):
        classement_de_poule(
            poule,
            [
                ResultatRencontre(a=a, b=b, sets_a=6, sets_b=0),
                ResultatRencontre(a=b, b=a, sets_a=0, sets_b=6),
            ],
            ConfigurationPoules(nb_poules=1),
        )
