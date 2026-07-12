"""Erreurs applicatives (ADR-0007) — un cas d'usage est impossible.

Racine `ApplicationError`. Traduites à la frontière API en 404 (ressource introuvable)
ou 409 (conflit d'état) ; la couche application, elle, ignore HTTP.
"""

from __future__ import annotations


class ApplicationError(Exception):
    """Racine des erreurs de cas d'usage. Chaque sous-classe porte un `code` stable."""

    code = "erreur_application"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class TournoiIntrouvable(ApplicationError):
    """Aucun tournoi ne correspond à l'identifiant demandé."""

    code = "tournoi_introuvable"


class ArcherIntrouvable(ApplicationError):
    """Aucun archer ne correspond à l'identifiant demandé."""

    code = "archer_introuvable"
