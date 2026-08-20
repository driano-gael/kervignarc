"""0048 — la table `franchissement_arret` : ce qu'un arrêt programmé a coupé (E05US033, ADR-0091).

## Ce qui demande une migration, et ce qui n'en demande pas

E05US033 ajoute **deux** notions, et une seule touche le schéma :

- la **définition** d'un arrêt (« après le tour 3, portée départ ») et le **découpage en
  tours** d'une qualification sont de la *configuration d'étape*. Ils vivent donc dans
  `deroule_etape.config`, en JSON, et **aucune migration n'est nécessaire** : c'est exactement la
  propriété qu'ADR-0046 achète en laissant le document libre à la racine, et que l'ADR-0011 avait
  posée avant lui (« ajouter une politique sans migration de schéma »). Une base non migrée relit
  `arrets` absent comme « aucun arrêt », donc en comportement **inchangé** — le premier CA de l'US ;
- le **franchissement** est de l'*avancement* : cet arrêt-là a-t-il coupé, dans ce créneau-ci, et
  l'admin l'a-t-il relevé. C'est une entité neuve, propre au départ, et c'est cette table.

## Pourquoi persister ça, alors que le projet dérive tout le reste

C'est la question que la revue posera, donc autant y répondre ici. Le projet ne persiste **pas**
l'avancement : chaque service de format le recalcule à la lecture (ADR-0090 §5), et le lancement
d'un tour est un *événement*, pas un état (ADR-0056). Le franchissement fait exception parce que la
condition de déclenchement est **monotone** : une fois le tour 2 achevé, « le tour 2 est achevé et
un arrêt est posé après le tour 2 » reste vrai indéfiniment. Un déclencheur qui relirait cette
condition sans mémoire remettrait la phase en pause **à chaque reprise** — l'organisateur perdrait
la main définitivement, et la salle ne repartirait jamais. La trace n'est donc pas un confort
d'implémentation : c'est ce qui rend la reprise possible.

## La forme de la table

`phase_id` désigne la phase **déclenchante** et `apres_tour` l'arrêt dans la définition de son étape
: le couple porte l'unicité. Cette contrainte n'est pas décorative — c'est l'idempotence du
déclencheur tenue par le **schéma** et non seulement par le service, ce qui compte parce qu'il
tourne après chaque validation de score et que ~30 tablettes valident.

Pas de `depart_id` : il se lit par jointure sur `phase`. Le dupliquer serait une seconde source pour
ce que la phase dit déjà — le raisonnement de `PhaseORM.ordre` face à un `etape_id` (DETTE-026).

Deux documents JSON (`tours_a_finir`, `phases_arretees`) plutôt que deux tables d'association : les
volumes sont de quelques lignes par créneau, rien ne les interroge autrement que « pour cet arrêt »,
et la règle 12 dit où mettre la rigueur — au moteur métier, pas à l'outillage.

⚠️ **`ON DELETE CASCADE` absent, comme partout** (`DETTE-001`) : cette table est un descendant du
départ par la phase, et la politique de suppression de la descendance du tournoi n'est pas tranchée.
Ne pas la contourner ici serait la seule façon de la traiter un jour d'un seul geste.

## Descente

`downgrade` supprime la table. **La perte est assumée et bornée** : ce qui disparaît est l'état
« cet arrêt a coupé, il attend une relance ». Après descente, les phases mises en pause **restent en
pause** — leur statut vit dans `phase.statut`, que cette migration ne touche pas — et se relancent
par le geste manuel qui existait déjà (`POST /departs/{id}/phases/{id}/statut`, transition
`reprendre`). Aucune donnée sportive n'est en jeu : ni score, ni classement, ni appariement.

⚠️ Le seul effet de bord d'une descente est que les arrêts programmés **se redéclencheraient** à la
remontée, la mémoire ayant disparu. C'est bénin sur un tournoi terminé et gênant en pleine journée —
donc à ne pas faire le jour J, ce qui vaut de toute façon pour toute descente de schéma.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0048_franchissement_arret"
down_revision = "0047_vue_en_cours"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Crée `franchissement_arret`. Aucune donnée à reprendre : la notion est neuve."""
    op.create_table(
        "franchissement_arret",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("phase_id", sa.Integer(), sa.ForeignKey("phase.id"), nullable=False),
        sa.Column("apres_tour", sa.Integer(), nullable=False),
        sa.Column("etat", sa.String(), nullable=False),
        # Défauts serveur : une ligne écrite par un chemin qui ne les renseignerait pas reste
        # relisible (`json.loads` d'une chaîne vide lèverait). Les documents vides sont le cas
        # normal d'un arrêt de portée « phase », qui n'a aucun tour à attendre.
        sa.Column("tours_a_finir", sa.String(), nullable=False, server_default="{}"),
        sa.Column("phases_arretees", sa.String(), nullable=False, server_default="[]"),
        sa.UniqueConstraint("phase_id", "apres_tour", name="uq_franchissement_phase_tour"),
    )


def downgrade() -> None:
    """Supprime la table. Les phases en pause le restent, relançables à la main (cf. en-tête)."""
    op.drop_table("franchissement_arret")
