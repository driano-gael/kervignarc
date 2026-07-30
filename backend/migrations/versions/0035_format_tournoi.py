"""format de tournoi : la brique de bibliothèque qui décrit un déroulé (E01US023, ADR-0060 §5)

Crée la table `format_tournoi`. Un format porte un `nom` (**unique**), une `origine`
(`ffta` / `utilisateur`) et une `config` JSON contenant la **séquence de modèles de phases** —
même forme, étape par étape, que `PhaseORM.config`, pour que les deux se relisent avec les mêmes
fonctions.

**Pourquoi une table neuve plutôt qu'un `tournoi_id` nullable sur `phase`** (le geste appliqué aux
catégories et aux blasons en `0034`) : le barème n'est pas une entité — il vit dans la `config` de
la phase de qualification, il n'y a rien à relâcher — et l'invariant d'une phase est **collectif**
(`SequencePhases` exige des ordres contigus 1..N). Des phases de bibliothèque au `tournoi_id` nul
porteraient un statut vide de sens et des ordres en collision : toute lecture globale casserait
l'invariant qui protège le moteur de phases. Cf. ADR-0060 §5.

**Aucune FK vers `tournoi`** : un format n'appartient pas à une édition (même régime que `club`).
Rien ne migre — la table naît vide et se remplit au préchargement ou à la main. Le `downgrade` la
supprime avec son contenu, ce qu'il annonce : les formats n'ont aucun tournoi où retomber, et les
phases déjà appliquées ne les référencent pas (elles survivent intactes).

Revision ID: 0035_format_tournoi
Revises: 0034_briques_patrimoine
Create Date: 2026-07-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0035_format_tournoi"
down_revision: str | Sequence[str] | None = "0034_briques_patrimoine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée `format_tournoi` (nom unique, origine, config JSON de la séquence d'étapes)."""
    op.create_table(
        "format_tournoi",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nom", sa.String(), nullable=False),
        sa.Column("origine", sa.String(), nullable=False, server_default="utilisateur"),
        sa.Column("config", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nom"),
    )


def downgrade() -> None:
    """Supprime `format_tournoi` — **et donc tous les formats de la bibliothèque**.

    Destructeur et assumé comme tel : un format n'a aucun tournoi où retomber. Les **phases** déjà
    appliquées ne sont pas touchées — elles portent leur propre copie du déroulé et ne référencent
    aucun format (ADR-0060 §2). Un retour arrière silencieusement destructeur serait pire ; celui-ci
    l'est ouvertement.
    """
    op.drop_table("format_tournoi")
