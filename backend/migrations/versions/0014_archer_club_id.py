"""archer : rattachement au club du referentiel

Revision ID: 0014_archer_club_id
Revises: 0013_club
Create Date: 2026-07-15

Ajoute `archer.club_id` (FK -> club.id) — le lien qui rattache un archer a son club (E02US001).

**Nullable, et ce n'est pas provisoire par negligence.** Le club est facultatif a ce stade ;
E02US002 le rendra obligatoire, en meme temps qu'il ajoutera `prenom` et `categorie_id`. Nullable
est le seul choix possible ici : les archers deja inscrits n'ont pas de club a retro-remplir, et
inventer un club « inconnu » polluerait le referentiel d'une valeur que personne n'a saisie.

**Pourquoi ce lien nait avec le referentiel et non avec l'inscription complete.** Il est ce qui
rend le CA « un club utilise n'est pas supprimable » exercable : sans lui, le refus serait un
garde-fou qu'aucun chemin reel ne pourrait declencher, et aucun test ne pourrait l'exercer
autrement que contre le vide.

**Hors perimetre de DETTE-001.** Les autres FK d'`archer` pointent vers la descendance de
`tournoi` ; celle-ci pointe vers `club`, qui n'en fait pas partie. Supprimer un tournoi (donc ses
archers) ne la viole jamais — c'est le sens inverse qu'elle contraint, et ce cas est tranche par
le service (refus 409, `ClubReference`), comme l'est deja `categorie.blason_id`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_archer_club_id"
down_revision: str | None = "0013_club"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ajoute `archer.club_id` (INTEGER, nullable) et sa FK vers `club`."""
    with op.batch_alter_table("archer") as batch:
        batch.add_column(sa.Column("club_id", sa.Integer(), nullable=True))
        # `batch_alter_table` recree la table : la contrainte doit etre **nommee** pour que le
        # downgrade puisse la cibler (SQLite ne sait pas supprimer une contrainte anonyme).
        batch.create_foreign_key("fk_archer_club_id", "club", ["club_id"], ["id"])


def downgrade() -> None:
    """Retire la FK puis la colonne `club_id`."""
    with op.batch_alter_table("archer") as batch:
        batch.drop_constraint("fk_archer_club_id", type_="foreignkey")
        batch.drop_column("club_id")
