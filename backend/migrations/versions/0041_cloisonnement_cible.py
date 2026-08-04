"""cloisonnement catégorie/blason des cibles — E03US007

Revision ID: 0041_cloisonnement_cible
Revises: 0040_effectif_minimum_exige
Create Date: 2026-08-04

RG-4 fait du cloisonnement d'une cible une **contrainte de placement activable**, indépendante du
type de tournoi. Le réglage est donc une **donnée saisie** par l'organisateur, que rien ne permet de
retrouver : d'où cette colonne, sur `tournoi` (le gabarit de salle, lui, est une brique de
patrimoine partagée — deux tournois montés sur le même plan de salle peuvent cloisonner
différemment).

Quatre valeurs : ``aucun`` (défaut), ``categorie``, ``blason``, ``blason_et_categorie``. La colonne
est **NOT NULL** avec un ``server_default`` : « aucun cloisonnement » est une *valeur*, pas une
absence, et un ``NULL`` aurait ouvert un cinquième état à traduire dans chaque sens. Le défaut
serveur remplit aussi les lignes existantes en une passe — les tournois d'avant l'US gardent
**exactement** le comportement d'E03US001.

Pas de contrainte ``CHECK`` sur les valeurs : le dépôt stocke déjà ses énumérations en texte libre
(``tournoi.statut``, ``tournoi.type_tournoi``) et les valide au repository, qui enveloppe une valeur
illisible en ``InfrastructureError``. Ajouter un ``CHECK`` ici seul serait une exception locale à
une convention, pas un garde-fou de plus.

Le ``downgrade`` retire la colonne : les réglages saisis sont perdus et les tournois retombent sur
« aucun cloisonnement ». Perte réelle mais **sans danger** — on redescend vers un placement *moins*
contraint, jamais vers un plan incohérent.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0041_cloisonnement_cible"
down_revision = "0040_effectif_minimum_exige"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # `batch_alter_table` comme toutes les migrations de colonne du dépôt (0040 en dernier) : sous
    # SQLite, Alembic y recrée la table plutôt que d'émettre un `ALTER TABLE`. L'ajout passerait
    # sans lui ; le `downgrade`, non — `DROP COLUMN` date de SQLite 3.35.
    with op.batch_alter_table("tournoi") as batch:
        batch.add_column(
            sa.Column("cloisonnement", sa.String(), nullable=False, server_default="aucun")
        )


def downgrade() -> None:
    with op.batch_alter_table("tournoi") as batch:
        batch.drop_column("cloisonnement")
