"""Test bout-en-bout de l'API de complétude du tournoi (E12US005).

Écrit **après** l'implémentation (règle 9 : la frontière n'a pas d'oracle — l'agrégation est prouvée
au service, `test_service_completude.py`). On vérifie ici le structurel de l'endpoint : forme de la
réponse (deux sections séparées, clés stables, phases éliminatoires *à venir*), garde **admin**, et
mapping d'erreur (tournoi inconnu → 404). Un tournoi vide suffit : le contenu chiffré est couvert
ailleurs.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from tests.conftest import ConnecterAdmin

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


@pytest.fixture
def app_session(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _creer_tournoi(client: TestClient, connecter_admin: ConnecterAdmin) -> int:
    connecter_admin(client)
    reponse = client.post("/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14"})
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def test_completude_expose_les_deux_sections_separees(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`D-17` : sportif (qualification, phases, classement) et hors sportif (paiements) séparés."""
    with TestClient(app_session) as client:
        tournoi_id = _creer_tournoi(client, connecter_admin)

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/completude")

        assert reponse.status_code == 200, reponse.text
        corps = reponse.json()
        assert [ligne["cle"] for ligne in corps["sportif"]] == [
            "qualification",
            "phases_eliminatoires",
            "classement",
        ]
        assert [ligne["cle"] for ligne in corps["hors_sportif"]] == ["paiements"]


def test_completude_sequence_les_phases_eliminatoires(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Les duels (EPIC-05 non livré) apparaissent en `a_venir` — séquencés, jamais bloquants."""
    with TestClient(app_session) as client:
        tournoi_id = _creer_tournoi(client, connecter_admin)

        corps = client.get(f"/api/v1/tournois/{tournoi_id}/completude").json()

        phases = next(li for li in corps["sportif"] if li["cle"] == "phases_eliminatoires")
        assert phases["etat"] == "a_venir"


def test_completude_tournoi_vide_signale_le_sportif_incomplet(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un tournoi tout juste créé : rien de placé → sportif incomplet, qualif *en attente*."""
    with TestClient(app_session) as client:
        tournoi_id = _creer_tournoi(client, connecter_admin)

        corps = client.get(f"/api/v1/tournois/{tournoi_id}/completude").json()

        assert corps["sportif_complet"] is False
        qualif = next(li for li in corps["sportif"] if li["cle"] == "qualification")
        assert qualif["etat"] == "en_attente"


def test_completude_exige_l_admin(app_session: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_session) as client:
        tournoi_id = _creer_tournoi(client, connecter_admin)
        client.headers.pop("Authorization", None)

        assert client.get(f"/api/v1/tournois/{tournoi_id}/completude").status_code == 401


def test_completude_tournoi_inconnu_rend_404(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_session) as client:
        connecter_admin(client)
        assert client.get("/api/v1/tournois/9999/completude").status_code == 404
