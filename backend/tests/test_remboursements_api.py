"""Test bout-en-bout de l'API remboursements (E08US005, ADR-0057).

Traverse toutes les couches — DTO → file d'écriture → service → repository → DB — sur les routes
`GET /api/v1/tournois/{id}/remboursements` et `PUT …/remboursements/{id}`. Un poste naît d'une
désinscription payée confirmée (le seul chemin de création exposé), puis on le liste et le traite.
Vérifie aussi le mapping des erreurs (404 inconnu, 409 déjà traité) et la garde admin (401).
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
def app_remboursements(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _poste_par_desinscription(client: TestClient) -> tuple[int, int]:
    """Crée un remboursement via une désinscription payée confirmée ; renvoie (tournoi, poste)."""
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
        f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": 810, "horaire": "09:00"}
    ).json()["id"]
    inscription_id = client.post(
        f"/api/v1/archers/{archer_id}/inscriptions", json={"depart_id": depart_id}
    ).json()["id"]
    client.put(f"/api/v1/inscriptions/{inscription_id}", json={"paye": True})
    client.delete(f"/api/v1/inscriptions/{inscription_id}?confirme=true")
    poste_id = client.get(f"/api/v1/tournois/{tid}/remboursements").json()[0]["id"]
    return tid, poste_id


def test_lister_les_remboursements(
    app_remboursements: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """GET liste les postes ouverts avec leur instantané (archer, créneau, montant, statut)."""
    with TestClient(app_remboursements) as client:
        connecter_admin(client)
        tid, _ = _poste_par_desinscription(client)

        postes = client.get(f"/api/v1/tournois/{tid}/remboursements")
        assert postes.status_code == 200, postes.text
        corps = postes.json()
        assert len(corps) == 1
        poste = corps[0]
        assert poste["montant_centimes"] == 810
        assert poste["statut"] == "a_rembourser"
        assert poste["motif"] == "desinscription"
        assert poste["archer_prenom"] == "Alice"
        assert poste["traite_le"] is None


def test_marquer_rembourse(app_remboursements: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """PUT `{statut: rembourse}` clôt le poste (statut + date de traitement)."""
    with TestClient(app_remboursements) as client:
        connecter_admin(client)
        tid, poste_id = _poste_par_desinscription(client)

        maj = client.put(
            f"/api/v1/tournois/{tid}/remboursements/{poste_id}", json={"statut": "rembourse"}
        )
        assert maj.status_code == 200, maj.text
        assert maj.json()["statut"] == "rembourse"
        assert maj.json()["traite_le"] is not None


def test_marquer_reporte(app_remboursements: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """PUT `{statut: reporte}` marque le report (intention consignée)."""
    with TestClient(app_remboursements) as client:
        connecter_admin(client)
        tid, poste_id = _poste_par_desinscription(client)

        maj = client.put(
            f"/api/v1/tournois/{tid}/remboursements/{poste_id}", json={"statut": "reporte"}
        )
        assert maj.status_code == 200, maj.text
        assert maj.json()["statut"] == "reporte"


def test_marquer_deja_traite_409(
    app_remboursements: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Re-traiter un poste déjà remboursé → 409 `remboursement_deja_traite`."""
    with TestClient(app_remboursements) as client:
        connecter_admin(client)
        tid, poste_id = _poste_par_desinscription(client)
        client.put(
            f"/api/v1/tournois/{tid}/remboursements/{poste_id}", json={"statut": "rembourse"}
        )

        rejet = client.put(
            f"/api/v1/tournois/{tid}/remboursements/{poste_id}", json={"statut": "reporte"}
        )
        assert rejet.status_code == 409
        assert rejet.json()["code"] == "remboursement_deja_traite"


def test_marquer_inconnu_404(app_remboursements: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Traiter un remboursement inexistant → 404 `remboursement_introuvable`."""
    with TestClient(app_remboursements) as client:
        connecter_admin(client)
        tid = client.post(
            "/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14"}
        ).json()["id"]
        rejet = client.put(
            f"/api/v1/tournois/{tid}/remboursements/999", json={"statut": "rembourse"}
        )
        assert rejet.status_code == 404
        assert rejet.json()["code"] == "remboursement_introuvable"


def test_lister_tournoi_inconnu_404(
    app_remboursements: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Lister les remboursements d'un tournoi inexistant → 404 `tournoi_introuvable`."""
    with TestClient(app_remboursements) as client:
        connecter_admin(client)
        rejet = client.get("/api/v1/tournois/999/remboursements")
        assert rejet.status_code == 404
        assert rejet.json()["code"] == "tournoi_introuvable"


def test_lecture_sans_session_admin_401(app_remboursements: FastAPI) -> None:
    """Lire les remboursements sans être admin → 401 (montants non publics)."""
    with TestClient(app_remboursements) as client:
        rejet = client.get("/api/v1/tournois/1/remboursements")
    assert rejet.status_code == 401
