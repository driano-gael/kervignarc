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


class IdentifiantsInvalides(ApplicationError):
    """Login/mot de passe admin incorrects (E10US002). Traduite en 401 à la frontière."""

    code = "identifiants_invalides"


class NonAuthentifie(ApplicationError):
    """Action admin demandée sans session valide (E10US002). Traduite en 401."""

    code = "non_authentifie"


class AccesDejaConfigure(ApplicationError):
    """Tentative de (re)définir l'accès admin alors qu'il existe déjà (E10US002) → 409."""

    code = "acces_deja_configure"


class AccesNonConfigure(ApplicationError):
    """Connexion demandée alors qu'aucun accès admin n'est encore défini (E10US002) → 409."""

    code = "acces_non_configure"
