"""Placement intégral 1→N & cascade de routage (E05US010) — tests écrits **depuis le CA**.

Règle 9 : ces tests dérivent des CA de `stories/E05-moteur-phases.md` § E05US010 et des règles **R**
et **T** de `moteur-placement-lucky-loser.md` (§ 4 et § 3), **pas** de l'implémentation : ils ont
été
écrits avant elle. Le micro-exemple à 8 archers du § 5 du même document sert de référence de
structure : c'est le seul endroit du projet où le format est dessiné à la main, donc le seul oracle
indépendant à cette maille (l'oracle 120 en est le pendant à taille réelle,
`test_oracle_120_placement.py`).

Vocabulaire (règle 3) : une **plage** est l'intervalle de rangs qu'un participant peut encore
atteindre ; un **match terminal** est celui dont l'issue fixe deux rangs définitifs (Règle T).
"""

from __future__ import annotations

import pytest

from domain.erreurs import EffectifTableauInvalide, PlageInvalide
from domain.participant import Participant
from domain.plage import Plage
from domain.politiques import (
    ByesAuxMieuxClasses,
    ContexteRoutage,
    Depth,
    EliminationSeche,
    HorsTableau,
    PlacementEnCascade,
    ProfondeurPodium,
    ProfondeurUnVersN,
    Routing,
    SeedingSerpent,
    VersPlage,
)
from domain.tableau import Tableau, construire_tableau

SEEDING = SeedingSerpent()
BYES = ByesAuxMieuxClasses()
CASCADE = PlacementEnCascade()
INTEGRAL = ProfondeurUnVersN()
PODIUM = ProfondeurPodium()


def p(rang: int) -> Participant:
    """Le participant ensemencé au rang `rang` (identité = rang, pour lire les assertions)."""
    return Participant.individuel(rang)


def construire(effectif: int, *, routing: Routing = CASCADE, depth: Depth = INTEGRAL) -> Tableau:
    """Un tableau pour `effectif` participants classés 1..effectif."""
    return construire_tableau(
        [p(r) for r in range(1, effectif + 1)],
        seeding=SEEDING,
        byes=BYES,
        routing=routing,
        depth=depth,
    )


def _derouler_gagne_mieux_classe(tableau: Tableau) -> Tableau:
    """Joue tout le tableau en faisant gagner systématiquement le mieux classé.

    C'est le déroulé « sans surprise » : il rend le classement final **prédictible** (chaque
    participant finit à son rang de départ), ce qui en fait l'oracle le plus discriminant du
    placement intégral — toute erreur de routage ou de division de plage déplace au moins un rang.
    """
    courant = tableau
    encore = True
    while encore:
        encore = False
        for m in courant.matchs:
            if m.est_jouable and m.haut is not None and m.bas is not None:
                mieux = m.haut if m.haut.ref_id < m.bas.ref_id else m.bas
                courant = courant.jouer(m.numero, mieux)
                encore = True
                break
    return courant


# --- CA « division récursive » : [a..b] → moitié haute / moitié basse jusqu'à largeur 2 ----------


def test_une_plage_se_divise_en_deux_moities_egales() -> None:
    plage = Plage(1, 8)
    assert plage.moitie_haute() == Plage(1, 4)
    assert plage.moitie_basse() == Plage(5, 8)


def test_la_division_descend_jusqu_a_la_largeur_deux() -> None:
    plage = Plage(5, 8).moitie_basse()
    assert plage == Plage(7, 8)
    assert plage.largeur == 2
    assert plage.est_terminale


def test_une_plage_de_largeur_deux_ne_se_divise_plus() -> None:
    with pytest.raises(PlageInvalide):
        Plage(7, 8).moitie_haute()


def test_une_plage_vide_ou_inversee_est_refusee() -> None:
    with pytest.raises(PlageInvalide):
        Plage(8, 5)


# --- CA « routing cascade » : route(perdant, tour) → sous-tableau ; personne n'est éliminé -------


def test_la_cascade_envoie_le_perdant_dans_la_moitie_basse_de_sa_plage() -> None:
    """Règle R : perdre au niveau de plage [1..8] fait entrer dans le sous-tableau [5..8]."""
    destination = CASCADE.route(ContexteRoutage(tour=1, plage=Plage(1, 8)))
    assert destination == VersPlage(Plage(5, 8))


def test_l_elimination_seche_envoie_le_perdant_hors_du_tableau() -> None:
    assert EliminationSeche().route(ContexteRoutage(tour=1, plage=Plage(1, 8))) == HorsTableau()


def test_en_placement_integral_personne_n_est_elimine() -> None:
    """CA « routing cascade » : chaque perdant d'un match non terminal a un match aval."""
    tableau = construire(8)
    for m in tableau.matchs:
        if m.plage is not None and m.plage.est_terminale:
            continue  # un match terminal fixe deux rangs : le perdant n'a plus à jouer
        assert (
            tableau.match_aval_du_perdant(m.numero) is not None
        ), f"le perdant du match {m.numero} n'est routé nulle part"


# --- CA « rangs terminaux » (Règle T) -----------------------------------------------------------


