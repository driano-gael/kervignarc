"""table tournoi (agrégat trivial du walking skeleton)

Revision ID: 0002_tournoi
Revises: 0001_initiale
Create Date: 2026-07-11

Première table métier (E00US009) : persiste l'agrégat `Tournoi` (gabarit de bout en bout).
Correspond au modèle ORM `infrastructure.db.models.TournoiORM`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_tournoi"
down_revision: str | None = "0001_initiale"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée la table `tournoi`."""
    op.create_table(
        "tournoi",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nom", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Supprime la table `tournoi`."""
    op.drop_table("tournoi")
