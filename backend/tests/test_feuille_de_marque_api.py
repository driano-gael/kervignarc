"""Test bout-en-bout de l'API de la feuille de marque (E09US001) — **câblage** de la route.

Traverse HTTP → `ServiceFeuilleDeMarque` → adapter ReportLab, après avoir peuplé un tournoi via les
endpoints existants et matérialisé le plan de cibles. La composition du document est déjà couverte
par `test_service_feuille_de_marque` (oracle du CA) et le rendu par le test de l'adapter ReportLab ;
ici on valide la route : réponse `application/pdf` téléchargeable, protection admin, mapping 404.
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
def app_feuille(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _preparer_depart_avec_plan(client: TestClient) -> tuple[int, int]:
    """Crée un tournoi complet (gabarit, catégorie, départ, deux archers) et matérialise le plan.

    Renvoie `(tournoi_id, depart_id)`."""
    tournoi = client.post("/api/v1/tournois", json={"nom": "Trophée", "date": "2026-03-14"})
    assert tournoi.status_code == 201, tournoi.text
    tournoi_id = int(tournoi.json()["id"])

    modele = client.post("/api/v1/gabarits", json={"nom": "Salle", "nb_cibles": 2})
    assert modele.status_code == 201, modele.text
    applique = client.put(
        f"/api/v1/tournois/{tournoi_id}/gabarit", json={"modele_id": modele.json()["id"]}
    )
    assert applique.status_code == 200, applique.text

    blason = client.post(
        f"/api/v1/tournois/{tournoi_id}/blasons",
        json={"nom": "Blason 40", "taille": 0.5, "capacite": 1},
    )
    assert blason.status_code == 201, blason.text
    categorie = client.post(
        f"/api/v1/tournois/{tournoi_id}/categories",
        json={"libelle": "Senior", "blason_id": blason.json()["id"], "hauteur_cm": 130},
    )
    assert categorie.status_code == 201, categorie.text
    categorie_id = int(categorie.json()["id"])

    depart = client.post(f"/api/v1/tournois/{tournoi_id}/departs", json={"tarif_centimes": 0})
    assert depart.status_code == 201, depart.text
    depart_id = int(depart.json()["id"])

    for prenom in ("Guillaume", "Walter"):
        archer = client.post(
            f"/api/v1/tournois/{tournoi_id}/archers",
            json={"nom": "Tell", "prenom": prenom, "categorie_id": categorie_id},
        )
        assert archer.status_code == 201, archer.text
        inscription = client.post(
            f"/api/v1/archers/{archer.json()['id']}/inscriptions", json={"depart_id": depart_id}
        )
        assert inscription.status_code == 201, inscription.text

    plan = client.post(
        f"/api/v1/tournois/{tournoi_id}/departs/{depart_id}/plan-de-cibles/regenerer"
    )
    assert plan.status_code == 200, plan.text
    return tournoi_id, depart_id


def test_telecharge_un_pdf(app_feuille: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """La route renvoie un PDF téléchargeable (`application/pdf` + `Content-Disposition`)."""
    with TestClient(app_feuille) as client:
        connecter_admin(client)
        tournoi_id, depart_id = _preparer_depart_avec_plan(client)
        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/departs/{depart_id}/feuille-de-marque")

    assert reponse.status_code == 200, reponse.text
    assert reponse.headers["content-type"] == "application/pdf"
    assert "attachment" in reponse.headers["content-disposition"]
    assert reponse.content.startswith(b"%PDF")


def test_sans_admin_refuse(app_feuille: FastAPI) -> None:
    """Route réservée à l'admin (E10US001) : sans session, 401."""
    with TestClient(app_feuille) as client:
        reponse = client.get("/api/v1/tournois/1/departs/1/feuille-de-marque")

    assert reponse.status_code == 401, reponse.text


def test_tournoi_inconnu_404(app_feuille: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_feuille) as client:
        connecter_admin(client)
        reponse = client.get("/api/v1/tournois/9999/departs/1/feuille-de-marque")

    assert reponse.status_code == 404, reponse.text


def test_depart_inconnu_404(app_feuille: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_feuille) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer_depart_avec_plan(client)
        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/departs/9999/feuille-de-marque")

    assert reponse.status_code == 404, reponse.text
