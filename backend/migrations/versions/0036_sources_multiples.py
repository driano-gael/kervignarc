"""peuplement d'une phase : `config.source` (unique) → `config.sources` (liste) — E05US010

Revision ID: 0036_sources_multiples
Revises: 0035_format_tournoi
Create Date: 2026-07-31

E05US010 / ADR-0061 fait passer le peuplement d'une phase d'**une** source à **plusieurs**, chacune
portant sa `nature` (`rangs` / `issue_de_tour` / `reste`). Migration de **données** (pas de schéma :
les colonnes `config` restent des `String` JSON) :

    {"source": {"ordre_source": 1, "rang_debut": 1, "rang_fin": 16}, …}
    → {"sources": [{"nature": "rangs", "ordre_source": 1, "rang_debut": 1, "rang_fin": 16}], …}

⚠️ **Deux tables**, et c'est le point à ne pas manquer : `SourcePhase` est sérialisée dans
`phase.config` **et**, depuis E01US023 (ADR-0060 §5), dans `format_tournoi.config`, où elle est
imbriquée sous `etapes[]`. Migrer la première seule laisserait les **formats de bibliothèque** en
forme ancienne — donc les tournois créés à partir d'eux. C'est l'élargissement de DETTE-015 relevé
à la revue d'E01US023, que cette US résorbe.

La migration est **idempotente** (une ligne déjà en forme `sources` est laissée intacte) et la
relecture reste tolérante à l'ancienne forme (`repositories._vers_sources`), filet pour une base
restaurée d'une sauvegarde antérieure — même régime que la migration `0028`.

Le `downgrade` **ne peut pas être total**, et l'assume plutôt que de mentir : une phase à plusieurs
sources, ou à source non « par rangs », n'a pas de représentation dans l'ancienne forme. Il rétablit
donc le cas migrable (une seule source par rangs, à fin bornée) et **laisse en place** les autres,
plutôt que de choisir arbitrairement une source à conserver et d'en perdre silencieusement. Une base
ainsi redescendue reste lisible par le code d'avant l'US pour les phases simples, qui sont les
seules qu'il savait produire.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

revision: str = "0036_sources_multiples"
down_revision: str | Sequence[str] | None = "0035_format_tournoi"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _vers_liste(config: dict[str, Any]) -> bool:
    """Réécrit `source` → `sources` **en place**. Rend `True` si la config a changé."""
    if "sources" in config:
        return False  # déjà migrée
    source = config.pop("source", None)
    if source is None:
        return False  # phase alimentée par les inscriptions : rien à migrer
    config["sources"] = [
        {
            "nature": "rangs",
            "ordre_source": source["ordre_source"],
            "rang_debut": source["rang_debut"],
            "rang_fin": source["rang_fin"],
        }
    ]
    return True


def _vers_unique(config: dict[str, Any]) -> bool:
    """Réécrit `sources` → `source` quand c'est représentable. Rend `True` si la config a changé."""
    sources = config.get("sources")
    if not isinstance(sources, list) or len(sources) != 1:
        return False  # zéro ou plusieurs sources : pas d'équivalent dans l'ancienne forme
    source = sources[0]
    if source.get("nature", "rangs") != "rangs" or source.get("rang_fin") is None:
        return False  # nature ou fin ouverte inexprimables avant E05US010
    config.pop("sources")
    config["source"] = {
        "ordre_source": source["ordre_source"],
        "rang_debut": source["rang_debut"],
        "rang_fin": source["rang_fin"],
    }
    return True


def _migrer_phases(sens: Any) -> None:
    conn = op.get_bind()
    for ligne in conn.execute(sa.text("SELECT id, config FROM phase")).fetchall():
        config = json.loads(ligne.config)
        if sens(config):
            conn.execute(
                sa.text("UPDATE phase SET config = :config WHERE id = :id"),
                {"config": json.dumps(config), "id": ligne.id},
            )


def _migrer_formats(sens: Any) -> None:
    conn = op.get_bind()
    for ligne in conn.execute(sa.text("SELECT id, config FROM format_tournoi")).fetchall():
        config = json.loads(ligne.config)
        etapes = config.get("etapes")
        if not isinstance(etapes, list):
            continue
        # ⚠️ On matérialise les résultats **avant** de tester : `any(sens(e) for e in etapes)`
        # court-circuiterait à la première étape migrée et laisserait les suivantes en forme
        # ancienne, dans un format à moitié converti que plus rien ne signalerait.
        modifiees = [sens(etape) for etape in etapes]
        if any(modifiees):
            conn.execute(
                sa.text("UPDATE format_tournoi SET config = :config WHERE id = :id"),
                {"config": json.dumps(config), "id": ligne.id},
            )


def upgrade() -> None:
    """`config.source` → `config.sources` (liste), dans `phase` **et** dans `format_tournoi`."""
    _migrer_phases(_vers_liste)
    _migrer_formats(_vers_liste)


def downgrade() -> None:
    """Rétablit `config.source` là où c'est représentable (une source « par rangs » bornée)."""
    _migrer_phases(_vers_unique)
    _migrer_formats(_vers_unique)
