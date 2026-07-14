"""Test bout-en-bout de l'API gabarits de salle (E01US007).

Traverse toutes les couches — DTO Pydantic → file d'écriture → service → repository → DB,
puis relecture/listing — et vérifie le **mapping des erreurs typées** à la frontière :
- création (avec plafond) puis listing d'un gabarit, positions dérivées ;
- plafond par défaut (4) ; édition (PUT) et suppression (204) ;
- gabarit introuvable → 404 ; plafond/nombre de cibles invalide → 422 ; corps invalide → 400 ;
- action admin refusée sans session → 401.
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
def app_gabarits(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def test_creer_puis_lister_un_gabarit(
    app_gabarits: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """POST crée le gabarit (via la file) ; GET le liste avec ses cibles et positions."""
    with TestClient(app_gabarits) as client:
        connecter_admin(client)
        creation = client.post(
            "/api/v1/gabarits", json={"nom": "Salle A", "nb_cibles": 2, "capacite": 2}
        )
        assert creation.status_code == 201, creation.text
        cree = creation.json()
        assert cree["nom"] == "Salle A"
        assert cree["nb_cibles"] == 2
        assert isinstance(cree["id"], int)
        assert cree["cibles"] == [
            {"index": 1, "capacite": 2, "positions": ["A", "B"]},
            {"index": 2, "capacite": 2, "positions": ["A", "B"]},
        ]

        liste = client.get("/api/v1/gabarits")
        assert liste.status_code == 200
        assert liste.json() == [cree]


def test_plafond_par_defaut_est_quatre(
    app_gabarits: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Sans plafond fourni, les cibles sont à 4 (positions A/B/C/D)."""
    with TestClient(app_gabarits) as client:
        connecter_admin(client)
        cree = client.post("/api/v1/gabarits", json={"nom": "Salle", "nb_cibles": 1}).json()
    assert cree["cibles"][0]["capacite"] == 4
    assert cree["cibles"][0]["positions"] == ["A", "B", "C", "D"]


def test_lister_est_public(app_gabarits: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """La liste des gabarits est lisible sans session (lecture publique)."""
    with TestClient(app_gabarits) as client:
        connecter_admin(client)
        client.post("/api/v1/gabarits", json={"nom": "Salle", "nb_cibles": 1})
    with TestClient(app_gabarits) as anonyme:
        reponse = anonyme.get("/api/v1/gabarits")
    assert reponse.status_code == 200
    assert [g["nom"] for g in reponse.json()] == ["Salle"]


def test_modifier_un_gabarit(app_gabarits: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """PUT édite nom/nb cibles/plafond ; la relecture reflète la modification."""
    with TestClient(app_gabarits) as client:
        connecter_admin(client)
        cree = client.post(
            "/api/v1/gabarits", json={"nom": "Ancien", "nb_cibles": 2, "capacite": 4}
        ).json()
        modif = client.put(
            f"/api/v1/gabarits/{cree['id']}",
            json={"nom": "Nouveau", "nb_cibles": 3, "capacite": 1},
        )
        assert modif.status_code == 200
        corps = modif.json()
        assert corps["nom"] == "Nouveau"
        assert corps["nb_cibles"] == 3
        assert all(c["capacite"] == 1 and c["positions"] == ["A"] for c in corps["cibles"])
        assert client.get("/api/v1/gabarits").json() == [corps]


def test_supprimer_un_gabarit(app_gabarits: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """DELETE → 204 ; le gabarit disparaît de la liste."""
    with TestClient(app_gabarits) as client:
        connecter_admin(client)
        cree = client.post("/api/v1/gabarits", json={"nom": "Salle", "nb_cibles": 1}).json()
        assert client.delete(f"/api/v1/gabarits/{cree['id']}").status_code == 204
        assert client.get("/api/v1/gabarits").json() == []


def test_creer_sans_jeton_401(app_gabarits: FastAPI) -> None:
    """La création est une action admin : refusée sans session (401)."""
    with TestClient(app_gabarits) as client:
        reponse = client.post("/api/v1/gabarits", json={"nom": "Salle", "nb_cibles": 1})
    assert reponse.status_code == 401
    assert reponse.json()["code"] == "non_authentifie"


def test_modifier_gabarit_introuvable(
    app_gabarits: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """PUT sur un gabarit inconnu → 404 typé."""
    with TestClient(app_gabarits) as client:
        connecter_admin(client)
        reponse = client.put("/api/v1/gabarits/999", json={"nom": "X", "nb_cibles": 1})
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "gabarit_introuvable"


def test_creer_plafond_invalide_erreur_domaine(
    app_gabarits: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un plafond hors de [1, 4] → 422 avec le code métier (règle du domaine)."""
    with TestClient(app_gabarits) as client:
        connecter_admin(client)
        reponse = client.post(
            "/api/v1/gabarits", json={"nom": "Salle", "nb_cibles": 2, "capacite": 5}
        )
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "capacite_cible_invalide"


def test_creer_nombre_cibles_invalide_erreur_domaine(
    app_gabarits: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un nombre de cibles nul → 422 avec le code métier (règle du domaine)."""
    with TestClient(app_gabarits) as client:
        connecter_admin(client)
        reponse = client.post("/api/v1/gabarits", json={"nom": "Salle", "nb_cibles": 0})
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "nombre_cibles_invalide"


def test_creer_requete_invalide_erreur_400(
    app_gabarits: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un corps invalide (nb_cibles non entier) → 400 avec le détail."""
    with TestClient(app_gabarits) as client:
        connecter_admin(client)
        reponse = client.post("/api/v1/gabarits", json={"nom": "Salle", "nb_cibles": "beaucoup"})
    assert reponse.status_code == 400
    corps = reponse.json()
    assert corps["code"] == "requete_invalide"
    assert "details" in corps
