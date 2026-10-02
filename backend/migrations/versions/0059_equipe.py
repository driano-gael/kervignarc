"""tables equipe et membre_equipe — les équipes d'un tournoi et leurs membres (E13US002)

Revision ID: 0059_equipe
Revises: 0058_archer_licence
Create Date: 2026-10-01

Enfants du tournoi : FK **sans `ON DELETE`** (ADR-0077, purge applicative dans
`TournoiRepositorySQL.supprimer`). Correspond aux modèles ORM `EquipeORM` et `MembreEquipeORM`.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0059_equipe"
down_revision = "0058_archer_licence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "equipe",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournoi_id", sa.Integer(), nullable=False),
        sa.Column("nom", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("effectif_attendu", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tournoi_id"], ["tournoi.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tournoi_id", "nom", name="uq_equipe_tournoi_nom"),
    )
    op.create_table(
        "membre_equipe",
        sa.Column("equipe_id", sa.Integer(), nullable=False),
        sa.Column("archer_id", sa.Integer(), nullable=False),
        sa.Column("ordre", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["equipe_id"], ["equipe.id"]),
        sa.ForeignKeyConstraint(["archer_id"], ["archer.id"]),
        sa.PrimaryKeyConstraint("equipe_id", "archer_id"),
    )


def downgrade() -> None:
    op.drop_table("membre_equipe")
    op.drop_table("equipe")