def test_un_match_terminal_donne_le_rang_superieur_au_gagnant() -> None:
    """Règle T : la paire (2k-1, 2k) donne gagnant = rang supérieur, perdant = rang suivant.

    Le match terminal des places 5-6 n'est peuplé qu'une fois son sous-tableau de placement joué :
    on déroule jusqu'à ce qu'il devienne jouable, puis on fait gagner le **moins bien classé** —
    si le rang suivait l'ensemencement plutôt que l'issue du match, l'assertion le dirait.
    """
    tableau = construire(8)
    while not tableau.match(_numero_terminal(tableau, (5, 6))).est_jouable:
        m = next(m for m in tableau.matchs if m.est_jouable and m.place_en_jeu != (5, 6))
        tableau = tableau.jouer(m.numero, m.haut)  # type: ignore[arg-type]
    terminal = tableau.match(_numero_terminal(tableau, (5, 6)))
    assert terminal.haut is not None and terminal.bas is not None
    duellistes = (terminal.haut, terminal.bas)
    outsider = max(duellistes, key=lambda part: part.ref_id)
    favori = min(duellistes, key=lambda part: part.ref_id)
    joue = tableau.jouer(terminal.numero, outsider)
    classement = {place.participant: place.rang for place in joue.classement()}
    assert classement[outsider] == 5
    assert classement[favori] == 6


def _numero_terminal(tableau: Tableau, place: tuple[int, int]) -> int:
    return next(m.numero for m in tableau.matchs if m.place_en_jeu == place)


def test_chaque_rang_de_1_a_n_sort_d_un_match_terminal_unique() -> None:
    """CA « rangs terminaux » : 8 archers → 4 matchs terminaux couvrant les paires (1,2)…(7,8)."""
    tableau = construire(8)
    paires = sorted(m.place_en_jeu for m in tableau.matchs if m.place_en_jeu is not None)
    assert paires == [(1, 2), (3, 4), (5, 6), (7, 8)]


# --- CA « placement intégral 1→N » --------------------------------------------------------------


def test_le_micro_exemple_a_huit_archers_produit_douze_matchs() -> None:
    """§ 5 du document de formalisation : 3 niveaux, 12 matchs (4 quarts + 8 de progression)."""
    assert len(construire(8).matchs) == 12


def test_le_placement_integral_classe_tout_le_monde_de_un_a_n() -> None:
    tableau = _derouler_gagne_mieux_classe(construire(8))
    classement = tableau.classement()
    assert [place.rang for place in classement] == list(range(1, 9))


def test_le_mieux_classe_qui_gagne_toujours_finit_a_son_rang_de_depart() -> None:
    """Le déroulé sans surprise doit rendre l'ordre d'ensemencement à l'identique (Règle R + T)."""
    tableau = _derouler_gagne_mieux_classe(construire(8))
    assert [place.participant for place in tableau.classement()] == [p(r) for r in range(1, 9)]


def test_une_defaite_fait_basculer_dans_la_moitie_inferieure_de_la_plage() -> None:
    """§ 4 : « chaque défaite le fait basculer dans la moitié inférieure de sa plage courante »."""
    tableau = construire(8)
    quart = next(m for m in tableau.matchs if m.tour == 1 and m.est_jouable)
    battu = quart.bas
    tableau = tableau.jouer(quart.numero, quart.haut)  # type: ignore[arg-type]
    tableau = _derouler_gagne_mieux_classe(tableau)
    rang = next(pl.rang for pl in tableau.classement() if pl.participant == battu)
    assert rang >= 5, "un battu du premier tour ne peut plus atteindre la moitié haute"


@pytest.mark.parametrize("effectif", [2, 3, 4, 5, 8, 12, 16, 17])
def test_tout_effectif_recoit_un_classement_complet_et_sans_doublon(effectif: int) -> None:
    """Q5 : « division par deux systématique quel que soit l'effectif, byes automatiques »."""
    tableau = _derouler_gagne_mieux_classe(construire(effectif))
    classement = tableau.classement()
    assert [place.rang for place in classement] == list(range(1, effectif + 1))
    assert len({place.participant for place in classement}) == effectif


def test_un_effectif_inferieur_a_deux_reste_refuse() -> None:
    with pytest.raises(EffectifTableauInvalide):
        construire(1)


# --- CA « byes dans les plages non-puissance-de-2 » (Q4 du document) ----------------------------


def test_le_perdant_d_un_bye_n_est_pas_route(effectif: int = 5) -> None:
    """Un match gagné d'office n'a pas de perdant : son camp aval reste une place d'exempt."""
    tableau = construire(effectif)
    bye = next(m for m in tableau.matchs if m.est_bye)
    aval = tableau.match_aval_du_perdant(bye.numero)
    assert aval is None


def test_les_plages_tronquees_par_l_effectif_ne_sont_pas_engendrees() -> None:
    """12 archers dans un tableau de 16 : aucun match ne joue les rangs 13 à 16 — ils n'existent
    pas."""
    tableau = construire(12)
    rangs_en_jeu = {r for m in tableau.matchs if m.place_en_jeu for r in m.place_en_jeu}
    assert max(rangs_en_jeu) == 12


# --- non-régression : l'élimination directe livrée reste inchangée (E05US005) --------------------


def test_la_profondeur_podium_reproduit_le_tableau_a_elimination_directe() -> None:
    """Le format livré par E05US005 est le placement tronqué au rang 4 : 8 archers → 8 matchs."""
    tableau = construire(8, depth=PODIUM)
    assert len(tableau.matchs) == 8
    assert sorted(m.place_en_jeu for m in tableau.matchs if m.place_en_jeu) == [(1, 2), (3, 4)]


def test_la_petite_finale_departage_les_perdants_des_demies() -> None:
    tableau = construire(8, depth=PODIUM)
    petite = tableau.petite_finale
    assert petite is not None
    assert petite.place_en_jeu == (3, 4)


def test_en_elimination_seche_aucun_rang_au_dela_du_titre_n_est_departage() -> None:
    """Routing « le perdant sort » : ni petite finale, ni tableau de placement."""
    tableau = construire(8, routing=EliminationSeche(), depth=INTEGRAL)
    assert sorted(m.place_en_jeu for m in tableau.matchs if m.place_en_jeu) == [(1, 2)]
    assert tableau.petite_finale is None
