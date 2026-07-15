"""archer : vide la table et ses scores, puis ajoute prenom et categorie

Revision ID: 0015_archer_inscription
Revises: 0014_archer_club_id
Create Date: 2026-07-15

Complete `archer` pour l'inscription reelle (E02US002) : ajoute `prenom` (NOT NULL) et
`categorie_id` (FK -> categorie.id, NOT NULL). Le club, lui, **reste nullable** : voir ADR-0014.

**Cette migration vide la table `archer` — et, avec elle, la table `score`** (les fleches des
archers supprimes n'ont plus de tireur ; elles partent avec eux, et leur FK l'imposerait de toute
facon). Ce n'est pas un raccourci, c'est le seul chemin praticable. `categorie_id` est NOT NULL et
la colonne n'existait pas avant cette revision : aucune ligne existante ne peut porter de
categorie, donc aucune ne peut satisfaire la contrainte. Les trois issues possibles ont ete
pesees :

- **retro-remplir** avec une categorie arbitraire : inventer une donnee que personne n'a saisie,
  et fausser d'emblee classement, placement et facturation qui en dependent tous ;
- **echouer** si des lignes subsistent : impasse — aucun ecran ni endpoint ne permet aujourd'hui
  d'editer ou de supprimer un archer (c'est E02US003), l'utilisateur ne pourrait rien corriger ;
- **supprimer** : les seules lignes concernees sont les archers de la tranche verticale (E00US011),
  sans prenom ni categorie, cree avant que l'inscription n'existe. C'est le choix retenu.

Le `downgrade` ne les rend pas : il retire les colonnes, pas les lignes. Une base de production
n'existe pas encore a ce stade du projet (jalon J1 en cours), et l'arbitrage a ete pris.

**Ce precedent est borne — ne pas le recopier tel quel.** L'argument decisif ci-dessus (« aucune
base reelle ») est une premisse **datee**, qui expirera sans que rien ne se declenche. Passe le
premier tournoi joue sur cette application, une colonne NOT NULL non retro-remplissable est un
**blocage d'US**, pas une autorisation de purge : il faudra une valeur par defaut metier, ou un
ecran de correction livre avant la migration. Cette revision est un cas de jalon J1, pas un
patron.

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
    """Vide `archer` et ses `score`, puis ajoute `prenom` et `categorie_id` (NOT NULL) + la FK."""
    # Avant l'ALTER : les lignes existantes ne peuvent pas satisfaire `categorie_id NOT NULL`
    # (cf. docstring). `DELETE` plutot que `DROP`/`CREATE` : la FK entrante (`score.archer_id`,
    # la seule vers `archer`) reste en place.
    #
    # `score` d'abord, et ce n'est pas cosmetique : ce sont les fleches des archers qu'on supprime
    # juste apres — elles n'auront plus de tireur, et la FK refuserait l'ordre inverse.
    op.execute(sa.text("DELETE FROM score"))
    op.execute(sa.text("DELETE FROM archer"))
    with op.batch_alter_table("archer") as batch:
        # Aucun `server_default` sur ces colonnes NOT NULL, et ce n'est pas un oubli :
        # `create_foreign_key` ci-dessous force le mode *recreate* d'Alembic, qui reconstruit la
        # table et recopie les lignes par INSERT ... SELECT plutot que d'emettre un ALTER ADD
        # COLUMN. La table est vide (DELETE ci-dessus), donc il n'y a rien a recopier et aucun
        # defaut n'est requis. Un `server_default` ici serait pire qu'inutile : il rendrait un
        # prenom vide insereable en silence, alors que `Archer.creer` en fait une erreur.
        batch.add_column(sa.Column("prenom", sa.String(), nullable=False))
        batch.add_column(sa.Column("categorie_id", sa.Integer(), nullable=False))
        # Contrainte **nommee** : SQLite ne sait pas supprimer une contrainte anonyme, et le
        # downgrade doit pouvoir la cibler (meme raison qu'en 0014).
        batch.create_foreign_key("fk_archer_categorie_id", "categorie", ["categorie_id"], ["id"])


def downgrade() -> None:
    """Retire la FK puis les colonnes `categorie_id` et `prenom` (ne restaure aucune ligne)."""
    with op.batch_alter_table("archer") as batch:
        batch.drop_constraint("fk_archer_categorie_id", type_="foreignkey")
        batch.drop_column("categorie_id")
        batch.drop_column("prenom")
