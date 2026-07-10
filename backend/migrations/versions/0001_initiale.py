"""baseline initiale (schema vide)

Revision ID: 0001_initiale
Revises:
Create Date: 2026-07-10

Migration **baseline** (E00US006) : établit la chaîne de migrations et la table de
suivi `alembic_version`. Aucune table métier n'est encore définie — les premières
entités (agrégat trivial) seront introduites en E00US009 avec leur propre migration.
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0001_initiale"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Baseline : aucune table à créer (voir docstring du module)."""


def downgrade() -> None:
    """Baseline : aucune table à défaire."""
