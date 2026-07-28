"""Non-pollution de la **vraie base** par la simulation éphémère (E15US002, ADR-0054) — intégration.

Le test de service (`test_service_simulation.py`) prouve le rejeu et la non-pollution *au niveau du
mécanisme* (repositories réels inchangés). Ici on va au bout du CA « non-pollution **vérifiable** »
: sur une **vraie base SQLite migrée**, on peuple un tournoi de test (scénario du jeu d'essai), on
**photographie** le contenu (nombre de lignes par table), on lance une **simulation complète**,
et on vérifie que **rien n'a bougé** — aucune ligne ajoutée, retirée ou modifiée. C'est la garantie
que la simulation câblée sur des adapters in-memory n'atteint jamais SQLite.
"""

from __future__ import annotations

import datetime
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy import text

from bootstrap.composition import create_app

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


@pytest.fixture
def app_simulation(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _photo(app: FastAPI) -> dict[str, int]:
    """Nombre de lignes de chaque table applicative (hors métadonnées Alembic)."""
    with app.state.database.engine.connect() as conn:
        tables = [
            nom
            for nom in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'table'")
            ).scalars()
            if not nom.startswith("sqlite_") and not nom.startswith("alembic")
        ]
        return {
            table: int(conn.execute(text(f'SELECT count(*) FROM "{table}"')).scalar_one())
            for table in tables
        }


def test_une_simulation_ne_modifie_pas_la_base(app_simulation: FastAPI) -> None:
    """Peupler un scénario, simuler, et constater la base **strictement inchangée**."""
    resultat = app_simulation.state.service_jeu_essai.instancier("petit", _DATE)
    tournoi_id = resultat.tournoi_id

    avant = _photo(app_simulation)
    assert avant.get("archer", 0) >= 1, "Le scénario a bien peuplé la base (préalable du test)."

    simulation = app_simulation.state.service_simulation.simuler(tournoi_id)
    assert simulation.tournoi_id == tournoi_id
    # Le classement simulé couvre bien les inscrits du scénario (le moteur a tourné).
    assert len(simulation.classement.lignes) == resultat.nombre_archers

    apres = _photo(app_simulation)
    assert apres == avant, "La simulation a écrit dans la vraie base — non-pollution violée."


def test_simuler_un_tournoi_demarre_est_refuse_sans_ecrire(app_simulation: FastAPI) -> None:
    """Le garde-fou tient aussi sur la vraie base : un tournoi démarré est refusé, base intacte."""
    from application.erreurs import SimulationTournoiDemarre

    resultat = app_simulation.state.service_jeu_essai.instancier("petit", _DATE)
    # Passer prêt puis démarrer via le service de cycle de vie (donnée réelle).
    app_simulation.state.service_tournois.vers_pret(resultat.tournoi_id)
    app_simulation.state.service_tournois.demarrer(resultat.tournoi_id)

    avant = _photo(app_simulation)
    with pytest.raises(SimulationTournoiDemarre):
        app_simulation.state.service_simulation.simuler(resultat.tournoi_id)
    assert _photo(app_simulation) == avant
