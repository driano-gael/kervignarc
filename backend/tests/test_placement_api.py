"""Test bout-en-bout de l'API du plan de cibles (E03US001).

Traverse toutes les couches en **lecture** — HTTP → `ServicePlacement` → moteur pur → repositories
— après avoir peuplé le tournoi via les endpoints existants (blason, catégorie, gabarit appliqué,
départ, archers, inscriptions). Vérifie la forme de la réponse et le **mapping des 404** (tournoi /
départ / gabarit absent). La logique de placement elle-même est couverte par `test_domain_placement`
et `test_service_placement` ; ici on valide le **câblage** de la route.
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
def app_placement(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _creer_tournoi(client: TestClient) -> int:
    reponse = client.post("/api/v1/tournois", json={"nom": "Trophée", "date": "2026-03-14"})
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def _appliquer_gabarit(client: TestClient, tournoi_id: int, nb_cibles: int) -> None:
    modele = client.post("/api/v1/gabarits", json={"nom": "Salle", "nb_cibles": nb_cibles})
    assert modele.status_code == 201, modele.text
    applique = client.put(
        f"/api/v1/tournois/{tournoi_id}/gabarit", json={"modele_id": modele.json()["id"]}
    )
    assert applique.status_code == 200, applique.text


def _creer_categorie(client: TestClient, tournoi_id: int) -> int:
    blason = client.post(
        f"/api/v1/tournois/{tournoi_id}/blasons",
        json={"nom": "Blason", "taille": 0.5, "capacite": 1},
    )
    assert blason.status_code == 201, blason.text
    categorie = client.post(
        f"/api/v1/tournois/{tournoi_id}/categories",
        json={"libelle": "Senior", "blason_id": blason.json()["id"], "hauteur_cm": 130},
    )
    assert categorie.status_code == 201, categorie.text
    return int(categorie.json()["id"])


def _creer_depart(client: TestClient, tournoi_id: int) -> int:
    reponse = client.post(f"/api/v1/tournois/{tournoi_id}/departs", json={"tarif_centimes": 0})
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def _inscrire_archer(
    client: TestClient, tournoi_id: int, categorie_id: int, depart_id: int, prenom: str
) -> int:
    # Prénoms distincts : deux archers de mêmes nom/prénom/club déclencheraient le garde-fou
    # homonyme (E02US002, 409), hors sujet ici.
    archer = client.post(
        f"/api/v1/tournois/{tournoi_id}/archers",
        json={"nom": "Tell", "prenom": prenom, "categorie_id": categorie_id},
    )
    assert archer.status_code == 201, archer.text
    archer_id = int(archer.json()["id"])
    inscription = client.post(
        f"/api/v1/archers/{archer_id}/inscriptions", json={"depart_id": depart_id}
    )
    assert inscription.status_code == 201, inscription.text
    return archer_id


def test_plan_de_cibles_place_les_inscrits(
    app_placement: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """GET renvoie le plan : les inscrits sont posés sur les cibles, sans conflit."""
    with TestClient(app_placement) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        _appliquer_gabarit(client, tournoi_id, nb_cibles=2)
        categorie_id = _creer_categorie(client, tournoi_id)
        depart_id = _creer_depart(client, tournoi_id)
        a1 = _inscrire_archer(client, tournoi_id, categorie_id, depart_id, prenom="Guillaume")
        a2 = _inscrire_archer(client, tournoi_id, categorie_id, depart_id, prenom="Walter")

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/departs/{depart_id}/plan-de-cibles")

    assert reponse.status_code == 200, reponse.text
    plan = reponse.json()
    assert plan["depart_id"] == depart_id
    assert len(plan["cibles"]) == 2
    places = {p["archer_id"] for cible in plan["cibles"] for p in cible["placements"]}
    assert places == {a1, a2}
    assert plan["conflits"] == []


def test_plan_de_cibles_tournoi_inconnu_404(
    app_placement: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un tournoi inexistant → 404."""
    with TestClient(app_placement) as client:
        connecter_admin(client)
        reponse = client.get("/api/v1/tournois/999999/departs/1/plan-de-cibles")
    assert reponse.status_code == 404, reponse.text


def test_plan_de_cibles_depart_inconnu_404(
    app_placement: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un départ inexistant dans un tournoi valide → 404."""
    with TestClient(app_placement) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        _appliquer_gabarit(client, tournoi_id, nb_cibles=1)
        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/departs/999999/plan-de-cibles")
    assert reponse.status_code == 404, reponse.text


def test_plan_de_cibles_sans_gabarit_404(
    app_placement: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Sans gabarit appliqué au tournoi, pas de cible → 404 `gabarit_du_tournoi_absent`."""
    with TestClient(app_placement) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        depart_id = _creer_depart(client, tournoi_id)
        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/departs/{depart_id}/plan-de-cibles")
    assert reponse.status_code == 404, reponse.text
    assert reponse.json()["code"] == "gabarit_du_tournoi_absent"
