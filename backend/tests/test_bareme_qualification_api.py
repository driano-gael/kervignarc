"""Test bout-en-bout de l'API barème de qualification (E01US009).

Traverse toutes les couches — DTO Pydantic → file d'écriture → service → repository → DB, puis
relecture — et vérifie le **mapping des erreurs typées** à la frontière :
- absence de barème → `null` ; définition (PUT) puis relecture avec total et score max dérivés ;
- redéfinition (upsert) ; lecture publique ; définition réservée à l'admin (401) ;
- tournoi inconnu → 404 ; valeurs invalides → 422 ; corps invalide → 400.
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
def app_bareme(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _creer_tournoi(client: TestClient) -> int:
    """Crée un tournoi via l'API (admin déjà connecté) et renvoie son identifiant."""
    reponse = client.post("/api/v1/tournois", json={"nom": "Kervignarc", "date": "2026-03-14"})
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def test_definir_puis_relire(app_bareme: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """PUT définit le barème (via la file) ; GET le relit avec total et score max dérivés."""
    with TestClient(app_bareme) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        assert client.get(f"/api/v1/tournois/{tournoi_id}/bareme-qualification").json() is None

        definition = client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 20, "nb_fleches_par_volee": 3},
        )
        assert definition.status_code == 200, definition.text
        assert definition.json() == {
            "nb_volees": 20,
            "nb_fleches_par_volee": 3,
            "nb_fleches_total": 60,
            "score_max": 600,
        }
        assert (
            client.get(f"/api/v1/tournois/{tournoi_id}/bareme-qualification").json()
            == definition.json()
        )


def test_redefinir_remplace_les_valeurs(
    app_bareme: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un second PUT met à jour le barème (upsert, une seule phase qualification)."""
    with TestClient(app_bareme) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 20, "nb_fleches_par_volee": 3},
        )
        maj = client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 10, "nb_fleches_par_volee": 6},
        )
        assert maj.status_code == 200
        corps = maj.json()
        assert corps["nb_volees"] == 10
        assert corps["nb_fleches_total"] == 60
        assert corps["score_max"] == 600


def test_lire_est_public(app_bareme: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Le barème d'un tournoi est lisible sans session (lecture publique)."""
    with TestClient(app_bareme) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 20, "nb_fleches_par_volee": 3},
        )
    with TestClient(app_bareme) as anonyme:
        reponse = anonyme.get(f"/api/v1/tournois/{tournoi_id}/bareme-qualification")
    assert reponse.status_code == 200
    assert reponse.json()["nb_volees"] == 20


def test_definir_sans_jeton_401(app_bareme: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Définir le barème est une action admin : refusée sans session (401)."""
    with TestClient(app_bareme) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
    with TestClient(app_bareme) as anonyme:
        reponse = anonyme.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 20, "nb_fleches_par_volee": 3},
        )
    assert reponse.status_code == 401
    assert reponse.json()["code"] == "non_authentifie"


def test_definir_tournoi_inconnu_404(app_bareme: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Définir sur un tournoi inexistant → 404 `tournoi_introuvable`."""
    with TestClient(app_bareme) as client:
        connecter_admin(client)
        reponse = client.put(
            "/api/v1/tournois/999/bareme-qualification",
            json={"nb_volees": 20, "nb_fleches_par_volee": 3},
        )
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"


def test_definir_valeur_invalide_422(app_bareme: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Un nombre de volées nul → 422 avec le code métier (règle du domaine)."""
    with TestClient(app_bareme) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 0, "nb_fleches_par_volee": 3},
        )
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "nombre_volees_invalide"


def test_definir_corps_invalide_400(app_bareme: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Un corps invalide (nb_volees non entier) → 400 avec le détail."""
    with TestClient(app_bareme) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": "beaucoup", "nb_fleches_par_volee": 3},
        )
    assert reponse.status_code == 400
    assert reponse.json()["code"] == "requete_invalide"
