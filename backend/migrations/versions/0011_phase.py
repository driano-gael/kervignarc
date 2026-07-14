"""table phase (barème de qualification, introduction minimale)

Revision ID: 0011_phase
Revises: 0010_gabarit_tournoi
Create Date: 2026-07-14

Table `phase` (E01US009 / ADR-0011) : introduction **minimale** du concept de phase pour héberger
le **barème de qualification** là où le modèle de données l'attend (`config.scoring`). E01US009
n'exploite qu'une phase de type `qualification` par tournoi ; `ordre` et `statut` sont conformes au
modèle cible mais non exploités avant le moteur (EPIC-05). Correspond au modèle ORM `PhaseORM`.

DETTE-001 (docs/dette.md) : la FK `tournoi_id` est posée **sans** `ON DELETE CASCADE`, comme le
reste de la descendance du tournoi ; la politique de suppression reste à trancher dans l'US dédiée.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_phase"
down_revision: str | None = "0010_gabarit_tournoi"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée la table `phase`."""
    op.create_table(
        "phase",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournoi_id", sa.Integer(), nullable=False),
        sa.Column("ordre", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("config", sa.String(), nullable=False),
        sa.Column("statut", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["tournoi_id"], ["tournoi.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Supprime la table `phase`."""
    op.drop_table("phase")
