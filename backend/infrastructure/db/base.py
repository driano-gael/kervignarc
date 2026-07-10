"""Base déclarative SQLAlchemy — métadonnées de schéma partagées.

Toutes les tables (mappées en E00US009 et au-delà) héritent de `Base` ; sa
`metadata` sert de cible à l'autogénération Alembic (`migrations/env.py`).
Aucune table n'est encore déclarée : la migration initiale est une **baseline**.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Racine déclarative de tous les modèles ORM du projet."""
