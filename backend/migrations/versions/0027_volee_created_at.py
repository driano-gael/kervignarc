"""colonne volee.created_at (le « quand » d'une saisie, metadonnee de persistance)

Revision ID: 0027_volee_created_at
Revises: 0026_serie_volee
Create Date: 2026-07-19

Ajoute `volee.created_at` (E04US002, tranche exposition PR2b) : l'horodatage de saisie d'une volée,
consultable (« volée 7 saisie par DURAND, 10h42 », ex-017). Métadonnée de **persistance**, hors du
domaine `Volee` (comme l'`id`) : posée par le repository via le port `Horloge`, et **préservée par
numéro** au travers du purge + réinsertion (l'identité d'une volée est son numéro dans sa série).

`NOT NULL` : SQLite exige un défaut pour ajouter une colonne `NOT NULL`, d'où
`server_default CURRENT_TIMESTAMP` — repris **à l'identique dans l'ORM `VoleeORM`** (pas de dérive
schéma ↔ modèle). L'application renseigne toujours `created_at` explicitement (UTC via `Horloge`) ;
le défaut n'est qu'un filet jamais déclenché en exploitation. `batch_alter_table` : SQLite ne sait
pas `ALTER TABLE ADD COLUMN` autrement que par recréation de la table (mode batch d'Alembic).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027_volee_created_at"
down_revision: str | None = "0026_serie_volee"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ajoute `volee.created_at` (`NOT NULL`, défaut `CURRENT_TIMESTAMP` — cf. en-tête)."""
    with op.batch_alter_table("volee") as batch:
        batch.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            )
        )


def downgrade() -> None:
    """Retire `volee.created_at`."""
    with op.batch_alter_table("volee") as batch:
        batch.drop_column("created_at")
