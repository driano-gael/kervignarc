"""Tests unitaires de l'agrégat Categorie (E01US003 ; `ages` multi-tranches : E01US013).

Domaine pur, sans base. La bascule de `tranche_age` (scalaire texte libre) vers `ages` (liste
fermée de `TrancheAge`) est le cœur d'E01US013 : une catégorie couvre **une ou plusieurs** tranches.
"""

from __future__ import annotations

import pytest

from domain.categorie import Categorie, SexeCategorie, TrancheAge
from domain.erreurs import LibelleCategorieInvalide


def test_creer_une_categorie_valide() -> None:
    """Libellé seul suffit : arme/ages/sexe vides, id à None, rattachée au tournoi."""
    categorie = Categorie.creer(1, "Senior Homme Arc Classique")
    assert categorie == Categorie(
        tournoi_id=1,
        libelle="Senior Homme Arc Classique",
        arme=None,
        ages=(),
        sexe=None,
        id=None,
    )


def test_creer_avec_attributs() -> None:
    """Arme, tranche d'âge (unique) et sexe explicites sont conservés."""
    categorie = Categorie.creer(
        1, "Senior H Classique", "classique", (TrancheAge.S1,), SexeCategorie.HOMME
    )
    assert categorie.arme == "classique"
    assert categorie.ages == (TrancheAge.S1,)
    assert categorie.sexe is SexeCategorie.HOMME


def test_creer_accepte_plusieurs_tranches() -> None:
    """CA E01US013 : une catégorie couvre plusieurs tranches (arc nu « U18 » = U15 + U18)."""
    categorie = Categorie.creer(1, "Arc Nu U18 H", "Arc Nu", (TrancheAge.U15, TrancheAge.U18))
    assert categorie.ages == (TrancheAge.U15, TrancheAge.U18)


def test_creer_dedoublonne_et_ordonne_les_tranches() -> None:
    """`ages` est un **ensemble** d'éligibilité : dédoublonné et remis dans l'ordre d'âge (U11→S3).

    L'appelant peut passer les tranches dans n'importe quel ordre, avec des répétitions ; deux
    catégories aux mêmes tranches sont alors égales, quelle que soit la saisie.
    """
    categorie = Categorie.creer(1, "Cat", ages=(TrancheAge.U18, TrancheAge.U15, TrancheAge.U18))
    assert categorie.ages == (TrancheAge.U15, TrancheAge.U18)


def test_creer_sans_tranche_a_des_ages_vides() -> None:
    """Sans tranche précisée, `ages` est vide (aucune contrainte) — pendant de l'ancien `None`."""
    assert Categorie.creer(1, "Libre").ages == ()


def test_creer_normalise_le_libelle_et_l_arme() -> None:
    """Libellé et arme restent normalisés (espaces de bord retirés) ; les tranches sont un enum."""
    categorie = Categorie.creer(1, "  Senior  ", "  poulie  ", (TrancheAge.S2,))
    assert categorie.libelle == "Senior"
    assert categorie.arme == "poulie"
    assert categorie.ages == (TrancheAge.S2,)


def test_creer_arme_vide_devient_none() -> None:
    """Une arme vide ou blanche reste facultative → None (les ages, eux, sont un enum typé)."""
    assert Categorie.creer(1, "Libre", "   ").arme is None


@pytest.mark.parametrize("libelle", ["", "   ", "\t\n"])
def test_creer_refuse_un_libelle_vide(libelle: str) -> None:
    """Un libellé vide ou blanc lève une erreur de domaine typée."""
    with pytest.raises(LibelleCategorieInvalide):
        Categorie.creer(1, libelle)


def test_modifier_met_a_jour_et_preserve_id_et_tournoi() -> None:
    """`modifier` change les attributs (dont `ages`) mais conserve `id` et `tournoi_id`."""
    categorie = Categorie(tournoi_id=3, libelle="Ancien", arme=None, ages=(), sexe=None, id=9)
    modifiee = categorie.modifier("Nouveau", "nu", (TrancheAge.U18,), SexeCategorie.FEMME)
    assert modifiee == Categorie(
        tournoi_id=3,
        libelle="Nouveau",
        arme="nu",
        ages=(TrancheAge.U18,),
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
