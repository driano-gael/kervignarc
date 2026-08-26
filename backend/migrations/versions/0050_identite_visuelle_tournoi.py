"""0050 — l'identité visuelle du tournoi : deux accents, deux logos (E16US006, ADR-0097).

## Une table, pas six colonnes sur `tournoi`

Les logos sont des **blobs**. Posés sur `tournoi`, ils seraient relus à chaque fois qu'on touche la
ligne — liste des tournois, tableau de bord, toute lecture publique — alors qu'ils ne servent qu'à
deux endroits (l'écran de salle et l'accueil public). Une table dédiée, dont la clé primaire **est**
la clé étrangère, garde la ligne chaude légère et tient l'unicité « au plus une identité par tournoi
» par le schéma plutôt que par une garde applicative.

## Pourquoi en base et pas sur le disque

Arbitrage du commanditaire, 25/08/2026 ([ADR-0097]). Trois conséquences le décident : sauvegarder le
jour J, c'est copier le `.db` — un logo sur le disque en sortirait ; supprimer un tournoi supprime
sa descendance, un fichier orphelin non ; et `EPIC-11` promet une archive **en lecture seule**, ce
qu'un fichier remplaçable sous les pieds du tournoi archivé ne tient pas. Le prix — des octets dans
la file d'écriture unique (règle 7) — est borné par `POIDS_LOGO_MAX_OCTETS` (512 Ko), et une
écriture de logo est un geste de préparation, jamais un chemin chaud du jour J.

## Aucune ligne créée, et c'est voulu

La migration ne peuple **rien** : un tournoi sans ligne d'identité n'est pas un tournoi incomplet,
c'est un tournoi qui porte l'identité du club (`IdentiteVisuelle.accents`, CA « défaut = identité
du club si rien n'est fourni »). Semer une ligne par tournoi existant aurait matérialisé un défaut
en donnée, et rendu indiscernable « l'organisateur a choisi le rouge du club » de « il n'a rien
choisi » — distinction dont l'écran a besoin pour dire *hérité* plutôt que *réglé*.

## Supprimer le tournoi supprime son identité

La clé étrangère porte `ON DELETE CASCADE`. L'identité suit le tournoi dans la tombe, sans geste
applicatif : elle n'a pas d'existence propre, et la conserver n'aurait de sens pour personne. Ce
choix sort explicitement `identite_tournoi` du périmètre de DETTE-001, qui décrit la descendance
*non tranchée* — ici, elle l'est. Trouvé en revue adversariale : sans la cascade, un tournoi dont on
avait seulement effleuré l'écran d'identité ne se supprimait plus, en 500.

## Descente

`downgrade` supprime la table, donc **les deux logos déposés et les accents réglés**. La perte est
totale sur cette donnée et sans recours (les octets ne vivent nulle part ailleurs), mais elle est
**purement cosmétique** : aucune règle sportive, aucun classement, aucune garde de cycle de vie n'en
dépend. Un tournoi redescendu retrouve l'identité du club et se joue à l'identique.

[ADR-0097]: ../../../docs/adr/0097-un-logo-de-tournoi-vit-en-base-avec-lui.md
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0050_identite_visuelle_tournoi"
down_revision = "0049_arret_de_circonstance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Crée `identite_tournoi`. Aucune donnée à reprendre (cf. en-tête)."""
    op.create_table(
        "identite_tournoi",
        # `ON DELETE CASCADE`, et **non** la FK nue que DETTE-001 décrit pour le reste de la
        # descendance : l'identité n'est pas une donnée *du* tournoi, c'est un **composant strict**
        # de son agrégat — une ligne, sans descendance, cosmétique, qui n'a aucun sens sans lui.
        # C'est le traitement que le schéma réserve déjà à cette population (`volee.serie_id`,
        # `placement.phase_id`), la cascade applicative restant pour ce qui se supprime pour de bon.
        #
        # Sans cela, `PRAGMA foreign_keys=ON` (engine.py) ferait échouer la suppression du tournoi
        # dès qu'une identité existe — et comme la ligne naît au premier réglage et n'est jamais
        # retirée, le tournoi devenait **définitivement** indéracinable. L'argument d'[ADR-0097]
        # § « en base plutôt que sur le disque » (« supprimer un tournoi supprime sa descendance »)
        # aurait alors été rendu faux par la table même qu'il justifie.
        #
        # Clé primaire **et** étrangère : au plus une identité par tournoi, tenu par le schéma.
        sa.Column(
            "tournoi_id",
            sa.Integer(),
            sa.ForeignKey("tournoi.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        # Forme normalisée `#rrggbb` (`domain.identite.Couleur.hex`), ou `NULL`.
        #
        # ⚠️ **Nullables, et c'est le point délicat du schéma.** Une ligne peut exister sans
        # qu'aucune couleur ait été choisie : elle naît dès le dépôt d'un **logo**, les deux
        # gestes étant indépendants à l'écran. Y mettre les couleurs du club par défaut ferait
        # passer ce tournoi pour *réglé* alors qu'il **hérite** — distinction dont l'écran a
        # besoin, et que le CA impose (« défaut = identité du club **si rien n'est fourni** »).
        sa.Column("accent_primaire", sa.String(), nullable=True),
        sa.Column("accent_secondaire", sa.String(), nullable=True),
        # Chaque logo est un triplet (octets, type MIME, empreinte) : tous `NULL` ensemble, ou
        # aucun. Le
        # `CHECK` correspondant n'est pas posé — SQLite l'accepterait, mais l'invariant est déjà
        # tenu d'un seul endroit (l'adapter écrit toujours le couple), et une contrainte de plus ne
        # protégerait que d'un écrivain qui n'existe pas.
        sa.Column("logo_evenement", sa.LargeBinary(), nullable=True),
        sa.Column("logo_evenement_type", sa.String(), nullable=True),
        # L'empreinte du contenu, **stockée** : la projection des réglages se fait sans charger un
        # octet, et hacher 512 Ko à chaque affichage public pour connaître un numéro de version
        # aurait annulé la raison d'être de cette table. Elle sert aussi d'`ETag`.
        sa.Column("logo_evenement_empreinte", sa.String(), nullable=True),
        sa.Column("logo_club", sa.LargeBinary(), nullable=True),
        sa.Column("logo_club_type", sa.String(), nullable=True),
        sa.Column("logo_club_empreinte", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Supprime la table — donc les logos et les accents. Perte cosmétique (cf. en-tête)."""
    op.drop_table("identite_tournoi")
