"""Tests du référentiel FFTA des catégories salle 18 m (E01US004 ; regroupements d'âge : E01US013).

Vérifie que le jeu pré-chargeable correspond aux catégories **officielles par division** du
`docs/referentiel-ffta.md` §3 — dont les **regroupements d'âge** de l'arc nu, que la bascule vers
`ages` (liste) permet enfin d'exprimer fidèlement (« U18 » = U15+U18, « Scratch » = U21..S3), là où
un scalaire `tranche_age` les écrasait.
"""

from __future__ import annotations

from collections import defaultdict

from application.referentiel_ffta import ModeleCategorieFFTA, categories_salle_18m
from domain.categorie import SexeCategorie, TrancheAge


def _libelles() -> list[str]:
    return [modele.libelle for modele in categories_salle_18m()]


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


def test_exemples_de_libelles_attendus() -> None:
    """Quelques libellés de contrôle attestent la composition « arme âge/regroupement sexe »."""
    libelles = set(_libelles())
    assert "Arc Classique U11 Homme" in libelles
    assert "Arc à Poulies S3 Femme" in libelles
    assert "Arc Nu U18 Femme" in libelles
    assert "Arc Nu Scratch Homme" in libelles
