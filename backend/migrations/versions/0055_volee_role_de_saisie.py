"""volee : retenir le rôle qui a écrit, pour arbitrer une écriture concurrente

Revision ID: 0055_volee_role_de_saisie
Revises: 0054_volee_annulation_validation
Create Date: 2026-09-12

E16US020 (ADR-0107). La règle compare le rôle **entrant** à celui **qui a déjà écrit** ; la garde ne
fournit jamais que le premier. Le second n'existait nulle part : `saisie_par` est un nom déclaratif
qu'ADR-0107 §2 interdit d'employer comme autorité, et `validee_par` n'apparaît qu'une fois la volée
validée — or le cas visé est la volée **non validée**. D'où cette colonne.

**Reprise : aucune.** Les volées d'avant l'US restent à `NULL`, c'est-à-dire « aucune préséance
revendiquée », donc écrasables par n'importe quel rôle — le comportement qu'elles avaient déjà.
Deviner un rôle rétroactivement (« validée ⇒ scoreur ») aurait **inventé** des refus sur des
volées qu'aucun conflit n'a touchées, et le nom du validateur ne dit pas sous quel rôle la
*saisie* avait eu lieu.

⚠️ La colonne stocke le **nom** du rôle (`Role.name`), jamais son rang : renuméroter l'ordre
d'ADR-0107 ne doit pas réinterpréter les lignes déjà écrites.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0055_volee_role_de_saisie"
down_revision: str | None = "0054_volee_annulation_validation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Ajoute la colonne, sans reprise : `NULL` = aucune préséance revendiquée."""
    op.add_column("volee", sa.Column("role_de_saisie", sa.String(), nullable=True))


def downgrade() -> None:
    """Retire la colonne — on retombe sur le dernier écrit gagne, sans arbitrage."""
    op.drop_column("volee", "role_de_saisie")
