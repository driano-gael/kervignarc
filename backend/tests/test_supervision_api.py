"""Test bout-en-bout de l'API de supervision des postes (E12US001, ADR-0038).

Vérifie le parcours et le mapping d'erreurs de la console du jour J :
- console admin : liste des postes de cible avec leur état ; postes préparés mais sans tablette →
  *non rattaché* ; compteur global ;
- heartbeat (jeton de poste requis) : un poste qui pingue passe *en ligne*, avec son IP en
  diagnostic ; sans jeton → 401 ;
- révocation admin : le poste repasse *non rattaché* et son jeton cesse de valoir ;
- gardes : console et révocation réservées à l'admin ; tournoi/poste inconnu → 404.

Le **passage hors-ligne par expiration** (le temps qui passe) est prouvé côté service avec une
horloge injectée (`test_service_supervision.py`) : ici l'app tourne sur l'horloge système, on ne
rejoue donc que le chemin *en ligne* et le structurel. Plan de cibles semé via le repository ; tout
le reste passe par HTTP.
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
from domain.gabarit_salle import GabaritSalle
from infrastructure.db import Database, GabaritSalleRepositorySQL
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
    database: Database = app.state.database
    modele = GabaritSalle.creer("Plan", nb_cibles=nb_cibles)
    GabaritSalleRepositorySQL(database.session_factory).ajouter(modele.pour_tournoi(tournoi_id))


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
    return tournoi_id, reponse.json()


def _rattacher(client: TestClient, code: str) -> str:
    """Rattache une tablette par code et renvoie son jeton de poste."""
    reponse = client.post("/api/v1/postes/session", json={"code": code})
    assert reponse.status_code == 200, reponse.text
    return str(reponse.json()["jeton"])


def test_console_liste_les_postes_non_rattaches(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Codes préparés mais aucune tablette dessus : tous *non rattachés*, aucun en ligne."""
    with TestClient(app_session) as client:
        tournoi_id, _ = _preparer(client, app_session, connecter_admin, nb_cibles=3)

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/supervision")

        assert reponse.status_code == 200, reponse.text
        corps = reponse.json()
        assert corps["nb_total"] == 3
        assert corps["nb_en_ligne"] == 0
        assert [ligne["cible_index"] for ligne in corps["postes"]] == [1, 2, 3]
        assert all(ligne["etat"] == "non_rattache" for ligne in corps["postes"])
        assert all(ligne["ip"] is None for ligne in corps["postes"])
        assert all(ligne["avancement"] is None for ligne in corps["postes"])


def test_heartbeat_rend_le_poste_en_ligne(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un poste rattaché qui pingue passe *en ligne*, avec son IP affichée en diagnostic."""
    with TestClient(app_session) as client:
        tournoi_id, postes = _preparer(client, app_session, connecter_admin)
        jeton = _rattacher(client, str(postes[0]["code"]))

        battement = client.post(
            "/api/v1/postes/session/heartbeat", headers={"X-Jeton-Poste": jeton}
        )
        assert battement.status_code == 204, battement.text

        corps = client.get(f"/api/v1/tournois/{tournoi_id}/supervision").json()
        assert corps["nb_en_ligne"] == 1
        ligne = next(li for li in corps["postes"] if li["cible_index"] == 1)
        assert ligne["etat"] == "en_ligne"
        assert ligne["ip"] is not None  # l'IP du client de test, en diagnostic


def test_heartbeat_sans_jeton_rend_401(app_session: FastAPI) -> None:
    with TestClient(app_session) as client:
        assert client.post("/api/v1/postes/session/heartbeat").status_code == 401


def test_console_exige_l_admin(app_session: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_session) as client:
        tournoi_id, _ = _preparer(client, app_session, connecter_admin)
        client.headers.pop("Authorization", None)

        assert client.get(f"/api/v1/tournois/{tournoi_id}/supervision").status_code == 401


def test_revoquer_fait_repasser_non_rattache_et_invalide_le_jeton(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA/`D-07` bout en bout : révoquer un poste le remet *non rattaché* et périme son jeton."""
    with TestClient(app_session) as client:
        tournoi_id, postes = _preparer(client, app_session, connecter_admin)
        poste_id = int(str(postes[0]["id"]))
        jeton = _rattacher(client, str(postes[0]["code"]))
        client.post("/api/v1/postes/session/heartbeat", headers={"X-Jeton-Poste": jeton})

        revocation = client.post(f"/api/v1/tournois/{tournoi_id}/postes/{poste_id}/revocation")
        assert revocation.status_code == 204, revocation.text

        corps = client.get(f"/api/v1/tournois/{tournoi_id}/supervision").json()
        ligne = next(li for li in corps["postes"] if li["cible_index"] == 1)
        assert ligne["etat"] == "non_rattache"
        assert ligne["ip"] is None
        # Le jeton révoqué ne vaut plus rien : la relecture de cible est refusée.
        assert (
            client.get("/api/v1/postes/session", headers={"X-Jeton-Poste": jeton}).status_code
            == 401
        )


def test_revoquer_exige_l_admin(app_session: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_session) as client:
        tournoi_id, postes = _preparer(client, app_session, connecter_admin)
        poste_id = int(str(postes[0]["id"]))
        client.headers.pop("Authorization", None)

        reponse = client.post(f"/api/v1/tournois/{tournoi_id}/postes/{poste_id}/revocation")
        assert reponse.status_code == 401, reponse.text


def test_revoquer_un_poste_inconnu_rend_404(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_session) as client:
        tournoi_id, _ = _preparer(client, app_session, connecter_admin)

        reponse = client.post(f"/api/v1/tournois/{tournoi_id}/postes/999999/revocation")

        assert reponse.status_code == 404, reponse.text
        assert reponse.json()["code"] == "poste_introuvable"


def test_console_tournoi_inconnu_rend_404(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_session) as client:
        _preparer(client, app_session, connecter_admin)  # connecte l'admin

        reponse = client.get("/api/v1/tournois/999999/supervision")

        assert reponse.status_code == 404, reponse.text
        assert reponse.json()["code"] == "tournoi_introuvable"
