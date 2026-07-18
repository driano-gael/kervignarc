"""table scoreur (personnes habilitées à valider les scores d'un tournoi)

Revision ID: 0023_scoreur
Revises: 0022_placement
Create Date: 2026-07-18

Table `scoreur` (E10US003) : les scoreurs d'un tournoi (nom + code individuel). Enfant du tournoi
(`tournoi_id`), comme `depart` : FK **sans `ON DELETE`** (DETTE-001, purge à traiter dans la
politique de suppression du tournoi, non tranchée).

`code` est `UNIQUE` **global** (pas par tournoi) : le scoreur ouvre sa session par son seul code,
qui doit désigner un scoreur sans ambiguïté d'un tournoi à l'autre. Unicité **exacte** (garde-fou
d'intégrité) ; le service stocke le code déjà normalisé (majuscules, `normaliser_code`) et
l'alphabet du code n'a pas d'accent — pas de repli fonctionnel élargi comme pour le nom de club.
Correspond au modèle ORM `ScoreurORM`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_scoreur"
down_revision: str | None = "0022_placement"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée la table `scoreur` (FK vers `tournoi`, `code` unique global)."""
    op.create_table(
        "scoreur",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournoi_id", sa.Integer(), nullable=False),
        sa.Column("nom", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["tournoi_id"], ["tournoi.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )


def downgrade() -> None:
    """Supprime la table `scoreur`."""
    op.drop_table("scoreur")
