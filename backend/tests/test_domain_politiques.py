"""Tests unitaires des **politiques injectables** du moteur de phases (E05US003 / ADR-0004).

Domaine **pur**, sans base ni serveur. Les attentes dérivent des **règles écrites** (règle 9) —
pas de l'implémentation : seeding serpent `r vs 2^k+1-r` (`moteur-placement-lucky-loser.md`, CA
E05US005), byes « aux mieux classés » (ADR-0004), départage FFTA « 10 puis 9 »
(`referentiel-ffta.md` §8.1), cumul des points validés (§6.1), profondeur 1→N (ADR-0004).

On teste ici les **politiques** (stratégies pures) et leur **assemblage** depuis `config.policies`.
Le *tableau* qui les orchestre (dimensionnement, progression, podium) est E05US005/E05US010 ; il
consomme ces stratégies déjà éprouvées.
"""

from __future__ import annotations

import pytest

from domain.erreurs import PolitiqueInconnue, PolitiqueMalFormee
from domain.politiques import (
    ByesAuxMieuxClasses,
    DecompteDepartage,
    DestinationPerdant,
    EliminationSeche,
    FamillePolitique,
    PolitiquesPhase,
    ProfondeurUnVersN,
    ScoreCumul,
    SeedingSerpent,
    TiebreakFftaDefaut,
    assembler_politiques,
    registre_par_defaut,
)

# --- scoring : cumul des points des volées validées (§6.1) --------------------------------------


def test_score_cumul_additionne_les_points() -> None:
    """Le cumul est la **somme** des points de volée (le classement de qualification, §6.1)."""
    assert ScoreCumul().total([27, 30, 24]) == 81


def test_score_cumul_sans_volee_vaut_zero() -> None:
    """Aucune volée validée → total nul (un archer sans flèche figure au classement à 0)."""
    assert ScoreCumul().total([]) == 0


# --- seeding : serpent `r vs 2^k+1-r` (CA E05US005, moteur-placement) ---------------------------


def test_seeding_serpent_bracket_de_huit() -> None:
    """L'ordre serpent d'un tableau de 8 : chaque paire adjacente somme à `2^k+1` = 9."""
    ordre = SeedingSerpent().ordre_des_tetes(8)
    assert ordre == (1, 8, 4, 5, 2, 7, 3, 6)
    # Règle vérifiable indépendamment de l'ordre exact : tête `r` affronte `2^k+1-r`.
    for i in range(0, len(ordre), 2):
        assert ordre[i] + ordre[i + 1] == 9


def test_seeding_serpent_arrondit_a_la_puissance_de_deux_superieure() -> None:
    """Un effectif non-puissance de 2 se place dans le tableau `2^k` immédiatement supérieur :
    5 archers → tableau de 8, les têtes 6/7/8 étant des places d'exempt (byes)."""
    assert SeedingSerpent().ordre_des_tetes(5) == (1, 8, 4, 5, 2, 7, 3, 6)


def test_seeding_serpent_tableau_minimal() -> None:
    """Deux archers : le tableau minimal, tête 1 contre tête 2."""
    assert SeedingSerpent().ordre_des_tetes(2) == (1, 2)


def test_seeding_serpent_grand_tableau_conserve_la_regle() -> None:
    """À plus grande échelle (16), la règle tient : chaque paire adjacente somme à `2^k+1` = 17,
    et la tête 2 tombe dans la **seconde moitié** du tableau — elle ne croise la tête 1 qu'en
    finale (propriété du serpent, pas seulement l'appariement d'un tableau de 8)."""
    ordre = SeedingSerpent().ordre_des_tetes(16)
    assert sorted(ordre) == list(range(1, 17))  # permutation de 1..16, sans trou ni doublon
    for i in range(0, len(ordre), 2):
        assert ordre[i] + ordre[i + 1] == 17
    assert ordre.index(2) >= len(ordre) // 2


