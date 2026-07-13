"""table categorie (catégories d'un tournoi)

Revision ID: 0006_categorie
Revises: 0005_tournoi_statut
Create Date: 2026-07-13

Table `categorie` (E01US003) : une catégorie de tir appartient à un tournoi et sert à classer
les archers. Seul `libelle` est obligatoire ; `arme`, `tranche_age` et `sexe` sont facultatifs
(le référentiel FFTA officiel sera pré-chargé en E01US004). Correspond au modèle ORM `CategorieORM`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_categorie"
down_revision: str | None = "0005_tournoi_statut"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée la table `categorie`."""
    op.create_table(
        "categorie",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournoi_id", sa.Integer(), nullable=False),
        sa.Column("libelle", sa.String(), nullable=False),
        sa.Column("arme", sa.String(), nullable=True),
        sa.Column("tranche_age", sa.String(), nullable=True),
        sa.Column("sexe", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["tournoi_id"], ["tournoi.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Supprime la table `categorie`."""
    op.drop_table("categorie")
