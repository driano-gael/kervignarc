"""Tests du référentiel FFTA des catégories salle 18 m (E01US004 ; regroupements d'âge : E01US013).

Vérifie que le jeu pré-chargeable correspond aux catégories **officielles par division** du
`docs/referentiel-ffta.md` §3 — dont les **regroupements d'âge** de l'arc nu, que la bascule vers
`ages` (liste) permet enfin d'exprimer fidèlement (« U18 » = U15+U18, « Scratch » = U21..S3), là où
un scalaire `tranche_age` les écrasait.
"""

from __future__ import annotations

from collections import defaultdict

from application.referentiel_ffta import (
    ModeleCategorieFFTA,
    blasons_salle_18m,
    categories_salle_18m,
)
from domain.blason import ZoneScore
from domain.categorie import SexeCategorie, TrancheAge


def _libelles() -> list[str]:
    return [modele.libelle for modele in categories_salle_18m()]


def _blason_par_libelle() -> dict[str, str]:
    return {modele.libelle: modele.blason_nom for modele in categories_salle_18m()}


def test_effectif_total_et_par_division() -> None:
    """32 catégories : 16 Classique + 12 Poulies + 4 Nu (arc nu = 2 regroupements x Homme/Femme)."""
    modeles = categories_salle_18m()
    assert len(modeles) == 32
    par_arme = {"Arc Classique": 0, "Arc à Poulies": 0, "Arc Nu": 0}
    for modele in modeles:
        par_arme[modele.arme] += 1
    assert par_arme == {"Arc Classique": 16, "Arc à Poulies": 12, "Arc Nu": 4}


def test_seulement_homme_et_femme() -> None:
    """Le jeu individuel ne distingue que Homme/Femme (« Mixte » réservé aux équipes)."""
    sexes = {modele.sexe for modele in categories_salle_18m()}
    assert sexes == {SexeCategorie.HOMME, SexeCategorie.FEMME}


def test_libelles_uniques_et_non_vides() -> None:
    """Chaque catégorie a un libellé non vide et distinct des autres."""
    libelles = _libelles()
    assert all(libelle.strip() for libelle in libelles)
    assert len(set(libelles)) == len(libelles)


def test_chaque_modele_porte_au_moins_une_tranche() -> None:
    """Un modèle FFTA porte toujours arme + au moins une tranche typée (contrairement au CRUD)."""
    for modele in categories_salle_18m():
        assert isinstance(modele, ModeleCategorieFFTA)
        assert modele.arme
        assert modele.ages
        assert all(isinstance(tranche, TrancheAge) for tranche in modele.ages)


def test_classique_et_poulies_couvrent_une_seule_tranche() -> None:
    """Hors arc nu, une catégorie de classement = une tranche unique (pas de regroupement)."""
    for modele in categories_salle_18m():
        if modele.arme in ("Arc Classique", "Arc à Poulies"):
            assert len(modele.ages) == 1


def test_arc_nu_regroupe_plusieurs_tranches() -> None:
    """CA E01US013 : en arc nu, « U18 » couvre U15+U18 et « Scratch » couvre U21+S1+S2+S3."""
    ages_par_libelle = {m.libelle: m.ages for m in categories_salle_18m() if m.arme == "Arc Nu"}
    assert ages_par_libelle["Arc Nu U18 Homme"] == (TrancheAge.U15, TrancheAge.U18)
    assert ages_par_libelle["Arc Nu Scratch Femme"] == (
        TrancheAge.U21,
        TrancheAge.S1,
        TrancheAge.S2,
        TrancheAge.S3,
    )


def test_scratch_est_un_libelle_pas_une_tranche() -> None:
    """« Scratch » est un **libellé** de regroupement, jamais une valeur d'âge (CA E01US013)."""
    assert "Scratch" not in {tranche.value for tranche in TrancheAge}
    assert "Arc Nu Scratch Homme" in set(_libelles())


def test_bornes_par_division() -> None:
    """Poulies démarre à U15 (pas de U11/U13) — les tranches restent dans le vocabulaire fermé."""
    ages_poulies = {
        tranche
        for modele in categories_salle_18m()
        if modele.arme == "Arc à Poulies"
        for tranche in modele.ages
    }
    assert TrancheAge.U11 not in ages_poulies
    assert TrancheAge.U13 not in ages_poulies
    assert TrancheAge.U15 in ages_poulies


def test_eligibilite_unique_par_arme_et_sexe() -> None:
    """Invariant CA E01US013 : à (arme, sexe) fixés, les catégories ont des tranches **disjointes**.

    Un archer (arme, âge, sexe) retombe donc sur **au plus une** catégorie du jeu. On le vérifie ici
    comme une **propriété du preset** — l'agrégat `Archer` ne portant pas encore arme/âge/sexe, la
    vérification à l'exécution est hors périmètre de cette US (reportée à l'US qui les modélisera).
    """
    par_groupe: dict[tuple[str, SexeCategorie], list[frozenset[TrancheAge]]] = defaultdict(list)
    for modele in categories_salle_18m():
        par_groupe[(modele.arme, modele.sexe)].append(frozenset(modele.ages))
    for ensembles in par_groupe.values():
        deja_vues: set[TrancheAge] = set()
        for ensemble in ensembles:
            assert deja_vues.isdisjoint(ensemble), "deux catégories partagent une tranche d'âge"
            deja_vues |= ensemble


