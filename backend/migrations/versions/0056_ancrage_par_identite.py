"""la séquence s'ancre sur l'identité de l'étape — E05US022, ADR-0078

Revision ID: 0056_ancrage_par_identite
Revises: 0055_volee_role_de_saisie
Create Date: 2026-09-20

Trois gestes, et **l'ordre entre eux est la migration** : tant que les rangs sont encore justes,
on s'en sert pour écrire les identités ; ensuite seulement on leur retire leur rôle.

1. ``phase.etape_id`` remplace ``phase.ordre``. La reprise apparie chaque avancement à l'étape de
   **même rang dans le tournoi de son créneau** — c'est-à-dire exactement la jointure que le code
   faisait à la lecture jusqu'ici, donc la reprise conserve le comportement observé, y compris sur
   une base dont les rangs auraient déjà divergé : on fige ce que l'application affichait, on ne
   tente pas de deviner ce qu'elle aurait dû afficher.
2. les ``config`` de ``deroule_etape`` passent de ``ordre_source`` à ``etape_source_id``, résolus
   **dans le même tournoi**. Les deux formes historiques sont reprises : ``config.sources`` (liste,
   E05US010) et ``config.source`` (objet unique, E05US001) — oublier la seconde laisserait muets
   les prélèvements des plus vieux tournois.
3. ``uq_deroule_tournoi_ordre`` est levée (arbitrage du 20/09/2026, cf. ADR-0078 § Conséquences).
   Elle disait vrai, mais le rang ne désigne plus rien : ce qu'elle coûtait — garer tous les rangs
   en négatif avant de les reposer — n'avait plus de contrepartie. La suite 1..N reste tenue par
   le domaine (``verifier_sequence``), à chaque écriture.

``format_tournoi`` n'est **pas** touchée : ses ``ModelePhase`` n'ont pas d'identité par
construction (ADR-0060 §5), et l'ancrage par rang y est correct, pas dégradé (ADR-0078 §3).

⚠️ **Un avancement dont le rang n'a aucune étape est supprimé**, pas migré. Il était déjà invisible
à toute lecture — les deux adapters écartent l'orpheline — et ``etape_id`` est ``NOT NULL`` : le
garder exigerait d'inventer un rattachement. Le nombre supprimé part au journal d'Alembic.

Le ``downgrade`` rétablit ``phase.ordre`` depuis le rang de l'étape désignée, et les
``ordre_source`` depuis les identités. Il est **fidèle** tant que la séquence est cohérente 1..N,
ce que le domaine garantit ; sur une base trafiquée à la main, il rend ce que l'ancien code aurait
lu. La contrainte d'unicité est reposée **en premier**, pour que l'échec précède toute réécriture
de données — deux étapes au même rang est un état qu'ADR-0078 rend possible et que l'ancien
schéma interdisait.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "0056_ancrage_par_identite"
down_revision = "0055_volee_role_de_saisie"
branch_labels = None
depends_on = None

_JOURNAL = logging.getLogger("alembic.runtime.migration")


def _etapes_par_tournoi(connexion: sa.Connection) -> dict[int, dict[int, int]]:
    """``{tournoi_id: {ordre: etape_id}}`` — la table de résolution, lue une fois."""
    table: dict[int, dict[int, int]] = {}
    for etape_id, tournoi_id, ordre in connexion.execute(
        sa.text("SELECT id, tournoi_id, ordre FROM deroule_etape")
    ):
        table.setdefault(tournoi_id, {})[ordre] = etape_id
    return table


def _rangs_par_etape(connexion: sa.Connection) -> dict[int, int]:
    """``{etape_id: ordre}`` — la réciproque, pour le ``downgrade``."""
    lignes = connexion.execute(sa.text("SELECT id, ordre FROM deroule_etape")).all()
    return {int(etape_id): int(ordre) for etape_id, ordre in lignes}


def _brutes(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Les prélèvements d'une ``config``, forme E05US010 (liste) **ou** E05US001 (objet unique)."""
    sources = config.get("sources")
    if sources is None:
        unique = config.get("source")
        return [] if unique is None else [unique]
    return list(sources)


def _reecrire_sources(
    connexion: sa.Connection,
    resoudre: Callable[[int, dict[str, Any]], dict[str, Any] | None],
) -> None:
    """Réécrit les ancres de toutes les ``config`` de ``deroule_etape``.

    ⚠️ **Normalise au passage la forme ancienne en liste** : une ``config.source`` unique ressort
    en ``config.sources`` d'un élément. Le lecteur cible ne consulte plus ``config.source``, donc
    la laisser en place reviendrait à perdre le prélèvement.

    ⚠️ **Un prélèvement que ``resoudre`` rend ``None`` est RETIRÉ**, pas laissé à demi écrit
    (correctif de revue). Le laisser sans ancre rendait la ``config`` illisible, et comme les
    étapes se relisent par lot, c'était **tout le déroulé du tournoi** qui tombait en erreur —
    définitivement, sans écran pour le réparer.
    """
    lignes = list(
        connexion.execute(sa.text("SELECT id, tournoi_id, config FROM deroule_etape")).fetchall()
    )
    for etape_id, tournoi_id, brut in lignes:
        config = json.loads(brut)
        sources = _brutes(config)
        if not sources:
            continue
        config.pop("source", None)
        reecrites = [resoudre(tournoi_id, source) for source in sources]
        config["sources"] = [source for source in reecrites if source is not None]
        connexion.execute(
            sa.text("UPDATE deroule_etape SET config = :config WHERE id = :id"),
            {"config": json.dumps(config), "id": etape_id},
        )


