"""Test bout-en-bout de l'endpoint de suivi du déroulé (E07US004) — écrit **après** l'impl.

Ce qui se vérifie ici est propre à la frontière :

- la **lecture est publique** (l'écran de salle est public, il ne porte aucun jeton admin) ;
- rien de sensible ne transite (ni nom, ni code de poste, ni donnée de paiement) ;
- la forme des blocs est **celle du diagnostic d'atelier** (E01US024), plus un calque `avancement` —
  c'est ce qui permet au front de n'avoir qu'un seul composant de dessin ;
- un tournoi sans phase répond, il ne casse pas.
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


@pytest.fixture
def app_session(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    preparer_base(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _tournoi(client: TestClient, connecter_admin: ConnecterAdmin) -> int:
    connecter_admin(client)
    return int(
        client.post("/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14"}).json()[
            "id"
        ]
    )


def _depart(client: TestClient, tournoi_id: int) -> int:
    """Le créneau porteur de la séquence (ADR-0075) — les phases y pendent, pas au tournoi."""
    reponse = client.post(
        f"/api/v1/tournois/{tournoi_id}/departs",
        json={"horaire": "09:00", "tarif_centimes": 800},
    )
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def test_un_tournoi_sans_phase_repond_un_suivi_vide(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Avant qu'un format soit appliqué, il n'y a rien à suivre — ce n'est pas une erreur."""
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/suivi-deroule")

        assert reponse.status_code == 200, reponse.text
        assert reponse.json() == {
            "effectif": 0,
            "ordre_courant": None,
            "blocs": [],
            "avancement": [],
        }


def test_le_suivi_est_une_lecture_publique(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """L'écran de salle n'a pas de jeton admin : sans lecture publique, il n'affiche rien."""
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)

    with TestClient(app_session) as anonyme:
        reponse = anonyme.get(f"/api/v1/tournois/{tournoi_id}/suivi-deroule")

    assert reponse.status_code == 200, reponse.text


def test_un_tournoi_inconnu_est_un_404(app_session: FastAPI) -> None:
    with TestClient(app_session) as client:
        reponse = client.get("/api/v1/tournois/9999/suivi-deroule")

        assert reponse.status_code == 404
        assert reponse.json()["code"] == "tournoi_introuvable"


def test_les_phases_apparaissent_avec_leur_statut(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le calque `avancement` s'apparie aux `blocs` par `ordre` — la clé du dessin superposé."""
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        depart_id = _depart(client, tournoi_id)
        creation = client.post(
            f"/api/v1/tournois/{depart_id}/phases", json={"type": "placement", "effectif": 8}
        )
        assert creation.status_code == 201, creation.text

        corps = client.get(f"/api/v1/tournois/{tournoi_id}/suivi-deroule").json()

        assert [bloc["ordre"] for bloc in corps["blocs"]] == [1]
        assert [av["ordre"] for av in corps["avancement"]] == [1]
        assert corps["avancement"][0]["statut"] == "a_venir"
        assert corps["avancement"][0]["tour_courant"] is None
        assert corps["ordre_courant"] is None
        # Les braquets sont dessinés (« duels attendus ») alors que rien n'est joué : c'est
        # exactement le CA — le schéma existe d'abord, il se **remplit** ensuite.
        assert corps["avancement"][0]["duels_attendus"] == 7
        assert corps["avancement"][0]["duels_joues"] == 0
        assert [tour["duels"] for tour in corps["blocs"][0]["tours"]] == [4, 2, 1]
