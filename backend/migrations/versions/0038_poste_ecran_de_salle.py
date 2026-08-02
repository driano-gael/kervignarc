"""le poste devient typé : cible ou écran de salle — E07US004

Revision ID: 0038_poste_ecran_de_salle
Revises: 0037_handicap_archer
Create Date: 2026-08-01

E07US004 fait de l'écran de salle un **poste** de l'appli publique, rattaché par jeton exactement
comme une tablette de cible (CA : *« rien de neuf à inventer — réemploi du jeton, du QR, de la
supervision »*). Une seule table `poste` sert donc les deux natures, discriminées par `type`
(ADR-0064) :

- ``cible`` : ``cible_index`` renseigné, ``libelle`` et ``deroule_json`` nuls ;
- ``ecran`` : ``libelle`` renseigné, ``cible_index`` nul, ``deroule_json`` facultatif.

**Trois effets à connaître avant d'appliquer :**

1. ``type`` arrive avec ``server_default='cible'`` : les lignes existantes — toutes des cibles —
   sont correctes sans backfill, et un client qui insérerait sans préciser le type resterait dans
   l'ancien comportement. Le défaut est **conservé** en base (et non retiré après remplissage)
   parce qu'il documente exactement cela.
2. ``cible_index`` devient **nullable**. C'est ce qui **affaiblit** ``uq_poste_tournoi_cible`` : en
   SQLite deux ``NULL`` ne s'égalent pas, donc plusieurs écrans coexistent sans la heurter — c'est
   le CA (« plusieurs écrans possibles »). La contrainte continue de protéger « une seule cible N
   par tournoi », le seul cas où elle avait un sens.
3. L'exclusivité ``cible_index`` ↔ ``libelle`` n'est **pas** un ``CHECK`` : elle est portée par le
   domaine (``Poste.creer`` / ``Poste.creer_ecran``, ``Poste.cible()``). Le projet n'utilise de
   ``CHECK`` nulle part, et en poser un ici ferait vivre une règle métier hors du domaine
   (règle 2). Le prix assumé : une écriture SQL directe pourrait produire une ligne incohérente.

``deroule_json`` sérialise la ``SequenceVues`` d'un écran sous la forme
``[{"vue": "classement", "cadence_s": 30}]`` — même parti que ``phase.sources_json`` (migration
0036) : du JSON dans une colonne texte plutôt qu'une table enfant, pour un réglage qui se lit et
s'écrit toujours **en entier**, jamais ligne à ligne. ``NULL`` n'est pas une anomalie : c'est un
écran qui joue le déroulé par défaut.

Le ``downgrade`` **supprime les écrans avant de rendre ``cible_index`` obligatoire** — sans quoi le
recréation de table échouerait sur des lignes à ``NULL``. La perte est assumée et réelle (les écrans
et leurs déroulés disparaissent) : redescendre sous cette révision, c'est revenir à un modèle où
l'écran de salle n'existe pas.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0038_poste_ecran_de_salle"
down_revision = "0037_handicap_archer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("poste") as batch:
        batch.add_column(
            sa.Column("type", sa.String(), nullable=False, server_default="cible"),
        )
        batch.add_column(sa.Column("libelle", sa.String(), nullable=True))
        batch.add_column(sa.Column("deroule_json", sa.String(), nullable=True))
        batch.alter_column("cible_index", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    # Les écrans n'ont pas de cible : les garder rendrait la colonne non nullable impossible à
    # rétablir. On les supprime explicitement plutôt que de laisser échouer la recréation de table.
    op.execute(sa.text("DELETE FROM poste WHERE type = 'ecran'"))
    with op.batch_alter_table("poste") as batch:
        batch.alter_column("cible_index", existing_type=sa.Integer(), nullable=False)
        batch.drop_column("deroule_json")
        batch.drop_column("libelle")
        batch.drop_column("type")
