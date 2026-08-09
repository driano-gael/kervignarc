"""Tests du **placement des poules** — écrits depuis le CA d'E05US023 (règle 9).

Source : `stories/E05-moteur-phases.md`, E05US023, puces « CA — la taille commande, le nombre de
groupes s'en déduit » et « CA — une poule occupe un bloc de couloirs contigus ». Ces tests sont
écrits **avant** l'implémentation : ils décrivent ce que le commanditaire a demandé le 09/08/2026,
pas ce que le code fait.

⚠️ Deux arbitrages du 09/08/2026 sont l'objet même de ce fichier, et aucun n'est déductible du
code d'avant :

1. L'organisateur saisit une **taille de poule**, pas un nombre de poules, et le reste **gonfle**
   quelques poules (jamais de poule plus petite que demandé).
2. L'empreinte d'une poule n'est **pas son effectif** mais le nombre d'archers simultanément sur la
   ligne — deux fois `effectif ÷ 2` — parce que la méthode du cercle ne fait tirer que la moitié des
   membres par tour. Une poule de 5 tient donc sur **une** cible de 4 couloirs.
"""

from __future__ import annotations

import pytest

from domain.gabarit_salle import GabaritSalle
from domain.participant import Participant
from domain.placement_poules import placer_les_poules
from domain.poule import ConfigurationPoules, composer_poules, couloirs_occupes, nb_poules_pour


def _archers(nombre: int) -> list[Participant]:
    """`nombre` participants individuels, dans l'ordre de rang (indice 0 = premier)."""
    return [Participant.individuel(index) for index in range(1, nombre + 1)]


# --------------------------------------------------------------------------------------------
# CA — la taille commande, le nombre de groupes s'en déduit
# --------------------------------------------------------------------------------------------


def test_effectif_multiple_de_la_taille_donne_des_poules_pleines() -> None:
    """32 archers en poules de 4 → 8 poules de 4 (CA, exemple donné par le commanditaire)."""
    assert nb_poules_pour(effectif=32, taille_visee=4) == 8

    poules = composer_poules(_archers(32), ConfigurationPoules(nb_poules=8))
    assert [len(poule.membres) for poule in poules] == [4] * 8


def test_le_reste_gonfle_quelques_poules_au_lieu_d_en_creer_une_petite() -> None:
    """30 archers en poules de 4 → **7** poules : cinq de 4 et deux de 5 (CA, arbitrage 09/08).

    C'est l'arrondi **vers le bas** sur le nombre de groupes. L'arrondi vers le haut aurait donné
    8 poules dont deux de 3 — refusé par le commanditaire : « il est possible pour répartir de faire
    quelques poules de 5 ».
    """
    assert nb_poules_pour(effectif=30, taille_visee=4) == 7

    poules = composer_poules(_archers(30), ConfigurationPoules(nb_poules=7))
    tailles = sorted(len(poule.membres) for poule in poules)
    assert tailles == [4, 4, 4, 4, 4, 5, 5]


def test_aucune_poule_ne_compte_moins_que_la_taille_demandee() -> None:
    """L'invariant du CA, vérifié sur toute une plage d'effectifs plutôt que sur un cas choisi."""
    taille = 4
    for effectif in range(taille, 61):
        poules = composer_poules(
            _archers(effectif),
            ConfigurationPoules(nb_poules=nb_poules_pour(effectif, taille)),
        )
        assert (
            min(len(poule.membres) for poule in poules) >= taille
        ), f"effectif {effectif} : une poule est descendue sous la taille demandée"


def test_effectif_inferieur_au_double_de_la_taille_donne_une_seule_poule() -> None:
    """7 archers en poules de 4 → **une** poule de 7 (CA, cas extrême nommé).

    Conséquence assumée de « aucune poule sous la taille demandée » : deux poules donneraient 4 + 3.
    Le CA exige en contrepartie que l'écran **montre** la répartition obtenue, pour que
    l'organisateur voie cette poule de 7 et change sa taille s'il ne la veut pas.
    """
    assert nb_poules_pour(effectif=7, taille_visee=4) == 1
    assert nb_poules_pour(effectif=4, taille_visee=4) == 1


