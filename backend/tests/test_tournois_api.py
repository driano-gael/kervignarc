"""Test bout-en-bout de l'API tournois (E00US009, E01US001).

Traverse toutes les couches — DTO Pydantic → file d'écriture → service → repository → DB,
puis relecture/listing — et vérifie le **mapping des erreurs typées** à la frontière :
- création (avec métadonnées) puis relecture d'un tournoi (aller-retour complet) ;
- listing des tournois créés ;
- tournoi introuvable → 404 (`ApplicationError`) ;
- nom vide → 422 (`DomainError`, code métier) ;
- champ obligatoire manquant (date) → 400 (validation d'entrée).
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
def app_tournois(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def test_creer_puis_consulter_un_tournoi(
    app_tournois: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """POST crée le tournoi (via la file d'écriture) ; GET le relit à l'identique."""
    with TestClient(app_tournois) as client:
        connecter_admin(client)
        creation = client.post(
            "/api/v1/tournois",
            json={
                "nom": "Salle 18m",
                "date": "2026-03-14",
                "lieu": "Quimper",
                "type_tournoi": "officiel",
            },
        )
        assert creation.status_code == 201
        cree = creation.json()
        assert cree["nom"] == "Salle 18m"
        assert cree["date"] == "2026-03-14"
        assert cree["lieu"] == "Quimper"
        assert cree["type_tournoi"] == "officiel"
        assert isinstance(cree["id"], int)

        relecture = client.get(f"/api/v1/tournois/{cree['id']}")
        assert relecture.status_code == 200
        assert relecture.json() == cree


def test_creer_defauts_lieu_et_type(app_tournois: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Sans lieu ni type : lieu à None, type non officiel par défaut."""
    with TestClient(app_tournois) as client:
        connecter_admin(client)
        cree = client.post("/api/v1/tournois", json={"nom": "Trophée", "date": "2026-03-14"}).json()
    assert cree["lieu"] is None
    assert cree["type_tournoi"] == "non_officiel"


def test_lister_les_tournois(app_tournois: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """GET liste les tournois créés (le plus récent en premier)."""
    with TestClient(app_tournois) as client:
        connecter_admin(client)
        assert client.get("/api/v1/tournois").json() == []
        client.post("/api/v1/tournois", json={"nom": "Ancien", "date": "2026-03-14"})
        client.post("/api/v1/tournois", json={"nom": "Récent", "date": "2026-03-15"})
        noms = [t["nom"] for t in client.get("/api/v1/tournois").json()]
    assert noms == ["Récent", "Ancien"]


def test_consulter_tournoi_introuvable(app_tournois: FastAPI) -> None:
    """Un identifiant inconnu → 404 avec le code applicatif typé."""
    with TestClient(app_tournois) as client:
        reponse = client.get("/api/v1/tournois/999")
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"


def test_creer_nom_vide_erreur_domaine(
    app_tournois: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un nom vide → 422 avec le code métier (règle du domaine)."""
    with TestClient(app_tournois) as client:
        connecter_admin(client)
        reponse = client.post("/api/v1/tournois", json={"nom": "   ", "date": "2026-03-14"})
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "nom_tournoi_invalide"


def test_creer_requete_invalide_erreur_400(
    app_tournois: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un corps invalide (champ `date` obligatoire manquant) → 400 avec le détail."""
    with TestClient(app_tournois) as client:
        connecter_admin(client)
        reponse = client.post("/api/v1/tournois", json={"nom": "Trophée"})
    assert reponse.status_code == 400
    corps = reponse.json()
    assert corps["code"] == "requete_invalide"
    assert "details" in corps
