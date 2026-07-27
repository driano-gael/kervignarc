"""forfait : abandon / disqualification d'un archer (E04US015, ADR-0050)

Table `forfait` — une ligne par `(tournoi, archer, phase)`. On persiste **qui** déclare
(`declare_par`, un nom, pas une FK — la trace survit à la suppression du scoreur), **quand**
(`declare_le`, UTC), la **nature** (`abandon` / `disqualification`, valeur d'énum stockée telle
quelle) et un **motif** optionnel. Un abandon **relègue** l'archer au classement de qualif, une DSQ
l'en **sort** ; en duels, un forfait fait **passer l'adversaire**. Les flèches (`serie`/`volee`) ne
sont **jamais** touchées : l'annulation supprime seulement cette ligne.

`ON DELETE CASCADE` sur `phase_id` (feuille dérivée d'une phase, comme `duel`/`placement_tableau`).
Les FK `tournoi_id`/`archer_id` restent sans `ON DELETE` (DETTE-001, comme `serie`/`entree_audit`).

Revision ID: 0031_forfait
Revises: 0030_duel
Create Date: 2026-07-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031_forfait"
down_revision: str | None = "0030_duel"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "forfait",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournoi_id", sa.Integer(), nullable=False),
        sa.Column("archer_id", sa.Integer(), nullable=False),
        sa.Column("phase_id", sa.Integer(), nullable=False),
        sa.Column("nature", sa.String(), nullable=False),
        sa.Column("declare_par", sa.String(), nullable=False),
        sa.Column("declare_le", sa.DateTime(), nullable=False),
        sa.Column("motif", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["tournoi_id"], ["tournoi.id"]),
        sa.ForeignKeyConstraint(["archer_id"], ["archer.id"]),
        sa.ForeignKeyConstraint(["phase_id"], ["phase.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tournoi_id", "archer_id", "phase_id", name="uq_forfait_tournoi_archer_phase"
        ),
    )


def downgrade() -> None:
    op.drop_table("forfait")
