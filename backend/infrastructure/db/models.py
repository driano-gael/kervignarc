"""Modèles ORM SQLAlchemy — mapping des agrégats vers les tables (E00US009).

**Séparés du domaine** : le domaine ignore SQLAlchemy (ADR-0003). Un repository
(`repositories.py`) traduit dans les deux sens ORM ↔ agrégat de domaine. Ces classes
peuplent `Base.metadata`, cible des migrations Alembic.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.base import Base


class TournoiORM(Base):
    """Table `tournoi` — persistance de l'agrégat `Tournoi`."""

    __tablename__ = "tournoi"

    id: Mapped[int] = mapped_column(primary_key=True)
    nom: Mapped[str] = mapped_column(nullable=False)


class ArcherORM(Base):
    """Table `archer` — persistance de l'agrégat `Archer` (E00US011)."""

    __tablename__ = "archer"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournoi_id: Mapped[int] = mapped_column(ForeignKey("tournoi.id"), nullable=False)
    nom: Mapped[str] = mapped_column(nullable=False)
    cible: Mapped[int | None] = mapped_column(nullable=True)


class ScoreORM(Base):
    """Table `score` — persistance de l'agrégat `Score` (E00US011)."""

    __tablename__ = "score"

    id: Mapped[int] = mapped_column(primary_key=True)
    archer_id: Mapped[int] = mapped_column(ForeignKey("archer.id"), nullable=False)
    points: Mapped[int] = mapped_column(nullable=False)
