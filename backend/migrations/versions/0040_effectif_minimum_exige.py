"""minimum d'inscrits exigé par un tournoi — E05US021

Revision ID: 0040_effectif_minimum_exige
Revises: 0039_barrage_de_places
Create Date: 2026-08-04

E05US021 refuse de **démarrer** un tournoi qui compte moins d'inscrits que son déroulé n'en réclame.
Ce minimum a deux sources, et **une seule** a besoin d'une colonne :

- le **plancher technique** se *déduit* des prélèvements des phases (« les rangs 33 et suivants »
  exige 34 classés). Il ne se stocke pas : les phases sont déjà en base, le recalculer à la lecture
  garantit qu'il ne peut pas se périmer quand l'organisateur retouche son déroulé. Une colonne
  dupliquerait un fait dérivable, et la copie serait fausse au premier ajustement ;
- le minimum **exigé en plus** par le club (« pas de tournoi de ce type sous 40 archers ») est, lui,
  une donnée saisie que rien ne permet de retrouver. D'où cette colonne.

``NULL`` = aucune exigence propre : le plancher déduit fait seul la règle. Ce n'est **pas** la même
chose que ``0``, que le domaine refuse (`ExigenceEffectifInvalide`) — « aucune exigence » se dit en
ne réglant rien, comme pour ``phase.barrage_jusqu_au`` (0039).

**Pourquoi le format n'apparaît pas ici.** ``FormatTournoi`` porte la même exigence, et se sérialise
déjà en JSON dans ``format_tournoi.config`` (0035) : la clé ``effectif_minimum_exige`` s'y ajoute
sans migration, exactement comme les prélèvements l'avaient fait. Un format antérieur relu sans la
clé rend ``None`` — le comportement d'avant l'US, mot pour mot.

Le ``downgrade`` retire la colonne : les exigences saisies sont perdues, et les tournois retombent
sur leur seul plancher déduit. La perte est réelle mais **sans danger** — on redescend vers un
contrôle *moins* strict, jamais vers un tournoi incohérent, et le garde-fou du moteur
(``EffectifTableauInvalide``) reste en dernier recours.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0040_effectif_minimum_exige"
down_revision = "0039_barrage_de_places"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tournoi", sa.Column("effectif_minimum_exige", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("tournoi", "effectif_minimum_exige")
