"""Test bout-en-bout de l'API du palmarès (E06US004).

Traverse les couches — HTTP → `ServicePalmares` → classement + saisie de duels → repositories —
après avoir peuplé un tournoi (gabarit, catégorie, départ, 4 archers **classés**) et une phase
d'élimination directe. Vérifie le **câblage** : la route rend le classement final, le filtre par
catégorie passe, l'export PDF sort un vrai document, et les deux se lisent **sans
authentification** (contrat de lecture publique, E10US001).

La règle métier est couverte par `test_service_palmares` et `test_domain_palmares` — tests écrits,
eux, **depuis le CA** (règle 9) ; ceux-ci le sont après l'implémentation, il n'y a pas d'oracle en
jeu à cette couche.
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
from tests.test_placement_duels_api import _phase_elimination, _quatre_archers_classes


@pytest.fixture
def app_palmares(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    preparer_base(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _preparer(app: FastAPI, client: TestClient) -> tuple[int, list[int]]:
    """Tournoi peuplé (gabarit, 4 archers classés, phase de tableau) avec le plan de duels posé."""
    tournoi_id = _creer_tournoi(client)
    _appliquer_gabarit(client, tournoi_id, nb_cibles=2)
    archers = _quatre_archers_classes(app, client, tournoi_id)
    phase_id = _phase_elimination(app, tournoi_id)
    regen = client.post(f"/api/v1/tournois/{tournoi_id}/phases/{phase_id}/plan-de-duels/regenerer")
    assert regen.status_code == 200, regen.text
    return tournoi_id, archers


def test_le_palmares_rend_une_ligne_par_archer_avec_ses_deux_rangs(
    app_palmares: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Câblage : une ligne par archer du tournoi, rangs scratch et catégorie, origine renseignée."""
    with TestClient(app_palmares) as client:
        connecter_admin(client)
        tournoi_id, archers = _preparer(app_palmares, client)

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/palmares")

    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["tournoi_id"] == tournoi_id
    assert {ligne["archer_id"] for ligne in corps["lignes"]} == set(archers)
    for ligne in corps["lignes"]:
        assert ligne["rang_min"] is not None and ligne["rang_max"] is not None
        assert ligne["rang_categorie_min"] is not None
        assert ligne["origine"] in {"duels", "qualification"}
        assert ligne["statut"] == "en_lice"
        assert ligne["nom"] != ""


def test_les_podiums_sortent_par_categorie(
    app_palmares: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le DTO porte un podium **par catégorie** : c'est là que se remettent les médailles.

    Aucun duel n'étant tranché, les quatre archers sont encore en lice et **aucun** rang n'est
    décerné : le podium est vide, mais la catégorie est bien listée. C'est la lecture au fil de
    l'eau — l'écran affiche la catégorie et dira « en cours », pas « catégorie absente ».
    """
    with TestClient(app_palmares) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer(app_palmares, client)

        corps = client.get(f"/api/v1/tournois/{tournoi_id}/palmares").json()

    assert len(corps["podiums"]) == 1
    assert corps["podiums"][0]["categorie_libelle"] != ""
    assert corps["podiums"][0]["lignes"] == []


def test_le_filtre_par_categorie_est_transmis(
    app_palmares: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`categorie_id` traverse jusqu'au service : une catégorie inconnue rend un palmarès vide."""
    with TestClient(app_palmares) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer(app_palmares, client)

        reponse = client.get(
            f"/api/v1/tournois/{tournoi_id}/palmares", params={"categorie_id": 9999}
        )

    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["lignes"] == []


def test_tournoi_inconnu_rend_404(app_palmares: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """`TournoiIntrouvable` est traduit à la frontière, comme pour le classement."""
    with TestClient(app_palmares) as client:
        connecter_admin(client)
        _preparer(app_palmares, client)

        reponse = client.get("/api/v1/tournois/9999/palmares")

    assert reponse.status_code == 404, reponse.text


def test_l_export_pdf_rend_un_document(
    app_palmares: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA « exportable » : un vrai PDF, servi `inline` pour être ouvert puis imprimé."""
    with TestClient(app_palmares) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer(app_palmares, client)

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/palmares.pdf")

    assert reponse.status_code == 200, reponse.text
    assert reponse.headers["content-type"] == "application/pdf"
    assert "inline" in reponse.headers["content-disposition"]
    assert reponse.content.startswith(b"%PDF")


def test_lecture_publique_sans_authentification(
    app_palmares: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Contrat E10US001 : le palmarès se lit **sans jeton** — il finit sur l'écran de salle et sur
    le téléphone du public, qui n'ont pas de session."""
    with TestClient(app_palmares) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer(app_palmares, client)
        client.cookies.clear()

        json = client.get(f"/api/v1/tournois/{tournoi_id}/palmares")
        pdf = client.get(f"/api/v1/tournois/{tournoi_id}/palmares.pdf")

    assert json.status_code == 200, json.text
    assert pdf.status_code == 200, pdf.text
