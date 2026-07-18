"""Test bout-en-bout de l'API blasons (E01US005).

Traverse toutes les couches — DTO Pydantic → file d'écriture → service → repository → DB,
puis relecture/listing — et vérifie le **mapping des erreurs typées** à la frontière :
- création (avec attributs) puis listing d'un blason ;
- édition (PUT) et suppression (204) ;
- blason/tournoi introuvable → 404 ; taille/capacité invalide → 422 ; corps invalide → 400 ;
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
def app_blasons(tmp_path: Path) -> Iterator[FastAPI]:
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


def test_creer_puis_lister_un_blason(app_blasons: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """POST crée le blason (via la file) ; GET le liste avec ses attributs."""
    with TestClient(app_blasons) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        creation = client.post(
            f"/api/v1/tournois/{tournoi_id}/blasons",
            json={"nom": "Trispot 40", "taille": 0.5, "capacite": 3},
        )
        assert creation.status_code == 201, creation.text
        cree = creation.json()
        assert cree["nom"] == "Trispot 40"
        assert cree["taille"] == 0.5
        assert cree["capacite"] == 3
        assert cree["tournoi_id"] == tournoi_id
        assert isinstance(cree["id"], int)

        liste = client.get(f"/api/v1/tournois/{tournoi_id}/blasons")
        assert liste.status_code == 200
        assert liste.json() == [cree]


def test_lister_blasons_d_un_tournoi(app_blasons: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """GET liste les blasons du tournoi, dans l'ordre de création."""
    with TestClient(app_blasons) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        assert client.get(f"/api/v1/tournois/{tournoi_id}/blasons").json() == []
        client.post(
            f"/api/v1/tournois/{tournoi_id}/blasons",
            json={"nom": "A", "taille": 0.5, "capacite": 1},
        )
        client.post(
            f"/api/v1/tournois/{tournoi_id}/blasons",
            json={"nom": "B", "taille": 1.0, "capacite": 2},
        )
        noms = [b["nom"] for b in client.get(f"/api/v1/tournois/{tournoi_id}/blasons").json()]
    assert noms == ["A", "B"]


