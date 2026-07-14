"""table blason (blasons d'un tournoi)

Revision ID: 0007_blason
Revises: 0006_categorie
Create Date: 2026-07-14

Table `blason` (E01US005) : un blason appartient à un tournoi et modélise l'occupation d'une
cible. `nom` est obligatoire ; `taille` est une fraction de place (`0 < taille <= 1`) et
`capacite` un entier `>= 1` (validation portée par le domaine). Correspond au modèle ORM
`BlasonORM`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_blason"
down_revision: str | None = "0006_categorie"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée la table `blason`."""
    op.create_table(
        "blason",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournoi_id", sa.Integer(), nullable=False),
        sa.Column("nom", sa.String(), nullable=False),
        sa.Column("taille", sa.Float(), nullable=False),
        sa.Column("capacite", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tournoi_id"], ["tournoi.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Supprime la table `blason`."""
    op.drop_table("blason")
