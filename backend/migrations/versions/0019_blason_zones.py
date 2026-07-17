"""blason : ajoute `zones` (tableau JSON des valeurs de score admises)

Revision ID: 0019_blason_zones
Revises: 0018_categorie_ages
Create Date: 2026-07-17

E01US014. Un blason ne se réduit pas à sa taille : les **valeurs de score admises** en dépendent —
un triple 40 n'a pas les zones 5 → 1, son minimum est 6 (`docs/referentiel-ffta.md` §4.4). Sans
cette donnée, le pavé de saisie (EPIC-04) ne peut pas se construire. C'est le défaut d'E01US005,
que cette revision corrige.

**Backfill : le jeu complet d'un blason simple** (`["10", ..., "1", "M"]`) pour toutes les lignes
existantes. On ne peut pas faire mieux : `taille` est une *fraction de place*, pas un diamètre —
rien en base ne dit si un blason est un triple. Déduire du `nom` (« Trispot… ») serait une
heuristique sur du texte libre, qui se tromperait en silence sur une donnée qui pilote la saisie.
Le sur-ensemble est le choix retenu (arbitrage du 17/07/2026, CA d'E01US014) : il n'invente rien.

⚠️ **Conséquence à connaître** : un triple 40 déjà en base ressort avec les zones 5 → 1, qu'on ne
peut pas y tirer. L'administrateur doit les restreindre à la main. C'est assumé — cf. la note de
l'US ; aucune donnée existante ne permet de le faire à sa place.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_blason_zones"
down_revision: str | None = "0018_categorie_ages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ZONES_DEFAUT = json.dumps(["10", "9", "8", "7", "6", "5", "4", "3", "2", "1", "M"])

_blason = sa.table(
    "blason",
    sa.column("id", sa.Integer),
    sa.column("zones", sa.String),
)


def upgrade() -> None:
    """Ajoute `zones`, backfille les blasons existants, puis passe la colonne NOT NULL."""
    connexion = op.get_bind()
    op.add_column("blason", sa.Column("zones", sa.String(), nullable=True))
    connexion.execute(_blason.update().values(zones=_ZONES_DEFAUT))
    with op.batch_alter_table("blason") as batch:
        batch.alter_column("zones", existing_type=sa.String(), nullable=False)


def downgrade() -> None:
    """Retire `zones` — la donnée est perdue (rien ne la portait avant cette revision)."""
    with op.batch_alter_table("blason") as batch:
        batch.drop_column("zones")
