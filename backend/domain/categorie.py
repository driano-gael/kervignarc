"""Agrégat `Categorie` — une catégorie de tir d'un tournoi (E01US003).

Sert à **classer et cloisonner** les archers (arme, tranche d'âge, sexe). Agrégat de domaine
**pur** (aucune dépendance framework, immuable), validé à la création/édition : seul le `libelle`
est obligatoire ; `arme`, `tranche_age` et `sexe` sont facultatifs (le référentiel FFTA officiel
sera pré-chargé et modifiable en E01US004). L'association à un **blason** par défaut viendra en
E01US006 (le blason n'existe qu'à partir d'E01US005).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from domain.erreurs import LibelleCategorieInvalide
from domain.tournoi import TournoiId

CategorieId = int
"""Identifiant technique d'une catégorie, attribué par la persistance."""


class SexeCategorie(str, Enum):
    """Sexe d'une catégorie : homme, femme ou mixte (facultatif au niveau de la catégorie)."""

    HOMME = "H"
    FEMME = "F"
    MIXTE = "mixte"


@dataclass(frozen=True)
class Categorie:
    """Une catégorie rattachée à un tournoi. `id` vaut `None` tant qu'elle n'est pas persistée."""

    tournoi_id: TournoiId
    libelle: str
    arme: str | None = None
    tranche_age: str | None = None
    sexe: SexeCategorie | None = None
    id: CategorieId | None = None

    @staticmethod
    def creer(
        tournoi_id: TournoiId,
        libelle: str,
        arme: str | None = None,
        tranche_age: str | None = None,
        sexe: SexeCategorie | None = None,
    ) -> Categorie:
        """Crée une catégorie valide ; lève `LibelleCategorieInvalide` si le libellé est vide.

        Le libellé, l'arme et la tranche d'âge sont normalisés (espaces de bord retirés) ; une
        valeur vide devient `None` pour les champs facultatifs.
        """
        return Categorie(
            tournoi_id=tournoi_id,
            libelle=_libelle_valide(libelle),
            arme=_texte_facultatif(arme),
            tranche_age=_texte_facultatif(tranche_age),
            sexe=sexe,
        )

    def modifier(
        self,
        libelle: str,
        arme: str | None = None,
        tranche_age: str | None = None,
        sexe: SexeCategorie | None = None,
    ) -> Categorie:
        """Renvoie une copie aux attributs mis à jour (mêmes règles que `creer`).

        L'`id` et le `tournoi_id` sont **préservés** (on ne déplace pas une catégorie d'un
        tournoi à l'autre). Lève `LibelleCategorieInvalide` si le libellé est vide.
        """
        return replace(
            self,
            libelle=_libelle_valide(libelle),
            arme=_texte_facultatif(arme),
            tranche_age=_texte_facultatif(tranche_age),
            sexe=sexe,
        )


def _libelle_valide(libelle: str) -> str:
    """Normalise le libellé ; lève `LibelleCategorieInvalide` s'il est vide."""
    libelle_normalise = libelle.strip()
    if not libelle_normalise:
        raise LibelleCategorieInvalide("Le libellé d'une catégorie ne peut pas être vide.")
    return libelle_normalise


def _texte_facultatif(valeur: str | None) -> str | None:
    """Normalise un champ texte facultatif ; une valeur vide ou absente devient `None`."""
    if valeur is None:
        return None
    valeur_normalisee = valeur.strip()
    return valeur_normalisee or None
