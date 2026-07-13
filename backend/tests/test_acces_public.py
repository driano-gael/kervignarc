"""Contrat d'accès public en lecture seule (E10US001).

Garantit, à la frontière API, les deux moitiés du critère « consultation publique ouverte » :
- **toutes les lectures** (`GET`) répondent **sans authentification** (jamais 401) ;
- **toute écriture** (`POST`/`PUT`/`PATCH`/`DELETE`) exige une session : **401 sans jeton**.

Le garde-fou d'écriture est **dynamique** : il énumère les routes réellement montées sur l'app et
vérifie que chacune (hors amorçage d'accès explicitement public) refuse une requête sans jeton.
Ajouter demain un endpoint d'écriture non protégé fera donc **échouer ce test** — ce que sa version
statique n'aurait pas détecté. Les rôles archer/scoreur (E10US007/E10US003) élargiront plus tard
l'autorisation des écritures au-delà de l'admin, sans jamais les rouvrir au public.
"""

from __future__ import annotations

import re
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

_METHODES_ECRITURE = {"POST", "PUT", "PATCH", "DELETE"}

# Écritures **délibérément publiques** : amorçage de l'accès admin (définition au 1ᵉʳ usage) et
# connexion (login). Elles n'exigent pas de jeton *par nature* ; toute autre écriture doit 401.
_ECRITURES_PUBLIQUES = {"/api/v1/auth/configurer", "/api/v1/auth/connexion"}

# Endpoints de LECTURE — doivent répondre sans authentification (jamais 401).
_LECTURES = [
    "/health",
    "/api/v1/auth/etat",
    "/api/v1/tournois",
    "/api/v1/tournois/1",
    "/api/v1/tournois/1/classement",
    "/api/v1/tournois/1/categories",
]


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


def _routes_ecriture_protegees(app: FastAPI) -> list[tuple[str, str]]:
    """(méthode, chemin concret) de toute écriture censée exiger une session.

    Source = **schéma OpenAPI** de l'app (contrat public, stable entre versions de FastAPI) :
    il énumère tous les endpoints REST montés, chemin templaté inclus. On y retranche les
    écritures publiques d'amorçage. `{param}` est remplacé par `1` pour concrétiser l'URL.
    """
    routes: list[tuple[str, str]] = []
    for chemin, operations in app.openapi()["paths"].items():
        if chemin in _ECRITURES_PUBLIQUES:
            continue
        chemin_concret = re.sub(r"\{[^}]+\}", "1", chemin)
        for methode in operations:
            if methode.upper() in _METHODES_ECRITURE:
                routes.append((methode.upper(), chemin_concret))
    return routes


@pytest.mark.parametrize("chemin", _LECTURES)
def test_lectures_publiques_sans_auth(app_acces: FastAPI, chemin: str) -> None:
    """Chaque lecture répond sans jeton (200 si présent, 404 si absent — jamais 401)."""
    with TestClient(app_acces) as client:
        reponse = client.get(chemin)
    assert reponse.status_code != 401, f"{chemin} exige une auth alors que c'est une lecture"
    assert reponse.status_code in (200, 404)


def test_toutes_les_ecritures_exigent_une_session(app_acces: FastAPI) -> None:
    """AUCUNE écriture (hors amorçage public) n'est accessible sans session — vérif dynamique."""
    routes = _routes_ecriture_protegees(app_acces)
    assert routes, "Aucune route d'écriture détectée : l'énumération est cassée."
    with TestClient(app_acces) as client:
        # Accès admin configuré (mais pas authentifié) : l'écriture doit rester refusée.
        client.post("/api/v1/auth/configurer", json={"login": "admin", "mot_de_passe": "secret"})
        non_protegees = [
            (methode, chemin, client.request(methode, chemin, json={}).status_code)
            for methode, chemin in routes
        ]
    fautives = [r for r in non_protegees if r[2] != 401]
    assert fautives == [], f"Écritures accessibles sans session : {fautives}"


def test_ecritures_publiques_amorcage_accessibles_sans_jeton(app_acces: FastAPI) -> None:
    """Amorçage explicitement public : `configurer` (1ᵉʳ accès) puis `connexion` sans jeton."""
    identifiants = {"login": "admin", "mot_de_passe": "secret"}
    with TestClient(app_acces) as client:
        assert client.post("/api/v1/auth/configurer", json=identifiants).status_code == 201
        assert client.post("/api/v1/auth/connexion", json=identifiants).status_code == 200


def test_ecriture_jeton_invalide_401(app_acces: FastAPI) -> None:
    """Un jeton bidon ne vaut pas une session : écriture refusée (401)."""
    with TestClient(app_acces) as client:
        reponse = client.post(
            "/api/v1/tournois",
            json={"nom": "T", "date": "2026-03-14"},
            headers={"Authorization": "Bearer faux"},
        )
    assert reponse.status_code == 401
    assert reponse.json()["code"] == "non_authentifie"


def test_ecriture_corps_invalide_sans_jeton_reste_401(app_acces: FastAPI) -> None:
    """Sans jeton, un corps invalide donne 401 (auth), pas 422 : l'auth précède la validation."""
    with TestClient(app_acces) as client:
        reponse = client.post("/api/v1/tournois", json={"nom": ""})  # date manquante
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