def upgrade() -> None:
    connexion = op.get_bind()
    par_tournoi = _etapes_par_tournoi(connexion)

    # (1) `phase.etape_id`, rempli par la jointure que le code faisait déjà à la lecture.
    with op.batch_alter_table("phase") as lot:
        lot.add_column(sa.Column("etape_id", sa.Integer(), nullable=True))
    connexion.execute(
        sa.text(
            "UPDATE phase SET etape_id = ("
            "  SELECT e.id FROM deroule_etape e"
            "  JOIN depart d ON d.id = phase.depart_id"
            "  WHERE e.tournoi_id = d.tournoi_id AND e.ordre = phase.ordre"
            ")"
        )
    )
    orphelines = connexion.execute(
        sa.text("SELECT COUNT(*) FROM phase WHERE etape_id IS NULL")
    ).scalar_one()
    if orphelines:
        # Déjà invisibles à toute lecture (écartées comme orphelines par les deux adapters) : les
        # supprimer est ce qui rend la colonne `NOT NULL` tenable sans inventer de rattachement.
        # ⚠️ `franchissement_arret` pend à `phase` **sans** `ON DELETE CASCADE`, et Alembic tourne
        # sans `PRAGMA foreign_keys` : sans cette purge, la suppression laisserait des lignes
        # pendantes que rien ne signalerait jamais (correctif de revue).
        connexion.execute(
            sa.text(
                "DELETE FROM franchissement_arret WHERE phase_id IN "
                "(SELECT id FROM phase WHERE etape_id IS NULL)"
            )
        )
        connexion.execute(sa.text("DELETE FROM phase WHERE etape_id IS NULL"))
        _JOURNAL.info("0056 : %s avancement(s) orphelin(s) supprimé(s).", orphelines)

    # (2) les prélèvements, tant que les rangs disent encore vrai.
    def vers_identite(tournoi_id: int, source: dict[str, Any]) -> dict[str, Any] | None:
        ancre = source.pop("ordre_source", None)
        if ancre is None:
            return source
        etape_id = par_tournoi.get(tournoi_id, {}).get(int(ancre))
        if etape_id is None:
            # ⚠️ **Rang sans étape : on RETIRE le prélèvement** (correctif de revue). Il ne
            # désignait déjà rien — la lecture d'avant le rendait inerte —, donc le retirer
            # conserve le comportement observé. Le garder sans ancre rendait toute l'étape, et
            # donc tout le déroulé du tournoi, illisible.
            return None
        return {**source, "etape_source_id": etape_id}

    _reecrire_sources(connexion, vers_identite)

    # (3) le rang perd son rôle : colonne retirée côté phase, unicité levée côté déroulé.
    with op.batch_alter_table("phase") as lot:
        lot.drop_constraint("uq_phase_depart_ordre", type_="unique")
        lot.drop_column("ordre")
        lot.alter_column("etape_id", existing_type=sa.Integer(), nullable=False)
        lot.create_foreign_key("fk_phase_etape", "deroule_etape", ["etape_id"], ["id"])
        lot.create_unique_constraint("uq_phase_depart_etape", ["depart_id", "etape_id"])
    with op.batch_alter_table("deroule_etape") as lot:
        lot.drop_constraint("uq_deroule_tournoi_ordre", type_="unique")


def downgrade() -> None:
    connexion = op.get_bind()
    rangs = _rangs_par_etape(connexion)

    with op.batch_alter_table("deroule_etape") as lot:
        lot.create_unique_constraint("uq_deroule_tournoi_ordre", ["tournoi_id", "ordre"])

    def vers_rang(_tournoi_id: int, source: dict[str, Any]) -> dict[str, Any] | None:
        ancre = source.pop("etape_source_id", None)
        if ancre is None:
            return source
        ordre = rangs.get(int(ancre))
        # Même règle qu'à l'aller : une ancre qui ne se résout pas fait retirer le prélèvement.
        return None if ordre is None else {**source, "ordre_source": ordre}

    _reecrire_sources(connexion, vers_rang)

    with op.batch_alter_table("phase") as lot:
        lot.add_column(sa.Column("ordre", sa.Integer(), nullable=True))
    connexion.execute(
        sa.text(
            "UPDATE phase SET ordre = ("
            "  SELECT e.ordre FROM deroule_etape e WHERE e.id = phase.etape_id"
            ")"
        )
    )
    with op.batch_alter_table("phase") as lot:
        lot.drop_constraint("uq_phase_depart_etape", type_="unique")
        lot.drop_constraint("fk_phase_etape", type_="foreignkey")
        lot.drop_column("etape_id")
        lot.alter_column("ordre", existing_type=sa.Integer(), nullable=False)
        lot.create_unique_constraint("uq_phase_depart_ordre", ["depart_id", "ordre"])
