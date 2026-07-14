"""gabarit_salle : instance appliquée à un tournoi (FK tournoi_id)

Revision ID: 0010_gabarit_tournoi
Revises: 0009_gabarit_salle
Create Date: 2026-07-14

Ajoute à `gabarit_salle` une colonne `tournoi_id` (E01US008) : `NULL` = **modèle** de
bibliothèque (réutilisable, E01US007), renseigné = **instance** appliquée à un tournoi (copie
ajustable propre à ce tournoi). SQLite ne sait pas ajouter une contrainte par `ALTER TABLE` : on
passe par le mode **batch** d'Alembic (recréation de la table). Correspond au modèle ORM
`GabaritSalleORM`.

DETTE-001 (docs/dette.md) : la FK est posée **sans** `ON DELETE CASCADE`, comme le reste de la
descendance du tournoi ; la politique de suppression reste à trancher dans l'US dédiée.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_gabarit_tournoi"
down_revision: str | None = "0009_gabarit_salle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ajoute `gabarit_salle.tournoi_id` (nullable) et sa FK vers `tournoi.id`."""
    with op.batch_alter_table("gabarit_salle") as batch:
        batch.add_column(sa.Column("tournoi_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_gabarit_salle_tournoi_id", "tournoi", ["tournoi_id"], ["id"])


def downgrade() -> None:
    """Retire la FK et la colonne `tournoi_id`."""
    with op.batch_alter_table("gabarit_salle") as batch:
        batch.drop_constraint("fk_gabarit_salle_tournoi_id", type_="foreignkey")
        batch.drop_column("tournoi_id")
