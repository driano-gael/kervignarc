"""Test bout-en-bout de l'API de **définition** des scoreurs (E10US003, volet admin).

Traverse toutes les couches — DTO → file d'écriture → service → repository → DB — et vérifie le
mapping des erreurs à la frontière : création (code généré), listing trié, renommage (code figé),
suppression, et les refus 404 / 422 / 400 / 401. La **lecture est protégée** (`exiger_admin`), à
rebours des clubs : la réponse porte les **codes**, des secrets à distribuer.
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
from infrastructure.scoreurs import ALPHABET_CODE, LONGUEUR_CODE
from tests.conftest import ConnecterAdmin

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


@pytest.fixture
def app_scoreurs(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _creer_tournoi(client: TestClient) -> int:
    reponse = client.post("/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14"})
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def _creer_scoreur(client: TestClient, tournoi_id: int, nom: str) -> dict[str, object]:
    reponse = client.post(f"/api/v1/tournois/{tournoi_id}/scoreurs", json={"nom": nom})
    assert reponse.status_code == 201, reponse.text
    resultat: dict[str, object] = reponse.json()
    return resultat


def test_alphabet_code_exclut_les_confondables() -> None:
    """CA : un code lisible sur papier — l'alphabet **exclut** les caractères confondables.

    Assertion dérivée du **CA**, pas de la constante : elle attraperait une régression qui
    réintroduirait `0`/`O`/`1`/`I` dans `ALPHABET_CODE` (le test d'appartenance `caractère in
    ALPHABET_CODE`, lui, resterait vert). 6 caractères, alphabet en majuscules.
    """
    assert set(ALPHABET_CODE).isdisjoint({"I", "O", "0", "1"})
    assert ALPHABET_CODE.isupper()
    assert LONGUEUR_CODE >= 4


def test_creer_scoreur_genere_un_code(
    app_scoreurs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le nom seul est fourni ; le serveur attribue un code court lisible."""
    with TestClient(app_scoreurs) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        scoreur = _creer_scoreur(client, tournoi_id, "Camille Dubois")

        assert scoreur["nom"] == "Camille Dubois"
        assert scoreur["tournoi_id"] == tournoi_id
        code = scoreur["code"]
        assert isinstance(code, str)
        assert len(code) == LONGUEUR_CODE
        assert all(caractere in ALPHABET_CODE for caractere in code)


def test_creer_normalise_le_nom(app_scoreurs: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_scoreurs) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        scoreur = _creer_scoreur(client, tournoi_id, "  Camille  ")

        assert scoreur["nom"] == "Camille"


def test_plusieurs_scoreurs_ont_des_codes_distincts(
    app_scoreurs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_scoreurs) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        codes = {_creer_scoreur(client, tournoi_id, f"Scoreur {i}")["code"] for i in range(4)}

        assert len(codes) == 4


def test_lister_trie_par_nom(app_scoreurs: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_scoreurs) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        _creer_scoreur(client, tournoi_id, "Zoé")
        _creer_scoreur(client, tournoi_id, "Élodie")
        _creer_scoreur(client, tournoi_id, "bob")

        listing = client.get(f"/api/v1/tournois/{tournoi_id}/scoreurs")

        assert listing.status_code == 200, listing.text
        assert [s["nom"] for s in listing.json()] == ["bob", "Élodie", "Zoé"]


def test_lister_ne_renvoie_que_les_scoreurs_du_tournoi(
    app_scoreurs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_scoreurs) as client:
        connecter_admin(client)
        tournoi_a = _creer_tournoi(client)
        reponse_b = client.post("/api/v1/tournois", json={"nom": "Autre", "date": "2026-11-21"})
        tournoi_b = int(reponse_b.json()["id"])
        _creer_scoreur(client, tournoi_a, "Alice")
        _creer_scoreur(client, tournoi_b, "Bob")

        listing_a = client.get(f"/api/v1/tournois/{tournoi_a}/scoreurs")

        assert [s["nom"] for s in listing_a.json()] == ["Alice"]


def test_renommer_conserve_le_code(app_scoreurs: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_scoreurs) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        scoreur = _creer_scoreur(client, tournoi_id, "Camile")

        edition = client.put(
            f"/api/v1/tournois/{tournoi_id}/scoreurs/{scoreur['id']}",
            json={"nom": "Camille Dubois"},
        )

        assert edition.status_code == 200, edition.text
        assert edition.json()["nom"] == "Camille Dubois"
        assert edition.json()["code"] == scoreur["code"]


def test_supprimer_un_scoreur(app_scoreurs: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_scoreurs) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        scoreur = _creer_scoreur(client, tournoi_id, "Camille")

        suppression = client.delete(f"/api/v1/tournois/{tournoi_id}/scoreurs/{scoreur['id']}")

        assert suppression.status_code == 204
        assert client.get(f"/api/v1/tournois/{tournoi_id}/scoreurs").json() == []


def test_creer_dans_un_tournoi_inconnu_rend_404(
    app_scoreurs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_scoreurs) as client:
        connecter_admin(client)
        reponse = client.post("/api/v1/tournois/404/scoreurs", json={"nom": "Camille"})

        assert reponse.status_code == 404, reponse.text
        assert reponse.json()["code"] == "tournoi_introuvable"


def test_scoreur_introuvable_rend_404(
    app_scoreurs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_scoreurs) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        edition = client.put(f"/api/v1/tournois/{tournoi_id}/scoreurs/404", json={"nom": "Camille"})
        assert edition.status_code == 404, edition.text
        assert edition.json()["code"] == "scoreur_introuvable"

        suppression = client.delete(f"/api/v1/tournois/{tournoi_id}/scoreurs/404")
        assert suppression.status_code == 404, suppression.text


def test_modifier_un_scoreur_d_un_autre_tournoi_rend_404(
    app_scoreurs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un scoreur d'un autre tournoi n'existe pas du point de vue de celui de l'URL."""
    with TestClient(app_scoreurs) as client:
        connecter_admin(client)
        tournoi_a = _creer_tournoi(client)
        reponse_b = client.post("/api/v1/tournois", json={"nom": "Autre", "date": "2026-11-21"})
        tournoi_b = int(reponse_b.json()["id"])
        scoreur = _creer_scoreur(client, tournoi_a, "Alice")

        edition = client.put(
            f"/api/v1/tournois/{tournoi_b}/scoreurs/{scoreur['id']}", json={"nom": "Bob"}
        )

        assert edition.status_code == 404, edition.text
        assert edition.json()["code"] == "scoreur_introuvable"


def test_creer_nom_blanc_rend_422(app_scoreurs: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Un nom d'espaces passe le DTO (non vide) mais viole la règle métier → 422."""
    with TestClient(app_scoreurs) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        reponse = client.post(f"/api/v1/tournois/{tournoi_id}/scoreurs", json={"nom": "   "})

        assert reponse.status_code == 422, reponse.text
        assert reponse.json()["code"] == "nom_scoreur_invalide"


def test_creer_corps_invalide_rend_400(
    app_scoreurs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Nom absent (ou vide, `min_length=1`) : entrée non conforme au DTO → 400."""
    with TestClient(app_scoreurs) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        reponse = client.post(f"/api/v1/tournois/{tournoi_id}/scoreurs", json={})

        assert reponse.status_code == 400, reponse.text
        assert reponse.json()["code"] == "requete_invalide"


@pytest.mark.parametrize(
    ("methode", "chemin", "corps"),
    [
        ("post", "/api/v1/tournois/1/scoreurs", {"nom": "Camille"}),
        ("get", "/api/v1/tournois/1/scoreurs", None),
        ("put", "/api/v1/tournois/1/scoreurs/1", {"nom": "Camille"}),
        ("delete", "/api/v1/tournois/1/scoreurs/1", None),
    ],
)
def test_definition_reservee_a_l_admin(
    app_scoreurs: FastAPI,
    methode: str,
    chemin: str,
    corps: dict[str, str] | None,
) -> None:
    """Toute la définition — **lecture comprise** — est admin : la liste porte les codes secrets."""
    with TestClient(app_scoreurs) as client:
        reponse = getattr(client, methode)(chemin, **({"json": corps} if corps else {}))

        assert reponse.status_code == 401, reponse.text
