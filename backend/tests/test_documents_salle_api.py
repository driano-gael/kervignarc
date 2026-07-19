"""Test bout-en-bout de l'API des documents de salle (E09US008) — **câblage** des routes.

Traverse HTTP → `ServiceDocumentsSalle` → adapter ReportLab, après avoir peuplé un tournoi via les
endpoints existants (gabarit + préparation des postes pour les cibles, création de scoreurs). La
composition des documents est déjà couverte par `test_service_documents_salle` (oracle du CA) et le
rendu par le test de l'adapter ReportLab ; ici on valide les routes : réponse `application/pdf`
téléchargeable, protection admin, mapping 404.
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
def app_salle(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _preparer_tournoi_avec_cibles_et_scoreurs(client: TestClient) -> int:
    """Crée un tournoi, applique un gabarit à 2 cibles, prépare les codes de poste et 2 scoreurs.

    Renvoie `tournoi_id`."""
    tournoi = client.post("/api/v1/tournois", json={"nom": "Trophée", "date": "2026-03-14"})
    assert tournoi.status_code == 201, tournoi.text
    tournoi_id = int(tournoi.json()["id"])

    modele = client.post("/api/v1/gabarits", json={"nom": "Salle", "nb_cibles": 2})
    assert modele.status_code == 201, modele.text
    applique = client.put(
        f"/api/v1/tournois/{tournoi_id}/gabarit", json={"modele_id": modele.json()["id"]}
    )
    assert applique.status_code == 200, applique.text

    # Prépare un code par cible (E04US001) — sans quoi il n'y a rien à imprimer.
    prepare = client.post(f"/api/v1/tournois/{tournoi_id}/postes")
    assert prepare.status_code == 200, prepare.text
    assert len(prepare.json()) == 2

    for nom in ("Alice", "Bob"):
        scoreur = client.post(f"/api/v1/tournois/{tournoi_id}/scoreurs", json={"nom": nom})
        assert scoreur.status_code == 201, scoreur.text

    return tournoi_id


def test_etiquettes_qr_telecharge_un_pdf(
    app_salle: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La route renvoie un PDF téléchargeable (`application/pdf` + `Content-Disposition`)."""
    with TestClient(app_salle) as client:
        connecter_admin(client)
        tournoi_id = _preparer_tournoi_avec_cibles_et_scoreurs(client)
        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/postes/etiquettes-qr")

    assert reponse.status_code == 200, reponse.text
    assert reponse.headers["content-type"] == "application/pdf"
    assert "attachment" in reponse.headers["content-disposition"]
    assert reponse.content.startswith(b"%PDF")


def test_cartes_scoreurs_telecharge_un_pdf(
    app_salle: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_salle) as client:
        connecter_admin(client)
        tournoi_id = _preparer_tournoi_avec_cibles_et_scoreurs(client)
        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/scoreurs/cartes-codes")

    assert reponse.status_code == 200, reponse.text
    assert reponse.headers["content-type"] == "application/pdf"
    assert "attachment" in reponse.headers["content-disposition"]
    assert reponse.content.startswith(b"%PDF")


def test_etiquettes_qr_sans_admin_refuse(app_salle: FastAPI) -> None:
    """Route réservée à l'admin (codes = secrets d'usage) : sans session, 401."""
    with TestClient(app_salle) as client:
        reponse = client.get("/api/v1/tournois/1/postes/etiquettes-qr")

    assert reponse.status_code == 401, reponse.text


def test_cartes_scoreurs_sans_admin_refuse(app_salle: FastAPI) -> None:
    with TestClient(app_salle) as client:
        reponse = client.get("/api/v1/tournois/1/scoreurs/cartes-codes")

    assert reponse.status_code == 401, reponse.text


def test_etiquettes_qr_tournoi_inconnu_404(
    app_salle: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_salle) as client:
        connecter_admin(client)
        reponse = client.get("/api/v1/tournois/9999/postes/etiquettes-qr")

    assert reponse.status_code == 404, reponse.text


def test_cartes_scoreurs_tournoi_inconnu_404(
    app_salle: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_salle) as client:
        connecter_admin(client)
        reponse = client.get("/api/v1/tournois/9999/scoreurs/cartes-codes")

    assert reponse.status_code == 404, reponse.text
