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
from domain.plage import Plage
from domain.politiques import (
    AucunClassement,
    ByesAuxMieuxClasses,
    ContexteRoutage,
    ContexteScore,
    DecompteDepartage,
    EliminationSeche,
    FamillePolitique,
    HorsTableau,
    PlacementEnCascade,
    PolitiquesPhase,
    ProfondeurUnVersN,
    RoutingRepechage,
    ScoreAvecHandicap,
    ScoreCumul,
    SeedingSerpent,
    TiebreakAvecBarrage,
    TiebreakFftaDefaut,
    TiebreakPoules,
    VersPlage,
    VersRepechage,
    assembler_politiques,
    registre_par_defaut,
)

# --- scoring : cumul des points des volées validées (§6.1) --------------------------------------


def test_score_cumul_additionne_les_points() -> None:
    """Le cumul est la **somme** des points de volée (le classement de qualification, §6.1)."""
    assert ScoreCumul().total([27, 30, 24], ContexteScore()) == 81


def test_score_cumul_sans_volee_vaut_zero() -> None:
    """Aucune volée validée → total nul (un archer sans flèche figure au classement à 0)."""
    assert ScoreCumul().total([], ContexteScore()) == 0


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
    """En élimination directe, le perdant quitte le tournoi : aucun sous-tableau ne l'accueille."""
    contexte = ContexteRoutage(tour=1, plage=Plage(1, 8))
    assert EliminationSeche().route(contexte) == HorsTableau()


def test_routing_placement_cascade_fait_descendre_le_perdant_d_une_moitie() -> None:
    """*Règle R* : perdre sur la plage [1..8] fait entrer dans le sous-tableau [5..8]."""
    contexte = ContexteRoutage(tour=1, plage=Plage(1, 8))
    assert PlacementEnCascade().route(contexte) == VersPlage(Plage(5, 8))


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


# --- E05US015 : les politiques du catalogue de types ---------------------------------------------


def test_repechage_sort_du_tableau_les_perdants_des_tours_designes() -> None:
    """CA « repêchage World Archery » : `routing = repêchage` **réinjecte** certains perdants.

    La règle WA s'énonce « les perdants du 1ᵉʳ tour sont repêchés » ; `ContexteRoutage.tour` étant
    compté **depuis la racine**, cela s'écrit `{1}`.
    """
    routing = RoutingRepechage(tours_repeches=frozenset({1}), sinon=PlacementEnCascade())
    assert routing.route(ContexteRoutage(tour=1, plage=Plage(1, 8))) == VersRepechage()


def test_repechage_delegue_les_autres_tours_a_sa_politique_de_repli() -> None:
    """Le repêchage **excepte** quelques tours, il ne remplace pas le placement : c'est le format du
    club, où le « Lucky-Looser » remonte et où les autres battus descendent se classer."""
    routing = RoutingRepechage(tours_repeches=frozenset({1}), sinon=PlacementEnCascade())
    assert routing.route(ContexteRoutage(tour=2, plage=Plage(1, 8))) == VersPlage(Plage(5, 8))


def test_repechage_composable_avec_l_elimination_seche() -> None:
    routing = RoutingRepechage(tours_repeches=frozenset({1}), sinon=EliminationSeche())
    assert routing.route(ContexteRoutage(tour=3, plage=Plage(1, 4))) == HorsTableau()


def test_le_repechage_se_resout_depuis_la_config() -> None:
    """Première politique **composite** du registre : sa fabrique en résout une autre."""
    registre = registre_par_defaut()
    politiques = assembler_politiques(
        {"routing": {"nom": "repechage", "tours": [1], "sinon": {"nom": "elimination_seche"}}},
        registre,
    )
    assert politiques.routing == RoutingRepechage(
        tours_repeches=frozenset({1}), sinon=EliminationSeche()
    )


def test_le_repechage_prend_le_placement_en_cascade_par_defaut() -> None:
    """Le cas du format club : les battus non repêchés descendent malgré tout se classer."""
    politiques = assembler_politiques(
        {"routing": {"nom": "repechage", "tours": [1]}}, registre_par_defaut()
    )
    assert politiques.routing == RoutingRepechage(
        tours_repeches=frozenset({1}), sinon=PlacementEnCascade()
    )


def test_un_repechage_sans_tour_est_refuse() -> None:
    """Un repêchage qui ne repêche rien est un `placement_cascade` déguisé : l'accepter laisserait
    croire à l'organisateur que son format repêche alors qu'il n'en fait rien."""
    with pytest.raises(PolitiqueMalFormee):
        assembler_politiques({"routing": {"nom": "repechage", "tours": []}}, registre_par_defaut())


def test_un_tour_repeche_non_entier_est_refuse() -> None:
    with pytest.raises(PolitiqueMalFormee):
        assembler_politiques(
            {"routing": {"nom": "repechage", "tours": ["premier"]}}, registre_par_defaut()
        )


def test_le_handicap_s_ajoute_au_score_realise() -> None:
    """Règle donnée par le commanditaire (31/07/2026) : « score réalisé + handicap »."""
    assert ScoreAvecHandicap().total([27, 30, 24], ContexteScore(handicap=100)) == 181


def test_sans_handicap_le_format_retombe_sur_le_scratch() -> None:
    """`0` est le neutre : un archer non évalué concourt sans casser le classement."""
    assert ScoreAvecHandicap().total([27, 30, 24], ContexteScore()) == 81


