"""duel : le tir d'un match du tableau (saisie en duels, sets/cumul/barrage)

Table `duel` (E04US013, ADR-0049) — une ligne par match joué, keyée `(phase_id, match_numero)`.
On ne persiste que le **tir** : les manches (JSON), l'éventuel barrage (JSON) et le validateur. Le
barème (résolu par arme) et les participants (l'appariement) ne sont pas stockés — fidèle à
ADR-0048, l'appariement est recalculé du classement, le barème réinjecté. `ON DELETE CASCADE`
sur `phase_id` (feuille dérivée d'une phase, même exception que `placement_tableau`).

Revision ID: 0030_duel
Revises: 0029_placement_tableau
Create Date: 2026-07-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030_duel"
down_revision: str | None = "0029_placement_tableau"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "duel",
        sa.Column("phase_id", sa.Integer(), nullable=False),
        sa.Column("match_numero", sa.Integer(), nullable=False),
        sa.Column("manches", sa.String(), nullable=False),
        sa.Column("barrage", sa.String(), nullable=True),
        sa.Column("validee_par", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["phase_id"], ["phase.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("phase_id", "match_numero"),
    )


def downgrade() -> None:
    op.drop_table("duel")
