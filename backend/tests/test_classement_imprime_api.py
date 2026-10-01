"""Test bout-en-bout du classement de qualification imprimable (E09US005).

Traverse les couches — HTTP → `ServiceClassementImprime` → `ServiceClassement` → repositories —
sur une base migrée. Tests **après** l'implémentation (frontière API et câblage, règle 9) : la
règle métier est couverte par `test_domain_classement_imprime` et `test_service_classement_imprime`.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from tests.base_migree import preparer_base
from tests.conftest import ConnecterAdmin
from tests.test_placement_api import _appliquer_gabarit, _creer_tournoi
from tests.test_placement_duels_api import _quatre_archers_classes


@pytest.fixture
def app_classement(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    preparer_base(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _preparer(app: FastAPI, client: TestClient) -> int:
    tournoi_id = _creer_tournoi(client)
    _appliquer_gabarit(client, tournoi_id, nb_cibles=2)
    _quatre_archers_classes(app, client, tournoi_id)
    return tournoi_id


def _chemin(tournoi_id: int) -> str:
    return f"/api/v1/tournois/{tournoi_id}/classement-qualification/document"


def test_le_pdf_sort_sans_authentification(
    app_classement: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_classement) as client:
        connecter_admin(client)
        tournoi_id = _preparer(app_classement, client)
        client.cookies.clear()

        reponse = client.get(_chemin(tournoi_id))

    assert reponse.status_code == 200, reponse.text
    assert reponse.headers["content-type"] == "application/pdf"
    assert "inline" in reponse.headers["content-disposition"]
    assert reponse.content.startswith(b"%PDF")


def test_le_csv_rend_une_ligne_par_archer_classe(
    app_classement: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_classement) as client:
        connecter_admin(client)
        tournoi_id = _preparer(app_classement, client)

        reponse = client.get(_chemin(tournoi_id), params={"format": "csv"})

    assert reponse.status_code == 200, reponse.text
    assert "attachment" in reponse.headers["content-disposition"]
    lignes = reponse.content.decode("utf-8-sig").splitlines()
    assert lignes[0] == (
        "Départ;Catégorie;Rang catégorie;Rang général;Nom;Prénom;Club;Total;10;9;Statut;Classement"
    )
    assert len(lignes) == 1 + 4


def test_le_xlsx_rend_un_classeur(app_classement: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_classement) as client:
        connecter_admin(client)
        tournoi_id = _preparer(app_classement, client)

        reponse = client.get(_chemin(tournoi_id), params={"format": "xlsx"})

    assert reponse.status_code == 200, reponse.text
    assert reponse.content[:2] == b"PK"


def test_un_depart_inconnu_rend_404(
    app_classement: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_classement) as client:
        connecter_admin(client)
        tournoi_id = _preparer(app_classement, client)

        reponse = client.get(_chemin(tournoi_id), params={"depart_id": 9999})

    assert reponse.status_code == 404, reponse.text


def test_un_tournoi_inconnu_rend_404(app_classement: FastAPI) -> None:
    with TestClient(app_classement) as client:
        reponse = client.get(_chemin(9999))

    assert reponse.status_code == 404, reponse.text


def test_le_catalogue_annonce_les_trois_formats(
    app_classement: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_classement) as client:
        connecter_admin(client)
        reponse = client.get("/api/v1/exports")

    assert reponse.status_code == 200, reponse.text
    entrees = {entree["identifiant"]: entree for entree in reponse.json()}
    assert [f["code"] for f in entrees["classement-qualification"]["formats"]] == [
        "pdf",
        "csv",
        "xlsx",
    ]