def test_seeding_serpent_effectif_unitaire() -> None:
    """Cas dégénéré : un seul archer tombe dans le tableau minimal de 2 (tête 2 = exempt)."""
    assert SeedingSerpent().ordre_des_tetes(1) == (1, 2)


# --- byes : aux mieux classés, universel pour tout effectif (ADR-0004) --------------------------


def test_byes_aucun_si_effectif_puissance_de_deux() -> None:
    """Un tableau plein (8 pour 8) n'attribue aucun bye."""
    assert ByesAuxMieuxClasses().porteurs_de_bye(8) == frozenset()


def test_byes_attribues_aux_mieux_classes() -> None:
    """5 archers dans un tableau de 8 → 3 byes, aux **têtes de série** 1, 2 et 3 (ADR-0004)."""
    assert ByesAuxMieuxClasses().porteurs_de_bye(5) == frozenset({1, 2, 3})


def test_byes_calcul_universel() -> None:
    """La règle vaut pour tout effectif : 6 dans 8 → byes aux têtes 1 et 2."""
    assert ByesAuxMieuxClasses().porteurs_de_bye(6) == frozenset({1, 2})


def test_byes_effectif_unitaire() -> None:
    """Cas dégénéré : un seul archer dans un tableau de 2 → un bye pour la tête 1."""
    assert ByesAuxMieuxClasses().porteurs_de_bye(1) == frozenset({1})


# --- tiebreak : départage FFTA « 10 puis 9 », séquentiel (§8.1) ---------------------------------


def test_tiebreak_departage_sur_les_dix() -> None:
    """Plus de 10 = mieux classé (clé de comparaison négative pour l'entrée en tête)."""
    a = DecompteDepartage(nb_dix=10, nb_neuf=5)
    b = DecompteDepartage(nb_dix=8, nb_neuf=9)
    assert TiebreakFftaDefaut().departager(a, b) < 0


def test_tiebreak_departage_sur_les_neuf_a_dix_egaux() -> None:
    """Les 9 ne départagent **qu'à** 10 égaux (critères séquentiels, §8.1)."""
    a = DecompteDepartage(nb_dix=8, nb_neuf=10)
    b = DecompteDepartage(nb_dix=8, nb_neuf=7)
    assert TiebreakFftaDefaut().departager(a, b) < 0


def test_tiebreak_ex_aequo_si_egalite_parfaite() -> None:
    """Mêmes 10 et mêmes 9 : ex æquo (0) — le défaut FFTA sans barrage (E06US003 l'ouvrira)."""
    a = DecompteDepartage(nb_dix=8, nb_neuf=7)
    b = DecompteDepartage(nb_dix=8, nb_neuf=7)
    assert TiebreakFftaDefaut().departager(a, b) == 0


# --- depth : profondeur 1→N, personne n'est retranché (ADR-0004) --------------------------------


def test_profondeur_un_vers_n_classe_tout_le_monde() -> None:
    """1→N produit tous les rangs de 1 à l'effectif — personne n'est laissé sans rang."""
    assert ProfondeurUnVersN().rangs_a_classer(4) == (1, 2, 3, 4)


def test_profondeur_un_vers_n_effectif_unitaire() -> None:
    assert ProfondeurUnVersN().rangs_a_classer(1) == (1,)


# --- routing : élimination sèche (le perdant sort du tableau, ADR-0004) -------------------------


def test_routing_elimination_seche_evince_le_perdant() -> None:
    """En élimination directe, le perdant quitte le tournoi : destination = éliminé."""
    assert EliminationSeche().destination_du_perdant() is DestinationPerdant.ELIMINE


# --- registre : catalogue nom → implémentation, peuplé par la composition root ------------------


