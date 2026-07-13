"""cycle de vie du tournoi (statut)

Revision ID: 0005_tournoi_statut
Revises: 0004_tournoi_metadonnees
Create Date: 2026-07-13

Ajoute `statut` à la table `tournoi` (E01US002) : cycle de vie `brouillon` / `en_cours` /
`termine` (obligatoire). Un `server_default` **temporaire** rétro-remplit les lignes existantes
au statut `brouillon`, puis il est **retiré** : le `NOT NULL` garde son effet protecteur (un
INSERT direct omettant la valeur échoue au lieu d'hériter d'une sentinelle) et l'application
fournit toujours le statut via l'ORM.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_tournoi_statut"
down_revision: str | None = "0004_tournoi_metadonnees"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ajoute `statut` (défaut de backfill `brouillon`), puis retire le `server_default`."""
    with op.batch_alter_table("tournoi") as batch:
        batch.add_column(
            sa.Column(
                "statut",
                sa.String(),
                nullable=False,
                server_default=sa.text("'brouillon'"),
            )
        )
    # Le défaut n'a servi qu'au rétro-remplissage des lignes existantes ; on le retire pour
    # que le NOT NULL reste réellement contraignant (la valeur vient de l'application).
    with op.batch_alter_table("tournoi") as batch:
        batch.alter_column("statut", server_default=None)


def downgrade() -> None:
    """Retire la colonne `statut`."""
    with op.batch_alter_table("tournoi") as batch:
        batch.drop_column("statut")
