"""remboursement : registre des sommes encaissées à rendre (E08US005, ADR-0057)

Table `remboursement` — une ligne par inscription **payée** effacée (départ supprimé,
désinscription).
La ligne **survit** à la disparition de l'inscription/du départ : pas de FK vers eux (souvent
détruits), on fige des **instantanés textuels** (`archer_prenom`, `archer_nom`, `creneau`) et le
`montant_centimes` encaissé — comme `entree_audit`/`forfait` figent le **nom** de l'auteur plutôt
qu'une FK. `motif` (`depart_supprime`/`desinscription`) et `statut`
(`a_rembourser`/`rembourse`/`reporte`) stockent la valeur d'énum telle quelle. `traite_le` est
nullable (rempli au traitement).

Seule FK : `tournoi_id`, **sans `ON DELETE`** (DETTE-001, comme `forfait`/`entree_audit`) — la purge
liée au tournoi relève de sa politique de suppression, non tranchée.

Revision ID: 0033_remboursement
Revises: 0032_depart_horaire_hhmm
Create Date: 2026-07-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033_remboursement"
down_revision: str | None = "0032_depart_horaire_hhmm"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "remboursement",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournoi_id", sa.Integer(), nullable=False),
        sa.Column("archer_prenom", sa.String(), nullable=False),
        sa.Column("archer_nom", sa.String(), nullable=False),
        sa.Column("creneau", sa.String(), nullable=False),
        sa.Column("montant_centimes", sa.Integer(), nullable=False),
        sa.Column("motif", sa.String(), nullable=False),
        sa.Column("statut", sa.String(), nullable=False),
        sa.Column("cree_le", sa.DateTime(), nullable=False),
        sa.Column("traite_le", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tournoi_id"], ["tournoi.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("remboursement")
