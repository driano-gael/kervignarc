"""table poste (credential d'une cible : rattachement d'une tablette à sa cible)

Revision ID: 0024_poste
Revises: 0023_scoreur
Create Date: 2026-07-18

Table `poste` (E04US001, ADR-0029) : le credential d'une **cible** d'un tournoi — le couple
`(tournoi_id, cible_index)` plus le `code` imprimé sous le QR. Enfant du tournoi (`tournoi_id`),
comme `scoreur` : FK **sans `ON DELETE`** (DETTE-001, purge non tranchée).

`code` est `UNIQUE` **global** (le rattachement se fait par le seul code) ; `(tournoi_id,
cible_index)` est `UNIQUE` (une seule cible N par tournoi). Correspond au modèle ORM `PosteORM`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024_poste"
down_revision: str | None = "0023_scoreur"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée la table `poste` (FK vers `tournoi`, `code` unique global, cible unique par tournoi)."""
    op.create_table(
        "poste",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournoi_id", sa.Integer(), nullable=False),
        sa.Column("cible_index", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["tournoi_id"], ["tournoi.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("tournoi_id", "cible_index", name="uq_poste_tournoi_cible"),
    )


def downgrade() -> None:
    """Supprime la table `poste`."""
    op.drop_table("poste")
