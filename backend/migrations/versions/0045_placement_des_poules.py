"""une poule occupe un bloc de couloirs contigus — E05US023

Revision ID: 0045_placement_des_poules
Revises: 0044_serie_par_phase
Create Date: 2026-08-09

[ADR-0083] §3 rend les poules jouables et tranche l'unité de placement : **la poule, pas l'archer**.

Le reste d'E05US023 se passe de migration — les réglages entrent dans `config.policies` (ADR-0046)
et le tir des rencontres réutilise la table `duel`, keyée `(phase_id, match_numero)`. Cette table-ci
est la **seule** exception, et sa raison tient en une phrase : `placement_tableau` porte un couloir
**par archer** (`phase_id, inscription_id`), or un membre de poule n'en a pas.

`poule.couloirs_occupes` en donne le pourquoi. La méthode du cercle ne fait tirer que
`effectif ÷ 2` rencontres par tour — à effectif impair, un membre se repose. Une poule de 5 tient
donc sur 4 couloirs, comme une poule de 4. **Mais le membre au repos change à chaque tour** : les
cinq tournent sur le bloc, et aucun n'a de couloir attitré. Écrire « archer → couloir » serait donc
écrire une information *fausse*, pas seulement incomplète — un plan de salle qui montrerait Dupont
au couloir C alors qu'il s'y trouve deux tours sur trois.

## Ce que la table porte, et ce qu'elle ne porte pas

Une ligne = **un couloir** attribué à une poule, plus son `rang` dans le bloc (1-based). Le rang
n'est pas décoratif : un bloc déborde librement d'une cible sur la suivante (« la poule d'après
démarre au couloir libre juste après », règle du commanditaire du 09/08/2026), et les cibles ont
une capacité **variable** de 1 à 4 depuis `GabaritSalle.ajuster`. « Cible 3, couloir C » ne dit donc
pas à lui seul s'il précède « cible 4, couloir A » ; le rang, si.

Les couloirs de chaque **rencontre**, tour par tour, ne sont **pas** persistés : ils sont dérivés à
la lecture, exactement comme l'appariement d'un tableau ([ADR-0023] / [ADR-0048]). Persister le bloc
et dériver le détail est ce qui permet de déplacer une poule entière sans réécrire un plan de
rencontres qui dépend du tour affiché.

## Clés

La **clé primaire est le couloir** — `(phase_id, cible_index, position)` — et non la poule. Elle
porte ainsi l'invariant qui compte en salle, *un couloir, un occupant*, et la base le fait respecter
au lieu de s'en remettre au seul service. `UNIQUE(phase_id, poule_numero, rang)` tient l'autre
bout : un bloc ne saute ni ne répète de position, et son index sert la lecture « les couloirs de la
poule *n* », requête de tous les appelants.

`ON DELETE CASCADE` sur `phase_id` : donnée dérivée d'une phase, feuille de la descendance — même
exception à DETTE-001 que `placement_tableau` (ADR-0024) et `duel`.

## Reprise des données et downgrade

**Aucune reprise.** La table naît vide : aucune phase de poules n'était jouable avant cette US, donc
il n'existe nulle part de plan à convertir. C'est le cas le plus simple qu'une migration puisse
avoir, et il vaut d'être dit — l'absence de bloc de reprise ici n'est pas un oubli.

Le downgrade **supprime la table**, donc les plans posés. Réversible structurellement, pas
fonctionnellement : le modèle antérieur n'a aucun endroit où loger un couloir de poule
(`placement_tableau` est keyé par inscription, ce qui est précisément ce qui ne convient pas). Même
aveu que la `0044` — le downgrade dépanne un déploiement, il ne fait pas revenir en arrière
durablement. Rien n'est journalisé ici, à la différence de la `0044` : la perte est **totale et
évidente** (la table entière), pas un résidu qu'on risquerait de ne pas voir.

[ADR-0023]: ../../../docs/adr/0023-moteur-de-placement-glouton-deterministe.md
[ADR-0048]: ../../../docs/adr/0048-cote-a-cote-des-duellistes-par-reordonnancement.md
[ADR-0083]: ../../../docs/adr/0083-le-contrat-de-phase-jouable.md
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0045_placement_des_poules"
down_revision = "0044_serie_par_phase"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Crée `placement_poule` — la table naît vide, aucune donnée à reprendre."""
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


def downgrade() -> None:
    """Supprime la table, donc les plans posés — perte totale et assumée (cf. l'en-tête)."""
    op.drop_table("placement_poule")