def test_la_taille_visee_doit_permettre_au_moins_une_rencontre() -> None:
    """Une « poule » de 1 n'apparie personne : c'est un réglage à refuser, pas à arrondir."""
    with pytest.raises(ValueError):
        nb_poules_pour(effectif=32, taille_visee=1)
    with pytest.raises(ValueError):
        nb_poules_pour(effectif=32, taille_visee=0)


def test_un_effectif_plus_petit_que_la_taille_ne_fabrique_pas_de_poule_vide() -> None:
    """3 archers en poules de 4 : une poule de 3, pas zéro poule ni une poule vide."""
    assert nb_poules_pour(effectif=3, taille_visee=4) == 1


# --------------------------------------------------------------------------------------------
# CA — l'empreinte d'une poule est son parallélisme, pas son effectif
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("effectif", "couloirs"),
    [
        (2, 2),  # une seule rencontre
        (3, 2),  # 1 rencontre par tour, un membre se repose
        (4, 4),  # 2 rencontres : une cible pile
        (5, 4),  # 2 rencontres aussi — c'est tout l'arbitrage du 09/08
        (6, 6),  # 3 rencontres : déborde d'une cible de 4
        (7, 6),
        (8, 8),
    ],
)
def test_l_empreinte_vaut_deux_fois_le_nombre_de_rencontres_simultanees(
    effectif: int, couloirs: int
) -> None:
    """Deux fois `effectif ÷ 2` : le cercle ne fait tirer que la moitié des membres par tour.

    Le cas **(5, 4)** est celui que le commanditaire a relevé : « à 5 je ne fais que deux matchs en
    parallèle, donc 4 couloirs suffisent ». Prendre l'effectif aurait réservé 5 couloirs et fait
    déborder toutes les poules impaires sans raison.
    """
    assert couloirs_occupes(effectif) == couloirs


def test_l_empreinte_est_coherente_avec_les_rencontres_que_le_moteur_produit() -> None:
    """Garde-fou : l'empreinte doit suivre le moteur, pas une formule qui lui ressemble.

    On compte les rencontres du tour le plus chargé et on vérifie que l'empreinte les loge toutes.
    Si `rencontres_de_poule` changeait d'appariement, ce test tomberait — c'est voulu : une
    empreinte qui ne suit plus le moteur place des archers sur des couloirs qui n'existent pas.
    """
    from collections import Counter

    from domain.poule import rencontres_de_poule

    for effectif in range(2, 9):
        poules = composer_poules(_archers(effectif), ConfigurationPoules(nb_poules=1))
        rencontres = rencontres_de_poule(poules[0], ConfigurationPoules(nb_poules=1))
        par_tour = Counter(rencontre.tour for rencontre in rencontres)
        tour_le_plus_charge = max(par_tour.values())
        assert couloirs_occupes(effectif) == tour_le_plus_charge * 2


# --------------------------------------------------------------------------------------------
# CA — une poule occupe un bloc de couloirs contigus, et la suivante s'accole
# --------------------------------------------------------------------------------------------


def test_des_poules_de_quatre_occupent_une_cible_chacune() -> None:
    """Le cas nominal du club : poules de 4, gabarit à 4 couloirs → une poule par cible."""
    poules = composer_poules(_archers(16), ConfigurationPoules(nb_poules=4))
    plan = placer_les_poules(poules, GabaritSalle.creer("salle", nb_cibles=6, capacite=4))

    assert [bloc.cible_index for bloc in plan.blocs] == [1, 2, 3, 4]
    assert all(bloc.position_depart == "A" for bloc in plan.blocs)
    assert all(bloc.nb_couloirs == 4 for bloc in plan.blocs)
    assert plan.conflits == ()


def test_une_poule_de_cinq_tient_encore_sur_une_seule_cible() -> None:
    """L'arbitrage du 09/08 en situation : 30 archers en poules de 4 → 7 poules, 7 cibles.

    Sans la règle d'empreinte, les deux poules de 5 auraient réclamé 5 couloirs et fait glisser
    toute la salle — cinq cibles auraient suffi pour rien.
    """
    poules = composer_poules(_archers(30), ConfigurationPoules(nb_poules=7))
    plan = placer_les_poules(poules, GabaritSalle.creer("salle", nb_cibles=8, capacite=4))

    assert [bloc.cible_index for bloc in plan.blocs] == [1, 2, 3, 4, 5, 6, 7]
    assert all(bloc.nb_couloirs == 4 for bloc in plan.blocs)
    assert plan.conflits == ()


