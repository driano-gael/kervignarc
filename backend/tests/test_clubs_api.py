"""Test bout-en-bout de l'API clubs (E02US001).

Traverse toutes les couches — DTO Pydantic → file d'écriture → service → repository → DB,
puis relecture/listing — et vérifie le **mapping des erreurs typées** à la frontière :
- création puis listing d'un club ;
- renommage (PUT) et suppression (204) ;
- club introuvable → 404 ; nom déjà pris → 409 ; nom vide → 422 ; corps invalide → 400 ;
- action admin refusée sans session → 401 ; consultation ouverte à tous (E10US001).

Les routes sont **à la racine** (`/api/v1/clubs`), pas sous un tournoi : le référentiel est
global (réutilisable entre tournois) — c'est ce que vérifie `test_le_referentiel_est_global`.
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
def app_clubs(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _creer_club(client: TestClient, nom: str) -> int:
    """Crée un club et renvoie son identifiant (client déjà authentifié admin)."""
    reponse = client.post("/api/v1/clubs", json={"nom": nom})
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def test_creer_puis_lister_un_club(app_clubs: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """POST crée le club (via la file) ; GET le liste."""
    with TestClient(app_clubs) as client:
        connecter_admin(client)
        creation = client.post("/api/v1/clubs", json={"nom": "Arc Club Rennes"})

        assert creation.status_code == 201, creation.text
        assert creation.json()["nom"] == "Arc Club Rennes"
        assert creation.json()["id"] is not None

        listing = client.get("/api/v1/clubs")
        assert listing.status_code == 200
        assert listing.json() == [creation.json()]


def test_creer_normalise_le_nom(app_clubs: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_clubs) as client:
        connecter_admin(client)
        creation = client.post("/api/v1/clubs", json={"nom": "  Arc Club Rennes  "})

        assert creation.status_code == 201, creation.text
        assert creation.json()["nom"] == "Arc Club Rennes"


def test_lister_un_referentiel_vide(app_clubs: FastAPI) -> None:
    with TestClient(app_clubs) as client:
        reponse = client.get("/api/v1/clubs")

        assert reponse.status_code == 200
        assert reponse.json() == []


def test_lister_trie_par_nom(app_clubs: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Casse et accents repliés : « Élan » se classe à sa place alphabétique, pas après « Z »."""
    with TestClient(app_clubs) as client:
        connecter_admin(client)
        _creer_club(client, "Zénith Archerie")
        _creer_club(client, "Élan de Fougères")
        _creer_club(client, "arc club Rennes")
        _creer_club(client, "Bretagne Archerie")

        listing = client.get("/api/v1/clubs")

        assert [club["nom"] for club in listing.json()] == [
            "arc club Rennes",
            "Bretagne Archerie",
            "Élan de Fougères",
            "Zénith Archerie",
        ]