def test_hauteur_de_centre_u11_a_110_sinon_130() -> None:
    """E03US001 (ADR-0022) : les U11 tirent à 110 cm (blason 80 cm, §5), les autres à 130 cm."""
    for modele in categories_salle_18m():
        attendue = 110 if TrancheAge.U11 in modele.ages else 130
        assert modele.hauteur_cm == attendue, modele.libelle
    # Contrôle explicite d'au moins un U11, sans quoi le test passerait sur un jeu sans U11.
    hauteurs_u11 = {m.hauteur_cm for m in categories_salle_18m() if TrancheAge.U11 in m.ages}
    assert hauteurs_u11 == {110}


def test_exemples_de_libelles_attendus() -> None:
    """Quelques libellés de contrôle attestent la composition « arme âge/regroupement sexe »."""
    libelles = set(_libelles())
    assert "Arc Classique U11 Homme" in libelles
    assert "Arc à Poulies S3 Femme" in libelles
    assert "Arc Nu U18 Femme" in libelles
    assert "Arc Nu Scratch Homme" in libelles


# --- Blason par défaut du §3 (E01US022) -------------------------------------------------------


def test_blasons_salle_18m_est_le_jeu_du_paragraphe_3() -> None:
    """CA E01US022 : quatre blasons FFTA à 18 m — 80, 60, 40 (§3) et triple 40 (poulies)."""
    blasons = blasons_salle_18m()
    par_nom = {b.nom: b for b in blasons}
    assert set(par_nom) == {"Blason 80 cm", "Blason 60 cm", "Blason 40 cm", "Triple 40 cm"}
    # Tailles = fractions de place canoniques du placement (1/2/4 par butte, §5) ; un archer par
    # carton en qualification.
    assert (par_nom["Blason 80 cm"].taille, par_nom["Blason 80 cm"].capacite) == (1.0, 1)
    assert (par_nom["Blason 60 cm"].taille, par_nom["Blason 60 cm"].capacite) == (0.5, 1)
    assert (par_nom["Blason 40 cm"].taille, par_nom["Blason 40 cm"].capacite) == (0.25, 1)
    assert (par_nom["Triple 40 cm"].taille, par_nom["Triple 40 cm"].capacite) == (0.25, 1)


def test_triple_40_exclut_les_zones_5_a_1() -> None:
    """CA E01US022 (§4.4) : le triple 40 exclut 5 → 1 ; les simples gardent le jeu complet."""
    par_nom = {b.nom: b for b in blasons_salle_18m()}
    triple = par_nom["Triple 40 cm"]
    assert triple.zones == (
        ZoneScore.DIX,
        ZoneScore.NEUF,
        ZoneScore.HUIT,
        ZoneScore.SEPT,
        ZoneScore.SIX,
        ZoneScore.MANQUE,
    )
    # Les blasons simples n'imposent pas de zones : le domaine appliquera son jeu complet.
    assert par_nom["Blason 80 cm"].zones is None
    assert par_nom["Blason 60 cm"].zones is None
    assert par_nom["Blason 40 cm"].zones is None


def test_blason_par_defaut_classique_selon_la_tranche() -> None:
    """CA E01US022 (§3) : Classique U11 → 80 cm, U13/U15 → 60 cm, U18 et au-delà → 40 cm."""
    blason = _blason_par_libelle()
    assert blason["Arc Classique U11 Homme"] == "Blason 80 cm"
    assert blason["Arc Classique U13 Femme"] == "Blason 60 cm"
    assert blason["Arc Classique U15 Homme"] == "Blason 60 cm"
    for age in ("U18", "U21", "S1", "S2", "S3"):
        assert blason[f"Arc Classique {age} Homme"] == "Blason 40 cm", age


def test_blason_par_defaut_poulies_toujours_triple_40() -> None:
    """CA E01US022 (§3) : toutes les catégories Arc à Poulies tirent sur triples 40."""
    poulies = {m.blason_nom for m in categories_salle_18m() if m.arme == "Arc à Poulies"}
    assert poulies == {"Triple 40 cm"}


def test_blason_par_defaut_arc_nu_selon_le_regroupement() -> None:
    """CA E01US022 (§3) : Arc Nu « U18 » (=U15+U18) → 60 cm, « Scratch » (=U21..S3) → 40 cm."""
    blason = _blason_par_libelle()
    assert blason["Arc Nu U18 Homme"] == "Blason 60 cm"
    assert blason["Arc Nu U18 Femme"] == "Blason 60 cm"
    assert blason["Arc Nu Scratch Homme"] == "Blason 40 cm"
    assert blason["Arc Nu Scratch Femme"] == "Blason 40 cm"


def test_chaque_categorie_reference_un_blason_du_jeu() -> None:
    """Tout `blason_nom` de catégorie pointe vers un blason du jeu pré-chargé (pas d'orphelin)."""
    noms_blasons = {b.nom for b in blasons_salle_18m()}
    for modele in categories_salle_18m():
        assert modele.blason_nom in noms_blasons, modele.libelle
