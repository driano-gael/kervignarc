"""Test bout-en-bout de l'API départs (E02US004, ADR-0017).

Traverse toutes les couches — DTO Pydantic → file d'écriture → service → repository → DB — sur les
routes imbriquées `/api/v1/tournois/{id}/departs`, et vérifie le mapping des erreurs typées :
- création (numéro attribué par le serveur) puis listing trié ;
- édition (PUT) du tarif et de l'horaire ; suppression (204) ;
- tarif hors plage → 422 (`DomainError`) ; tarif non entier → 400 (validation) ;
- tournoi inconnu → 404 ; départ d'un autre tournoi → 404 ;
- garde admin : écriture sans session → 401.
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
def app_departs(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _creer_tournoi(client: TestClient) -> int:
    """Crée un tournoi et renvoie son identifiant (l'appelant est déjà connecté admin)."""
    reponse = client.post("/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14"})
    assert reponse.status_code == 201
    tournoi_id = reponse.json()["id"]
    assert isinstance(tournoi_id, int)
    return tournoi_id


def test_creer_puis_lister_les_departs(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """POST crée les créneaux (numéros 1 puis 2, attribués par le serveur) ; GET les liste triés."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)

        premier = client.post(
            f"/api/v1/tournois/{tid}/departs",
            json={"tarif_centimes": 810, "horaire": "9h00"},
        )
        assert premier.status_code == 201
        corps = premier.json()
        assert corps["numero"] == 1
        assert corps["tarif_centimes"] == 810
        assert corps["horaire"] == "9h00"
        assert corps["tournoi_id"] == tid
        assert isinstance(corps["id"], int)

        second = client.post(f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": 1000})
        assert second.json()["numero"] == 2
        assert second.json()["horaire"] is None

        liste = client.get(f"/api/v1/tournois/{tid}/departs").json()
        assert [d["numero"] for d in liste] == [1, 2]


def test_creer_tarif_negatif_erreur_domaine(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un tarif négatif → 422 avec le code métier."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)
        reponse = client.post(f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": -1})
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "tarif_depart_invalide"


def test_creer_tarif_non_entier_erreur_400(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un tarif en euros décimaux (8.10) est rejeté par le DTO : l'API compte en centimes."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)
        reponse = client.post(f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": 8.10})
    assert reponse.status_code == 400
    assert reponse.json()["code"] == "requete_invalide"


def test_creer_sur_tournoi_inconnu_404(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Créer un départ sur un tournoi inexistant → 404 typé."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        reponse = client.post("/api/v1/tournois/999/departs", json={"tarif_centimes": 810})
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"


def test_modifier_un_depart(app_departs: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """PUT met à jour tarif et horaire ; le numéro ne bouge pas."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)
        cree = client.post(
            f"/api/v1/tournois/{tid}/departs",
            json={"tarif_centimes": 810, "horaire": "9h00"},
        ).json()

        modif = client.put(
            f"/api/v1/tournois/{tid}/departs/{cree['id']}",
            json={"tarif_centimes": 1250, "horaire": "14h00"},
        )
        assert modif.status_code == 200
        corps = modif.json()
        assert corps["numero"] == 1
        assert corps["tarif_centimes"] == 1250
        assert corps["horaire"] == "14h00"


def test_modifier_depart_d_un_autre_tournoi_404(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Éditer un départ via un autre tournoi → 404 `depart_introuvable` (pas de fuite du voisin)."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid_a = _creer_tournoi(client)
        autre = client.post("/api/v1/tournois", json={"nom": "Autre", "date": "2026-03-15"}).json()
        cree = client.post(f"/api/v1/tournois/{tid_a}/departs", json={"tarif_centimes": 810}).json()

        reponse = client.put(
            f"/api/v1/tournois/{autre['id']}/departs/{cree['id']}",
            json={"tarif_centimes": 900},
        )
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "depart_introuvable"


def test_supprimer_un_depart(app_departs: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """DELETE → 204 ; le créneau disparaît de la liste."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)
        cree = client.post(f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": 810}).json()

        assert client.delete(f"/api/v1/tournois/{tid}/departs/{cree['id']}").status_code == 204
        assert client.get(f"/api/v1/tournois/{tid}/departs").json() == []


def test_ecriture_sans_session_admin_401(app_departs: FastAPI) -> None:
    """Créer un départ sans être connecté admin → 401 (route protégée)."""
    with TestClient(app_departs) as client:
        reponse = client.post("/api/v1/tournois/1/departs", json={"tarif_centimes": 810})
    assert reponse.status_code == 401


def _inscrire_un_archer_sur(client: TestClient, tid: int, depart_id: int) -> int:
    """Monte une catégorie + un archer et l'inscrit sur `depart_id` ; renvoie l'id d'inscription."""
    categorie_id = client.post(
        f"/api/v1/tournois/{tid}/categories", json={"libelle": "Senior 1 H"}
    ).json()["id"]
    archer_id = client.post(
        f"/api/v1/tournois/{tid}/archers",
        json={"nom": "Martin", "prenom": "Alice", "categorie_id": categorie_id},
    ).json()["id"]
    return int(
        client.post(
            f"/api/v1/archers/{archer_id}/inscriptions", json={"depart_id": depart_id}
        ).json()["id"]
    )


def test_supprimer_depart_avec_inscriptions_409(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Supprimer un créneau à inscriptions → 409 `depart_avec_inscriptions` (garde-fou E02US009)."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)
        depart_id = client.post(
            f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": 810}
        ).json()["id"]
        _inscrire_un_archer_sur(client, tid, depart_id)

        rejet = client.delete(f"/api/v1/tournois/{tid}/departs/{depart_id}")
        assert rejet.status_code == 409
        assert rejet.json()["code"] == "depart_avec_inscriptions"
        # Rien détruit : le créneau survit tant que l'admin n'a pas confirmé.
        assert [d["id"] for d in client.get(f"/api/v1/tournois/{tid}/departs").json()] == [
            depart_id
        ]


def test_supprimer_depart_avec_inscriptions_confirme_204(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Avec `autoriser_suppression_inscrits=true`, l'admin confirme : 204, le créneau part."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)
        depart_id = client.post(
            f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": 810}
        ).json()["id"]
        _inscrire_un_archer_sur(client, tid, depart_id)

        confirme = client.delete(
            f"/api/v1/tournois/{tid}/departs/{depart_id}",
            params={"autoriser_suppression_inscrits": True},
        )
        assert confirme.status_code == 204
        assert client.get(f"/api/v1/tournois/{tid}/departs").json() == []
