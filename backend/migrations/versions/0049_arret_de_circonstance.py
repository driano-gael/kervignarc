"""0049 — l'arrêt posé le jour J, et l'heure de la coupe (E05US034, ADR-0092).

## Deux ajouts, une seule idée : rendre la pause **visible** et **posable en cours de journée**

- la table `arret_de_circonstance` — une pause décidée **pendant** que la salle tire (« bloque-moi
  dans deux tours »), propre à **un créneau** ;
- la colonne `franchissement_arret.arrete_depuis` — l'instant où un arrêt a éteint sa **première**
  phase, que la pastille du tableau de bord décompte (« 2 phases attendent votre relance depuis
  14 min »).

## Pourquoi une table, alors qu'`E05US033` s'en était passé pour la définition

Parce que ce ne sont pas les mêmes arrêts, et [ADR-0076] trace la frontière :

- un arrêt **programmé à l'atelier** est de la *composition*. Il vit dans `deroule_etape.config`, en
  JSON, sans migration (§4), et **tous les créneaux du tournoi le rejouent** — c'est même le sens de
  cet ADR ;
- un arrêt **posé le jour J** est de la *conduite* (§5). Le mettre au même endroit ferait s'arrêter
  le créneau de l'après-midi pour une panne de chauffage du matin : une décision locale
  **propagée**, symétrique exact de la divergence silencieuse qu'ADR-0076 a supprimée.

D'où un rangement distinct, porteur d'un `depart_id`. Et une **table** plutôt qu'un document JSON
sur `depart` : l'unicité `(depart_id, phase_id, apres_tour)` doit être tenue par le schéma, la pose
étant concurrente (l'organisateur clique pendant que ~30 tablettes valident, et un double-clic est
un geste du jour J). Un document JSON ne sait pas tenir une contrainte d'unicité. Le volume, lui,
ne tranche rien : quelques lignes par créneau dans les deux cas.

## La colonne `arrete_depuis`, et pourquoi elle est nullable

`NULL` a un **sens** : cet arrêt n'a encore rien éteint. Deux cas réels — un arrêt de créneau *armé*
dont aucune phase n'a fini son tour, et une pause *manquée* (avancement sauté, phase déjà tout
tirée) tracée `LEVE` sans mise en pause. Y mettre une heure ferait apparaître au tableau de bord
une attente qui n'a jamais existé.

⚠️ **Aucune règle du mécanisme n'en dépend** — c'est une donnée d'affichage. C'est ce qui rend le
`NULL` inoffensif sur les lignes **existantes** : une base migrée en pleine journée garde ses arrêts
franchis, qui perdent seulement leur compteur « depuis ». La salle se relance exactement pareil.

## Descente

`downgrade` supprime la table et la colonne. **La perte est bornée et non sportive** : disparaissent
les arrêts posés en cours de journée (les arrêts de l'atelier, eux, sont dans le JSON d'étape et ne
bougent pas) et les heures de coupe. Les phases en pause **restent en pause** — leur statut vit dans
`phase.statut`, que cette migration ne touche pas — et se relancent par le bouton de relance, qui
lit `franchissement_arret`, table conservée.

⚠️ Comme pour `0048`, l'effet de bord d'une descente en pleine journée est qu'un arrêt de
circonstance non encore franchi disparaît sans prévenir : l'organisateur attendrait une pause qui
ne viendra jamais. Bénin sur un tournoi terminé, à ne pas faire le jour J — ce qui vaut pour toute
descente de schéma.

[ADR-0076]: ../../../docs/adr/0076-un-deroule-defini-une-fois-un-avancement-par-depart.md
[ADR-0092]: ../../../docs/adr/0092-un-arret-pose-le-jour-j-appartient-au-creneau.md
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0049_arret_de_circonstance"
down_revision = "0048_franchissement_arret"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Crée `arret_de_circonstance` et date les franchissements. Aucune donnée à reprendre."""
    op.create_table(
        "arret_de_circonstance",
        sa.Column("id", sa.Integer(), primary_key=True),
        # DETTE-001 : FK sans ON DELETE CASCADE — descendance du tournoi, politique de suppression
        # non tranchée. Ne pas la contourner ici est la seule façon de la traiter d'un geste.
        sa.Column("depart_id", sa.Integer(), sa.ForeignKey("depart.id"), nullable=False),
        sa.Column("phase_id", sa.Integer(), sa.ForeignKey("phase.id"), nullable=False),
        sa.Column("apres_tour", sa.Integer(), nullable=False),
        sa.Column("portee", sa.String(), nullable=False),
        sa.UniqueConstraint(
            "depart_id", "phase_id", "apres_tour", name="uq_arret_circonstance_phase_tour"
        ),
    )
    # Nullable **sans** `server_default` : « pas encore de coupe » est un état légitime, pas une
    # valeur manquante à combler. Un défaut serveur devrait mentir sur une heure.
    op.add_column(
        "franchissement_arret",
        sa.Column("arrete_depuis", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    """Retire la table et la colonne. Les phases en pause le restent, relançables (cf. en-tête)."""
    op.drop_column("franchissement_arret", "arrete_depuis")
    op.drop_table("arret_de_circonstance")
