"""Test bout-en-bout du déroulé horaire imprimable (E09US007).

HTTP → `ServiceDerouleImprime` → `ServicePhases` → repositories, sur une base migrée. Tests
**après** l'implémentation (frontière API et câblage, règle 9) : la règle métier est couverte par
`test_domain_deroule_imprime` et `test_service_deroule_imprime`.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from domain.horaire_prevu import HeurePrevue
from tests.base_migree import preparer_base
from tests.conftest import ConnecterAdmin
from tests.test_placement_api import _creer_tournoi


@pytest.fixture
def app_deroule(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    preparer_base(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _chemin(tournoi_id: int) -> str:
    return f"/api/v1/tournois/{tournoi_id}/deroule-horaire/document"


def _preparer(client: TestClient) -> tuple[int, int]:
    """Un tournoi, un créneau à 09:00, un déroulé qualification (90 min) → tableau."""
    tournoi_id = _creer_tournoi(client)
    depart = client.post(
        f"/api/v1/tournois/{tournoi_id}/departs", json={"horaire": "09:00", "tarif_centimes": 800}
    ).json()
    base = f"/api/v1/tournois/{tournoi_id}/phases"
    qualif = client.post(base, json={"type": "qualification", "duree_prevue": 90}).json()
    client.post(
        base,
        json={
            "type": "elimination_directe",
            "sources": [{"etape_source_id": qualif["id"], "rang_debut": 1, "rang_fin": 8}],
        },
    )
    return tournoi_id, depart["id"]


def test_le_pdf_sort_sans_authentification(
    app_deroule: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_deroule) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer(client)
        client.headers.pop("Authorization", None)
        client.cookies.clear()

        reponse = client.get(_chemin(tournoi_id))

    assert reponse.status_code == 200, reponse.text
    assert reponse.headers["content-type"] == "application/pdf"
    assert "inline" in reponse.headers["content-disposition"]
    assert reponse.content.startswith(b"%PDF")


def test_le_cablage_lit_le_deroule_et_les_heures_persistes(
    app_deroule: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le document servi est bien bâti sur les repositories réels — pas sur un décor vide."""
    with TestClient(app_deroule) as client:
        connecter_admin(client)
        tournoi_id, depart_id = _preparer(client)

        document = app_deroule.state.service_deroule_imprime.document(tournoi_id, depart_id)

    (bloc,) = document.blocs
    assert bloc.libelle.endswith("09:00")
    assert [(ligne.debut, ligne.fin) for ligne in bloc.lignes] == [
        (HeurePrevue(9 * 60), HeurePrevue(10 * 60 + 30)),
        (HeurePrevue(10 * 60 + 30), None),
    ]


def test_un_autre_format_que_le_pdf_est_refuse(
    app_deroule: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_deroule) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer(client)

        reponse = client.get(_chemin(tournoi_id), params={"format": "csv"})

    assert reponse.status_code == 400, reponse.text
    assert reponse.json()["code"] == "format_export_indisponible"


def test_le_depart_d_un_autre_tournoi_rend_404(
    app_deroule: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_deroule) as client:
        connecter_admin(client)
        _, depart_id = _preparer(client)
        autre_id, _ = _preparer(client)

        reponse = client.get(_chemin(autre_id), params={"depart_id": depart_id})

    assert reponse.status_code == 404, reponse.text


def test_un_tournoi_sans_creneau_rend_409(
    app_deroule: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_deroule) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        reponse = client.get(_chemin(tournoi_id))

    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["code"] == "tournoi_sans_depart"


def test_un_tournoi_inconnu_rend_404(app_deroule: FastAPI) -> None:
    with TestClient(app_deroule) as client:
        reponse = client.get(_chemin(9999))

    assert reponse.status_code == 404, reponse.text
