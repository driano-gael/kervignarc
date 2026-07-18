"""Test bout-en-bout de l'API de **session** scoreur (E10US003, volet scoreur).

Vérifie le parcours et le mapping d'erreurs :
- connexion par code → jeton + identité (nom, tournoi) ; code normalisé ; code inconnu → 401 ;
- la déconnexion exige le jeton scoreur dans l'en-tête **dédié** `X-Jeton-Scoreur` (le Bearer admin
  n'y donne pas accès : modes d'identité orthogonaux) ; après déconnexion, le jeton ne vaut plus ;
- supprimer un scoreur (admin) **invalide sa session** (le CA « supprimer invalide la session »).
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
def app_session(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _creer_scoreur(client: TestClient, tournoi_id: int, nom: str) -> dict[str, object]:
    """Crée un scoreur (client déjà admin) et renvoie sa représentation (dont le code)."""
    reponse = client.post(f"/api/v1/tournois/{tournoi_id}/scoreurs", json={"nom": nom})
    assert reponse.status_code == 201, reponse.text
    resultat: dict[str, object] = reponse.json()
    return resultat


def _preparer_scoreur(client: TestClient, connecter_admin: ConnecterAdmin) -> dict[str, object]:
    """Configure l'admin, crée un tournoi et un scoreur ; renvoie le scoreur (dont le code)."""
    connecter_admin(client)
    tournoi = client.post("/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14"})
    tournoi_id = int(tournoi.json()["id"])
    return _creer_scoreur(client, tournoi_id, "Camille Dubois")


def test_connexion_par_code_ouvre_une_session(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_session) as client:
        scoreur = _preparer_scoreur(client, connecter_admin)

        reponse = client.post("/api/v1/scoreurs/session", json={"code": scoreur["code"]})

        assert reponse.status_code == 200, reponse.text
        corps = reponse.json()
        assert isinstance(corps["jeton"], str) and corps["jeton"]
        assert corps["scoreur"]["nom"] == "Camille Dubois"
        assert corps["scoreur"]["tournoi_id"] == scoreur["tournoi_id"]
        # La connexion est publique : elle ne ré-émet **pas** le code (secret), même celui que
        # l'appelant vient de fournir (moindre exposition — ADR-0025).
        assert "code" not in corps["scoreur"]


def test_connexion_normalise_la_saisie(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le code retapé en minuscules (ou avec une espace) ouvre quand même la session."""
    with TestClient(app_session) as client:
        scoreur = _preparer_scoreur(client, connecter_admin)
        code = str(scoreur["code"])

        reponse = client.post("/api/v1/scoreurs/session", json={"code": f"  {code.lower()} "})

        assert reponse.status_code == 200, reponse.text


def test_connexion_code_inconnu_rend_401(app_session: FastAPI) -> None:
    with TestClient(app_session) as client:
        reponse = client.post("/api/v1/scoreurs/session", json={"code": "ZZ99ZZ"})

        assert reponse.status_code == 401, reponse.text
        assert reponse.json()["code"] == "code_scoreur_inconnu"


def test_connexion_corps_invalide_rend_400(app_session: FastAPI) -> None:
    with TestClient(app_session) as client:
        reponse = client.post("/api/v1/scoreurs/session", json={})

        assert reponse.status_code == 400, reponse.text
        assert reponse.json()["code"] == "requete_invalide"


def test_deconnexion_invalide_le_jeton(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Après déconnexion (204), rejouer la déconnexion avec le même jeton est refusé (401)."""
    with TestClient(app_session) as client:
        scoreur = _preparer_scoreur(client, connecter_admin)
        jeton = client.post("/api/v1/scoreurs/session", json={"code": scoreur["code"]}).json()[
            "jeton"
        ]
        entete = {"X-Jeton-Scoreur": jeton}

        assert (
            client.post("/api/v1/scoreurs/session/deconnexion", headers=entete).status_code == 204
        )
        rejeu = client.post("/api/v1/scoreurs/session/deconnexion", headers=entete)

        assert rejeu.status_code == 401, rejeu.text


def test_deconnexion_sans_jeton_scoreur_rend_401(app_session: FastAPI) -> None:
    with TestClient(app_session) as client:
        reponse = client.post("/api/v1/scoreurs/session/deconnexion")

        assert reponse.status_code == 401, reponse.text


def test_le_bearer_admin_n_ouvre_pas_la_session_scoreur(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Modes d'identité **orthogonaux** : le jeton admin (Bearer) ne vaut pas un jeton scoreur.

    L'`Authorization: Bearer <jeton admin>` est bien présent (le client est connecté admin), mais la
    déconnexion scoreur exige l'en-tête `X-Jeton-Scoreur` — absent, donc 401.
    """
    with TestClient(app_session) as client:
        _preparer_scoreur(client, connecter_admin)  # pose l'en-tête Authorization admin

        reponse = client.post("/api/v1/scoreurs/session/deconnexion")

        assert reponse.status_code == 401, reponse.text


def test_supprimer_un_scoreur_invalide_sa_session(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le CA, bout en bout : un scoreur supprimé ne peut plus agir avec son ancien jeton."""
    with TestClient(app_session) as client:
        scoreur = _preparer_scoreur(client, connecter_admin)
        jeton = client.post("/api/v1/scoreurs/session", json={"code": scoreur["code"]}).json()[
            "jeton"
        ]

        suppression = client.delete(
            f"/api/v1/tournois/{scoreur['tournoi_id']}/scoreurs/{scoreur['id']}"
        )
        assert suppression.status_code == 204, suppression.text

        refus = client.post(
            "/api/v1/scoreurs/session/deconnexion", headers={"X-Jeton-Scoreur": jeton}
        )
        assert refus.status_code == 401, refus.text
