"""Test bout-en-bout de l'API des postes de cible (E04US001).

Vérifie le parcours et le mapping d'erreurs :
- préparation admin des codes (un par cible du plan) → 200 avec les codes ;
- rattachement par code → jeton + cible (tournoi, numéro), **sans** ré-émettre le code ; code
  normalisé ; code inconnu → 401 ; tournoi terminé → 409 ;
- réouverture : `GET` avec l'en-tête dédié `X-Jeton-Poste` retrouve la cible ; sans jeton → 401 ;
- déconnexion (204) puis rejeu du jeton → 401 ;
- **révocation** : terminer le tournoi invalide la session (401) — l'ancrage d'ADR-0029.

Le plan de cibles et le statut du tournoi sont semés via les repositories (testés ailleurs) ; tout
le reste passe par HTTP.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from domain.gabarit_salle import GabaritSalle
from domain.tournoi import StatutTournoi
from infrastructure.db import Database, GabaritSalleRepositorySQL, TournoiRepositorySQL
from tests.conftest import ConnecterAdmin

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


@pytest.fixture
def app_session(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _semer_plan(app: FastAPI, tournoi_id: int, nb_cibles: int) -> None:
    """Applique au tournoi un plan de salle de `nb_cibles` cibles (via le repository gabarit)."""
    database: Database = app.state.database
    modele = GabaritSalle.creer("Plan", nb_cibles=nb_cibles)
    GabaritSalleRepositorySQL(database.session_factory).ajouter(modele.pour_tournoi(tournoi_id))


def _terminer(app: FastAPI, tournoi_id: int) -> None:
    """Force le tournoi au statut `terminé` (via le repository tournoi)."""
    database: Database = app.state.database
    tournois = TournoiRepositorySQL(database.session_factory)
    tournoi = tournois.par_id(tournoi_id)
    assert tournoi is not None
    tournois.enregistrer(dataclasses.replace(tournoi, statut=StatutTournoi.TERMINE))


def _preparer(
    client: TestClient, app: FastAPI, connecter_admin: ConnecterAdmin, nb_cibles: int = 3
) -> tuple[int, list[dict[str, object]]]:
    """Admin connecté, tournoi + plan créés, codes préparés ; rend (tournoi_id, postes)."""
    connecter_admin(client)
    tournoi_id = int(
        client.post("/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14"}).json()[
            "id"
        ]
    )
    _semer_plan(app, tournoi_id, nb_cibles)
    reponse = client.post(f"/api/v1/tournois/{tournoi_id}/postes")
    assert reponse.status_code == 200, reponse.text
    postes: list[dict[str, object]] = reponse.json()
    return tournoi_id, postes


def test_preparer_emet_un_code_par_cible(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_session) as client:
        _tournoi_id, postes = _preparer(client, app_session, connecter_admin, nb_cibles=3)

        assert [p["cible_index"] for p in postes] == [1, 2, 3]
        assert all(isinstance(p["code"], str) and p["code"] for p in postes)


def test_preparer_exige_l_admin(app_session: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """La préparation porte les **codes** (secrets à imprimer) : réservée à l'admin."""
    with TestClient(app_session) as client:
        tournoi_id, _ = _preparer(client, app_session, connecter_admin)
        client.headers.pop("Authorization", None)

        reponse = client.post(f"/api/v1/tournois/{tournoi_id}/postes")

        assert reponse.status_code == 401, reponse.text


