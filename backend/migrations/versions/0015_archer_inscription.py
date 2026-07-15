"""archer : inscription complete (prenom, categorie)

Revision ID: 0015_archer_inscription
Revises: 0014_archer_club_id
Create Date: 2026-07-15

Complete `archer` pour l'inscription reelle (E02US002) : ajoute `prenom` (NOT NULL) et
`categorie_id` (FK -> categorie.id, NOT NULL). Le club, lui, **reste nullable** : voir ADR-0014.

**Cette migration vide la table `archer`.** Ce n'est pas un raccourci, c'est le seul chemin
praticable. `categorie_id` est NOT NULL et la colonne n'existait pas avant cette revision : aucune
ligne existante ne peut porter de categorie, donc aucune ne peut satisfaire la contrainte. Les
trois issues possibles ont ete pesees :

- **retro-remplir** avec une categorie arbitraire : inventer une donnee que personne n'a saisie,
  et fausser d'emblee classement, placement et facturation qui en dependent tous ;
- **echouer** si des lignes subsistent : impasse — aucun ecran ni endpoint ne permet aujourd'hui
  d'editer ou de supprimer un archer (c'est E02US003), l'utilisateur ne pourrait rien corriger ;
- **supprimer** : les seules lignes concernees sont les archers de la tranche verticale (E00US011),
  sans prenom ni categorie, cree avant que l'inscription n'existe. C'est le choix retenu.

Le `downgrade` ne les rend pas : il retire les colonnes, pas les lignes. Une base de production
n'existe pas encore a ce stade du projet (jalon J1 en cours), et l'arbitrage a ete pris.

**DETTE-001 (docs/dette.md) elargie.** `archer.categorie_id` est une FK **de la descendance du
tournoi** — contrairement a `archer.club_id` pose par 0014, qui pointe vers le referentiel global
des clubs. Elle rejoint donc la politique de suppression d'un tournoi non tranchee, et la ligne du
registre est elargie plutot que contournee localement.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_archer_inscription"
down_revision: str | None = "0014_archer_club_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Vide `archer`, puis ajoute `prenom` et `categorie_id` (NOT NULL) avec sa FK."""
    # Avant l'ALTER : les lignes existantes ne peuvent pas satisfaire `categorie_id NOT NULL`
    # (cf. docstring). `DELETE` plutot que `DROP`/`CREATE` : les FK entrantes (`score.archer_id`)
    # restent en place, et `score` est vide de fait puisqu'il n'y a plus d'archer a marquer.
    op.execute(sa.text("DELETE FROM score"))
    op.execute(sa.text("DELETE FROM archer"))
    with op.batch_alter_table("archer") as batch:
        # `server_default=''` puis retire : `batch_alter_table` recree la table et recopie les
        # lignes — il n'y en a plus aucune ici, mais SQLite exige malgre tout un defaut pour une
        # colonne NOT NULL ajoutee. On ne le laisse pas : un prenom vide ne doit pas etre
        # insereable en silence, c'est `Archer.creer` qui garde cette regle.
        batch.add_column(sa.Column("prenom", sa.String(), nullable=False, server_default=""))
        batch.add_column(sa.Column("categorie_id", sa.Integer(), nullable=False))
        # Contrainte **nommee** : SQLite ne sait pas supprimer une contrainte anonyme, et le
        # downgrade doit pouvoir la cibler (meme raison qu'en 0014).
        batch.create_foreign_key("fk_archer_categorie_id", "categorie", ["categorie_id"], ["id"])
    with op.batch_alter_table("archer") as batch:
        batch.alter_column("prenom", server_default=None)


def downgrade() -> None:
    """Retire la FK puis les colonnes `categorie_id` et `prenom` (ne restaure aucune ligne)."""
    with op.batch_alter_table("archer") as batch:
        batch.drop_constraint("fk_archer_categorie_id", type_="foreignkey")
        batch.drop_column("categorie_id")
        batch.drop_column("prenom")
