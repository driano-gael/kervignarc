"""placement : plan de cibles matérialisé (affectation d'un inscrit sur une case)

Revision ID: 0022_placement
Revises: 0021_depart_quota
Create Date: 2026-07-18

E03US004 (ADR-0024). Le plan de cibles cesse d'être recalculé à la demande (E03US001) : il est
**matérialisé** pour être ajustable (glisser-déposer, réserve, échange). Une ligne = un inscrit
**posé** sur une case (`inscription_id` en clé primaire) ; un inscrit **sans** ligne est en réserve.

**`ON DELETE CASCADE`**, à rebours de DETTE-001 : donnée dérivée, reconstructible et feuille — sa
disparition suit celle de l'inscription/du départ (cf. ADR-0024). Pas de backfill : les départs
existants n'ont pas de plan matérialisé tant que l'admin ne le génère pas (tout en réserve).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_placement"
down_revision: str | None = "0021_depart_quota"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée la table `placement` (affectation par inscription), FK cascade inscription/départ."""
    op.create_table(
        "placement",
        sa.Column("inscription_id", sa.Integer(), nullable=False),
        sa.Column("depart_id", sa.Integer(), nullable=False),
        sa.Column("cible_index", sa.Integer(), nullable=False),
        sa.Column("position", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["inscription_id"], ["inscription.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["depart_id"], ["depart.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("inscription_id"),
    )


def downgrade() -> None:
    """Retire la table `placement` — la donnée (dérivée) est perdue, régénérable par l'auto."""
    op.drop_table("placement")
