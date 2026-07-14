"""Erreurs du domaine (ADR-0007) — une règle métier est violée.

Racine `DomainError` : le domaine **ignore HTTP**. La traduction en réponse (HTTP 422,
code métier) se fait uniquement à la frontière API (`api/erreurs.py`).
"""

from __future__ import annotations


class DomainError(Exception):
    """Racine des erreurs métier. Chaque sous-classe porte un `code` stable."""

    code = "erreur_domaine"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NomTournoiInvalide(DomainError):
    """Le nom d'un tournoi est vide (après normalisation)."""

    code = "nom_tournoi_invalide"


class NomArcherInvalide(DomainError):
    """Le nom d'un archer est vide (après normalisation)."""

    code = "nom_archer_invalide"


class LibelleCategorieInvalide(DomainError):
    """Le libellé d'une catégorie est vide (après normalisation)."""

    code = "libelle_categorie_invalide"


class NomBlasonInvalide(DomainError):
    """Le nom d'un blason est vide (après normalisation)."""

    code = "nom_blason_invalide"


class TailleBlasonInvalide(DomainError):
    """La taille d'un blason sort de la plage autorisée (fraction de place `]0, 1]`)."""

    code = "taille_blason_invalide"


class CapaciteBlasonInvalide(DomainError):
    """La capacité d'un blason est inférieure à 1."""

    code = "capacite_blason_invalide"


class NomGabaritInvalide(DomainError):
    """Le nom d'un gabarit de salle est vide (après normalisation)."""

    code = "nom_gabarit_invalide"


class NombreCiblesInvalide(DomainError):
    """Le nombre de cibles d'un gabarit de salle est inférieur à 1."""

    code = "nombre_cibles_invalide"


class CapaciteCibleInvalide(DomainError):
    """Le plafond d'archers d'une cible sort de la plage autorisée (`[1, 4]`)."""

    code = "capacite_cible_invalide"


class CibleInvalide(DomainError):
    """Le numéro de cible d'un placement n'est pas un entier strictement positif."""

    code = "cible_invalide"


class NombreVoleesInvalide(DomainError):
    """Le nombre de volées d'un barème de qualification est inférieur à 1."""

    code = "nombre_volees_invalide"


class NombreFlechesParVoleeInvalide(DomainError):
    """Le nombre de flèches par volée d'un barème de qualification est inférieur à 1."""

    code = "nombre_fleches_par_volee_invalide"


class ScoreInvalide(DomainError):
    """La valeur d'un score sort de la plage autorisée pour une flèche (0 à 10)."""

    code = "score_invalide"