def test_lister_les_codes_prepares(app_session: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """`GET` renvoie les codes déjà préparés (admin), sans en recréer."""
    with TestClient(app_session) as client:
        tournoi_id, _ = _preparer(client, app_session, connecter_admin)

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/postes")

        assert reponse.status_code == 200, reponse.text
        assert [p["cible_index"] for p in reponse.json()] == [1, 2, 3]


def test_lister_exige_l_admin(app_session: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_session) as client:
        tournoi_id, _ = _preparer(client, app_session, connecter_admin)
        client.headers.pop("Authorization", None)

        assert client.get(f"/api/v1/tournois/{tournoi_id}/postes").status_code == 401


def test_rattacher_par_code_ouvre_une_session(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_session) as client:
        tournoi_id, postes = _preparer(client, app_session, connecter_admin)
        code = str(postes[0]["code"])

        reponse = client.post("/api/v1/postes/session", json={"code": code})

        assert reponse.status_code == 200, reponse.text
        corps = reponse.json()
        assert isinstance(corps["jeton"], str) and corps["jeton"]
        assert corps["poste"]["tournoi_id"] == tournoi_id
        assert corps["poste"]["cible_index"] == 1
        # Session publique : la réponse ne ré-émet pas le code de cible.
        assert "code" not in corps["poste"]


def test_rattacher_normalise_la_saisie(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_session) as client:
        _tournoi_id, postes = _preparer(client, app_session, connecter_admin)
        code = str(postes[0]["code"])

        reponse = client.post("/api/v1/postes/session", json={"code": f"  {code.lower()} "})

        assert reponse.status_code == 200, reponse.text


def test_rattacher_code_inconnu_rend_401(app_session: FastAPI) -> None:
    with TestClient(app_session) as client:
        reponse = client.post("/api/v1/postes/session", json={"code": "ZZ99ZZ"})

        assert reponse.status_code == 401, reponse.text
        assert reponse.json()["code"] == "code_poste_inconnu"


def test_rattacher_corps_invalide_rend_400(app_session: FastAPI) -> None:
    with TestClient(app_session) as client:
        reponse = client.post("/api/v1/postes/session", json={})

        assert reponse.status_code == 400, reponse.text
        assert reponse.json()["code"] == "requete_invalide"


def test_reouverture_retrouve_la_cible(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`GET` avec le jeton de poste renvoie la cible (« retrouve sa cible sans rien demander »)."""
    with TestClient(app_session) as client:
        tournoi_id, postes = _preparer(client, app_session, connecter_admin)
        jeton = client.post("/api/v1/postes/session", json={"code": postes[1]["code"]}).json()[
            "jeton"
        ]

        reponse = client.get("/api/v1/postes/session", headers={"X-Jeton-Poste": jeton})

        assert reponse.status_code == 200, reponse.text
        assert reponse.json() == {"tournoi_id": tournoi_id, "cible_index": 2}


def test_reouverture_sans_jeton_rend_401(app_session: FastAPI) -> None:
    with TestClient(app_session) as client:
        assert client.get("/api/v1/postes/session").status_code == 401


def test_deconnexion_invalide_le_jeton(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_session) as client:
        _tournoi_id, postes = _preparer(client, app_session, connecter_admin)
        jeton = client.post("/api/v1/postes/session", json={"code": postes[0]["code"]}).json()[
            "jeton"
        ]
        entete = {"X-Jeton-Poste": jeton}

        assert client.post("/api/v1/postes/session/deconnexion", headers=entete).status_code == 204
        # Le jeton ne vaut plus rien : la relecture de cible est refusée.
        assert client.get("/api/v1/postes/session", headers=entete).status_code == 401


def test_terminer_le_tournoi_revoque_la_session(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA/ADR-0029 bout en bout : terminer le tournoi rend le jeton de poste caduc (401)."""
    with TestClient(app_session) as client:
        tournoi_id, postes = _preparer(client, app_session, connecter_admin)
        jeton = client.post("/api/v1/postes/session", json={"code": postes[0]["code"]}).json()[
            "jeton"
        ]
        entete = {"X-Jeton-Poste": jeton}
        assert client.get("/api/v1/postes/session", headers=entete).status_code == 200

        _terminer(app_session, tournoi_id)

        assert client.get("/api/v1/postes/session", headers=entete).status_code == 401


def test_rattacher_sur_tournoi_termine_rend_409(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_session) as client:
        tournoi_id, postes = _preparer(client, app_session, connecter_admin)
        _terminer(app_session, tournoi_id)

        reponse = client.post("/api/v1/postes/session", json={"code": postes[0]["code"]})

        assert reponse.status_code == 409, reponse.text
        assert reponse.json()["code"] == "rattachement_tournoi_termine"
