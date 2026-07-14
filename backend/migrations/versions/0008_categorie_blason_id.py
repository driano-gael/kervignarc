"""catégorie : blason par défaut (FK blason_id)

Revision ID: 0008_categorie_blason_id
Revises: 0007_blason
Create Date: 2026-07-14

Ajoute à `categorie` une colonne `blason_id` (E01US006) : le **blason par défaut** de la
catégorie, facultatif (`NULL` = aucun), avec une FK vers `blason.id`. Exploité par le placement
(EPIC-03). SQLite ne sait pas ajouter une contrainte par `ALTER TABLE` : on passe par le mode
**batch** d'Alembic (recréation de la table). Correspond au modèle ORM `CategorieORM`.

DETTE-001 (docs/dette.md) : la FK est posée **sans** `ON DELETE CASCADE`, comme le reste de la
descendance du tournoi ; la politique de suppression reste à trancher dans l'US dédiée.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_categorie_blason_id"
down_revision: str | None = "0007_blason"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ajoute `categorie.blason_id` (nullable) et sa FK vers `blason.id`."""
    with op.batch_alter_table("categorie") as batch:
        batch.add_column(sa.Column("blason_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_categorie_blason_id", "blason", ["blason_id"], ["id"])


def downgrade() -> None:
    """Retire la FK et la colonne `blason_id`."""
    with op.batch_alter_table("categorie") as batch:
        batch.drop_constraint("fk_categorie_blason_id", type_="foreignkey")
        batch.drop_column("blason_id")
