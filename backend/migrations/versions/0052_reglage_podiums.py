"""réglage des podiums du tournoi — E16US014

Revision ID: 0052_reglage_podiums
Revises: 0051_reglage_pages_ecran
Create Date: 2026-08-31

A16 demande un podium **configurable** : l'organisateur choisit ce qu'il récompense (catégorie,
scratch, club) et sur combien de places. C'est une **donnée saisie** que rien ne permet de
retrouver, d'où ces deux colonnes — et sur `tournoi`, comme le cloisonnement (0041) : deux tournois
montés sur le même format ne remettent pas forcément les mêmes médailles.

``podium_portees`` est un **tableau JSON** de codes (``["categorie","scratch"]``) et non une colonne
par portée : les portées **se cumulent**, et une colonne chacune figerait l'énumération dans le
schéma — la portée *équipe* d'A16 arrivera avec EPIC-13. Même procédé que les tranches d'âge de
``categorie``.

Les deux colonnes sont **NOT NULL** avec un ``server_default`` qui remplit les lignes existantes en
une passe : ``["categorie"]`` et ``4`` **sont** le comportement d'E06US004, donc un tournoi déjà en
base rend exactement le même palmarès qu'avant l'US. C'est la seule garantie de non-régression du
réglage, et elle vit ici, pas dans le code.

Pas de ``CHECK`` sur le contenu du JSON ni sur la profondeur : le dépôt valide ses énumérations au
repository (convention de 0041), qui enveloppe une valeur illisible en ``InfrastructureError``, et
l'invariant « au moins une place » est tenu par ``ReglagePodiums``.

Le ``downgrade`` retire les deux colonnes : les réglages saisis sont perdus et tous les tournois
retombent sur les podiums par catégorie à quatre places. Perte réelle mais **sans danger** — on
redescend vers l'affichage d'E06US004, jamais vers un palmarès incohérent.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0052_reglage_podiums"
down_revision = "0051_reglage_pages_ecran"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # `batch_alter_table` comme toutes les migrations de colonne du dépôt : sous SQLite, Alembic y
    # recrée la table plutôt que d'émettre un `ALTER TABLE`. L'ajout passerait sans lui ; le
    # `downgrade`, non — `DROP COLUMN` date de SQLite 3.35.
    with op.batch_alter_table("tournoi") as batch:
        batch.add_column(
            sa.Column("podium_portees", sa.String(), nullable=False, server_default='["categorie"]')
        )
        batch.add_column(
            sa.Column("podium_profondeur", sa.Integer(), nullable=False, server_default="4")
        )


def downgrade() -> None:
    with op.batch_alter_table("tournoi") as batch:
        batch.drop_column("podium_profondeur")
        batch.drop_column("podium_portees")
