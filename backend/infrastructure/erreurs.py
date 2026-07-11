"""Erreurs d'infrastructure (ADR-0007) — une panne technique survient (DB, IO).

Racine `InfrastructureError`. Les adapters **enveloppent** les exceptions techniques
(ex. SQLAlchemy) dans cette famille : le domaine et l'application ne voient jamais
d'exception de bibliothèque brute. Traduite à la frontière API en 500, message générique
(le détail reste journalisé côté serveur).
"""

from __future__ import annotations


class InfrastructureError(Exception):
    """Racine des pannes techniques (persistance, entrées-sorties)."""

    code = "erreur_infrastructure"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
