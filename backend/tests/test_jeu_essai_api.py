"""Test bout-en-bout de l'API jeu d'essai (E15US001).

Traverse toutes les couches — DTO → file d'écriture → service (qui compose les autres services) →
repositories → DB — et vérifie le mapping des erreurs & la protection admin :
- le catalogue de scénarios se liste ;
- peupler crée bien N archers **réels** (relus par l'API des archers) ;
- un scénario instancie un tournoi **complet** qui peut ensuite passer `prêt` (prêt à lancer) ;
- scénario inconnu → 404 ; accès non authentifié → 401 ; `nombre` hors bornes → 400.

Tests **après** implémentation : c'est du câblage (API/composition), pas une règle métier — l'oracle
du comportement est déjà couvert côté service, depuis le CA (`test_service_jeu_essai`).
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
def app_jeu_essai(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _creer_tournoi(client: TestClient) -> int:
    reponse = client.post("/api/v1/tournois", json={"nom": "Trophée", "date": "2026-03-14"})
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def test_lister_scenarios(app_jeu_essai: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_jeu_essai) as client:
        connecter_admin(client)
        reponse = client.get("/api/v1/jeu-essai/scenarios")
        assert reponse.status_code == 200, reponse.text
        catalogue = reponse.json()
        assert {s["id"] for s in catalogue} == {"petit", "gros", "multi-format"}
        for scenario in catalogue:
            assert scenario["libelle"] and scenario["description"]
            assert scenario["nombre_archers"] >= 1


def test_peupler_cree_des_archers_reels(
    app_jeu_essai: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """POST peupler crée N archers relus par l'API des archers (donnée réelle persistée)."""
    with TestClient(app_jeu_essai) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/jeu-essai/peupler", json={"nombre": 12}
        )
        assert reponse.status_code == 201, reponse.text
        assert reponse.json()["nombre_archers_crees"] == 12

        archers = client.get(f"/api/v1/tournois/{tournoi_id}/archers")
        assert archers.status_code == 200, archers.text
        assert len(archers.json()) == 12


def test_peupler_tournoi_inconnu_404(
    app_jeu_essai: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_jeu_essai) as client:
        connecter_admin(client)
        reponse = client.post("/api/v1/tournois/9999/jeu-essai/peupler", json={"nombre": 5})
        assert reponse.status_code == 404, reponse.text
        assert reponse.json()["code"] == "tournoi_introuvable"


def test_peupler_nombre_hors_bornes_400(
    app_jeu_essai: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_jeu_essai) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/jeu-essai/peupler", json={"nombre": 0}
        )
        assert reponse.status_code == 400, reponse.text


def test_peupler_tournoi_demarre_409(
    app_jeu_essai: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Peupler un tournoi **démarré** est refusé (409) : pas de pollution d'une compétition."""
    with TestClient(app_jeu_essai) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        # brouillon → (départ requis) → prêt → en cours
        depart = client.post(
            f"/api/v1/tournois/{tournoi_id}/departs",
            json={"tarif_centimes": 1000, "horaire": "09:00"},
        )
        assert depart.status_code == 201, depart.text
        assert client.post(f"/api/v1/tournois/{tournoi_id}/vers-pret").status_code == 200
        assert client.post(f"/api/v1/tournois/{tournoi_id}/demarrer").status_code == 200

        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/jeu-essai/peupler", json={"nombre": 5}
        )
        assert reponse.status_code == 409, reponse.text
        assert reponse.json()["code"] == "peuplement_tournoi_demarre"


def test_instancier_scenario_pret_a_lancer(
    app_jeu_essai: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Instancier « petit » crée un tournoi complet, qui peut ensuite passer `prêt`."""
    with TestClient(app_jeu_essai) as client:
        connecter_admin(client)

        reponse = client.post("/api/v1/jeu-essai/scenarios/petit/instancier", json={})
        assert reponse.status_code == 201, reponse.text
        corps = reponse.json()
        assert corps["nombre_archers"] == 16
        assert corps["nombre_departs"] == 1
        tournoi_id = corps["tournoi_id"]

        archers = client.get(f"/api/v1/tournois/{tournoi_id}/archers")
        assert len(archers.json()) == 16

        pret = client.post(f"/api/v1/tournois/{tournoi_id}/vers-pret")
        assert pret.status_code == 200, pret.text
        assert pret.json()["statut"] == "pret"


def test_instancier_scenario_inconnu_404(
    app_jeu_essai: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_jeu_essai) as client:
        connecter_admin(client)
        reponse = client.post("/api/v1/jeu-essai/scenarios/bidon/instancier", json={})
        assert reponse.status_code == 404, reponse.text
        assert reponse.json()["code"] == "scenario_inconnu"


def test_jeu_essai_exige_admin(app_jeu_essai: FastAPI) -> None:
    """Sans session admin, toutes les routes du jeu d'essai renvoient 401."""
    with TestClient(app_jeu_essai) as client:
        assert client.get("/api/v1/jeu-essai/scenarios").status_code == 401
        assert (
            client.post("/api/v1/jeu-essai/scenarios/petit/instancier", json={}).status_code == 401
        )
        assert (
            client.post("/api/v1/tournois/1/jeu-essai/peupler", json={"nombre": 5}).status_code
            == 401
        )
