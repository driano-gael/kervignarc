"""Test bout-en-bout de la tranche verticale (E00US011).

Déroule le fil rouge du walking skeleton à travers toutes les couches — créer un tournoi →
inscrire un archer → le placer sur une cible → saisir des scores → consulter le classement —
et vérifie qu'**après chaque écriture, un événement est diffusé en direct** aux abonnés
WebSocket (mécanisme de mise à jour temps réel de l'écran de classement). Contrôle aussi le
mapping des erreurs typées à la frontière (ADR-0007).
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
def app_competition(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _creer_categorie(client: TestClient, tournoi_id: int) -> int:
    """Crée une catégorie du tournoi et renvoie son identifiant (obligatoire depuis E02US002)."""
    reponse = client.post(
        f"/api/v1/tournois/{tournoi_id}/categories", json={"libelle": "Senior 1 H"}
    )
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def test_tranche_verticale_bout_en_bout(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Tournoi → archer → placement → scores → classement, avec diffusion temps réel."""
    with TestClient(app_competition) as client, client.websocket_connect("/ws") as ws:
        assert ws.receive_json()["type"] == "connected"
        connecter_admin(client)  # accès admin requis pour créer le tournoi (E10US002)

        tournoi = client.post(
            "/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14"}
        ).json()
        assert ws.receive_json()["type"] == "donnees_modifiees"

        categorie_id = _creer_categorie(client, tournoi["id"])
        assert ws.receive_json()["type"] == "donnees_modifiees"

        alice = client.post(
            f"/api/v1/tournois/{tournoi['id']}/archers",
            json={"nom": "Martin", "prenom": "Alice", "categorie_id": categorie_id},
        )
        assert alice.status_code == 201, alice.text
        alice_id = alice.json()["id"]
        assert alice.json()["cible"] is None
        # Le DTO restitue l'identité complète : sans cette assertion, un `de_agregat` qui
        # confondrait `prenom` et `nom` passerait la suite entière au vert (les tests de
        # repository couvrent l'ORM, pas la traduction en DTO).
        assert (alice.json()["prenom"], alice.json()["categorie_id"]) == ("Alice", categorie_id)
        assert alice.json()["club_id"] is None
        assert ws.receive_json()["type"] == "donnees_modifiees"

        bob_id = client.post(
            f"/api/v1/tournois/{tournoi['id']}/archers",
            json={"nom": "Durand", "prenom": "Bob", "categorie_id": categorie_id},
        ).json()["id"]
        assert ws.receive_json()["type"] == "donnees_modifiees"

        place = client.post(f"/api/v1/archers/{alice_id}/placement", json={"cible": 3})
        assert place.status_code == 200
        assert place.json()["cible"] == 3
        assert ws.receive_json()["type"] == "donnees_modifiees"

        # Scores : Alice 10 + 9 = 19, Bob 8 → Alice devant.
        for archer_id, points in [(alice_id, 10), (alice_id, 9), (bob_id, 8)]:
            reponse = client.post(f"/api/v1/archers/{archer_id}/scores", json={"points": points})
            assert reponse.status_code == 201
            assert ws.receive_json()["type"] == "donnees_modifiees"

        classement = client.get(f"/api/v1/tournois/{tournoi['id']}/classement")
        assert classement.status_code == 200
        corps = classement.json()
        assert corps["tournoi_id"] == tournoi["id"]
        assert [
            (ligne["nom"], ligne["rang"], ligne["total"], ligne["cible"])
            for ligne in corps["lignes"]
        ] == [
            ("Martin", 1, 19, 3),
            ("Durand", 2, 8, None),
        ]
        # Le classement porte le signal « club inconnu » (E02US002, ADR-0014) : c'est la seule
        # surface où un archer inscrit apparaît, donc le seul endroit où l'anomalie se voit.
        assert [(ligne["prenom"], ligne["club_id"]) for ligne in corps["lignes"]] == [
            ("Alice", None),
            ("Bob", None),
        ]


