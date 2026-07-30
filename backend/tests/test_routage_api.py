"""Test bout-en-bout de l'API du panneau de routage (E04US018).

Traverse les couches — HTTP → `ServiceRoutage` → saisie/placement de duels → repositories — après
avoir peuplé un tournoi (gabarit, catégorie, départ, 4 archers **classés**) et une phase
d'élimination directe. Vérifie le **câblage** : la route rend une ligne par archer demandé, dans
l'ordre demandé ; elle **résout seule** la phase de tableau quand le client ne la donne pas (le cas
de la tablette de qualification) ; elle répond **sans authentification** (contrat de lecture
publique, E10US001). La logique métier est couverte par `test_service_routage` — tests écrits, eux,
**depuis le CA** (règle 9) ; ceux-ci le sont après l'implémentation, il n'y a pas d'oracle en jeu.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import get_args

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.routage import IssueRoutageReponse
from application.routage import IssueRoutage
from bootstrap.composition import create_app
from tests.conftest import ConnecterAdmin
from tests.test_placement_api import _appliquer_gabarit, _creer_tournoi
from tests.test_placement_duels_api import _phase_elimination, _quatre_archers_classes

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


@pytest.fixture
def app_routage(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _preparer(app: FastAPI, client: TestClient) -> tuple[int, int, list[int]]:
    """Tournoi peuplé (gabarit, 4 archers classés, phase de tableau) avec le plan de duels posé."""
    tournoi_id = _creer_tournoi(client)
    _appliquer_gabarit(client, tournoi_id, nb_cibles=2)
    archers = _quatre_archers_classes(app, client, tournoi_id)
    phase_id = _phase_elimination(app, tournoi_id)
    regen = client.post(f"/api/v1/tournois/{tournoi_id}/phases/{phase_id}/plan-de-duels/regenerer")
    assert regen.status_code == 200, regen.text
    return tournoi_id, phase_id, archers


def test_route_les_archers_demandes_dans_l_ordre_demande(
    app_routage: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Câblage : une ligne par `archer_id`, dans l'ordre de la grille (A→D), avec sa cible."""
    with TestClient(app_routage) as client:
        connecter_admin(client)
        tournoi_id, phase_id, archers = _preparer(app_routage, client)

        reponse = client.get(
            f"/api/v1/routage/{tournoi_id}",
            params={"archer_id": archers, "phase_id": phase_id},
        )

    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["phase_id"] == phase_id
    assert [ligne["archer_id"] for ligne in corps["archers"]] == archers
    for ligne in corps["archers"]:
        assert ligne["issue"] == "prochain_duel"
        assert ligne["prochain"]["cible"] is not None
        assert ligne["prochain"]["position"] in {"A", "B", "C", "D"}
        assert ligne["prochain"]["libelle"] == "Demi-finale"
        assert ligne["prochain"]["adversaire"] is not None
        # Plan frais et duellistes côte à côte : aucune alerte. Sans cette assertion, un `alerte`
        # figé à `None` dans le DTO passerait toute la suite — le champ ne prouverait rien.
        assert ligne["prochain"]["alerte"] is None
        assert ligne["nom"] != ""  # l'identité vient des archers du tournoi


def test_phase_de_tableau_resolue_sans_la_donner(
    app_routage: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Sans `phase_id` — le cas de la tablette de qualification — le service trouve le tableau."""
    with TestClient(app_routage) as client:
        connecter_admin(client)
        tournoi_id, phase_id, archers = _preparer(app_routage, client)

        reponse = client.get(f"/api/v1/routage/{tournoi_id}", params={"archer_id": archers[:1]})

    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["phase_id"] == phase_id


def test_lecture_publique_sans_authentification(
    app_routage: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Contrat E10US001 : le panneau se lit **sans jeton** — c'est un canal de routage (`D-09`),
    destiné à finir sur l'écran de salle et l'appli publique."""
    with TestClient(app_routage) as client:
        connecter_admin(client)
        tournoi_id, _, archers = _preparer(app_routage, client)

    with TestClient(app_routage) as anonyme:
        reponse = anonyme.get(f"/api/v1/routage/{tournoi_id}", params={"archer_id": archers})

    assert reponse.status_code == 200, reponse.text
    assert len(reponse.json()["archers"]) == len(archers)


def test_sans_phase_de_tableau_le_panneau_repond_motive(
    app_routage: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Pas de phase d'élimination configurée : 200 avec des lignes **motivées**, jamais un 4xx —
    le panneau doit rester consultable sans faire croire à une panne."""
    with TestClient(app_routage) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        _appliquer_gabarit(client, tournoi_id, nb_cibles=2)
        archers = _quatre_archers_classes(app_routage, client, tournoi_id)

        reponse = client.get(f"/api/v1/routage/{tournoi_id}", params={"archer_id": archers})

    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["phase_id"] is None
    assert all(ligne["issue"] == "indisponible" for ligne in corps["archers"])
    assert all(ligne["motif"] for ligne in corps["archers"])


def test_sans_archer_demande_la_reponse_est_vide(
    app_routage: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Aucun `archer_id` : la phase est résolue, la liste est vide — pas d'erreur de contrat."""
    with TestClient(app_routage) as client:
        connecter_admin(client)
        tournoi_id, phase_id, _ = _preparer(app_routage, client)

        reponse = client.get(f"/api/v1/routage/{tournoi_id}")

    assert reponse.status_code == 200, reponse.text
    assert reponse.json() == {"phase_id": phase_id, "archers": []}


def test_phase_imposee_introuvable_rend_404(
    app_routage: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Câblage du mapping : un `phase_id` **fourni par le client** et inconnu est un vrai refus, pas
    un placide « phase finale non configurée » (`PhaseIntrouvable` → 404, `api/erreurs.py`)."""
    with TestClient(app_routage) as client:
        connecter_admin(client)
        tournoi_id, _, archers = _preparer(app_routage, client)

        reponse = client.get(
            f"/api/v1/routage/{tournoi_id}",
            params={"archer_id": archers[:1], "phase_id": 9999},
        )

    assert reponse.status_code == 404, reponse.text
    assert reponse.json()["code"] == "phase_introuvable"


def test_trop_d_archers_demandes_est_refuse(
    app_routage: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La route est **publique et non authentifiée** : le plafond doit réellement mordre, et rendre
    le **400** du projet (`RequestValidationError`), pas un 422. Un garde-fou non testé rassure sans
    garder."""
    with TestClient(app_routage) as client:
        connecter_admin(client)
        tournoi_id, _, _ = _preparer(app_routage, client)

        limite = client.get(f"/api/v1/routage/{tournoi_id}", params={"archer_id": list(range(64))})
        au_dela = client.get(f"/api/v1/routage/{tournoi_id}", params={"archer_id": list(range(65))})

    assert limite.status_code == 200, limite.text  # la borne ne gêne pas les appelants réels
    assert au_dela.status_code == 400, au_dela.text


def test_issue_reponse_est_le_miroir_de_l_enumeration() -> None:
    """Le `Literal` du DTO est recopié à la main et posé par un `cast` : rien ne le rattacherait à
    `IssueRoutage` si une 4ᵉ issue apparaissait — la divergence se découvrirait à la sérialisation
    (500), au pire endroit. Cette égalité est le seul lien qui les tient ensemble."""
    assert set(get_args(IssueRoutageReponse)) == {issue.value for issue in IssueRoutage}
