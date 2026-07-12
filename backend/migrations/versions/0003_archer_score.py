"""tables archer et score (tranche verticale)

Revision ID: 0003_archer_score
Revises: 0002_tournoi
Create Date: 2026-07-12

Tables métier de la tranche verticale (E00US011) : un `archer` appartient à un tournoi et
peut être placé sur une cible ; un `score` est une flèche marquée par un archer. Correspond
aux modèles ORM `ArcherORM` / `ScoreORM`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_archer_score"
down_revision: str | None = "0002_tournoi"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée les tables `archer` et `score`."""
    op.create_table(
        "archer",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournoi_id", sa.Integer(), nullable=False),
        sa.Column("nom", sa.String(), nullable=False),
        sa.Column("cible", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["tournoi_id"], ["tournoi.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "score",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("archer_id", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["archer_id"], ["archer.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Supprime les tables `score` et `archer`."""
    op.drop_table("score")
    op.drop_table("archer")