def test_ajouter_archer_tournoi_inconnu_404(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Inscrire dans un tournoi inexistant → 404 (code applicatif typé), une fois authentifié."""
    with TestClient(app_competition) as client:
        connecter_admin(client)
        reponse = client.post(
            "/api/v1/tournois/999/archers",
            json={"nom": "Robin", "prenom": "Jean", "categorie_id": 1},
        )
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"


def test_placer_archer_inconnu_404(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Placer un archer inexistant → 404 avec le code applicatif typé (une fois authentifié)."""
    with TestClient(app_competition) as client:
        connecter_admin(client)
        reponse = client.post("/api/v1/archers/999/placement", json={"cible": 1})
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "archer_introuvable"


def test_score_hors_plage_422(app_competition: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Un score hors de 0-10 → 422 avec le code métier (règle du domaine)."""
    with TestClient(app_competition) as client:
        connecter_admin(client)
        tournoi = client.post(
            "/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14"}
        ).json()
        categorie_id = _creer_categorie(client, tournoi["id"])
        archer = client.post(
            f"/api/v1/tournois/{tournoi['id']}/archers",
            json={"nom": "Robin", "prenom": "Jean", "categorie_id": categorie_id},
        ).json()
        reponse = client.post(f"/api/v1/archers/{archer['id']}/scores", json={"points": 11})
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "score_invalide"


def test_classement_tournoi_inconnu_404(app_competition: FastAPI) -> None:
    """Consulter le classement d'un tournoi inexistant → 404."""
    with TestClient(app_competition) as client:
        reponse = client.get("/api/v1/tournois/999/classement")
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"


def _tournoi_avec_categorie(client: TestClient, nom: str = "Salle 18m") -> tuple[int, int]:
    """Crée un tournoi et une catégorie ; renvoie leurs identifiants."""
    tournoi = client.post("/api/v1/tournois", json={"nom": nom, "date": "2026-03-14"}).json()
    return int(tournoi["id"]), _creer_categorie(client, tournoi["id"])


def test_inscrire_sans_prenom_rend_400(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le prénom est obligatoire au **contrat d'entrée** → 400 Pydantic, avant tout métier."""
    with TestClient(app_competition) as client:
        connecter_admin(client)
        tournoi_id, categorie_id = _tournoi_avec_categorie(client)

        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/archers",
            json={"nom": "Robin", "categorie_id": categorie_id},
        )

    assert reponse.status_code == 400
    assert reponse.json()["code"] == "requete_invalide"


def test_inscrire_avec_un_prenom_vide_rend_422(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un prénom **présent mais vide** passe Pydantic et tombe sur la règle du domaine → 422."""
    with TestClient(app_competition) as client:
        connecter_admin(client)
        tournoi_id, categorie_id = _tournoi_avec_categorie(client)

        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/archers",
            json={"nom": "Robin", "prenom": "   ", "categorie_id": categorie_id},
        )

    assert reponse.status_code == 422
    assert reponse.json()["code"] == "prenom_archer_invalide"


def test_inscrire_avec_une_categorie_d_un_autre_tournoi_rend_409(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Conflit inter-agrégats → 409 (`categorie_hors_tournoi`), comme `blason_hors_tournoi`."""
    with TestClient(app_competition) as client:
        connecter_admin(client)
        tournoi_id, _ = _tournoi_avec_categorie(client)
        _, categorie_etrangere = _tournoi_avec_categorie(client, "Trophée d'hiver")

        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/archers",
            json={"nom": "Robin", "prenom": "Jean", "categorie_id": categorie_etrangere},
        )

    assert reponse.status_code == 409
    assert reponse.json()["code"] == "categorie_hors_tournoi"


def test_inscrire_un_homonyme_rend_409_puis_passe_sur_confirmation(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le protocole en **deux temps** d'E02US002, bout en bout : signaler, puis laisser passer.

    Le 409 n'est pas un refus définitif — c'est la question posée à l'admin. Le second appel,
    porteur de la réponse, inscrit le père **et** le fils.
    """
    with TestClient(app_competition) as client:
        connecter_admin(client)
        tournoi_id, categorie_id = _tournoi_avec_categorie(client)
        corps = {"nom": "Dupont", "prenom": "Jean", "categorie_id": categorie_id}

        premier = client.post(f"/api/v1/tournois/{tournoi_id}/archers", json=corps)
        assert premier.status_code == 201, premier.text

        signale = client.post(f"/api/v1/tournois/{tournoi_id}/archers", json=corps)
        assert signale.status_code == 409
        assert signale.json()["code"] == "homonyme_archer"

        confirme = client.post(
            f"/api/v1/tournois/{tournoi_id}/archers", json={**corps, "autoriser_homonyme": True}
        )
        assert confirme.status_code == 201, confirme.text
        assert confirme.json()["id"] != premier.json()["id"]
