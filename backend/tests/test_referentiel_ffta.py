"""Tests du référentiel FFTA des catégories salle 18 m (E01US004) — données pures.

Vérifie que le jeu pré-chargeable correspond aux catégories **officielles par division** du
`docs/referentiel-ffta.md` §3 (et non un produit cartésien inventant des catégories non ouvertes).
"""

from __future__ import annotations

from application.referentiel_ffta import ModeleCategorieFFTA, categories_salle_18m
from domain.categorie import SexeCategorie


def _libelles() -> list[str]:
    return [modele.libelle for modele in categories_salle_18m()]


def test_effectif_total_et_par_division() -> None:
    """32 catégories au total : 16 Classique + 12 Poulies + 4 Nu (chaque âge x Homme/Femme)."""
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


def test_attributs_toujours_renseignes() -> None:
    """Un modèle FFTA porte toujours arme + tranche d'âge (contrairement au CRUD libre)."""
    for modele in categories_salle_18m():
        assert isinstance(modele, ModeleCategorieFFTA)
        assert modele.arme
        assert modele.tranche_age


def test_bornes_par_division() -> None:
    """Poulies démarre à U15 (pas de U11/U13) ; Arc Nu est regroupé (U18 + Scratch)."""
    ages_poulies = {m.tranche_age for m in categories_salle_18m() if m.arme == "Arc à Poulies"}
    ages_nu = {m.tranche_age for m in categories_salle_18m() if m.arme == "Arc Nu"}
    assert "U11" not in ages_poulies
    assert "U13" not in ages_poulies
    assert ages_nu == {"U18", "Scratch"}


def test_exemples_de_libelles_attendus() -> None:
    """Quelques libellés de contrôle attestent la composition « arme âge sexe »."""
    libelles = set(_libelles())
    assert "Arc Classique U11 Homme" in libelles
    assert "Arc à Poulies Senior 3 Femme" in libelles
    assert "Arc Nu Scratch Homme" in libelles
