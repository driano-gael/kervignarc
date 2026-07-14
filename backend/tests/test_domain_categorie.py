"""Tests unitaires de l'agrégat Categorie (E01US003) — domaine pur, sans base."""

from __future__ import annotations

import pytest

from domain.categorie import Categorie, SexeCategorie
from domain.erreurs import LibelleCategorieInvalide


def test_creer_une_categorie_valide() -> None:
    """Libellé seul suffit : arme/âge/sexe à None, id à None, rattachée au tournoi."""
    categorie = Categorie.creer(1, "Senior Homme Arc Classique")
    assert categorie == Categorie(
        tournoi_id=1,
        libelle="Senior Homme Arc Classique",
        arme=None,
        tranche_age=None,
        sexe=None,
        id=None,
    )


def test_creer_avec_attributs() -> None:
    """Arme, tranche d'âge et sexe explicites sont conservés."""
    categorie = Categorie.creer(1, "Senior H Classique", "classique", "senior", SexeCategorie.HOMME)
    assert categorie.arme == "classique"
    assert categorie.tranche_age == "senior"
    assert categorie.sexe is SexeCategorie.HOMME


def test_creer_normalise_les_textes() -> None:
    """Libellé, arme et tranche d'âge sont normalisés (espaces de bord retirés)."""
    categorie = Categorie.creer(1, "  Senior  ", "  poulie  ", "  vétéran  ")
    assert categorie.libelle == "Senior"
    assert categorie.arme == "poulie"
    assert categorie.tranche_age == "vétéran"


def test_creer_champs_facultatifs_vides_deviennent_none() -> None:
    """Une arme ou une tranche d'âge vide ou blanche est facultative → None."""
    categorie = Categorie.creer(1, "Libre", "   ", "")
    assert categorie.arme is None
    assert categorie.tranche_age is None


@pytest.mark.parametrize("libelle", ["", "   ", "\t\n"])
def test_creer_refuse_un_libelle_vide(libelle: str) -> None:
    """Un libellé vide ou blanc lève une erreur de domaine typée."""
    with pytest.raises(LibelleCategorieInvalide):
        Categorie.creer(1, libelle)


def test_modifier_met_a_jour_et_preserve_id_et_tournoi() -> None:
    """`modifier` change les attributs mais conserve `id` et `tournoi_id`."""
    categorie = Categorie(
        tournoi_id=3,
        libelle="Ancien",
        arme=None,
        tranche_age=None,
        sexe=None,
        id=9,
    )
    modifiee = categorie.modifier("Nouveau", "nu", "cadet", SexeCategorie.FEMME)
    assert modifiee == Categorie(
        tournoi_id=3,
        libelle="Nouveau",
        arme="nu",
        tranche_age="cadet",
        sexe=SexeCategorie.FEMME,
        id=9,
    )


def test_modifier_valide_le_libelle() -> None:
    """`modifier` applique les mêmes règles que `creer` (libellé non vide)."""
    categorie = Categorie.creer(1, "Libre")
    with pytest.raises(LibelleCategorieInvalide):
        categorie.modifier("   ")


def test_creer_sans_blason_par_defaut() -> None:
    """E01US006 : sans blason précisé, `blason_id` vaut None (aucun blason par défaut)."""
    assert Categorie.creer(1, "Libre").blason_id is None


def test_creer_avec_blason_par_defaut() -> None:
    """E01US006 : `blason_id` transporte le blason par défaut (l'agrégat ne le valide pas)."""
    categorie = Categorie.creer(1, "Senior H", blason_id=42)
    assert categorie.blason_id == 42


def test_modifier_change_puis_retire_le_blason() -> None:
    """E01US006 : `modifier` remplace le blason par défaut, `None` le retire."""
    categorie = Categorie.creer(1, "Senior H", blason_id=42)
    assert categorie.modifier("Senior H", blason_id=7).blason_id == 7
    assert categorie.modifier("Senior H").blason_id is None
