"""API d'import des inscrits (E02US007) — bout en bout sur l'export Ianseo réel, et la licence."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from tests.base_migree import preparer_base
from tests.conftest import ConnecterAdmin

_IANSEO = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "sources"
    / "import inscription"
    / "Export_Ianseo_challenge-des-champions-de-kervignac.csv"
)
_LIGNE = "{licence};1;CL;F;;1;1;1;1;1;{nom};JEANNE;1;0356098;KERVIGNAC;1990-01-01;;;;;"


@pytest.fixture
def app_import(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    preparer_base(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _tournoi(client: TestClient) -> tuple[int, int]:
    """Tournoi d'une catégorie ouverte à tous et d'un départ n° 1 ; renvoie (tournoi, catégorie)."""
    tid = client.post("/api/v1/tournois", json={"nom": "Challenge", "date": "2026-11-15"}).json()[
        "id"
    ]
    categorie = client.post(f"/api/v1/tournois/{tid}/categories", json={"libelle": "Scratch"})
    client.post(f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": 800, "horaire": "09:00"})
    return tid, categorie.json()["id"]


def test_l_apercu_du_fichier_reel_n_ecrit_rien(
    app_import: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_import) as client:
        connecter_admin(client)
        tid, _ = _tournoi(client)

        reponse = client.post(
            f"/api/v1/tournois/{tid}/import-inscrits/apercu", content=_IANSEO.read_bytes()
        )

        assert reponse.status_code == 200, reponse.text
        rapport = reponse.json()
        assert rapport["source"] == "ianseo"
        assert rapport["importables"] == 99
        assert rapport["lignes"][0]["nom"] == "ADVENARD"
        assert client.get(f"/api/v1/tournois/{tid}/archers").json() == []


def test_confirmer_importe_le_fichier_reel_et_le_rapport_le_dit(
    app_import: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_import) as client:
        connecter_admin(client)
        tid, _ = _tournoi(client)

        reponse = client.post(
            f"/api/v1/tournois/{tid}/import-inscrits", content=_IANSEO.read_bytes()
        )

        assert reponse.status_code == 200, reponse.text
        assert reponse.json()["importables"] == 99
        archers = client.get(f"/api/v1/tournois/{tid}/archers").json()
        assert len(archers) == 99
        assert all(archer["licence"] for archer in archers)
        # Réimporter le même fichier : chaque licence est déjà inscrite sur ce départ.
        encore = client.post(
            f"/api/v1/tournois/{tid}/import-inscrits", content=_IANSEO.read_bytes()
        )
        assert encore.json()["importables"] == 0
        assert encore.json()["rejetees"] == 99


def test_un_homonyme_n_est_importe_que_coche(
    app_import: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_import) as client:
        connecter_admin(client)
        tid, categorie_id = _tournoi(client)
        client.post(
            f"/api/v1/tournois/{tid}/archers",
            json={"nom": "Dupont", "prenom": "Jeanne", "categorie_id": categorie_id},
        )
        club = client.get("/api/v1/clubs").json()
        assert (
            club == []
        )  # l'inscrit existant n'a pas de club : l'homonymie porte sur (nom, prénom)
        fichier = _LIGNE.format(licence="", nom="DUPONT").replace("KERVIGNAC", "").encode()

        sans = client.post(f"/api/v1/tournois/{tid}/import-inscrits", content=fichier).json()
        avec = client.post(
            f"/api/v1/tournois/{tid}/import-inscrits?homonymes=1", content=fichier
        ).json()

        assert sans["homonymes"] == 1 and sans["importables"] == 0
        assert avec["importables"] == 1
        assert len(client.get(f"/api/v1/tournois/{tid}/archers").json()) == 2


def test_un_fichier_non_reconnu_rend_422(
    app_import: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_import) as client:
        connecter_admin(client)
        tid, _ = _tournoi(client)

        reponse = client.post(f"/api/v1/tournois/{tid}/import-inscrits/apercu", content=b"a;b\n")

        assert reponse.status_code == 422
        assert reponse.json()["code"] == "fichier_inscrits_illisible"


def test_l_import_exige_l_admin(app_import: FastAPI) -> None:
    with TestClient(app_import) as client:
        reponse = client.post("/api/v1/tournois/1/import-inscrits/apercu", content=b"x")

        assert reponse.status_code == 401


def test_le_guichet_refuse_une_licence_deja_prise(
    app_import: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_import) as client:
        connecter_admin(client)
        tid, categorie_id = _tournoi(client)
        corps = {"nom": "Dupont", "prenom": "Jeanne", "categorie_id": categorie_id}
        cree = client.post(f"/api/v1/tournois/{tid}/archers", json={**corps, "licence": "1234567a"})
        assert cree.json()["licence"] == "1234567A"

        refus = client.post(
            f"/api/v1/tournois/{tid}/archers",
            json={**corps, "nom": "Martin", "licence": "1234567A", "autoriser_homonyme": True},
        )

        assert refus.status_code == 409
        assert refus.json()["code"] == "licence_deja_prise"


def test_une_licence_invalide_rend_422(
    app_import: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_import) as client:
        connecter_admin(client)
        tid, categorie_id = _tournoi(client)

        reponse = client.post(
            f"/api/v1/tournois/{tid}/archers",
            json={"nom": "A", "prenom": "B", "categorie_id": categorie_id, "licence": "12-34"},
        )

        assert reponse.status_code == 422
        assert reponse.json()["code"] == "licence_invalide"