def test_le_departage_de_poule_commence_par_les_points_de_match() -> None:
    """Référentiel §10.1 : points de match, diff de sets, diff de score, 10, 9.

    ⚠️ Cet ordre **diffère** de §8.1 (qualification) : ici A gagne malgré **moins** de 10.
    """
    a = DecompteDepartage(nb_dix=0, nb_neuf=0, points_match=6)
    b = DecompteDepartage(nb_dix=20, nb_neuf=20, points_match=3)
    assert TiebreakPoules().departager(a, b) < 0


def test_le_departage_de_poule_retombe_sur_les_criteres_ffta_a_tout_egal() -> None:
    """Dégradation **silencieuse mais juste** : trois premiers critères nuls → on lit §8.1."""
    a = DecompteDepartage(nb_dix=10, nb_neuf=2)
    b = DecompteDepartage(nb_dix=8, nb_neuf=9)
    assert TiebreakPoules().departager(a, b) < 0


def test_le_decompte_de_qualification_reste_constructible_a_deux_champs() -> None:
    """C'est ce qui rend l'élargissement d'E05US015 **non cassant** : le CA le désignait comme la
    rupture de contrat la plus risquée de l'US, elle se réduit à des champs facultatifs."""
    decompte = DecompteDepartage(nb_dix=10, nb_neuf=5)
    assert (decompte.points_match, decompte.diff_sets, decompte.diff_score) == (0, 0, 0)
    assert TiebreakFftaDefaut().departager(decompte, DecompteDepartage(nb_dix=8, nb_neuf=9)) < 0


def test_l_echauffement_ne_produit_aucun_rang() -> None:
    """« Sans point et sans classement » (§10.1) : le cas dégénéré de `Depth`, et il est demandé.

    Rendre `()` plutôt que laisser `depth` à `None` **dit** que la politique a été choisie.
    """
    assert AucunClassement().rangs_a_classer(120) == ()


def test_les_nouvelles_politiques_sont_au_registre() -> None:
    """Catalogue ouvert par la composition root (règle 2) : un format est de la configuration."""
    politiques = assembler_politiques(
        {
            "scoring": {"nom": "handicap"},
            "tiebreak": {"nom": "poules"},
            "depth": {"nom": "aucun"},
        },
        registre_par_defaut(),
    )
    assert isinstance(politiques.scoring, ScoreAvecHandicap)
    assert isinstance(politiques.tiebreak, TiebreakPoules)
    assert isinstance(politiques.depth, AucunClassement)


# --- fabrique du barrage (E06US003, ADR-0066) ----------------------------------------------------
#
# Six branches de refus pour un point d'injection par lequel passe **tout** le classement en
# production : la revue a relevé qu'aucune n'était couverte.


def _resoudre_tiebreak(params: dict[str, object]) -> object:
    return registre_par_defaut().resoudre(FamillePolitique.TIEBREAK, "barrage", params)


def test_un_barrage_sans_seuil_est_refuse() -> None:
    """Sans seuil, un barrage ne barre rien : c'est un `ffta_defaut` déguisé, et l'accepter
    laisserait croire à l'organisateur que son format départage au tir."""
    with pytest.raises(PolitiqueMalFormee, match="jusqu"):
        _resoudre_tiebreak({})


def test_un_seuil_booleen_est_refuse() -> None:
    """`True` est un `int` en Python : sans la garde explicite, `jusqu_au=True` réglerait un
    barrage jusqu'au rang 1."""
    with pytest.raises(PolitiqueMalFormee):
        _resoudre_tiebreak({"jusqu_au": True})


def test_un_seuil_nul_ou_negatif_est_refuse() -> None:
    with pytest.raises(PolitiqueMalFormee):
        _resoudre_tiebreak({"jusqu_au": 0})
    with pytest.raises(PolitiqueMalFormee):
        _resoudre_tiebreak({"jusqu_au": -3})


def test_un_barrage_enveloppe_le_departage_ffta_par_defaut() -> None:
    politique = _resoudre_tiebreak({"jusqu_au": 8})
    assert politique == TiebreakAvecBarrage(sous_jacent=TiebreakFftaDefaut(), jusqu_au=8)


def test_un_barrage_enveloppe_le_departage_nomme() -> None:
    politique = _resoudre_tiebreak({"jusqu_au": 4, "sinon": {"nom": "poules"}})
    assert politique == TiebreakAvecBarrage(sous_jacent=TiebreakPoules(), jusqu_au=4)


def test_un_sinon_mal_forme_est_refuse() -> None:
    with pytest.raises(PolitiqueMalFormee):
        _resoudre_tiebreak({"jusqu_au": 8, "sinon": "ffta_defaut"})
    with pytest.raises(PolitiqueMalFormee):
        _resoudre_tiebreak({"jusqu_au": 8, "sinon": {"nom": 3}})


def test_un_barrage_ne_s_enveloppe_pas_lui_meme() -> None:
    """Deux seuils imbriqués ne composent rien : le plus interne serait purement ignoré,
    `barrage_requis` n'étant jamais délégué. Refusé explicitement plutôt que toléré."""
    with pytest.raises(PolitiqueMalFormee, match="lui-même"):
        _resoudre_tiebreak({"jusqu_au": 8, "sinon": {"nom": "barrage", "jusqu_au": 4}})


def test_un_departage_inconnu_dans_le_sinon_est_signale() -> None:
    with pytest.raises(PolitiqueInconnue):
        _resoudre_tiebreak({"jusqu_au": 8, "sinon": {"nom": "inexistant"}})
