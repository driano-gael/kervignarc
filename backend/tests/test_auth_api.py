"""Test bout-en-bout de l'API d'accès admin (E10US002).

Vérifie le parcours et le mapping d'erreurs à la frontière :
- état initial « non configuré » → définition (201) → état « configuré » ;
- redéfinition refusée (409) ; connexion mauvais identifiants (401) puis bons (200) ;
- la **route protégée** (création de tournoi) : refusée sans/mauvais jeton (401), autorisée avec ;
- déconnexion (204) invalide le jeton pour la route protégée.
La **lecture** (listing des tournois) reste publique, sans jeton.
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
def app_auth(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable et un `.env` d'identifiants jetable."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


_TOURNOI = {"nom": "Salle 18m", "date": "2026-03-14"}
_IDENTIFIANTS = {"login": "admin", "mot_de_passe": "secret-123"}


def test_etat_puis_configuration(app_auth: FastAPI) -> None:
    """Non configuré au départ ; après définition, l'état passe à « configuré »."""
    with TestClient(app_auth) as client:
        assert client.get("/api/v1/auth/etat").json() == {"configure": False}
        reponse = client.post("/api/v1/auth/configurer", json=_IDENTIFIANTS)
        assert reponse.status_code == 201
        assert isinstance(reponse.json()["jeton"], str)
        assert client.get("/api/v1/auth/etat").json() == {"configure": True}


def test_configurer_deux_fois_conflit(app_auth: FastAPI) -> None:
    """Redéfinir un accès déjà configuré → 409 avec le code typé."""
    with TestClient(app_auth) as client:
        client.post("/api/v1/auth/configurer", json=_IDENTIFIANTS)
        reponse = client.post("/api/v1/auth/configurer", json=_IDENTIFIANTS)
    assert reponse.status_code == 409
    assert reponse.json()["code"] == "acces_deja_configure"


def test_connexion_mauvais_identifiants_401(app_auth: FastAPI) -> None:
    """De mauvais identifiants → 401 avec le code typé."""
    with TestClient(app_auth) as client:
        client.post("/api/v1/auth/configurer", json=_IDENTIFIANTS)
        reponse = client.post(
            "/api/v1/auth/connexion", json={"login": "admin", "mot_de_passe": "faux"}
        )
    assert reponse.status_code == 401
    assert reponse.json()["code"] == "identifiants_invalides"


def test_connexion_bons_identifiants_200(app_auth: FastAPI) -> None:
    """Les bons identifiants renvoient un jeton (200)."""
    with TestClient(app_auth) as client:
        client.post("/api/v1/auth/configurer", json=_IDENTIFIANTS)
        reponse = client.post("/api/v1/auth/connexion", json=_IDENTIFIANTS)
    assert reponse.status_code == 200
    assert isinstance(reponse.json()["jeton"], str)


def test_creer_tournoi_sans_jeton_401(app_auth: FastAPI) -> None:
    """Créer un tournoi sans authentification → 401 (route admin protégée)."""
    with TestClient(app_auth) as client:
        client.post("/api/v1/auth/configurer", json=_IDENTIFIANTS)
        reponse = client.post("/api/v1/tournois", json=_TOURNOI)
    assert reponse.status_code == 401
    assert reponse.json()["code"] == "non_authentifie"


def test_creer_tournoi_jeton_invalide_401(app_auth: FastAPI) -> None:
    """Un jeton bidon est refusé sur la route admin (401)."""
    with TestClient(app_auth) as client:
        client.post("/api/v1/auth/configurer", json=_IDENTIFIANTS)
        reponse = client.post(
            "/api/v1/tournois", json=_TOURNOI, headers={"Authorization": "Bearer faux"}
        )
    assert reponse.status_code == 401


def test_creer_tournoi_avec_jeton_201(app_auth: FastAPI) -> None:
    """Avec un jeton valide, la création de tournoi est autorisée (201)."""
    with TestClient(app_auth) as client:
        jeton = client.post("/api/v1/auth/configurer", json=_IDENTIFIANTS).json()["jeton"]
        reponse = client.post(
            "/api/v1/tournois", json=_TOURNOI, headers={"Authorization": f"Bearer {jeton}"}
        )
    assert reponse.status_code == 201


def test_lecture_tournois_reste_publique(app_auth: FastAPI) -> None:
    """Le listing des tournois est accessible sans jeton (lecture publique, E10US001)."""
    with TestClient(app_auth) as client:
        client.post("/api/v1/auth/configurer", json=_IDENTIFIANTS)
        reponse = client.get("/api/v1/tournois")
    assert reponse.status_code == 200


def test_deconnexion_invalide_le_jeton(app_auth: FastAPI) -> None:
    """Après déconnexion (204), le jeton ne permet plus la création de tournoi (401)."""
    with TestClient(app_auth) as client:
        jeton = client.post("/api/v1/auth/configurer", json=_IDENTIFIANTS).json()["jeton"]
        entete = {"Authorization": f"Bearer {jeton}"}
        assert client.post("/api/v1/auth/deconnexion", headers=entete).status_code == 204
        refus = client.post("/api/v1/tournois", json=_TOURNOI, headers=entete)
    assert refus.status_code == 401