def test_registre_par_defaut_resout_chaque_famille() -> None:
    """Le registre par défaut connaît **une** implémentation par famille (CA « au moins une »)."""
    registre = registre_par_defaut()
    assert isinstance(
        registre.resoudre(FamillePolitique.SCORING, "cumul", {"volees": 20, "fleches": 3}),
        ScoreCumul,
    )
    assert isinstance(
        registre.resoudre(FamillePolitique.ROUTING, "elimination_seche", {}), EliminationSeche
    )
    assert isinstance(registre.resoudre(FamillePolitique.SEEDING, "serpent", {}), SeedingSerpent)
    assert isinstance(
        registre.resoudre(FamillePolitique.BYES, "mieux_classes", {}), ByesAuxMieuxClasses
    )
    assert isinstance(
        registre.resoudre(FamillePolitique.TIEBREAK, "ffta_defaut", {}), TiebreakFftaDefaut
    )
    assert isinstance(registre.resoudre(FamillePolitique.DEPTH, "un_vers_n", {}), ProfondeurUnVersN)


def test_registre_nom_inconnu_leve_politique_inconnue() -> None:
    """Un nom d'implémentation non enregistré est une erreur métier explicite, pas un KeyError."""
    registre = registre_par_defaut()
    with pytest.raises(PolitiqueInconnue):
        registre.resoudre(FamillePolitique.SCORING, "sets_inexistant", {})


# --- assemblage : config.policies → jeu de politiques résolu (CA « assemblage ») ----------------


def test_assemblage_resout_une_qualification() -> None:
    """Une config de qualification (`policies.scoring` nommé + paramétré) s'assemble en un jeu où
    seule la politique déclarée est présente ; les autres restent `None` (non requises ici)."""
    politiques = assembler_politiques(
        {"scoring": {"nom": "cumul", "volees": 20, "fleches": 3}}, registre_par_defaut()
    )
    assert isinstance(politiques, PolitiquesPhase)
    assert isinstance(politiques.scoring, ScoreCumul)
    assert politiques.routing is None
    assert politiques.seeding is None


def test_assemblage_resout_plusieurs_politiques() -> None:
    """Un tableau d'élimination directe assemble routing/seeding/byes/tiebreak/depth d'un coup."""
    politiques = assembler_politiques(
        {
            "routing": {"nom": "elimination_seche"},
            "seeding": {"nom": "serpent"},
            "byes": {"nom": "mieux_classes"},
            "tiebreak": {"nom": "ffta_defaut"},
            "depth": {"nom": "un_vers_n"},
        },
        registre_par_defaut(),
    )
    assert isinstance(politiques.routing, EliminationSeche)
    assert isinstance(politiques.seeding, SeedingSerpent)
    assert isinstance(politiques.byes, ByesAuxMieuxClasses)
    assert isinstance(politiques.tiebreak, TiebreakFftaDefaut)
    assert isinstance(politiques.depth, ProfondeurUnVersN)


def test_assemblage_famille_inconnue_est_malformee() -> None:
    """Une clé de politique hors du catalogue ADR-0004 (`validation` n'en est **pas** une) est
    une config mal formée — c'est le garde-fou de la décision « validation hors policies »."""
    with pytest.raises(PolitiqueMalFormee):
        assembler_politiques({"validation": {"nom": "fin_de_serie"}}, registre_par_defaut())


def test_assemblage_sans_nom_est_malforme() -> None:
    """Une politique sans clé `nom` ne désigne aucune implémentation (décision « nom + params »)."""
    with pytest.raises(PolitiqueMalFormee):
        assembler_politiques({"scoring": {"volees": 20}}, registre_par_defaut())


def test_assemblage_nom_non_chaine_est_malforme() -> None:
    """Le `nom` doit être une **chaîne** : un `nom` numérique (base altérée) est mal formé, pas une
    implémentation à résoudre — on ne cherche pas `42` dans le catalogue."""
    with pytest.raises(PolitiqueMalFormee):
        assembler_politiques({"scoring": {"nom": 42}}, registre_par_defaut())


def test_assemblage_nom_inconnu_remonte_politique_inconnue() -> None:
    """Un `nom` non enregistré remonte l'erreur du registre à travers l'assemblage."""
    with pytest.raises(PolitiqueInconnue):
        assembler_politiques({"scoring": {"nom": "sets_inexistant"}}, registre_par_defaut())
