"""Test bout-en-bout de l'API tournois (E00US009).

Traverse toutes les couches — DTO Pydantic → file d'écriture → service → repository → DB,
puis relecture — et vérifie le **mapping des erreurs typées** à la frontière (ADR-0007) :
- création puis relecture d'un tournoi (aller-retour complet) ;
- tournoi introuvable → 404 (`ApplicationError`) ;
- nom vide → 422 (`DomainError`, code métier) ;
- requête invalide (champ manquant) → 400 (validation d'entrée).
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
    app = create_app(url)
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def test_creer_puis_consulter_un_tournoi(app_tournois: FastAPI) -> None:
    """POST crée le tournoi (via la file d'écriture) ; GET le relit à l'identique."""
    with TestClient(app_tournois) as client:
        creation = client.post("/api/v1/tournois", json={"nom": "Salle 18m"})
        assert creation.status_code == 201
        cree = creation.json()
        assert cree["nom"] == "Salle 18m"
        assert isinstance(cree["id"], int)

        relecture = client.get(f"/api/v1/tournois/{cree['id']}")
        assert relecture.status_code == 200
        assert relecture.json() == cree


def test_consulter_tournoi_introuvable(app_tournois: FastAPI) -> None:
    """Un identifiant inconnu → 404 avec le code applicatif typé."""
    with TestClient(app_tournois) as client:
        reponse = client.get("/api/v1/tournois/999")
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"


def test_creer_nom_vide_erreur_domaine(app_tournois: FastAPI) -> None:
    """Un nom vide → 422 avec le code métier (règle du domaine)."""
    with TestClient(app_tournois) as client:
        reponse = client.post("/api/v1/tournois", json={"nom": "   "})
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "nom_tournoi_invalide"


def test_creer_requete_invalide_erreur_400(app_tournois: FastAPI) -> None:
    """Un corps invalide (champ `nom` manquant) → 400 avec le détail des champs."""
    with TestClient(app_tournois) as client:
        reponse = client.post("/api/v1/tournois", json={})
    assert reponse.status_code == 400
    corps = reponse.json()
    assert corps["code"] == "requete_invalide"
    assert "details" in corps
