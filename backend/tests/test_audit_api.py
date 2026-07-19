"""Test bout-en-bout de l'API de consultation du journal d'audit (E10US005, socle).

Traverse les couches de **lecture** — endpoint → service → repository → DB — et vérifie : la
consultation renvoie les entrées d'un tournoi en ordre chronologique avec tous leurs champs, la
route est **réservée à l'admin** (401 sans session), et un tournoi inconnu répond 404.

Il n'y a **pas d'endpoint d'écriture** (les entrées naissent d'un acte métier, E04US002/E12US004) :
le test **ensemence** directement via `ServiceAudit.consigner` — la primitive du socle — avant de
consulter par l'API. L'horodatage vient de l'horloge système câblée : on n'en vérifie que la
présence (ISO), pas la valeur (le déterminisme de l'horloge est couvert côté service).
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
from domain.entree_audit import ActionAuditee
from tests.conftest import ConnecterAdmin

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


@pytest.fixture
def app_audit(tmp_path: Path) -> Iterator[FastAPI]:
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


def test_consultation_liste_les_entrees(
    app_audit: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Les entrées ensemencées par `consigner` sont consultables, en ordre chronologique."""
    with TestClient(app_audit) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        service = app_audit.state.service_audit
        service.consigner(tournoi_id, ActionAuditee.VALIDATION, "DURAND Jean", "Série 1 — cible 4A")
        service.consigner(
            tournoi_id,
            ActionAuditee.CORRECTION_SCORE,
            "ROUX Sophie",
            "Série 1, flèche 2",
            avant="8",
            apres="9",
        )

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/audit")

        assert reponse.status_code == 200, reponse.text
        entrees = reponse.json()
        assert [e["action"] for e in entrees] == ["validation", "correction_score"]
        assert [e["auteur"] for e in entrees] == ["DURAND Jean", "ROUX Sophie"]
        validation, correction = entrees
        assert validation["objet"] == "Série 1 — cible 4A"
        assert (validation["avant"], validation["apres"]) == (None, None)
        assert (correction["avant"], correction["apres"]) == ("8", "9")
        assert isinstance(validation["horodatage"], str) and validation["horodatage"]


def test_consultation_vide_sans_entree(app_audit: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_audit) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/audit")

        assert reponse.status_code == 200, reponse.text
        assert reponse.json() == []


def test_consultation_reservee_a_l_admin(app_audit: FastAPI) -> None:
    """Un journal de litiges n'est pas public : 401 sans session admin (E10US001 n'ouvre pas ça)."""
    with TestClient(app_audit) as client:
        reponse = client.get("/api/v1/tournois/1/audit")

        assert reponse.status_code == 401, reponse.text


def test_consultation_tournoi_inconnu_rend_404(
    app_audit: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un tournoi inconnu → 404 (et non une liste vide qui ferait croire « rien à signaler »)."""
    with TestClient(app_audit) as client:
        connecter_admin(client)

        reponse = client.get("/api/v1/tournois/404/audit")

        assert reponse.status_code == 404, reponse.text
        assert reponse.json()["code"] == "tournoi_introuvable"
