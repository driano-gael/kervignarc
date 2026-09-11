"""volee : l'acte de validation devient identifiable, et annulable

Revision ID: 0054_volee_annulation_validation
Revises: 0053_placement_tableau_par_tour
Create Date: 2026-09-11

E16US019 (ADR-0109). Jusqu'ici `validee_par` portait **deux** états à lui seul : « cette volée est
verrouillée » et « cette volée compte dans les totaux ». Annuler une validation demande de les
séparer — `correction_ouverte_par` rouvre l'écriture **sans** retirer la volée du cumul — et de
savoir quel bloc de volées un même acte de validation avait verrouillé, d'où `lot_validation`.

**Reprise** : les volées déjà validées reçoivent `lot_validation = numero`, c'est-à-dire **un lot
par volée**. Les lots d'avant l'US ne sont pas connus (aucune trace ne les distinguait), et les
inventer par le grain serait faux — le grain a pu changer entre-temps. La conséquence est bornée et
dicible : sur un tournoi antérieur, annuler rouvre **la volée seule** au lieu de son bloc. Ce
backfill tient l'invariant dont `Serie.annuler_validation` dépend : `lot_validation` est non `NULL`
si et seulement si `validee_par` l'est.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0054_volee_annulation_validation"
down_revision: str | None = "0053_placement_tableau_par_tour"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ajoute les deux colonnes, puis donne un lot à chaque volée déjà validée."""
    op.add_column("volee", sa.Column("lot_validation", sa.Integer(), nullable=True))
    op.add_column("volee", sa.Column("correction_ouverte_par", sa.String(), nullable=True))
    op.execute("UPDATE volee SET lot_validation = numero WHERE validee_par IS NOT NULL")


def downgrade() -> None:
    """Retire les deux colonnes — une correction en cours redevient une volée verrouillée."""
    op.drop_column("volee", "correction_ouverte_par")
    op.drop_column("volee", "lot_validation")
