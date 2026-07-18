"""depart : ajoute `quota` (nombre maximal d'inscrits d'un créneau, facultatif)

Revision ID: 0021_depart_quota
Revises: 0020_categorie_hauteur_centre
Create Date: 2026-07-17

E02US006. Un départ (créneau, ADR-0017) peut plafonner ses inscrits pour respecter la capacité de
la salle. Le quota est **facultatif** : `NULL` = créneau sans plafond.

**Pas de backfill**, à la différence de `0019` : `NULL` est déjà le défaut sémantiquement correct
pour les départs existants (aucun plafond tant que l'admin n'en pose pas). La colonne reste donc
**nullable** — un quota absent est un état de première classe, pas une valeur à combler.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_depart_quota"
down_revision: str | None = "0020_categorie_hauteur_centre"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ajoute la colonne `quota` (nullable) à `depart` ; aucun backfill (NULL = illimité)."""
    op.add_column("depart", sa.Column("quota", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Retire `quota` — la donnée est perdue (rien ne la portait avant cette revision)."""
    with op.batch_alter_table("depart") as batch:
        batch.drop_column("quota")
