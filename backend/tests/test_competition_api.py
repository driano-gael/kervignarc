"""Test bout-en-bout de la tranche verticale (E00US011).

Déroule le fil rouge du walking skeleton à travers toutes les couches — créer un tournoi →
inscrire un archer → le placer sur une cible → saisir des scores → consulter le classement —
et vérifie qu'**après chaque écriture, un événement est diffusé en direct** aux abonnés
WebSocket (mécanisme de mise à jour temps réel de l'écran de classement). Contrôle aussi le
mapping des erreurs typées à la frontière (ADR-0007).
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
def app_competition(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def test_tranche_verticale_bout_en_bout(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Tournoi → archer → placement → scores → classement, avec diffusion temps réel."""
    with TestClient(app_competition) as client, client.websocket_connect("/ws") as ws:
        assert ws.receive_json()["type"] == "connected"
        connecter_admin(client)  # accès admin requis pour créer le tournoi (E10US002)

        tournoi = client.post(
            "/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14"}
        ).json()
        assert ws.receive_json()["type"] == "donnees_modifiees"

        alice = client.post(f"/api/v1/tournois/{tournoi['id']}/archers", json={"nom": "Alice"})
        assert alice.status_code == 201
        alice_id = alice.json()["id"]
        assert alice.json()["cible"] is None
        assert ws.receive_json()["type"] == "donnees_modifiees"

        bob_id = client.post(
            f"/api/v1/tournois/{tournoi['id']}/archers", json={"nom": "Bob"}
        ).json()["id"]
        assert ws.receive_json()["type"] == "donnees_modifiees"

        place = client.post(f"/api/v1/archers/{alice_id}/placement", json={"cible": 3})
        assert place.status_code == 200
        assert place.json()["cible"] == 3
        assert ws.receive_json()["type"] == "donnees_modifiees"

        # Scores : Alice 10 + 9 = 19, Bob 8 → Alice devant.
        for archer_id, points in [(alice_id, 10), (alice_id, 9), (bob_id, 8)]:
            reponse = client.post(f"/api/v1/archers/{archer_id}/scores", json={"points": points})
            assert reponse.status_code == 201
            assert ws.receive_json()["type"] == "donnees_modifiees"

        classement = client.get(f"/api/v1/tournois/{tournoi['id']}/classement")
        assert classement.status_code == 200
        corps = classement.json()
        assert corps["tournoi_id"] == tournoi["id"]
        assert [
            (ligne["nom"], ligne["rang"], ligne["total"], ligne["cible"])
            for ligne in corps["lignes"]
        ] == [
            ("Alice", 1, 19, 3),
            ("Bob", 2, 8, None),
        ]


def test_ajouter_archer_tournoi_inconnu_404(app_competition: FastAPI) -> None:
    """Inscrire dans un tournoi inexistant → 404 avec le code applicatif typé."""
    with TestClient(app_competition) as client:
        reponse = client.post("/api/v1/tournois/999/archers", json={"nom": "Robin"})
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"


def test_placer_archer_inconnu_404(app_competition: FastAPI) -> None:
    """Placer un archer inexistant → 404 avec le code applicatif typé."""
    with TestClient(app_competition) as client:
        reponse = client.post("/api/v1/archers/999/placement", json={"cible": 1})
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "archer_introuvable"


def test_score_hors_plage_422(app_competition: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Un score hors de 0-10 → 422 avec le code métier (règle du domaine)."""
    with TestClient(app_competition) as client:
        connecter_admin(client)
        tournoi = client.post(
            "/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14"}
        ).json()
        archer = client.post(
            f"/api/v1/tournois/{tournoi['id']}/archers", json={"nom": "Robin"}
        ).json()
        reponse = client.post(f"/api/v1/archers/{archer['id']}/scores", json={"points": 11})
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "score_invalide"


def test_classement_tournoi_inconnu_404(app_competition: FastAPI) -> None:
    """Consulter le classement d'un tournoi inexistant → 404."""
    with TestClient(app_competition) as client:
        reponse = client.get("/api/v1/tournois/999/classement")
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"
