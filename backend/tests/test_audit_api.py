"""Test bout-en-bout de l'API de consultation du journal d'audit (E10US005, socle).

Traverse les couches de **lecture** — endpoint → service → repository → DB — et vérifie : la
consultation renvoie les entrées d'un tournoi en ordre chronologique avec tous leurs champs, la
route est **réservée à l'admin** (401 sans session), et un tournoi inconnu répond 404.

Il n'y a **pas d'endpoint d'écriture** : les entrées naissent d'un acte métier
(E04US002 la validation, E04US015 le forfait) — le test **ensemence** donc directement via
`ServiceAudit.consigner` — la primitive du socle — avant de
consulter par l'API. L'horodatage vient de l'horloge système câblée : on n'en vérifie que la
présence (ISO), pas la valeur (le déterminisme de l'horloge est couvert côté service).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from domain.entree_audit import ActionAuditee
from tests.base_migree import preparer_base
from tests.conftest import ConnecterAdmin

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _migrer(url: str) -> None:
    preparer_base(url)


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


# --- E16US016 : l'export du journal --------------------------------------------------------------
#
# Tests écrits **après** l'implémentation : c'est de la frontière API et du câblage, il n'y a pas
# d'oracle en jeu (règle 9). Ce qu'ils couvrent et qu'aucun test de service ne voit : la route est
# montée, le type MIME et l'extension dérivent du même format, et la garde admin est bien posée.

_CSV = "text/csv"
_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _tournoi_avec_deux_traces(app: FastAPI, client: TestClient) -> int:
    tournoi_id = _creer_tournoi(client)
    service = app.state.service_audit
    service.consigner(tournoi_id, ActionAuditee.VALIDATION, "DURAND Jean", "Série 1 — cible 4A")
    service.consigner(
        tournoi_id,
        ActionAuditee.CORRECTION_SCORE,
        "ROUX Sophie",
        "Série 1, f2",
        avant="8",
        apres="9",
    )
    return tournoi_id


def test_l_export_rend_un_csv_lisible_par_un_tableur(
    app_audit: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Défaut CSV, BOM et point-virgule (ADR-0101 §4) — sinon le fichier s'ouvre en bouillie."""
    with TestClient(app_audit) as client:
        connecter_admin(client)
        tournoi_id = _tournoi_avec_deux_traces(app_audit, client)

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/audit/document")

        assert reponse.status_code == 200, reponse.text
        assert reponse.headers["content-type"].startswith(_CSV)
        # ⚠️ `nosniff` **et** le type qu'il verrouille : l'en-tête seul ne veut rien dire.
        assert reponse.headers["x-content-type-options"] == "nosniff"
        assert 'filename="audit-' in reponse.headers["content-disposition"]
        texte = reponse.content.decode("utf-8-sig")
        assert "Horodatage;Auteur;Action;Objet;Avant;Après" in texte
        # ⚠️ « Correction » et non le slug `correction_score` : depuis la revue, l'export
        # nomme l'acte comme l'écran (règle 3) — l'organisateur comparait deux vocabulaires.
        assert "ROUX Sophie;Correction;Série 1, f2;8;9" in texte


def test_l_export_xlsx_rend_un_classeur(
    app_audit: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """L'extension **et** le type MIME viennent du même format (point unique, ADR-0101)."""
    with TestClient(app_audit) as client:
        connecter_admin(client)
        tournoi_id = _tournoi_avec_deux_traces(app_audit, client)

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/audit/document?format=xlsx")

        assert reponse.status_code == 200, reponse.text
        assert reponse.headers["content-type"].startswith(_XLSX)
        assert f'filename="audit-{tournoi_id}.xlsx"' in reponse.headers["content-disposition"]
        # Un `.xlsx` est un ZIP : les deux premiers octets le disent sans ouvrir openpyxl.
        assert reponse.content[:2] == b"PK"


def test_l_export_refuse_un_format_non_cable(
    app_audit: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le PDF n'est pas câblé pour ce document : 400 explicite, jamais un fichier vide."""
    with TestClient(app_audit) as client:
        connecter_admin(client)
        tournoi_id = _tournoi_avec_deux_traces(app_audit, client)

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/audit/document?format=pdf")

        assert reponse.status_code == 400, reponse.text


def test_l_export_est_reserve_a_l_admin(app_audit: FastAPI) -> None:
    """Même garde que la consultation : un journal de litiges ne s'ouvre pas au public (ADR-0050).

    ⚠️ **Aucune connexion du tout**, et c'est le point : `connecter_admin` pose un en-tête
    `Authorization`, que `client.cookies.clear()` ne retire pas. Un test de 401 écrit avec ce
    geste reste vert **la garde retirée** — le défaut relevé en revue d'`E16US007`.
    """
    with TestClient(app_audit) as client:
        reponse = client.get("/api/v1/tournois/1/audit/document")

        assert reponse.status_code == 401, reponse.text


def test_l_export_d_un_tournoi_inconnu_rend_404(
    app_audit: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_audit) as client:
        connecter_admin(client)

        reponse = client.get("/api/v1/tournois/404/audit/document")

        assert reponse.status_code == 404, reponse.text
