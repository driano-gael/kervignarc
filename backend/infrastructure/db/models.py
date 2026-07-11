"""Modèles ORM SQLAlchemy — mapping des agrégats vers les tables (E00US009).

**Séparés du domaine** : le domaine ignore SQLAlchemy (ADR-0003). Un repository
(`repositories.py`) traduit dans les deux sens ORM ↔ agrégat de domaine. Ces classes
peuplent `Base.metadata`, cible des migrations Alembic.
"""

from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base


class TournoiORM(Base):
    """Table `tournoi` — persistance de l'agrégat `Tournoi`."""

    __tablename__ = "tournoi"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(nullable=False)
