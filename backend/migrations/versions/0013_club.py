"""table club (référentiel global des clubs)

Revision ID: 0013_club
Revises: 0012_tournoi_tarif_depart
Create Date: 2026-07-15

Table `club` (E02US001) : référentiel des clubs d'appartenance des archers. `nom` est
obligatoire et **unique**.

Première table **hors descendance de `tournoi`** : aucune FK vers `tournoi`, car le référentiel
est réutilisé d'une compétition à l'autre. Elle n'est donc pas concernée par DETTE-001
(politique de suppression d'un tournoi non vide) — supprimer un tournoi ne touche pas aux clubs.

L'unicité `UNIQUE` est **exacte** (garde-fou d'intégrité) ; le refus fonctionnel du doublon,
**insensible à la casse**, est porté par `ServiceClubs`. Correspond au modèle ORM `ClubORM`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_club"
down_revision: str | None = "0012_tournoi_tarif_depart"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée la table `club`."""
    op.create_table(
        "club",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nom", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nom"),
    )


def downgrade() -> None:
    """Supprime la table `club`."""
    op.drop_table("club")
