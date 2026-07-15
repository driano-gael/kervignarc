"""tournoi : tarif d'un départ (en centimes entiers)

Revision ID: 0012_tournoi_tarif_depart
Revises: 0011_phase
Create Date: 2026-07-15

Ajoute `tarif_depart_centimes` à la table `tournoi` (E01US010) : prix d'un **départ**, qui
alimentera le montant dû (tarif multiplié par le nombre de départs, EF-8.1 / E08US001).

**INTEGER, pas REAL.** Le [modèle de données](../../../docs/modele-de-donnees.md) prévoyait
`tarif_depart REAL` ; l'argent en flottant binaire ne représente pas 8,10 € exactement, et
EPIC-08/09 **somment** ces montants par archer et par club (EF-9.6) — la dérive y serait visible.
On compte donc en **centimes entiers**, et le suffixe `_centimes` porte l'unité dans le nom.

**Nullable, sans défaut.** `NULL` = tarif **non défini** ; `0` = **gratuit**. Deux états distincts :
rétro-remplir à `0` ferait passer les tournois existants pour gratuits alors qu'ils n'ont
simplement jamais eu de tarif. Aucun `server_default` : la colonne est facultative, l'absence est
une information.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_tournoi_tarif_depart"
down_revision: str | None = "0011_phase"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ajoute `tarif_depart_centimes` (INTEGER, nullable — `NULL` = non défini)."""
    with op.batch_alter_table("tournoi") as batch:
        batch.add_column(sa.Column("tarif_depart_centimes", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Retire la colonne `tarif_depart_centimes`."""
    with op.batch_alter_table("tournoi") as batch:
        batch.drop_column("tarif_depart_centimes")
