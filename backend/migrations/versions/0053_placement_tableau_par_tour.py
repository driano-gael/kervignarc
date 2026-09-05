"""placement_tableau : la pose d'un duelliste appartient à un tour

Revision ID: 0053_placement_tableau_par_tour
Revises: 0052_reglage_podiums
Create Date: 2026-09-05

E03US012 (ADR-0106). La clé primaire `(phase_id, inscription_id)` de 0029 ne peut représenter
**qu'une** pose par archer et par phase. Or un archer change de cible d'un tour à l'autre : tant que
la clé ignore le tour, poser le tour 2 écraserait la pose du tour 1. La clé gagne donc `tour`.

**Reprise** : toutes les lignes existantes deviennent des poses du **tour 1** — c'est exactement ce
qu'elles étaient, le placement des duellistes ayant été tour-1 uniquement depuis E03US009. Aucun
tournoi déjà en base ne change donc d'affichage.

⚠️ **SQLite ne sait pas modifier une clé primaire** : la table est recréée et les lignes recopiées.
C'est possible sans démêlage parce que c'est une feuille dérivée (`ON DELETE CASCADE` des deux
côtés) — rien ne la référence.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0053_placement_tableau_par_tour"
down_revision: str | None = "0052_reglage_podiums"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_COLONNES = "phase_id, tour, inscription_id, cible_index, position"


def _creer(nom: str, *, avec_tour: bool) -> None:
    """Crée la table cible sous un nom temporaire — schéma écrit en clair, jamais réfléchi.

    ⚠️ **Pas de `batch_alter_table` ici** : en mode batch Alembic **réfléchit** la table existante
    et une `PrimaryKeyConstraint` passée en `table_args` s'y **ajoute** au lieu de la remplacer —
    SQLAlchemy émet un avertissement et garde l'ancienne clé. Recréer explicitement est le seul
    geste qui dit ce qu'il fait.
    """
    colonnes = [
        sa.Column("phase_id", sa.Integer(), nullable=False),
        sa.Column("inscription_id", sa.Integer(), nullable=False),
        sa.Column("cible_index", sa.Integer(), nullable=False),
        sa.Column("position", sa.String(), nullable=False),
    ]
    cle = ["phase_id", "inscription_id"]
    if avec_tour:
        colonnes.insert(1, sa.Column("tour", sa.Integer(), nullable=False))
        cle = ["phase_id", "tour", "inscription_id"]
    op.create_table(
        nom,
        *colonnes,
        sa.ForeignKeyConstraint(["phase_id"], ["phase.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inscription_id"], ["inscription.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint(*cle),
    )


def upgrade() -> None:
    """Recrée `placement_tableau` avec `tour` dans la clé ; l'existant devient le **tour 1**."""
    _creer("placement_tableau_nouveau", avec_tour=True)
    op.execute(
        sa.text(
            f"INSERT INTO placement_tableau_nouveau ({_COLONNES}) "
            "SELECT phase_id, 1, inscription_id, cible_index, position FROM placement_tableau"
        )
    )
    op.drop_table("placement_tableau")
    op.rename_table("placement_tableau_nouveau", "placement_tableau")


def downgrade() -> None:
    """Revient à une pose par (phase, inscription) — les poses des tours ≥ 2 sont perdues.

    ⚠️ Perte assumée et **non réversible** : la clé de destination ne peut pas les distinguer. On
    ne garde que le tour 1, seul représentable ; le reste se régénère (donnée dérivée).
    """
    _creer("placement_tableau_ancien", avec_tour=False)
    op.execute(
        sa.text(
            "INSERT INTO placement_tableau_ancien "
            "(phase_id, inscription_id, cible_index, position) "
            "SELECT phase_id, inscription_id, cible_index, position "
            "FROM placement_tableau WHERE tour = 1"
        )
    )
    op.drop_table("placement_tableau")
    op.rename_table("placement_tableau_ancien", "placement_tableau")
