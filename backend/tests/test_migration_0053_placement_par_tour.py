"""Migration 0053 — la pose appartient à un tour, **sans rien changer pour personne**.

Test **de non-régression** au sens de la règle 9 : l'oracle est le comportement décrit par la
docstring de la migration, et l'implémenteur est le mieux placé pour l'écrire.

⚠️ **Écrit en revue d'E03US012, où il manquait** — alors que le dépôt en a douze précédents.
`test_placement_tableau_repository.py` prouve le **schéma d'arrivée** : il tourne sur une base
déjà montée en tête de chaîne, donc il n'emprunte jamais le chemin de **reprise**. Or la reprise est
la seule garantie faite aux bases existantes — « les poses deviennent celles du tour 1 » — et le
`downgrade` est **destructeur**, ce qu'aucune ligne ne vérifiait.

Ce que ces tests gardent :

1. une pose **déjà en base** ressort au **tour 1**, cible et couloir inchangés ;
2. la clé primaire d'arrivée est bien `(phase_id, tour, inscription_id)`, dans **cet ordre** — les
   `session.get` de l'adapter en dépendent, et un ordre différent les ferait lire à côté ;
3. la descente **perd** les poses des tours ≥ 2, la docstring l'assume, le test l'épingle — et elle
   ne doit pas échouer pour autant.

Les clés étrangères sont désactivées côté Alembic (`env.py`) : on insère une pose sans matérialiser
la phase ni l'inscription, comme les tests de migration voisins.
"""

from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

_BACKEND_ROOT = Path(__file__).resolve().parents[1]

_AVANT = "0052_reglage_podiums"
_PAR_TOUR = "0053_placement_tableau_par_tour"


def _config(url: str) -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _base(tmp_path: Path, nom: str) -> tuple[sa.Engine, Config]:
    """Une base montée **jusqu'à la veille** de 0053, avec deux poses déjà dedans."""
    url = f"sqlite:///{(tmp_path / nom).as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, _AVANT)
    engine = sa.create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO placement_tableau (phase_id, inscription_id, cible_index, position) "
                "VALUES (7, 42, 3, 'B'), (7, 43, 3, 'C')"
            )
        )
    return engine, cfg


def test_une_pose_deja_en_base_devient_une_pose_du_tour_1(tmp_path: Path) -> None:
    """La propriété qui rend le déploiement invisible : aucun plan de duels ne change d'affichage.

    C'est exactement ce que ces lignes étaient — le placement des duellistes était tour-1 uniquement
    depuis E03US009 —, donc la reprise ne fait que **nommer** ce qui était implicite.
    """
    engine, cfg = _base(tmp_path, "reprise.db")

    command.upgrade(cfg, _PAR_TOUR)

    with engine.begin() as conn:
        lignes = conn.execute(
            sa.text(
                "SELECT phase_id, tour, inscription_id, cible_index, position "
                "FROM placement_tableau ORDER BY inscription_id"
            )
        ).all()
    assert [tuple(ligne) for ligne in lignes] == [(7, 1, 42, 3, "B"), (7, 1, 43, 3, "C")]
    engine.dispose()


def test_la_cle_primaire_porte_le_tour_en_deuxieme_position(tmp_path: Path) -> None:
    """⚠️ L'**ordre** de la clé est un contrat : `PlacementTableauRepositorySQL` adresse ses lignes
    par `session.get(PlacementTableauORM, (phase_id, tour, inscription_id))`, tuple positionnel. Un
    `tour` placé ailleurs ferait lire une autre ligne — sans erreur, silencieusement."""
    engine, cfg = _base(tmp_path, "cle.db")

    command.upgrade(cfg, _PAR_TOUR)

    with engine.begin() as conn:
        colonnes = conn.execute(sa.text("PRAGMA table_info(placement_tableau)")).all()
    cle = [str(c[1]) for c in sorted(colonnes, key=lambda c: int(c[5])) if int(c[5]) > 0]
    assert cle == ["phase_id", "tour", "inscription_id"]
    engine.dispose()


def test_deux_tours_du_meme_archer_coexistent_apres_la_montee(tmp_path: Path) -> None:
    """La raison d'être de la migration : l'ancienne clé refusait la seconde ligne."""
    engine, cfg = _base(tmp_path, "coexistence.db")
    command.upgrade(cfg, _PAR_TOUR)

    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO placement_tableau (phase_id, tour, inscription_id, cible_index, "
                "position) VALUES (7, 2, 42, 1, 'A')"
            )
        )
        total = conn.execute(
            sa.text("SELECT COUNT(*) FROM placement_tableau WHERE inscription_id = 42")
        ).scalar_one()
    assert total == 2
    engine.dispose()


def test_la_descente_ne_garde_que_le_tour_1_et_n_echoue_pas(tmp_path: Path) -> None:
    """La docstring de la migration assume la perte : la clé de destination ne peut pas distinguer
    deux poses du même archer. Ce qu'on épingle, c'est que la descente **aboutisse** — une
    migration qui plante au `downgrade` bloque un retour arrière le jour J."""
    engine, cfg = _base(tmp_path, "descente.db")
    command.upgrade(cfg, _PAR_TOUR)
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO placement_tableau (phase_id, tour, inscription_id, cible_index, "
                "position) VALUES (7, 2, 42, 1, 'A')"
            )
        )

    command.downgrade(cfg, _AVANT)

    with engine.begin() as conn:
        lignes = conn.execute(
            sa.text(
                "SELECT phase_id, inscription_id, cible_index, position "
                "FROM placement_tableau ORDER BY inscription_id"
            )
        ).all()
    assert [tuple(ligne) for ligne in lignes] == [(7, 42, 3, "B"), (7, 43, 3, "C")]
    engine.dispose()
