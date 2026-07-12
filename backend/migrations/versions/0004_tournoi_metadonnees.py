"""métadonnées du tournoi (date, lieu, type)

Revision ID: 0004_tournoi_metadonnees
Revises: 0003_archer_score
Create Date: 2026-07-12

Enrichit la table `tournoi` (E01US001) : `date` (obligatoire), `lieu` (facultatif) et
`type_tournoi` (`officiel` / `non_officiel`, obligatoire). Un `server_default` couvre les
éventuelles lignes préexistantes du walking skeleton (rétro-remplissage) ; l'application
fournit toujours des valeurs réelles à l'insertion (via l'ORM).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_tournoi_metadonnees"
down_revision: str | None = "0003_archer_score"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ajoute les colonnes `date`, `lieu` et `type_tournoi` à la table `tournoi`."""
    with op.batch_alter_table("tournoi") as batch:
        batch.add_column(
            sa.Column("date", sa.Date(), nullable=False, server_default=sa.text("'1970-01-01'"))
        )
        batch.add_column(sa.Column("lieu", sa.String(), nullable=True))
        batch.add_column(
            sa.Column(
                "type_tournoi",
                sa.String(),
                nullable=False,
                server_default=sa.text("'non_officiel'"),
            )
        )


def downgrade() -> None:
    """Retire les colonnes ajoutées."""
    with op.batch_alter_table("tournoi") as batch:
        batch.drop_column("type_tournoi")
        batch.drop_column("lieu")
        batch.drop_column("date")
