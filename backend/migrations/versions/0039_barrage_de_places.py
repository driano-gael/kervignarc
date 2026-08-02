"""barrage de places décisives : le barrage annoncé et ses tirs — E06US003

Revision ID: 0039_barrage_de_places
Revises: 0038_poste_ecran_de_salle
Create Date: 2026-08-02

E06US003 donne au moteur de barrage (livré pur par E05US015) sa **persistance**. Deux tables, et
le découpage n'est pas neutre :

- ``barrage`` : le barrage **annoncé** — qui il départage, dans quel classement, à quel rang ;
- ``barrage_tir`` : une flèche, au grain ``(barrage, manche, archer)``. C'est le « flèche par
  flèche » du CA, et c'est ce dont le moteur a besoin pour **rejouer** le verdict.

**Quatre points à connaître avant d'appliquer :**

1. **Le verdict n'est pas stocké.** Il se recalcule depuis les tirs à chaque lecture. C'est ce qui
   rend une flèche mal saisie corrigeable : la corriger corrige le classement. Une colonne
   ``ordre`` en plus des tirs créerait deux vérités, dont une périmée dès le premier correctif.
2. **``barrage_tir.score`` nul signifie ABSENT**, pas « pas encore saisi ». L'absence au barrage
   annoncé est une issue réglementaire (art. B.6.5.2.4 : l'archer est déclaré perdant) ; la saisie
   en attente n'a **pas de ligne**. C'est la ligne, pas le ``NULL``, qui distingue les deux — les
   confondre ferait perdre quelqu'un qui n'a pas encore tiré.
3. **``portee`` arrive avec ses trois valeurs** (``qualification``, ``poule``, ``big_shoot_off``)
   alors qu'une seule est câblée de bout en bout aujourd'hui, les moteurs de poule et de Big Shoot
   Off n'ayant encore aucun consommateur de production (**DETTE-028**). Le discriminant coûte une
   colonne maintenant, et une **migration de données** si on l'ajoutait après coup.
4. **``participants_json``** fige les tireurs (``[archer_id, …]``) à l'annonce, au même parti que
   ``phase.sources_json`` (0036) et ``poste.deroule_json`` (0038) : du JSON pour une donnée toujours
   lue et écrite en entier. Le figement est le point essentiel — recalculer les tireurs depuis le
   classement à chaque lecture les ferait changer sous les pieds du juge dès qu'une volée validée en
   retard arrive.

``uq_barrage_tir`` interdit deux flèches du même archer à la même manche d'un même barrage : à ce
grain, une seconde saisie est une **correction**, donc un ``UPDATE``, jamais une ligne de plus.

Le ``downgrade`` supprime les deux tables et, avec elles, tout barrage tiré. La perte est réelle et
assumée : redescendre sous cette révision, c'est revenir à un modèle où les ex æquo ne se
départagent pas au tir. Les classements concernés retomberaient sur le rang **partagé**, qui est le
défaut d'E06US001 — donc un classement dégradé mais **juste**, pas incohérent.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0039_barrage_de_places"
down_revision = "0038_poste_ecran_de_salle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "barrage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tournoi_id", sa.Integer(), sa.ForeignKey("tournoi.id"), nullable=False),
        sa.Column("phase_id", sa.Integer(), sa.ForeignKey("phase.id"), nullable=True),
        sa.Column("portee", sa.String(), nullable=False),
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("rang_dispute", sa.Integer(), nullable=True),
        sa.Column("participants_json", sa.String(), nullable=False),
        sa.Column("clos", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("cree_le", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "barrage_tir",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("barrage_id", sa.Integer(), sa.ForeignKey("barrage.id"), nullable=False),
        sa.Column("manche", sa.Integer(), nullable=False),
        sa.Column("archer_id", sa.Integer(), sa.ForeignKey("archer.id"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("distance_au_centre", sa.Integer(), nullable=True),
        sa.UniqueConstraint("barrage_id", "manche", "archer_id", name="uq_barrage_tir"),
    )


def downgrade() -> None:
    # Les tirs d'abord : ils référencent le barrage.
    op.drop_table("barrage_tir")
    op.drop_table("barrage")
