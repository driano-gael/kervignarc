"""Test bout-en-bout de l'API des **jalons « prêt à… »** (E16US012).

Écrit **après** l'implémentation (règle 9 : la frontière n'a pas d'oracle — la règle est prouvée au
domaine, `test_domain_jalon.py`, et l'agrégation au service, `test_service_jalons.py`). On vérifie
ici le structurel de l'endpoint : la **route unique paramétrée** rend bien deux membres différents,
la question voyage dans la réponse, la garde **admin** tient, et les trois mappings d'erreur
(tournoi inconnu → 404, membre non instruit → 404, segment hors famille → 400).
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


def _creer_tournoi(client: TestClient, connecter_admin: ConnecterAdmin) -> int:
    connecter_admin(client)
    reponse = client.post("/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14"})
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def test_le_jalon_demarrer_liste_ce_qui_manque_avant_le_clic(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un tournoi tout juste créé : aucun créneau, aucun déroulé — et **les deux se lisent d'un
    coup**, là où les gardes n'auraient rendu que la première à échouer."""
    with TestClient(app_session) as client:
        tournoi_id = _creer_tournoi(client, connecter_admin)

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/jalons/demarrer")

        assert reponse.status_code == 200, reponse.text
        corps = reponse.json()
        assert corps["jalon"] == "demarrer"
        assert corps["question"] == "Prêt à démarrer ?"
        assert [ligne["cle"] for ligne in corps["lignes"]] == ["creneaux", "effectif", "deroule"]
        assert corps["pret"] is False
        assert corps["bloquant"] is True


def test_le_jalon_terminer_rend_la_completude_sportive(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Même route, autre membre — et les lignes sont celles que l'écran de complétude rendait déjà.

    C'est le CA « sans doublonner » vérifié **au contrat** : si le jalon avait son propre calcul,
    ces clés pourraient diverger de `/completude` sans que rien ne le signale.
    """
    with TestClient(app_session) as client:
        tournoi_id = _creer_tournoi(client, connecter_admin)

        corps = client.get(f"/api/v1/tournois/{tournoi_id}/jalons/terminer").json()
        completude = client.get(f"/api/v1/tournois/{tournoi_id}/completude").json()

        assert corps["question"] == "Prêt à terminer ?"
        assert corps["lignes"] == completude["sportif"]
        assert corps["pret"] == completude["sportif_complet"]


def test_terminer_n_est_jamais_bloquant(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`D-15` au contrat : incomplet, mais l'action passe quand même."""
    with TestClient(app_session) as client:
        tournoi_id = _creer_tournoi(client, connecter_admin)

        corps = client.get(f"/api/v1/tournois/{tournoi_id}/jalons/terminer").json()

        assert corps["pret"] is False
        assert corps["bloquant"] is False


@pytest.mark.parametrize("jalon", ["archiver", "exporter"])
def test_un_membre_pas_encore_instruit_rend_404(
    app_session: FastAPI, connecter_admin: ConnecterAdmin, jalon: str
) -> None:
    """Plutôt qu'un 200 à liste vide, qui se lirait « rien ne manque, allez-y »."""
    with TestClient(app_session) as client:
        tournoi_id = _creer_tournoi(client, connecter_admin)

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/jalons/{jalon}")

        assert reponse.status_code == 404, reponse.text
        assert reponse.json()["code"] == "jalon_non_instruit"


def test_un_segment_hors_famille_rend_400(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """L'énumération du domaine sert de validation de chemin — pas de membre inventé.

    `400` et non `422` : le projet remappe `RequestValidationError` (cf. `api/erreurs.py`), une
    entrée invalide n'étant pas une règle métier violée.
    """
    with TestClient(app_session) as client:
        tournoi_id = _creer_tournoi(client, connecter_admin)

        assert client.get(f"/api/v1/tournois/{tournoi_id}/jalons/plier").status_code == 400


def test_les_jalons_exigent_l_admin(app_session: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_session) as client:
        tournoi_id = _creer_tournoi(client, connecter_admin)
        client.headers.pop("Authorization", None)

        assert client.get(f"/api/v1/tournois/{tournoi_id}/jalons/demarrer").status_code == 401


def test_un_tournoi_inconnu_rend_404(app_session: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_session) as client:
        connecter_admin(client)
        assert client.get("/api/v1/tournois/9999/jalons/demarrer").status_code == 404
