"""colonne inscription.cree_le (la date d'inscription, d'où se lit l'ancienneté d'une dette)

Revision ID: 0057_inscription_cree_le
Revises: 0056_ancrage_par_identite
Create Date: 2026-09-26

Ajoute `inscription.cree_le` (E17US012, planche A17 « DEPUIS ») : l'instant de l'inscription, posé
par `ServiceInscriptions` via le port `Horloge`. Un **fait du domaine** (`Inscription.cree_le`), pas
une métadonnée de persistance : l'ancienneté de la dette est une règle, testée dans
`domain.paiement.dater_la_dette`.

⚠️ **Nullable, sans `server_default`** — l'inverse exact de `0027_volee_created_at`. Un défaut
`CURRENT_TIMESTAMP` daterait chaque inscription existante **du jour de la migration** : une fausse
date, indiscernable d'une vraie, qui rajeunirait toutes les dettes en cours. `NULL` dit la vérité —
« date inconnue » — et c'est ce que l'écran affiche. `batch_alter_table` : SQLite ne sait pas
`ALTER TABLE` autrement que par recréation de la table.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0057_inscription_cree_le"
down_revision: str | None = "0056_ancrage_par_identite"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ajoute `inscription.cree_le` (nullable, **sans** défaut — cf. en-tête)."""
    with op.batch_alter_table("inscription") as batch:
        batch.add_column(sa.Column("cree_le", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Retire `inscription.cree_le` (la date d'inscription est perdue, rien d'autre)."""
    with op.batch_alter_table("inscription") as batch:
        batch.drop_column("cree_le")
