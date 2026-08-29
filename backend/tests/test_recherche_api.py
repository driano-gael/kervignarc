"""Test bout-en-bout de l'API de **recherche transverse** (E16US010).

Écrit **après** l'implémentation (règle 9 : la frontière n'a pas d'oracle — la règle est prouvée au
domaine, `test_domain_recherche.py`, et l'agrégation au service, `test_service_recherche.py`). On
vérifie ici le structurel : la route unique rend bien trois entités, la garde **admin** tient, le
scope tournoi voyage, et un segment hors famille part en 400.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from tests.base_migree import preparer_base
from tests.conftest import ConnecterAdmin


@pytest.fixture
def app_recherche(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    preparer_base(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _decor(client: TestClient, connecter_admin: ConnecterAdmin) -> int:
    """Un tournoi, un club et un archer accentué — de quoi exercer les trois entités."""
    connecter_admin(client)
    tournoi = client.post(
        "/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14", "lieu": "Kervignarc"}
    )
    assert tournoi.status_code == 201, tournoi.text
    tournoi_id = int(tournoi.json()["id"])

    club = client.post("/api/v1/clubs", json={"nom": "Arc Club de Kervignarc"})
    assert club.status_code == 201, club.text

    categorie = client.post(
        f"/api/v1/tournois/{tournoi_id}/categories", json={"libelle": "Senior 1 H"}
    )
    assert categorie.status_code == 201, categorie.text
    categorie_id = int(categorie.json()["id"])

    archer = client.post(
        f"/api/v1/tournois/{tournoi_id}/archers",
        json={
            "nom": "Lévêque",
            "prenom": "Jean",
            "categorie_id": categorie_id,
            "club_id": int(club.json()["id"]),
        },
    )
    assert archer.status_code == 201, archer.text

    # ⚠️ **Une SECONDE édition, avec un homonyme.** Sans elle, `ArcherRepositorySQL.tous()` n'était
    # jamais exercé sur plus d'un tournoi — or « la recherche traverse les éditions » est le CA
    # central de cette route, et il n'était prouvé qu'avec un faux (relevé par l'axe B).
    ancien = client.post(
        "/api/v1/tournois", json={"nom": "Salle 18m", "date": "2025-03-15", "lieu": "Kervignarc"}
    )
    assert ancien.status_code == 201, ancien.text
    ancien_id = int(ancien.json()["id"])
    categorie_ancienne = client.post(
        f"/api/v1/tournois/{ancien_id}/categories", json={"libelle": "Senior 1 H"}
    )
    assert categorie_ancienne.status_code == 201, categorie_ancienne.text
    jumeau = client.post(
        f"/api/v1/tournois/{ancien_id}/archers",
        json={
            "nom": "Lévêque",
            "prenom": "Jean",
            "categorie_id": int(categorie_ancienne.json()["id"]),
            "club_id": int(club.json()["id"]),
        },
    )
    assert jumeau.status_code == 201, jumeau.text
    return tournoi_id


def test_un_archer_se_trouve_sans_accents(
    app_recherche: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le geste réel : la saisie tablette n'accentue pas."""
    with TestClient(app_recherche) as client:
        _decor(client, connecter_admin)

        reponse = client.get("/api/v1/recherche", params={"entite": "archer", "q": "leveque"})

        assert reponse.status_code == 200, reponse.text
        corps = reponse.json()
        # Les DEUX éditions remontent : c'est le CA « hors pilotage, on traverse les éditions ».
        assert corps["total"] == 2
        assert corps["resultats"][0]["libelle"] == "Lévêque Jean"
        # Et elles se distinguent, malgré le même nom de tournoi et le même club.
        assert len({r["precision"] for r in corps["resultats"]}) == 2
        assert corps["resultats"][0]["entite"] == "archer"
        # Le tournoi d'ouverture voyage : sans lui, le front ne sait pas où mène le résultat.
        assert corps["resultats"][0]["tournoi_id"] is not None


def test_les_trois_entites_repondent_sur_la_meme_route(
    app_recherche: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Une route paramétrée, pas trois routes jumelles."""
    with TestClient(app_recherche) as client:
        _decor(client, connecter_admin)

        for entite, fragment, attendu in (
            ("tournoi", "salle", 2),
            ("club", "kervignarc", 1),
            ("archer", "jean", 2),
        ):
            reponse = client.get("/api/v1/recherche", params={"entite": entite, "q": fragment})

            assert reponse.status_code == 200, reponse.text
            assert reponse.json()["total"] == attendu, entite


def test_le_scope_tournoi_voyage_jusqu_au_service(
    app_recherche: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA « en pilotage » : le même chemin, restreint — un tournoi étranger ne rend rien."""
    with TestClient(app_recherche) as client:
        tournoi_id = _decor(client, connecter_admin)

        dedans = client.get(
            "/api/v1/recherche",
            params={"entite": "archer", "q": "leveque", "tournoi_id": tournoi_id},
        )
        ailleurs = client.get(
            "/api/v1/recherche",
            params={"entite": "archer", "q": "leveque", "tournoi_id": tournoi_id + 999},
        )

        assert dedans.json()["total"] == 1
        assert ailleurs.json()["total"] == 0


def test_une_recherche_vide_ne_rend_pas_le_referentiel(
    app_recherche: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La déroulante seule ne doit rien déverser."""
    with TestClient(app_recherche) as client:
        _decor(client, connecter_admin)

        reponse = client.get("/api/v1/recherche", params={"entite": "club", "q": ""})

        assert reponse.status_code == 200, reponse.text
        assert reponse.json() == {"resultats": [], "total": 0}


def test_une_entite_inconnue_rend_400(
    app_recherche: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_recherche) as client:
        connecter_admin(client)

        reponse = client.get("/api/v1/recherche", params={"entite": "blason", "q": "x"})

        assert reponse.status_code == 400, reponse.text


def test_la_recherche_est_reservee_a_l_admin(app_recherche: FastAPI) -> None:
    """Le référentiel des archers n'est pas public."""
    with TestClient(app_recherche) as client:
        reponse = client.get("/api/v1/recherche", params={"entite": "archer", "q": "a"})

        assert reponse.status_code == 401
