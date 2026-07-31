"""Test bout-en-bout de l'API des listes imprimables (E09US003) — **câblage** des routes.

Traverse HTTP → `ServiceListesImpression` → adapter ReportLab, après avoir peuplé un tournoi via les
endpoints existants (club, catégorie, départ, archers inscrits, plan matérialisé). La composition du
contenu est déjà couverte par `test_service_listes_impression` (oracle du CA) et le rendu par le
test de l'adapter ReportLab ; ici on valide les routes : réponse `application/pdf` téléchargeable,
paramètres `tri`/`depart_id`, protection admin, mapping 404.
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

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _migrer(url: str) -> None:
    preparer_base(url)


@pytest.fixture
def app_listes(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _preparer_tournoi(client: TestClient) -> tuple[int, int]:
    """Crée un tournoi complet (gabarit, club, catégorie, départ, deux archers inscrits) et
    matérialise le plan. Renvoie `(tournoi_id, depart_id)`."""
    tournoi = client.post("/api/v1/tournois", json={"nom": "Trophée", "date": "2026-03-14"})
    assert tournoi.status_code == 201, tournoi.text
    tournoi_id = int(tournoi.json()["id"])

    modele = client.post("/api/v1/gabarits", json={"nom": "Salle", "nb_cibles": 2})
    assert modele.status_code == 201, modele.text
    applique = client.put(
        f"/api/v1/tournois/{tournoi_id}/gabarit", json={"modele_id": modele.json()["id"]}
    )
    assert applique.status_code == 200, applique.text

    club = client.post("/api/v1/clubs", json={"nom": "Arcs de Test"})
    assert club.status_code == 201, club.text
    club_id = int(club.json()["id"])

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

    depart = client.post(
        f"/api/v1/tournois/{tournoi_id}/departs", json={"tarif_centimes": 800, "horaire": "09:00"}
    )
    assert depart.status_code == 201, depart.text
    depart_id = int(depart.json()["id"])

    for prenom, avec_club in (("Guillaume", True), ("Walter", False)):
        corps = {"nom": "Tell", "prenom": prenom, "categorie_id": categorie_id}
        if avec_club:
            corps["club_id"] = club_id
        archer = client.post(f"/api/v1/tournois/{tournoi_id}/archers", json=corps)
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


def test_placement_telecharge_un_pdf(app_listes: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """La liste de placement renvoie un PDF téléchargeable (`application/pdf` + attachment)."""
    with TestClient(app_listes) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer_tournoi(client)
        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/listes/placement")

    assert reponse.status_code == 200, reponse.text
    assert reponse.headers["content-type"] == "application/pdf"
    assert "attachment" in reponse.headers["content-disposition"]
    assert reponse.content.startswith(b"%PDF")


def test_placement_accepte_tri_et_filtre_depart(
    app_listes: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Les paramètres `tri=nom` et `depart_id` sont acceptés et renvoient un PDF."""
    with TestClient(app_listes) as client:
        connecter_admin(client)
        tournoi_id, depart_id = _preparer_tournoi(client)
        reponse = client.get(
            f"/api/v1/tournois/{tournoi_id}/listes/placement",
            params={"tri": "nom", "depart_id": depart_id},
        )

    assert reponse.status_code == 200, reponse.text
    assert reponse.headers["content-type"] == "application/pdf"
    assert f"depart-{depart_id}" in reponse.headers["content-disposition"]


def test_placement_tri_invalide_rejete(
    app_listes: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un `tri` hors des valeurs admises est rejeté par la validation (400 `requete_invalide`,
    mapping du projet à la frontière — `api/erreurs.py`)."""
    with TestClient(app_listes) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer_tournoi(client)
        reponse = client.get(
            f"/api/v1/tournois/{tournoi_id}/listes/placement", params={"tri": "hasard"}
        )

    assert reponse.status_code == 400, reponse.text
    assert reponse.json()["code"] == "requete_invalide"


def test_club_paiement_telecharge_un_pdf(
    app_listes: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La liste club & paiement renvoie un PDF téléchargeable."""
    with TestClient(app_listes) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer_tournoi(client)
        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/listes/club-paiement")

    assert reponse.status_code == 200, reponse.text
    assert reponse.headers["content-type"] == "application/pdf"
    assert "attachment" in reponse.headers["content-disposition"]
    assert reponse.content.startswith(b"%PDF")


def test_sans_admin_refuse(app_listes: FastAPI) -> None:
    """Routes réservées à l'admin (E10US001) : sans session, 401."""
    with TestClient(app_listes) as client:
        placement = client.get("/api/v1/tournois/1/listes/placement")
        club = client.get("/api/v1/tournois/1/listes/club-paiement")

    assert placement.status_code == 401, placement.text
    assert club.status_code == 401, club.text


def test_placement_tournoi_inconnu_404(
    app_listes: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_listes) as client:
        connecter_admin(client)
        reponse = client.get("/api/v1/tournois/9999/listes/placement")

    assert reponse.status_code == 404, reponse.text


def test_placement_depart_inconnu_404(app_listes: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_listes) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer_tournoi(client)
        reponse = client.get(
            f"/api/v1/tournois/{tournoi_id}/listes/placement", params={"depart_id": 9999}
        )

    assert reponse.status_code == 404, reponse.text


def test_club_paiement_tournoi_inconnu_404(
    app_listes: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_listes) as client:
        connecter_admin(client)
        reponse = client.get("/api/v1/tournois/9999/listes/club-paiement")

    assert reponse.status_code == 404, reponse.text
