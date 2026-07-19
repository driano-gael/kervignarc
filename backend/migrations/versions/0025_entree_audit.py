"""table entree_audit (journal d'audit metier : validations, corrections, forfaits)

Revision ID: 0025_entree_audit
Revises: 0024_poste
Create Date: 2026-07-19

Table `entree_audit` (E10US005, socle) : le journal d'audit métier d'un tournoi. Enfant du tournoi
(`tournoi_id`), comme `scoreur`/`poste` : FK **sans `ON DELETE`** (DETTE-001, purge à traiter dans
la politique de suppression du tournoi, non tranchée).

Journal **en ajout seul** : aucune contrainte d'unicité (deux traces peuvent tout coïncider à
l'instant près), aucune colonne modifiée après l'insertion. `action` porte la valeur de l'énum
`ActionAuditee` ; `auteur` est le **nom** de qui a agi (pas une FK vers `scoreur` : la trace survit
à sa suppression) ; `horodatage` le « quand » ; `avant`/`apres` sont **nullables** (une validation
n'a pas d'état antérieur). Correspond au modèle ORM `EntreeAuditORM`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025_entree_audit"
down_revision: str | None = "0024_poste"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée la table `entree_audit` (FK vers `tournoi`, ajout seul)."""
    op.create_table(
        "entree_audit",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournoi_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("auteur", sa.String(), nullable=False),
        sa.Column("horodatage", sa.DateTime(), nullable=False),
        sa.Column("objet", sa.String(), nullable=False),
        sa.Column("avant", sa.String(), nullable=True),
        sa.Column("apres", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["tournoi_id"], ["tournoi.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Supprime la table `entree_audit`."""
    op.drop_table("entree_audit")