def test_une_poule_qui_deborde_prend_la_suite_et_la_suivante_s_accole() -> None:
    """CA : « la poule d'après démarre au couloir libre juste après, sans trou » (arbitrage 09/08).

    Poules de 6 → 6 couloirs chacune sur un gabarit à 4 couloirs :
    - poule 1 : cible 1 (A→D) + cible 2 (A→B)
    - poule 2 : démarre **cible 2, couloir C** — pas cible 3.
    """
    poules = composer_poules(_archers(18), ConfigurationPoules(nb_poules=3))
    plan = placer_les_poules(poules, GabaritSalle.creer("salle", nb_cibles=6, capacite=4))

    assert [(bloc.cible_index, bloc.position_depart) for bloc in plan.blocs] == [
        (1, "A"),
        (2, "C"),
        (4, "A"),
    ]
    assert all(bloc.nb_couloirs == 6 for bloc in plan.blocs)
    assert plan.conflits == ()


def test_le_bloc_enumere_les_couloirs_qu_il_couvre_a_travers_les_cibles() -> None:
    """Un bloc qui déborde doit savoir dire **quels** couloirs il occupe, cible par cible.

    C'est ce que le plan de salle et la feuille de poule liront : sans cette énumération, un bloc
    « cible 1, couloir A, 6 couloirs » reste illisible pour qui doit poser les archers.
    """
    poules = composer_poules(_archers(6), ConfigurationPoules(nb_poules=1))
    plan = placer_les_poules(poules, GabaritSalle.creer("salle", nb_cibles=3, capacite=4))

    assert plan.blocs[0].couloirs() == (
        (1, "A"),
        (1, "B"),
        (1, "C"),
        (1, "D"),
        (2, "A"),
        (2, "B"),
    )


def test_une_salle_trop_petite_signale_les_poules_non_placees() -> None:
    """Le placement **rapporte** ce qu'il n'a pas pu poser, il ne tronque pas en silence.

    Même parti que `PlanDeCibles.conflits` en qualification (ADR-0024) : l'organisateur doit voir
    qu'une poule n'a pas de cible, pas la découvrir le jour J.
    """
    poules = composer_poules(_archers(16), ConfigurationPoules(nb_poules=4))
    plan = placer_les_poules(poules, GabaritSalle.creer("salle", nb_cibles=2, capacite=4))

    assert [bloc.poule for bloc in plan.blocs] == [1, 2]
    assert [conflit.poule for conflit in plan.conflits] == [3, 4]


def test_un_gabarit_a_capacite_reduite_fait_deborder_plus_tot() -> None:
    """Le débordement se lit sur la **capacité réelle de chaque cible**, pas sur un 4 supposé.

    `GabaritSalle` autorise une capacité de 1 à 4 par cible, et elle peut varier d'une cible à
    l'autre (`ajuster`). Une poule de 4 sur des cibles à 2 couloirs occupe donc deux cibles.
    """
    poules = composer_poules(_archers(8), ConfigurationPoules(nb_poules=2))
    plan = placer_les_poules(poules, GabaritSalle.creer("salle", nb_cibles=6, capacite=2))

    assert [(bloc.cible_index, bloc.position_depart) for bloc in plan.blocs] == [(1, "A"), (3, "A")]
    assert plan.blocs[0].couloirs() == ((1, "A"), (1, "B"), (2, "A"), (2, "B"))


def test_le_placement_est_deterministe() -> None:
    """Règle 9 : rejouer le même placement doit rendre le même plan, sans horloge ni aléa."""
    poules = composer_poules(_archers(30), ConfigurationPoules(nb_poules=7))
    gabarit = GabaritSalle.creer("salle", nb_cibles=8, capacite=4)

    assert placer_les_poules(poules, gabarit) == placer_les_poules(poules, gabarit)
