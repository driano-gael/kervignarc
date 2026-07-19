"""tables serie et volee (saisie de qualification : series d'archers, volees enfants)

Revision ID: 0026_serie_volee
Revises: 0025_entree_audit
Create Date: 2026-07-19

Tables `serie` et `volee` (E04US002, tranche persistance PR2a). `serie` est la racine de saisie de
qualification d'un archer — une par archer (`UNIQUE(tournoi_id, archer_id)`) ; `volee` en est la
table **enfant** (une ligne par volée : `numero`, `valeurs` en JSON, marqueurs `saisie_par` /
`validee_par`). Correspondent aux modèles ORM `SerieORM` / `VoleeORM`.

Profil DETTE-001 : `serie.tournoi_id` **et** `serie.archer_id` sont des FK **sans `ON DELETE`** —
donnée saisie de la descendance du tournoi, purge à traiter dans la politique de suppression non
tranchée (la cascade `archer` → `serie` est applicative, `ArcherRepositorySQL.supprimer`).
`volee.serie_id` fait **exception** (`ON DELETE CASCADE`), comme `placement` : composant strict de
l'agrégat `Serie`, dont le cycle de vie suit sa série (cf. docstring de `VoleeORM`).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026_serie_volee"
down_revision: str | None = "0025_entree_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée `serie` (FK tournoi + archer, DETTE-001) puis `volee` (enfant, `serie_id` CASCADE)."""
    op.create_table(
        "serie",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournoi_id", sa.Integer(), nullable=False),
        sa.Column("archer_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tournoi_id"], ["tournoi.id"]),
        sa.ForeignKeyConstraint(["archer_id"], ["archer.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tournoi_id", "archer_id", name="uq_serie_tournoi_archer"),
    )
    op.create_table(
        "volee",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("serie_id", sa.Integer(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("valeurs", sa.String(), nullable=False),
        sa.Column("saisie_par", sa.String(), nullable=True),
        sa.Column("validee_par", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["serie_id"], ["serie.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("serie_id", "numero", name="uq_volee_serie_numero"),
    )


def downgrade() -> None:
    """Supprime `volee` (enfant) puis `serie` (parent)."""
    op.drop_table("volee")
    op.drop_table("serie")
