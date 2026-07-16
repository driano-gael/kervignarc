"""Test bout-en-bout de l'API inscriptions (E02US009, ADR-0017).

Traverse toutes les couches — DTO Pydantic → file d'écriture → service → repository → DB — sur les
routes `/api/v1/archers/{id}/inscriptions` et `/api/v1/inscriptions/{id}`, et vérifie le mapping des
erreurs typées :
- inscrire (montant dû dérivé du tarif, `paye` à False) puis lister ;
- double inscription → 409 `deja_inscrit` ; départ d'un autre tournoi → 404 ;
- marquer payé (PUT) ; inscription inconnue → 404 ; désinscrire (204) ;
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
def app_inscriptions(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _preparer(client: TestClient) -> tuple[int, int, int]:
    """Monte tournoi + catégorie + archer + départ (tarif 810) ; renvoie (tournoi, archer, dép.)."""
    tid = client.post("/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14"}).json()[
        "id"
    ]
    categorie_id = client.post(
        f"/api/v1/tournois/{tid}/categories", json={"libelle": "Senior 1 H"}
    ).json()["id"]
    archer_id = client.post(
        f"/api/v1/tournois/{tid}/archers",
        json={"nom": "Martin", "prenom": "Alice", "categorie_id": categorie_id},
    ).json()["id"]
    depart_id = client.post(
        f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": 810, "horaire": "9h00"}
    ).json()["id"]
    return tid, archer_id, depart_id


def test_inscrire_puis_lister(app_inscriptions: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """POST inscrit (montant dérivé, `paye` False, n° de créneau restitué) ; GET liste."""
    with TestClient(app_inscriptions) as client:
        connecter_admin(client)
        _, archer_id, depart_id = _preparer(client)

        cree = client.post(
            f"/api/v1/archers/{archer_id}/inscriptions", json={"depart_id": depart_id}
        )
        assert cree.status_code == 201, cree.text
        corps = cree.json()
        assert corps["depart_id"] == depart_id
        assert corps["numero_depart"] == 1
        assert corps["horaire"] == "9h00"
        assert corps["paye"] is False
        assert corps["montant_du_centimes"] == 810
        assert isinstance(corps["id"], int)

        liste = client.get(f"/api/v1/archers/{archer_id}/inscriptions").json()
        assert [i["id"] for i in liste] == [corps["id"]]


def test_inscrire_deux_fois_le_meme_couple_409(
    app_inscriptions: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Réinscrire sur le même créneau → 409 `deja_inscrit`."""
    with TestClient(app_inscriptions) as client:
        connecter_admin(client)
        _, archer_id, depart_id = _preparer(client)
        client.post(f"/api/v1/archers/{archer_id}/inscriptions", json={"depart_id": depart_id})
        rejet = client.post(
            f"/api/v1/archers/{archer_id}/inscriptions", json={"depart_id": depart_id}
        )
    assert rejet.status_code == 409
    assert rejet.json()["code"] == "deja_inscrit"


