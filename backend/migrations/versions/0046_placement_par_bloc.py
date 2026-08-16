"""0046 — `placement_poule` devient `placement_par_bloc` (E05US026).

## Pourquoi renommer une table qui marche

La table posée par la `0045` porte « le bloc de couloirs contigus qu'occupe un groupe de tireurs ».
Elle a été écrite pour les **poules**, et son nom le disait — `placement_poule`, colonne
`poule_numero`.

Le système suisse a besoin du **même** mécanisme, pour **exactement la même raison** : le tireur
au repos change à chaque tour. Une poule de 5 tient sur 4 couloirs parce qu'un membre se repose,
mais jamais le même ; une ronde de suisse ré-apparie tout le plateau, donc aucun de ses tireurs n'a
de couloir attitré non plus. Dans les deux cas, persister « archer → couloir » écrirait une
information *fausse*, et c'est le bloc qu'il faut matérialiser.

Deux issues étaient possibles, et le commanditaire a tranché le **16/08/2026** :

- **y ranger les blocs du suisse sans rien renommer** : aucune migration, mais la table dit
  « poule » en contenant des rondes. C'était l'option tracée comme `DETTE-063` ;
- **renommer** : une migration, et le nom redevient vrai. **C'est l'option retenue.**

⚠️ **L'arbitrage est l'inverse de celui de `DETTE-042`** (`position` en base, « couloir de tir » en
métier), et la différence mérite d'être nommée : là-bas le mot juste ne changeait **rien** au
contenu de la colonne — c'est un synonyme non appliqué. Ici le nom désigne le mauvais **concept** :
une ronde de système suisse n'est pas une poule, ce n'est pas une question de vocabulaire mais de
vérité. Un lecteur qui trouve `poule_numero = 1` sur une phase de suisse ne se demande pas si le mot
est le bon, il se demande **ce qui a bien pu écrire ça**.

## Ce que la migration fait

SQLite ne renomme pas une colonne d'une table portant une contrainte nommée sans la reconstruire.
On crée donc la table cible, on **recopie** les lignes, puis on supprime l'ancienne — chemin
explicite, qui préserve les plans déjà posés plutôt que de les perdre comme le ferait un
`drop_table` / `create_table`.

Le contenu est **conservé à l'identique** : les blocs posés pour des phases de poules restent
valides, seule l'étiquette change. `groupe_numero` reçoit `poule_numero` sans transformation — le
numéro de poule *était déjà* un numéro de groupe.

## Descente

`downgrade` refait le chemin inverse, sans perte : le renommage est **réversible**, à la différence
de la `0045` dont la descente détruisait la table. C'est la propriété qui rend cette migration sûre
à jouer sur une base réelle.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0046_placement_par_bloc"
down_revision = "0045_placement_des_poules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Crée `placement_par_bloc`, recopie les blocs posés, supprime `placement_poule`."""
    op.create_table(
        "placement_par_bloc",
        sa.Column(
            "phase_id",
            sa.Integer(),
            sa.ForeignKey("phase.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("cible_index", sa.Integer(), nullable=False),
        sa.Column("position", sa.String(), nullable=False),
        sa.Column("groupe_numero", sa.Integer(), nullable=False),
        sa.Column("rang", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("phase_id", "cible_index", "position"),
        sa.UniqueConstraint("phase_id", "groupe_numero", "rang", name="uq_placement_par_bloc"),
    )
    op.execute(
        "INSERT INTO placement_par_bloc "
        "(phase_id, cible_index, position, groupe_numero, rang) "
        "SELECT phase_id, cible_index, position, poule_numero, rang FROM placement_poule"
    )
    op.drop_table("placement_poule")


def downgrade() -> None:
    """Rétablit `placement_poule` avec ses lignes — le renommage est réversible sans perte."""
    op.create_table(
        "placement_poule",
        sa.Column(
            "phase_id",
            sa.Integer(),
            sa.ForeignKey("phase.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("cible_index", sa.Integer(), nullable=False),
        sa.Column("position", sa.String(), nullable=False),
        sa.Column("poule_numero", sa.Integer(), nullable=False),
        sa.Column("rang", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("phase_id", "cible_index", "position"),
        sa.UniqueConstraint("phase_id", "poule_numero", "rang", name="uq_placement_poule_bloc"),
    )
    op.execute(
        "INSERT INTO placement_poule "
        "(phase_id, cible_index, position, poule_numero, rang) "
        "SELECT phase_id, cible_index, position, groupe_numero, rang FROM placement_par_bloc"
    )
    op.drop_table("placement_par_bloc")
