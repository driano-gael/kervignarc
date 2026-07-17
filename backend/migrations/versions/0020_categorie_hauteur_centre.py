"""categorie : ajoute `hauteur_cm` (hauteur du centre de l'or, en cm)

Revision ID: 0020_categorie_hauteur_centre
Revises: 0019_blason_zones
Create Date: 2026-07-17

E03US001 (ADR-0022) — résorbe DETTE-002. La hauteur du centre de l'or (sol → centre) devient une
donnée de la catégorie, car elle pilote une contrainte de placement de 1er rang : une **butte** n'a
qu'une hauteur de montage, un U11 (110 cm, blason 80 cm — art. C.3.1.1) ne peut donc pas partager
une cible avec les autres catégories (130 cm — `docs/referentiel-ffta.md` §5).

**Backfill (données, pas seulement schéma).** On ne peut pas ajouter une colonne NOT NULL vide : le
projet n'emploie pas `server_default` (patron des revisions 0018/0019). On ajoute la colonne
nullable, on backfille — **110 pour les catégories dont les `ages` contiennent `U11`, 130 sinon** —
puis on passe la colonne NOT NULL. Le backfill par `ages` couvre le seul écart réglementaire connu ;
une catégorie U11 non repérée (texte libre, sans tranche) ressort à 130, ajustable à la main.

Le `downgrade` retire simplement la colonne — rien ne la portait avant cette revision.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_categorie_hauteur_centre"
down_revision: str | None = "0019_blason_zones"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_HAUTEUR_DEFAUT = 130
_HAUTEUR_U11 = 110

_categorie = sa.table(
    "categorie",
    sa.column("id", sa.Integer),
    sa.column("ages", sa.String),
    sa.column("hauteur_cm", sa.Integer),
)


def _hauteur(ages_json: str | None) -> int:
    """Hauteur du centre à backfiller : 110 si `ages` contient `U11`, 130 sinon.

    Un `ages` illisible **ou non-liste** (ne devrait pas exister, le repository sérialise toujours
    une liste — mais un import ou une base corrompue le pourraient) retombe prudemment sur le défaut
    130 plutôt que de faire échouer la migration. Le `isinstance(list)` est indispensable : un JSON
    scalaire (`"null"`, `"5"`) décode sans lever, et `"U11" in None`/`in 5` lèverait un `TypeError`
    **hors** du `try` — le filet ne couvrirait alors pas ce qu'il prétend absorber."""
    try:
        decode = json.loads(ages_json) if ages_json else []
    except (json.JSONDecodeError, TypeError):
        decode = []
    tranches = decode if isinstance(decode, list) else []
    return _HAUTEUR_U11 if "U11" in tranches else _HAUTEUR_DEFAUT


def upgrade() -> None:
    """Ajoute `hauteur_cm`, backfille (110 pour U11, 130 sinon), passe la colonne NOT NULL."""
    connexion = op.get_bind()
    op.add_column("categorie", sa.Column("hauteur_cm", sa.Integer(), nullable=True))
    lignes = connexion.execute(sa.select(_categorie.c.id, _categorie.c.ages)).all()
    for identifiant, ages_json in lignes:
        connexion.execute(
            _categorie.update()
            .where(_categorie.c.id == identifiant)
            .values(hauteur_cm=_hauteur(ages_json))
        )
    with op.batch_alter_table("categorie") as batch:
        batch.alter_column("hauteur_cm", existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    """Retire `hauteur_cm` — la donnée est perdue (rien ne la portait avant cette revision)."""
    with op.batch_alter_table("categorie") as batch:
        batch.drop_column("hauteur_cm")
