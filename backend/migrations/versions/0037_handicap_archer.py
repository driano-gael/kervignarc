"""handicap de l'archer : valeur officielle + surcharge — E05US015

Revision ID: 0037_handicap_archer
Revises: 0036_sources_multiples
Create Date: 2026-07-31

E05US015 livre le **handicap** comme politique `scoring` (`ScoreAvecHandicap`) : le score final vaut
`score réalisé + handicap`, règle donnée par le commanditaire le 31/07/2026. La politique
**applique** le handicap ; sa **valeur** est une donnée de l'archer, d'où ces deux colonnes.

**Deux colonnes et non une**, à la demande explicite du commanditaire : un handicap « enregistré
comme officiel » (entretenu par le club, importé avec les archers) **et** une mécanique de
**surcharge** par archer, qui le prime pour cette édition sans réécrire la référence.

`NULL` signifie « non renseigné », **distinct** d'un handicap à `0` : les deux concourent pareil au
scratch, mais seul le second a été évalué. C'est pourquoi les colonnes sont nullables sans valeur
par défaut — un `DEFAULT 0` aurait effacé la distinction sur toutes les lignes existantes, en
affirmant que chaque archer déjà en base a été évalué à zéro.

⚠️ **Aucune table de handicap n'est chargée.** Le projet n'en possède aucune (la FFTA n'a pas de
système officiel ; celui qui fait référence est anglo-saxon), et en reconstituer une produirait des
classements plausibles mais faux. Cette migration ouvre l'emplacement, elle ne le remplit pas.

Le `downgrade` supprime les deux colonnes : la donnée est **perdue**, et c'est irréductible — elle
n'existe nulle part ailleurs. Redescendre sous cette révision suppose donc d'accepter de ressaisir
les handicaps, ce qu'une base d'avant l'US n'avait de toute façon pas.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0037_handicap_archer"
down_revision = "0036_sources_multiples"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("archer") as batch:
        batch.add_column(sa.Column("handicap_officiel", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("handicap_surcharge", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("archer") as batch:
        batch.drop_column("handicap_surcharge")
        batch.drop_column("handicap_officiel")