def test_le_referentiel_est_global(app_clubs: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Les clubs sont réutilisables entre tournois : ils ne sont rattachés à aucun d'eux.

    Deux tournois créés, un club créé — il est visible sans qu'aucun tournoi soit en paramètre.
    C'est le CA « réutilisable entre tournois » d'E02US001.
    """
    with TestClient(app_clubs) as client:
        connecter_admin(client)
        client.post("/api/v1/tournois", json={"nom": "Trophée A", "date": "2026-03-14"})
        client.post("/api/v1/tournois", json={"nom": "Trophée B", "date": "2026-11-21"})
        _creer_club(client, "Arc Club Rennes")

        listing = client.get("/api/v1/clubs")

        assert listing.status_code == 200
        assert [club["nom"] for club in listing.json()] == ["Arc Club Rennes"]


def test_renommer_un_club(app_clubs: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_clubs) as client:
        connecter_admin(client)
        club_id = _creer_club(client, "Arc Club Rennes")

        edition = client.put(f"/api/v1/clubs/{club_id}", json={"nom": "Arc Club de Rennes"})

        assert edition.status_code == 200, edition.text
        assert edition.json() == {"id": club_id, "nom": "Arc Club de Rennes"}
        assert client.get("/api/v1/clubs").json() == [edition.json()]


def test_renommer_a_l_identique_est_accepte(
    app_clubs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Formulaire semé réémis tel quel : le club ne doit pas buter sur son propre nom."""
    with TestClient(app_clubs) as client:
        connecter_admin(client)
        club_id = _creer_club(client, "Arc Club Rennes")

        edition = client.put(f"/api/v1/clubs/{club_id}", json={"nom": "Arc Club Rennes"})

        assert edition.status_code == 200, edition.text


def test_supprimer_un_club(app_clubs: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_clubs) as client:
        connecter_admin(client)
        club_id = _creer_club(client, "Arc Club Rennes")

        suppression = client.delete(f"/api/v1/clubs/{club_id}")

        assert suppression.status_code == 204
        assert client.get("/api/v1/clubs").json() == []


def _creer_tournoi(client: TestClient) -> int:
    """Crée un tournoi et renvoie son identifiant (client déjà authentifié admin)."""
    reponse = client.post("/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14"})
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def test_supprimer_un_club_utilise_rend_409(
    app_clubs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le CA de l'US, bout en bout : un club rattaché à un archer n'est pas supprimable."""
    with TestClient(app_clubs) as client:
        connecter_admin(client)
        club_id = _creer_club(client, "Arc Club Rennes")
        tournoi_id = _creer_tournoi(client)
        inscription = client.post(
            f"/api/v1/tournois/{tournoi_id}/archers", json={"nom": "Robin", "club_id": club_id}
        )
        assert inscription.status_code == 201, inscription.text
        assert inscription.json()["club_id"] == club_id

        suppression = client.delete(f"/api/v1/clubs/{club_id}")

        assert suppression.status_code == 409, suppression.text
        assert suppression.json()["code"] == "club_reference"
        # Le club est toujours là : le refus n'a rien supprimé au passage.
        assert [c["id"] for c in client.get("/api/v1/clubs").json()] == [club_id]


def test_inscrire_un_archer_sans_club_reste_possible(
    app_clubs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le club est **facultatif** en E02US001 : l'inscription sans club continue de marcher."""
    with TestClient(app_clubs) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        inscription = client.post(f"/api/v1/tournois/{tournoi_id}/archers", json={"nom": "Robin"})

        assert inscription.status_code == 201, inscription.text
        assert inscription.json()["club_id"] is None


def test_inscrire_un_archer_avec_un_club_inconnu_rend_404(
    app_clubs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un `club_id` qui ne correspond à rien → 404 (l'archer n'est pas créé)."""
    with TestClient(app_clubs) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        inscription = client.post(
            f"/api/v1/tournois/{tournoi_id}/archers", json={"nom": "Robin", "club_id": 404}
        )

        assert inscription.status_code == 404, inscription.text
        assert inscription.json()["code"] == "club_introuvable"


def test_supprimer_un_club_redevenu_libre(
    app_clubs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un club n'est bloqué que tant qu'il sert : les autres restent supprimables."""
    with TestClient(app_clubs) as client:
        connecter_admin(client)
        utilise = _creer_club(client, "Arc Club Rennes")
        libre = _creer_club(client, "Élan de Fougères")
        tournoi_id = _creer_tournoi(client)
        client.post(
            f"/api/v1/tournois/{tournoi_id}/archers", json={"nom": "Robin", "club_id": utilise}
        )

        assert client.delete(f"/api/v1/clubs/{libre}").status_code == 204
        assert client.delete(f"/api/v1/clubs/{utilise}").status_code == 409


def test_creer_un_homonyme_rend_409(app_clubs: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Conflit d'ensemble → 409 (`ApplicationError`), pas 422 : le nom pris est un état, pas
    une règle métier sur la valeur."""
    with TestClient(app_clubs) as client:
        connecter_admin(client)
        _creer_club(client, "Arc Club Rennes")

        doublon = client.post("/api/v1/clubs", json={"nom": "  arc club RENNES  "})

        assert doublon.status_code == 409, doublon.text
        assert doublon.json()["code"] == "nom_club_deja_pris"


def test_creer_un_homonyme_sans_accents_rend_409(
    app_clubs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Bout en bout : le nom saisi sans ses accents est bien reconnu comme le même club."""
    with TestClient(app_clubs) as client:
        connecter_admin(client)
        _creer_club(client, "Élan de Fougères")

        doublon = client.post("/api/v1/clubs", json={"nom": "Elan de Fougeres"})

        assert doublon.status_code == 409, doublon.text
        assert doublon.json()["code"] == "nom_club_deja_pris"


def test_renommer_vers_un_homonyme_rend_409(
    app_clubs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_clubs) as client:
        connecter_admin(client)
        _creer_club(client, "Arc Club Rennes")
        autre_id = _creer_club(client, "Élan de Fougères")

        conflit = client.put(f"/api/v1/clubs/{autre_id}", json={"nom": "arc club rennes"})

        assert conflit.status_code == 409, conflit.text
        assert conflit.json()["code"] == "nom_club_deja_pris"


def test_creer_un_nom_vide_rend_422(app_clubs: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Règle métier violée (`DomainError`) → 422 avec le code métier."""
    with TestClient(app_clubs) as client:
        connecter_admin(client)
        reponse = client.post("/api/v1/clubs", json={"nom": "   "})

        assert reponse.status_code == 422, reponse.text
        assert reponse.json()["code"] == "nom_club_invalide"


def test_corps_invalide_rend_400(app_clubs: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Entrée non conforme au DTO (champ absent) → 400, avant même le domaine."""
    with TestClient(app_clubs) as client:
        connecter_admin(client)
        reponse = client.post("/api/v1/clubs", json={})

        assert reponse.status_code == 400, reponse.text
        assert reponse.json()["code"] == "requete_invalide"


def test_club_introuvable_rend_404(app_clubs: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_clubs) as client:
        connecter_admin(client)

        edition = client.put("/api/v1/clubs/404", json={"nom": "Arc Club Rennes"})
        assert edition.status_code == 404, edition.text
        assert edition.json()["code"] == "club_introuvable"

        suppression = client.delete("/api/v1/clubs/404")
        assert suppression.status_code == 404, suppression.text


@pytest.mark.parametrize(
    ("methode", "chemin", "corps"),
    [
        ("post", "/api/v1/clubs", {"nom": "Arc Club Rennes"}),
        ("put", "/api/v1/clubs/1", {"nom": "Arc Club Rennes"}),
        ("delete", "/api/v1/clubs/1", None),
    ],
)
def test_action_admin_refusee_sans_session(
    app_clubs: FastAPI, methode: str, chemin: str, corps: dict[str, str] | None
) -> None:
    """Les écritures sont des actions admin (E10US002) ; la lecture reste ouverte (E10US001)."""
    with TestClient(app_clubs) as client:
        reponse = getattr(client, methode)(chemin, **({"json": corps} if corps else {}))

        assert reponse.status_code == 401, reponse.text
