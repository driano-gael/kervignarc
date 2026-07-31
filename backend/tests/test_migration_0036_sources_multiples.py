"""Migration 0036 — `config.source` (unique) → `config.sources` (liste), sur **deux** tables.

La suite d'API migre toujours une base **vide** jusqu'à `head` : la réécriture des lignes existantes
n'est exercée par aucun autre test. On pose donc des `phase` et des `format_tournoi` à l'ancienne
forme sur la révision `0035`, on applique `0036`, et on vérifie les deux tables — la seconde étant
précisément celle qu'E01US023 avait ajoutée et qu'il aurait été facile d'oublier (c'est l'écueil
que la story signalait).

Test **de non-régression** au sens de la règle 9 : l'oracle est le comportement attendu de la
migration, décrit dans sa docstring, et l'auteur de la migration est le mieux placé pour l'écrire.

Les clés étrangères sont désactivées côté Alembic (`env.py`) : on insère un `tournoi_id` fictif sans
matérialiser le tournoi parent — même geste que les tests de migration 0018/0020/0032.
"""

from __future__ import annotations

import json
from pathlib import Path

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

_BACKEND_ROOT = Path(__file__).resolve().parents[1]

_ANCIENNE_SOURCE = {"ordre_source": 1, "rang_debut": 1, "rang_fin": 16}
_NOUVELLE_SOURCE = {
    "nature": "rangs",
    "ordre_source": 1,
    "rang_debut": 1,
    "rang_fin": 16,
}


def _config(url: str) -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _inserer_phase(conn: sa.Connection, identifiant: int, config: dict[str, object]) -> None:
    conn.execute(
        sa.text(
            "INSERT INTO phase (id, tournoi_id, ordre, type, config, statut) "
            "VALUES (:id, 1, :ordre, 'placement', :config, 'a_venir')"
        ),
        {"id": identifiant, "ordre": identifiant, "config": json.dumps(config)},
    )


def _inserer_format(conn: sa.Connection, identifiant: int, etapes: list[dict[str, object]]) -> None:
    conn.execute(
        sa.text(
            "INSERT INTO format_tournoi (id, nom, origine, config) "
            "VALUES (:id, :nom, 'utilisateur', :config)"
        ),
        {
            "id": identifiant,
            "nom": f"format {identifiant}",
            "config": json.dumps({"etapes": etapes}),
        },
    )


def _configs_phases(engine: sa.Engine) -> dict[int, dict[str, object]]:
    with engine.connect() as conn:
        lignes = conn.execute(sa.text("SELECT id, config FROM phase")).all()
    return {int(ligne[0]): json.loads(ligne[1]) for ligne in lignes}


def _configs_formats(engine: sa.Engine) -> dict[int, dict[str, object]]:
    with engine.connect() as conn:
        lignes = conn.execute(sa.text("SELECT id, config FROM format_tournoi")).all()
    return {int(ligne[0]): json.loads(ligne[1]) for ligne in lignes}


def test_upgrade_convertit_la_source_unique_des_phases(tmp_path: Path) -> None:
    """Une `config.source` devient une liste d'un élément, de nature « rangs »."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, "0035_format_tournoi")

    engine = sa.create_engine(url)
    try:
        with engine.begin() as conn:
            _inserer_phase(conn, 1, {"source": dict(_ANCIENNE_SOURCE), "effectif": 16})
            _inserer_phase(
                conn, 2, {"effectif": 32}
            )  # sans source : alimentée par les inscriptions
            _inserer_phase(conn, 3, {"sources": [dict(_NOUVELLE_SOURCE)]})  # déjà migrée

        command.upgrade(cfg, "0036_sources_multiples")

        configs = _configs_phases(engine)
        assert configs[1]["sources"] == [_NOUVELLE_SOURCE]
        assert "source" not in configs[1]
        assert configs[1]["effectif"] == 16  # le reste de la config est préservé
        assert "sources" not in configs[2] and "source" not in configs[2]
        assert configs[3]["sources"] == [_NOUVELLE_SOURCE]  # idempotence
    finally:
        engine.dispose()


def test_upgrade_convertit_aussi_les_etapes_des_formats(tmp_path: Path) -> None:
    """La **seconde** table : les étapes d'un format de bibliothèque migrent également.

    C'est l'écueil de cette migration — un format resté en forme ancienne produirait, à
    l'application, des phases que le code d'aujourd'hui relit encore mais que plus rien n'écrit.
    """
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, "0035_format_tournoi")

    engine = sa.create_engine(url)
    try:
        with engine.begin() as conn:
            _inserer_format(
                conn,
                1,
                [
                    {"ordre": 1, "type": "qualification", "effectif": 64},
                    {"ordre": 2, "type": "placement", "source": dict(_ANCIENNE_SOURCE)},
                ],
            )

        command.upgrade(cfg, "0036_sources_multiples")

        etapes = _configs_formats(engine)[1]["etapes"]
        assert isinstance(etapes, list)
        assert etapes[1]["sources"] == [_NOUVELLE_SOURCE]
        assert "source" not in etapes[1]
        assert etapes[0]["type"] == "qualification"  # étape sans source : intacte
    finally:
        engine.dispose()


def test_downgrade_retablit_le_cas_representable_et_laisse_les_autres(tmp_path: Path) -> None:
    """Le retour arrière est **partiel et assumé** : seule une source « par rangs » bornée y passe.

    Une phase à deux sources, ou à fin ouverte, n'a pas d'ancienne forme : la migration la laisse
    telle quelle plutôt que d'en perdre une moitié en silence.
    """
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, "0036_sources_multiples")

    engine = sa.create_engine(url)
    try:
        deux_sources = [
            dict(_NOUVELLE_SOURCE),
            {"nature": "reste", "ordre_source": 1},
        ]
        fin_ouverte = [{"nature": "rangs", "ordre_source": 1, "rang_debut": 33, "rang_fin": None}]
        with engine.begin() as conn:
            _inserer_phase(conn, 1, {"sources": [dict(_NOUVELLE_SOURCE)]})
            _inserer_phase(conn, 2, {"sources": deux_sources})
            _inserer_phase(conn, 3, {"sources": fin_ouverte})

        command.downgrade(cfg, "0035_format_tournoi")

        configs = _configs_phases(engine)
        assert configs[1]["source"] == _ANCIENNE_SOURCE
        assert "sources" not in configs[1]
        assert configs[2]["sources"] == deux_sources  # inexprimable : conservée en l'état
        assert configs[3]["sources"] == fin_ouverte
    finally:
        engine.dispose()
