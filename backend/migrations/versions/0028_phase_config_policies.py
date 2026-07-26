"""phase.config : scoring de la racine vers policies (bascule DETTE-003)

Revision ID: 0028_phase_config_policies
Revises: 0027_volee_created_at
Create Date: 2026-07-26

E05US003 / ADR-0046 fait basculer la `config` d'une phase de la forme **à plat** (`config.scoring`
à la racine, posée par E01US009) vers la forme cible **`config.policies.scoring`**, et remplace la
clé `mode` par un `nom` d'implémentation (« cumul »). Cette migration de **données** (pas de
schéma : la colonne `config` reste un `String` JSON) réécrit les lignes `phase` existantes :

    {"scoring": {"volees": 20, "fleches": 3, "mode": "cumul"}, "validation": {…}}
    → {"policies": {"scoring": {"nom": "cumul", "volees": 20, "fleches": 3}}, "validation": {…}}

Seul `scoring` est concerné (seule politique écrite à ce jour) ; `validation`, `source`, `effectif`
restent **à la racine** (le grain de validation n'est pas une politique de moteur, ADR-0046). La
migration est **idempotente** : une ligne déjà en forme `policies` (ou sans `scoring`) est laissée
intacte. La relecture (`repositories._lire_scoring`) reste par ailleurs tolérante à l'ancienne
forme, filet pour une base restaurée d'une sauvegarde antérieure à cette migration.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028_phase_config_policies"
down_revision: str | None = "0027_volee_created_at"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Déplace `config.scoring` (racine) sous `config.policies.scoring`, `mode` → `nom`."""
    conn = op.get_bind()
    lignes = conn.execute(sa.text("SELECT id, config FROM phase")).fetchall()
    for ligne in lignes:
        config = json.loads(ligne.config)
        if "policies" in config or "scoring" not in config:
            continue  # déjà migrée, ou phase sans scoring (autre type)
        ancien = config.pop("scoring")
        scoring = {
            "nom": "cumul",
            "volees": ancien["volees"],
            "fleches": ancien["fleches"],
        }
        nouveau = {"policies": {"scoring": scoring}, **config}
        conn.execute(
            sa.text("UPDATE phase SET config = :config WHERE id = :id"),
            {"config": json.dumps(nouveau), "id": ligne.id},
        )


def downgrade() -> None:
    """Ramène `config.policies.scoring` à la racine (`config.scoring`), `nom` → `mode`."""
    conn = op.get_bind()
    lignes = conn.execute(sa.text("SELECT id, config FROM phase")).fetchall()
    for ligne in lignes:
        config = json.loads(ligne.config)
        policies = config.get("policies")
        if not isinstance(policies, dict) or "scoring" not in policies:
            continue
        scoring = policies["scoring"]
        config.pop("policies")
        ancien = {
            "scoring": {
                "volees": scoring["volees"],
                "fleches": scoring["fleches"],
                "mode": "cumul",
            },
            **config,
        }
        conn.execute(
            sa.text("UPDATE phase SET config = :config WHERE id = :id"),
            {"config": json.dumps(ancien), "id": ligne.id},
        )