def test_inscrire_archer_inconnu_404(
    app_inscriptions: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Inscrire un archer inexistant → 404 `archer_introuvable`."""
    with TestClient(app_inscriptions) as client:
        connecter_admin(client)
        _, _, depart_id = _preparer(client)
        rejet = client.post("/api/v1/archers/999/inscriptions", json={"depart_id": depart_id})
    assert rejet.status_code == 404
    assert rejet.json()["code"] == "archer_introuvable"


def test_inscrire_depart_d_un_autre_tournoi_404(
    app_inscriptions: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Inscrire sur un créneau d'un **autre** tournoi → 404 `depart_introuvable` (pas de fuite)."""
    with TestClient(app_inscriptions) as client:
        connecter_admin(client)
        _, archer_id, _ = _preparer(client)
        autre = client.post("/api/v1/tournois", json={"nom": "Autre", "date": "2026-03-15"}).json()[
            "id"
        ]
        depart_etranger = client.post(
            f"/api/v1/tournois/{autre}/departs", json={"tarif_centimes": 500}
        ).json()["id"]

        rejet = client.post(
            f"/api/v1/archers/{archer_id}/inscriptions", json={"depart_id": depart_etranger}
        )
    assert rejet.status_code == 404
    assert rejet.json()["code"] == "depart_introuvable"


def test_marquer_paye_puis_relire(
    app_inscriptions: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """PUT bascule `paye` ; le montant dû (dérivé) ne change pas."""
    with TestClient(app_inscriptions) as client:
        connecter_admin(client)
        _, archer_id, depart_id = _preparer(client)
        inscription_id = client.post(
            f"/api/v1/archers/{archer_id}/inscriptions", json={"depart_id": depart_id}
        ).json()["id"]

        maj = client.put(f"/api/v1/inscriptions/{inscription_id}", json={"paye": True})
        assert maj.status_code == 200
        assert maj.json()["paye"] is True
        assert maj.json()["montant_du_centimes"] == 810
        assert client.get(f"/api/v1/archers/{archer_id}/inscriptions").json()[0]["paye"] is True


def test_marquer_paye_inscription_inconnue_404(
    app_inscriptions: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Marquer payé une inscription inexistante → 404 `inscription_introuvable`."""
    with TestClient(app_inscriptions) as client:
        connecter_admin(client)
        rejet = client.put("/api/v1/inscriptions/999", json={"paye": True})
    assert rejet.status_code == 404
    assert rejet.json()["code"] == "inscription_introuvable"


def test_desinscrire(app_inscriptions: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """DELETE → 204 ; l'inscription disparaît de la liste de l'archer."""
    with TestClient(app_inscriptions) as client:
        connecter_admin(client)
        _, archer_id, depart_id = _preparer(client)
        inscription_id = client.post(
            f"/api/v1/archers/{archer_id}/inscriptions", json={"depart_id": depart_id}
        ).json()["id"]

        assert client.delete(f"/api/v1/inscriptions/{inscription_id}").status_code == 204
        assert client.get(f"/api/v1/archers/{archer_id}/inscriptions").json() == []


def test_ecriture_sans_session_admin_401(app_inscriptions: FastAPI) -> None:
    """Inscrire sans être connecté admin → 401 (route protégée)."""
    with TestClient(app_inscriptions) as client:
        rejet = client.post("/api/v1/archers/1/inscriptions", json={"depart_id": 1})
    assert rejet.status_code == 401


def test_montant_du_somme_les_tarifs_des_creneaux(
    app_inscriptions: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """GET /montant-du renvoie la **somme** des tarifs des créneaux inscrits (E08US001)."""
    with TestClient(app_inscriptions) as client:
        connecter_admin(client)
        tid, archer_id, depart_id = _preparer(client)  # 1er départ : tarif 810
        client.post(f"/api/v1/archers/{archer_id}/inscriptions", json={"depart_id": depart_id})
        autre = client.post(
            f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": 1000}
        ).json()["id"]
        client.post(f"/api/v1/archers/{archer_id}/inscriptions", json={"depart_id": autre})

        reponse = client.get(f"/api/v1/archers/{archer_id}/montant-du")
        assert reponse.status_code == 200, reponse.text
        assert reponse.json() == {"archer_id": archer_id, "montant_du_centimes": 1810}


def test_montant_du_sans_inscription_est_zero(
    app_inscriptions: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un archer existant sans aucune inscription doit 0."""
    with TestClient(app_inscriptions) as client:
        connecter_admin(client)
        _, archer_id, _ = _preparer(client)
        reponse = client.get(f"/api/v1/archers/{archer_id}/montant-du")
    assert reponse.status_code == 200
    assert reponse.json()["montant_du_centimes"] == 0


def test_montant_du_archer_inconnu_404(
    app_inscriptions: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le montant dû d'un archer inexistant → 404 `archer_introuvable`."""
    with TestClient(app_inscriptions) as client:
        connecter_admin(client)
        reponse = client.get("/api/v1/archers/999/montant-du")
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "archer_introuvable"
