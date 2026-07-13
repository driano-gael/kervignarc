"""Test bout-en-bout de l'API catégories (E01US003).

Traverse toutes les couches — DTO Pydantic → file d'écriture → service → repository → DB,
puis relecture/listing — et vérifie le **mapping des erreurs typées** à la frontière :
- création (avec attributs) puis listing d'une catégorie ;
- édition (PUT) et suppression (204) ;
- catégorie/tournoi introuvable → 404 ; libellé vide → 422 ; corps invalide → 400.
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
def app_categories(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _creer_tournoi(client: TestClient) -> int:
    """Crée un tournoi et renvoie son identifiant (client déjà authentifié admin)."""
    reponse = client.post("/api/v1/tournois", json={"nom": "Trophée", "date": "2026-03-14"})
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def test_creer_puis_lister_une_categorie(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """POST crée la catégorie (via la file) ; GET la liste avec ses attributs."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        creation = client.post(
            f"/api/v1/tournois/{tournoi_id}/categories",
            json={
                "libelle": "Senior H Classique",
                "arme": "classique",
                "tranche_age": "senior",
                "sexe": "H",
            },
        )
        assert creation.status_code == 201
        cree = creation.json()
        assert cree["libelle"] == "Senior H Classique"
        assert cree["arme"] == "classique"
        assert cree["sexe"] == "H"
        assert cree["tournoi_id"] == tournoi_id
        assert isinstance(cree["id"], int)

        liste = client.get(f"/api/v1/tournois/{tournoi_id}/categories")
        assert liste.status_code == 200
        assert liste.json() == [cree]


def test_creer_defauts_attributs_facultatifs(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Sans arme/âge/sexe : champs à None."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        cree = client.post(
            f"/api/v1/tournois/{tournoi_id}/categories", json={"libelle": "Libre"}
        ).json()
    assert cree["arme"] is None
    assert cree["tranche_age"] is None
    assert cree["sexe"] is None


def test_lister_categories_d_un_tournoi(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """GET liste les catégories du tournoi, dans l'ordre de création."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        assert client.get(f"/api/v1/tournois/{tournoi_id}/categories").json() == []
        client.post(f"/api/v1/tournois/{tournoi_id}/categories", json={"libelle": "A"})
        client.post(f"/api/v1/tournois/{tournoi_id}/categories", json={"libelle": "B"})
        libelles = [
            c["libelle"] for c in client.get(f"/api/v1/tournois/{tournoi_id}/categories").json()
        ]
    assert libelles == ["A", "B"]


def test_modifier_une_categorie(app_categories: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """PUT édite les attributs ; la relecture reflète la modification."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        cree = client.post(
            f"/api/v1/tournois/{tournoi_id}/categories", json={"libelle": "Ancien"}
        ).json()
        modif = client.put(
            f"/api/v1/categories/{cree['id']}",
            json={"libelle": "Nouveau", "arme": "poulie", "tranche_age": "vétéran", "sexe": "F"},
        )
        assert modif.status_code == 200
        corps = modif.json()
        assert corps["libelle"] == "Nouveau"
        assert corps["arme"] == "poulie"
        assert corps["sexe"] == "F"
        assert client.get(f"/api/v1/tournois/{tournoi_id}/categories").json() == [corps]


def test_supprimer_une_categorie(app_categories: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """DELETE → 204 ; la catégorie disparaît de la liste du tournoi."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        cree = client.post(
            f"/api/v1/tournois/{tournoi_id}/categories", json={"libelle": "Libre"}
        ).json()
        assert client.delete(f"/api/v1/categories/{cree['id']}").status_code == 204
        assert client.get(f"/api/v1/tournois/{tournoi_id}/categories").json() == []


def test_creer_dans_tournoi_introuvable(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Créer une catégorie dans un tournoi inconnu → 404 typé."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        reponse = client.post("/api/v1/tournois/999/categories", json={"libelle": "X"})
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"


def test_modifier_categorie_introuvable(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """PUT sur une catégorie inconnue → 404 typé."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        reponse = client.put("/api/v1/categories/999", json={"libelle": "X"})
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "categorie_introuvable"


def test_creer_libelle_vide_erreur_domaine(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un libellé vide → 422 avec le code métier (règle du domaine)."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.post(f"/api/v1/tournois/{tournoi_id}/categories", json={"libelle": "   "})
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "libelle_categorie_invalide"


def test_creer_requete_invalide_erreur_400(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un corps invalide (sexe hors énumération) → 400 avec le détail."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/categories",
            json={"libelle": "X", "sexe": "autre"},
        )
    assert reponse.status_code == 400
    corps = reponse.json()
    assert corps["code"] == "requete_invalide"
    assert "details" in corps
