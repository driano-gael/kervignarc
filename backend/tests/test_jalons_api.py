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


def _lancer(client: TestClient, tournoi_id: int) -> None:
    """Amène le tournoi jusqu'à *en cours* — le seul statut d'où « terminer » est offert.

    Sans créneau, `vers_pret` refuse (E02US010) : c'est la garde que le jalon *démarrer* énumère,
    et elle sert ici de décor. Aucun déroulé composé, donc aucun effectif exigé.
    """
    pose = client.post(
        f"/api/v1/tournois/{tournoi_id}/departs",
        json={"numero": 1, "distance_cm": 1800, "horaire": "09:00", "tarif_centimes": 1200},
    )
    assert pose.status_code == 201, pose.text
    assert client.post(f"/api/v1/tournois/{tournoi_id}/vers-pret").status_code == 200
    assert client.post(f"/api/v1/tournois/{tournoi_id}/demarrer").status_code == 200


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
        # Le refus tombera **dès** « Marquer prêt » : c'est la garde des créneaux qui manque.
        assert corps["moment"] == "dès le passage en « prêt »"
        assert "aucun départ" in corps["detail"]


def test_le_jalon_terminer_rend_la_completude_sportive(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Même route, autre membre — et les lignes sont celles que l'écran de complétude rendait déjà.

    C'est le CA « sans doublonner » vérifié **au contrat** : si le jalon avait son propre calcul,
    ces clés pourraient diverger de `/completude` sans que rien ne le signale.
    """
    with TestClient(app_session) as client:
        tournoi_id = _creer_tournoi(client, connecter_admin)
        _lancer(client, tournoi_id)

        corps = client.get(f"/api/v1/tournois/{tournoi_id}/jalons/terminer").json()
        completude = client.get(f"/api/v1/tournois/{tournoi_id}/completude").json()

        assert corps["question"] == "Prêt à terminer ?"
        assert corps["lignes"] == completude["sportif"]
        assert corps["pret"] == completude["sportif_complet"]


def test_terminer_n_est_jamais_bloquant_pendant_le_tournoi(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`D-15` au contrat : incomplet, mais l'action passe quand même.

    ⚠️ **Sur un tournoi en cours.** La première version posait la question sur un tournoi en
    *brouillon*, où terminer est en réalité refusé (`TransitionStatutInvalide`) : le test épinglait
    donc un « rien ne vous en empêchera » faux (relevé en revue, axe D).
    """
    with TestClient(app_session) as client:
        tournoi_id = _creer_tournoi(client, connecter_admin)
        _lancer(client, tournoi_id)

        corps = client.get(f"/api/v1/tournois/{tournoi_id}/jalons/terminer").json()

        assert corps["pret"] is False
        assert corps["bloquant"] is False


def test_terminer_hors_du_tournoi_en_cours_annonce_le_refus(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La garde de statut au contrat : sur un brouillon, terminer **sera** refusé."""
    with TestClient(app_session) as client:
        tournoi_id = _creer_tournoi(client, connecter_admin)

        corps = client.get(f"/api/v1/tournois/{tournoi_id}/jalons/terminer").json()

        assert corps["bloquant"] is True
        # Contenu, pas simple présence : c'est le contrat que liront `E16US007` et `E16US008`.
        assert corps["detail"] == "Seul un tournoi en cours peut être terminé."
        # ⚠️ Et la liste **reste**, contrairement à *démarrer* : elle porte l'état sportif, pas la
        # préparation. C'est ce qui rend la migration de l'écran sur ce jalon possible sans perdre
        # ce que l'organisateur vient y lire pendant la pause (5ᵉ passe de revue).
        assert [ligne["cle"] for ligne in corps["lignes"]] == [
            "qualification",
            "phases_eliminatoires",
            "classement",
        ]


def test_un_tournoi_deja_lance_ne_dit_pas_qu_il_peut_demarrer(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le **bloquant** de la revue, épinglé au contrat : c'est ce que liront `E16US007` et
    `E16US008`, qui n'auront pas le garde-fou que le front s'était donné."""
    with TestClient(app_session) as client:
        tournoi_id = _creer_tournoi(client, connecter_admin)
        _lancer(client, tournoi_id)

        corps = client.get(f"/api/v1/tournois/{tournoi_id}/jalons/demarrer").json()

        assert corps["pret"] is False
        # Ni liste, ni moment : il n'y a plus rien à préparer, donc rien à dater.
        assert corps["lignes"] == []
        assert corps["moment"] is None
        assert "déjà lancé" in corps["detail"]
        assert client.post(f"/api/v1/tournois/{tournoi_id}/demarrer").status_code == 409


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
