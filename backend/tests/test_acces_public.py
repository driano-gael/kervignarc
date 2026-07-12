"""Contrat d'accès public en lecture seule (E10US001).

Garantit, à la frontière API, les deux moitiés du critère « consultation publique ouverte » :
- **toutes les lectures** (`GET`) répondent **sans authentification** (jamais 401) ;
- **toutes les écritures** (`POST`) exigent une session : **401 sans jeton**, autorisées avec.

Ce test est le garde-fou de non-régression : ajouter un endpoint d'écriture non protégé le fera
échouer. Les rôles archer/scoreur (E10US007/E10US003) élargiront plus tard l'autorisation des
écritures au-delà de l'admin — sans jamais les rouvrir au public.
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
def app_acces(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


# (méthode, chemin, corps) de chaque endpoint d'ÉCRITURE — doit exiger une session.
_ECRITURES = [
    ("POST", "/api/v1/tournois", {"nom": "T", "date": "2026-03-14"}),
    ("POST", "/api/v1/tournois/1/archers", {"nom": "Robin"}),
    ("POST", "/api/v1/archers/1/placement", {"cible": 1}),
    ("POST", "/api/v1/archers/1/scores", {"points": 5}),
]

# Endpoints de LECTURE — doivent répondre sans authentification (jamais 401).
_LECTURES = [
    "/health",
    "/api/v1/auth/etat",
    "/api/v1/tournois",
    "/api/v1/tournois/1",
    "/api/v1/tournois/1/classement",
]


@pytest.mark.parametrize("chemin", _LECTURES)
def test_lectures_publiques_sans_auth(app_acces: FastAPI, chemin: str) -> None:
    """Chaque lecture répond sans jeton (200 si présent, 404 si absent — jamais 401)."""
    with TestClient(app_acces) as client:
        reponse = client.get(chemin)
    assert reponse.status_code != 401, f"{chemin} exige une auth alors que c'est une lecture"
    assert reponse.status_code in (200, 404)


@pytest.mark.parametrize("methode, chemin, corps", _ECRITURES)
def test_ecritures_refusees_sans_jeton(
    app_acces: FastAPI, methode: str, chemin: str, corps: dict[str, object]
) -> None:
    """Chaque écriture est refusée (401) sans session, même après configuration de l'accès."""
    with TestClient(app_acces) as client:
        # Configure l'accès admin (mais sans s'authentifier) : l'écriture doit rester refusée.
        client.post("/api/v1/auth/configurer", json={"login": "admin", "mot_de_passe": "secret"})
        reponse = client.request(methode, chemin, json=corps)
    assert reponse.status_code == 401
    assert reponse.json()["code"] == "non_authentifie"


def test_ecriture_autorisee_avec_session(
    app_acces: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Avec une session valide, l'écriture n'est plus refusée (création de tournoi → 201)."""
    with TestClient(app_acces) as client:
        connecter_admin(client)
        reponse = client.post("/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14"})
    assert reponse.status_code == 201
