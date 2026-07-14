"""Agrégat `Blason` — une cible en carton d'un tournoi (E01US005).

Modélise l'**occupation d'une cible** : un blason porte un `nom`, une `taille` (fraction de
place occupée sur une cible, `0 < taille <= 1`) et une `capacite` (nombre d'archers admis,
`>= 1`). Agrégat de domaine **pur** (aucune dépendance framework, immuable), validé à la
création/édition. Les blasons appartiennent à un tournoi ; l'association d'une **catégorie** à
un blason par défaut viendra en E01US006. Reprend et formalise le prototype `Blason`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from domain.erreurs import CapaciteBlasonInvalide, NomBlasonInvalide, TailleBlasonInvalide
from domain.tournoi import TournoiId

BlasonId = int
"""Identifiant technique d'un blason, attribué par la persistance."""


@dataclass(frozen=True)
class Blason:
    """Un blason rattaché à un tournoi. `id` vaut `None` tant qu'il n'est pas persisté."""

    tournoi_id: TournoiId
    nom: str
    taille: float
    capacite: int
    id: BlasonId | None = None

    @staticmethod
    def creer(tournoi_id: TournoiId, nom: str, taille: float, capacite: int) -> Blason:
        """Crée un blason valide.

        Le `nom` est normalisé (espaces de bord retirés) et ne peut pas être vide ; la `taille`
        doit être dans `]0, 1]` (fraction de place) ; la `capacite` doit être un entier `>= 1`.
        Lève l'erreur de domaine correspondante en cas de valeur invalide.
        """
        return Blason(
            tournoi_id=tournoi_id,
            nom=_nom_valide(nom),
            taille=_taille_valide(taille),
            capacite=_capacite_valide(capacite),
        )

    def modifier(self, nom: str, taille: float, capacite: int) -> Blason:
        """Renvoie une copie aux attributs mis à jour (mêmes règles que `creer`).

        L'`id` et le `tournoi_id` sont **préservés** (on ne déplace pas un blason d'un tournoi à
        l'autre). Lève l'erreur de domaine correspondante en cas de valeur invalide.
        """
        return replace(
            self,
            nom=_nom_valide(nom),
            taille=_taille_valide(taille),
            capacite=_capacite_valide(capacite),
        )


def _nom_valide(nom: str) -> str:
    """Normalise le nom ; lève `NomBlasonInvalide` s'il est vide."""
    nom_normalise = nom.strip()
    if not nom_normalise:
        raise NomBlasonInvalide("Le nom d'un blason ne peut pas être vide.")
    return nom_normalise


def _taille_valide(taille: float) -> float:
    """Vérifie que la taille est une fraction de place dans `]0, 1]`."""
    if not 0 < taille <= 1:
        raise TailleBlasonInvalide(
            "La taille d'un blason doit être une fraction de place strictement positive "
            "et au plus égale à 1."
        )
    return taille


def _capacite_valide(capacite: int) -> int:
    """Vérifie que la capacité est un entier `>= 1`."""
    if capacite < 1:
        raise CapaciteBlasonInvalide("La capacité d'un blason doit être d'au moins 1.")
    return capacite
