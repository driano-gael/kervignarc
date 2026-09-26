"""le n° de licence de l'archer, unique dans le tournoi — E02US007, ADR-0115

Revision ID: 0058_archer_licence
Revises: 0056_ancrage_par_identite
Create Date: 2026-09-26

Colonne **nullable** : la licence reste facultative au guichet (ADR-0014). L'unicité est un index
**partiel** (``WHERE licence IS NOT NULL``) : un ``UNIQUE`` plein refuserait deux archers sans
licence. Il double la garde de ``ServiceArchers`` et du plan d'import, il ne la remplace pas.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0058_archer_licence"
down_revision = "0056_ancrage_par_identite"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("archer", sa.Column("licence", sa.String(), nullable=True))
    op.create_index(
        "uq_archer_tournoi_licence",
        "archer",
        ["tournoi_id", "licence"],
        unique=True,
        sqlite_where=sa.text("licence IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_archer_tournoi_licence", table_name="archer")
    with op.batch_alter_table("archer") as batch:
        batch.drop_column("licence")
