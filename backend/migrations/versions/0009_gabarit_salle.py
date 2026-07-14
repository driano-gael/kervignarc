"""table gabarit_salle (plans de salle réutilisables)

Revision ID: 0009_gabarit_salle
Revises: 0008_categorie_blason_id
Create Date: 2026-07-14

Table `gabarit_salle` (E01US007) : un gabarit décrit une disposition de cibles **réutilisable**
(aucune FK vers `tournoi` ; le rattachement à un tournoi viendra en E01US008). `nom` est
obligatoire ; `nb_cibles` est le nombre de cibles ; `config` (JSON) porte le plafond d'archers de
chaque cible (`{"capacites": [...]}`). Correspond au modèle ORM `GabaritSalleORM`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_gabarit_salle"
down_revision: str | None = "0008_categorie_blason_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée la table `gabarit_salle`."""
    op.create_table(
        "gabarit_salle",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nom", sa.String(), nullable=False),
        sa.Column("nb_cibles", sa.Integer(), nullable=False),
        sa.Column("config", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Supprime la table `gabarit_salle`."""
    op.drop_table("gabarit_salle")