def test_modifier_un_blason(app_blasons: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """PUT édite les attributs ; la relecture reflète la modification."""
    with TestClient(app_blasons) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        cree = client.post(
            f"/api/v1/tournois/{tournoi_id}/blasons",
            json={"nom": "Ancien", "taille": 0.25, "capacite": 4},
        ).json()
        modif = client.put(
            f"/api/v1/blasons/{cree['id']}",
            json={"nom": "Nouveau", "taille": 0.5, "capacite": 2, "zones": cree["zones"]},
        )
        assert modif.status_code == 200
        corps = modif.json()
        assert corps["nom"] == "Nouveau"
        assert corps["taille"] == 0.5
        assert corps["capacite"] == 2
        assert client.get(f"/api/v1/tournois/{tournoi_id}/blasons").json() == [corps]


def test_supprimer_un_blason(app_blasons: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """DELETE → 204 ; le blason disparaît de la liste du tournoi."""
    with TestClient(app_blasons) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        cree = client.post(
            f"/api/v1/tournois/{tournoi_id}/blasons",
            json={"nom": "Monospot", "taille": 1.0, "capacite": 1},
        ).json()
        assert client.delete(f"/api/v1/blasons/{cree['id']}").status_code == 204
        assert client.get(f"/api/v1/tournois/{tournoi_id}/blasons").json() == []


def test_supprimer_blason_reference_409(
    app_blasons: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """E01US006 : supprimer un blason utilisé par une catégorie → 409 typé (`blason_reference`).

    Après réaffectation de la catégorie (blason retiré), la suppression réussit (204).
    """
    with TestClient(app_blasons) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        blason = client.post(
            f"/api/v1/tournois/{tournoi_id}/blasons",
            json={"nom": "Trispot 40", "taille": 0.5, "capacite": 3},
        ).json()
        categorie = client.post(
            f"/api/v1/tournois/{tournoi_id}/categories",
            json={"libelle": "Senior H", "blason_id": blason["id"]},
        ).json()

        refus = client.delete(f"/api/v1/blasons/{blason['id']}")
        assert refus.status_code == 409
        assert refus.json()["code"] == "blason_reference"
        # Le blason est toujours présent tant qu'il est référencé.
        assert len(client.get(f"/api/v1/tournois/{tournoi_id}/blasons").json()) == 1

        client.put(
            f"/api/v1/categories/{categorie['id']}",
            json={"libelle": "Senior H", "blason_id": None, "hauteur_cm": 130},
        )
        assert client.delete(f"/api/v1/blasons/{blason['id']}").status_code == 204


def test_creer_sans_jeton_401(app_blasons: FastAPI) -> None:
    """La création est une action admin : refusée sans session (401)."""
    with TestClient(app_blasons) as client:
        reponse = client.post(
            "/api/v1/tournois/1/blasons",
            json={"nom": "Blason", "taille": 0.5, "capacite": 1},
        )
    assert reponse.status_code == 401
    assert reponse.json()["code"] == "non_authentifie"


def test_creer_dans_tournoi_introuvable(
    app_blasons: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Créer un blason dans un tournoi inconnu → 404 typé."""
    with TestClient(app_blasons) as client:
        connecter_admin(client)
        reponse = client.post(
            "/api/v1/tournois/999/blasons",
            json={"nom": "Blason", "taille": 0.5, "capacite": 1},
        )
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"


def test_modifier_blason_introuvable(app_blasons: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """PUT sur un blason inconnu → 404 typé."""
    with TestClient(app_blasons) as client:
        connecter_admin(client)
        reponse = client.put(
            "/api/v1/blasons/999",
            json={"nom": "X", "taille": 0.5, "capacite": 1, "zones": ["10", "M"]},
        )
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "blason_introuvable"


def test_creer_taille_invalide_erreur_domaine(
    app_blasons: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Une taille hors de `]0, 1]` → 422 avec le code métier (règle du domaine)."""
    with TestClient(app_blasons) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/blasons",
            json={"nom": "Blason", "taille": 1.5, "capacite": 1},
        )
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "taille_blason_invalide"


def test_creer_capacite_invalide_erreur_domaine(
    app_blasons: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Une capacité inférieure à 1 → 422 avec le code métier (règle du domaine)."""
    with TestClient(app_blasons) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/blasons",
            json={"nom": "Blason", "taille": 0.5, "capacite": 0},
        )
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "capacite_blason_invalide"


def test_creer_requete_invalide_erreur_400(
    app_blasons: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un corps invalide (taille non numérique) → 400 avec le détail."""
    with TestClient(app_blasons) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/blasons",
            json={"nom": "Blason", "taille": "grand", "capacite": 1},
        )
    assert reponse.status_code == 400
    corps = reponse.json()
    assert corps["code"] == "requete_invalide"
    assert "details" in corps


# --- Zones : valeurs de score admises (E01US014) --------------------------------------------


def test_creer_expose_les_zones_par_defaut(
    app_blasons: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`zones` omis : l'API renvoie le défaut du domaine (blason simple complet)."""
    with TestClient(app_blasons) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/blasons",
            json={"nom": "Monospot 60", "taille": 1.0, "capacite": 1},
        )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["zones"] == ["10", "9", "8", "7", "6", "5", "4", "3", "2", "1", "M"]


def test_creer_avec_les_zones_d_un_triple_40(
    app_blasons: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le cas de l'US : un triple 40 s'arrête à 6 ; les zones traversent jusqu'à la relecture."""
    with TestClient(app_blasons) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        creation = client.post(
            f"/api/v1/tournois/{tournoi_id}/blasons",
            json={
                "nom": "Trispot 40",
                "taille": 0.5,
                "capacite": 3,
                "zones": ["10", "9", "8", "7", "6", "M"],
            },
        )
        assert creation.status_code == 201, creation.text
        assert creation.json()["zones"] == ["10", "9", "8", "7", "6", "M"]

        liste = client.get(f"/api/v1/tournois/{tournoi_id}/blasons")
    assert liste.json() == [creation.json()]


def test_modifier_les_zones(app_blasons: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """PUT édite les zones comme le reste du blason (CA « modifiable », RG-8)."""
    with TestClient(app_blasons) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        cree = client.post(
            f"/api/v1/tournois/{tournoi_id}/blasons",
            json={"nom": "Trispot 40", "taille": 0.5, "capacite": 3},
        ).json()
        reponse = client.put(
            f"/api/v1/blasons/{cree['id']}",
            json={
                "nom": "Trispot 40",
                "taille": 0.5,
                "capacite": 3,
                "zones": ["10", "9", "8", "7", "6", "M"],
            },
        )
    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["zones"] == ["10", "9", "8", "7", "6", "M"]


def test_modifier_sans_zones_erreur_400(
    app_blasons: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """L'édition est un **remplacement complet** : `zones` omis → 400, comme un nom omis.

    `zones` n'est pas le seul champ partiel d'un PUT par ailleurs total : ce serait tendre un
    piège de read-modify-write au prochain client construisant son corps depuis un modèle
    incomplet.
    """
    with TestClient(app_blasons) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        cree = client.post(
            f"/api/v1/tournois/{tournoi_id}/blasons",
            json={
                "nom": "Trispot 40",
                "taille": 0.5,
                "capacite": 3,
                "zones": ["10", "9", "8", "7", "6", "M"],
            },
        ).json()
        reponse = client.put(
            f"/api/v1/blasons/{cree['id']}",
            json={"nom": "Trispot 40 (rebaptisé)", "taille": 0.5, "capacite": 3},
        )
    assert reponse.status_code == 400
    assert reponse.json()["code"] == "requete_invalide"


def test_creer_zone_hors_vocabulaire_erreur_400(
    app_blasons: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Une zone hors vocabulaire → 400 à la frontière : le domaine ne la voit jamais.

    Même régime qu'`ages` (ADR-0019, règle 6) : le vocabulaire est fermé par le DTO (`ZoneScore`),
    les règles structurelles restent au domaine (cf. le test 422 ci-dessous).
    """
    with TestClient(app_blasons) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/blasons",
            json={"nom": "Blason", "taille": 0.5, "capacite": 1, "zones": ["10", "X", "M"]},
        )
    assert reponse.status_code == 400
    assert reponse.json()["code"] == "requete_invalide"


def test_creer_zones_sans_manque_erreur_domaine(
    app_blasons: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Une règle **structurelle** (M obligatoire) reste au domaine → 422 avec le code métier."""
    with TestClient(app_blasons) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/blasons",
            json={"nom": "Blason", "taille": 0.5, "capacite": 1, "zones": ["10", "9"]},
        )
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "zones_blason_invalides"
