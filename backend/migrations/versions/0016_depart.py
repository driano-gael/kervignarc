"""depart : cree la table des creneaux du tournoi et retire le tarif du tournoi

Revision ID: 0016_depart
Revises: 0015_archer_inscription
Create Date: 2026-07-16

Un **depart** devient un *creneau* du tournoi (E02US004, ADR-0017) : le tournoi peut se jouer
plusieurs fois dans la journee, et l'archer s'inscrira sur un ou plusieurs creneaux (E02US009). Deux
mouvements dans une seule revision, parce qu'ils sont les deux faces d'une meme decision :

- **cree la table `depart`** — `tournoi_id` (FK -> tournoi.id, NOT NULL), `numero` (NOT NULL,
  attribue par le service), `horaire` (libelle de creneau, nullable), `tarif_centimes` (NOT NULL,
  centimes entiers, ADR-0012). Contrainte `UNIQUE(tournoi_id, numero)` : deux creneaux d'un meme
  tournoi ne partagent pas de numero ;
- **retire `tournoi.tarif_depart_centimes`** — pose par 0012 (E01US010) quand aucune entite `Depart`
  n'existait ; le tarif vit desormais **par creneau** (obligatoire, prix possiblement differents),
  plus au tournoi. Aucune donnee reelle a preserver (jalon J1, pre-production) ; le `downgrade`
  recree la colonne nullable mais ne restaure aucune valeur.

**DETTE-001 (docs/dette.md) elargie.** `depart.tournoi_id` est une FK **de la descendance du
tournoi**, sans `ON DELETE CASCADE` ni suppression applicative equivalente : elle rejoint la
politique de suppression d'un tournoi non tranchee. La ligne du registre est elargie plutot que
contournee ici. La contrainte est **nommee** (`fk_depart_tournoi_id`) : SQLite ne sait pas cibler
une contrainte anonyme au downgrade (meme raison qu'en 0014/0015).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_depart"
down_revision: str | None = "0015_archer_inscription"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Cree la table `depart` puis retire `tournoi.tarif_depart_centimes`."""
    op.create_table(
        "depart",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tournoi_id", sa.Integer(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("horaire", sa.String(), nullable=True),
        sa.Column("tarif_centimes", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tournoi_id"], ["tournoi.id"], name="fk_depart_tournoi_id"),
        sa.UniqueConstraint("tournoi_id", "numero", name="uq_depart_tournoi_numero"),
    )
    with op.batch_alter_table("tournoi") as batch:
        batch.drop_column("tarif_depart_centimes")


def downgrade() -> None:
    """Recree `tournoi.tarif_depart_centimes` (nullable, sans valeur) puis supprime `depart`."""
    with op.batch_alter_table("tournoi") as batch:
        batch.add_column(sa.Column("tarif_depart_centimes", sa.Integer(), nullable=True))
    op.drop_table("depart")
