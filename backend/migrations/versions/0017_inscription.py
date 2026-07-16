"""inscription : cree la table de liaison archer <-> depart, portant `paye`

Revision ID: 0017_inscription
Revises: 0016_depart
Create Date: 2026-07-16

Le lien **archer <-> depart** (E02US009, ADR-0017) : un archer s'inscrit sur un ou plusieurs
creneaux (departs) de son tournoi. La table porte le seul fait qui lui soit propre, `paye` ;
le **montant du n'est pas stocke** — il se derive du `tarif_centimes` du depart a la lecture. C'est
ici que reviennent les colonnes `paye`/`montant_du` que le modele v0.3 posait a tort sur `depart`.

Contrainte `UNIQUE(archer_id, depart_id)` (`uq_inscription_archer_depart`) : un archer ne s'inscrit
qu'une fois sur un meme creneau (le refus fonctionnel, `DejaInscrit` -> 409, est porte en amont par
le service).

**DETTE-001 (docs/dette.md) elargie.** L'inscription porte **deux** FK de la descendance du tournoi,
sans `ON DELETE CASCADE` : `archer_id` (-> archer.id) et `depart_id` (-> depart.id). La purge en
cascade est **applicative et maitrisee** (`ArcherRepositorySQL.supprimer` et
`DepartRepositorySQL.supprimer` effacent les inscriptions liees dans leur transaction) ; la cascade
depuis le tournoi reste, elle, ouverte. Les contraintes sont **nommees** : SQLite ne sait pas cibler
une contrainte anonyme au downgrade (meme raison qu'en 0014/0015/0016).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_inscription"
down_revision: str | None = "0016_depart"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Cree la table `inscription` (liaison archer <-> depart, portant `paye`)."""
    op.create_table(
        "inscription",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("archer_id", sa.Integer(), nullable=False),
        sa.Column("depart_id", sa.Integer(), nullable=False),
        sa.Column("paye", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("id"),
        # DETTE-001 (docs/dette.md) : deux FK sans ON DELETE — descendance du tournoi via archer ET
        # via depart. Cascade applicative maitrisee cote adapters ; ne pas contourner ici.
        sa.ForeignKeyConstraint(["archer_id"], ["archer.id"], name="fk_inscription_archer_id"),
        sa.ForeignKeyConstraint(["depart_id"], ["depart.id"], name="fk_inscription_depart_id"),
        sa.UniqueConstraint("archer_id", "depart_id", name="uq_inscription_archer_depart"),
    )


def downgrade() -> None:
    """Supprime la table `inscription`."""
    op.drop_table("inscription")
