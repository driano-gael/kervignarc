"""briques du club : `categorie` et `blason` deviennent bibliothèque ou copie (E01US023, ADR-0060)

Deux changements par table, sur le patron déjà en place pour `gabarit_salle` (E01US008) :

- `tournoi_id` devient **nullable** — `NULL` = **modèle de bibliothèque** (patrimoine du club,
  réutilisable d'une année sur l'autre), renseigné = **copie** appartenant à un tournoi, ajustable
  sans altérer le modèle ;
- `origine` (`ffta` / `utilisateur`) distingue le référentiel officiel de la création du club. Les
  lignes existantes prennent `utilisateur` : c'est le seul défaut honnête, car rien dans la base ne
  permet de savoir a posteriori si une catégorie vient de `precharger_ffta` ou d'une saisie — le
  préchargement était idempotent **par nom**, sans marque d'origine.

⚠️ **SQLite ne sait pas relâcher une contrainte `NOT NULL` en place** : `ALTER COLUMN` n'existe pas.
Alembic passe donc par un `batch_alter_table`, qui recrée la table et recopie les lignes. C'est
transparent ici (tables de configuration, quelques dizaines de lignes) mais **pas** anodin en
général : la recréation perd ce qui n'est pas redéclaré dans le modèle.

**Aucune donnée n'est déplacée.** Les catégories et blasons existants restent attachés à leur
tournoi ; ils deviennent, rétroactivement, des « copies » — ce qu'ils étaient déjà de fait. La
bibliothèque part vide et se remplit au préchargement FFTA ou à la main.

Revision ID: 0034_briques_patrimoine
Revises: 0033_remboursement
Create Date: 2026-07-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0034_briques_patrimoine"
down_revision: str | Sequence[str] | None = "0033_remboursement"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("categorie", "blason")


def upgrade() -> None:
    for table in _TABLES:
        with op.batch_alter_table(table) as lot:
            lot.alter_column("tournoi_id", existing_type=sa.Integer(), nullable=True)
            lot.add_column(
                sa.Column(
                    "origine",
                    sa.String(),
                    nullable=False,
                    server_default="utilisateur",
                )
            )


def downgrade() -> None:
    """Retour arrière **destructeur si la bibliothèque a été peuplée**.

    Les modèles de bibliothèque (`tournoi_id IS NULL`) n'ont pas de tournoi où retomber : les
    remettre sous une contrainte `NOT NULL` est impossible sans les **supprimer**. On les supprime
    donc explicitement, plutôt que de laisser la migration échouer sur une contrainte — et on le
    dit ici : un retour arrière silencieusement destructeur est pire qu'un retour arrière refusé.
    """
    for table in _TABLES:
        op.execute(sa.text(f"DELETE FROM {table} WHERE tournoi_id IS NULL"))
        with op.batch_alter_table(table) as lot:
            lot.drop_column("origine")
            lot.alter_column("tournoi_id", existing_type=sa.Integer(), nullable=False)
