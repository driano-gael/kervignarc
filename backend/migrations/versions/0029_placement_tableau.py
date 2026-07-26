"""placement_tableau : plan de duels matérialisé (pose d'un duelliste par phase)

Revision ID: 0029_placement_tableau
Revises: 0028_phase_config_policies
Create Date: 2026-07-26

E03US009 (ADR-0048). Le **plan de duels** — placement des duellistes d'une phase de tableau côte à
côte — est **matérialisé** pour être ajustable (glisser-déposer), à l'image du plan de cibles de
qualification (`placement`, 0022). Distinct de celui-ci : scoppé par **phase**, clé primaire
**composite** `(phase_id, inscription_id)` — un archer a une pose en qualif *et* une en tableau.
Un inscrit **sans** ligne est en réserve.

**`ON DELETE CASCADE`**, à rebours de DETTE-001 : donnée dérivée, reconstructible (l'appariement est
recalculé du classement, la pose seule est persistée) et feuille — sa disparition suit celle de la
phase ou de l'inscription (cf. ADR-0024/0048). Pas de backfill : aucune phase n'a de plan de duels
tant que l'admin ne le génère pas (tout en réserve).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029_placement_tableau"
down_revision: str | None = "0028_phase_config_policies"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée `placement_tableau` (pose par (phase, inscription)), FK cascade phase/inscription."""
    op.create_table(
        "placement_tableau",
        sa.Column("phase_id", sa.Integer(), nullable=False),
        sa.Column("inscription_id", sa.Integer(), nullable=False),
        sa.Column("cible_index", sa.Integer(), nullable=False),
        sa.Column("position", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["phase_id"], ["phase.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inscription_id"], ["inscription.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("phase_id", "inscription_id"),
    )


def downgrade() -> None:
    """Retire `placement_tableau` — la donnée (dérivée) est perdue, régénérable par l'auto."""
    op.drop_table("placement_tableau")
