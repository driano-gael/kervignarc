"""Tests bout-en-bout de l'API de pilotage de simulation (E15US003).

Traversent DTO → service de pilotage (en mémoire) → harnais in-memory, et vérifient le **câblage** :
protection admin, mapping des erreurs, et le **canal de diffusion isolé** `/ws/simulation`.

Tests **après** implémentation : c'est du câblage (API/composition/WS), pas une règle métier —
l'oracle du comportement (bot, pause, reprise en main, garde-fous) est couvert côté service, depuis
le CA (`test_service_pilotage_simulation`).

On monte un tournoi simulable avec le jeu d'essai (« petit ») **plus** un barème de qualification
(le scénario n'en crée pas ; sans lui, `demarrer` refuserait faute de déroulé à générer).
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
def app_simulation(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _tournoi_simulable(client: TestClient) -> int:
    """Instancie « petit » (16 archers inscrits) et lui donne un barème de qualification court."""
    reponse = client.post("/api/v1/jeu-essai/scenarios/petit/instancier", json={})
    assert reponse.status_code == 201, reponse.text
    tournoi_id = int(reponse.json()["tournoi_id"])
    bareme = client.put(
        f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
        json={"nb_volees": 2, "nb_fleches_par_volee": 3},
    )
    assert bareme.status_code == 200, bareme.text
    return tournoi_id


def test_cycle_complet_via_api(app_simulation: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Démarrer → terminer classe tous les archers ; l'état est servi au format cockpit."""
    with TestClient(app_simulation) as client:
        connecter_admin(client)
        tournoi_id = _tournoi_simulable(client)

        depart = client.post("/api/v1/simulations", json={"tournoi_id": tournoi_id, "graine": 1})
        assert depart.status_code == 201, depart.text
        etat = depart.json()
        session_id = etat["session_id"]
        assert etat["etat_pilote"] == "en_cours"
        assert etat["etape"] == "qualification"

        fin = client.post(f"/api/v1/simulations/{session_id}/terminer")
        assert fin.status_code == 200, fin.text
        corps = fin.json()
        assert corps["etat_pilote"] == "terminee"
        assert len(corps["classement"]["lignes"]) == 16
        assert all(ligne["total"] > 0 for ligne in corps["classement"]["lignes"])

        # Lecture indépendante (le front recharge après un signal de diffusion).
        relecture = client.get(f"/api/v1/simulations/{session_id}")
        assert relecture.status_code == 200
        assert relecture.json()["etat_pilote"] == "terminee"


def test_pause_saisie_manuelle_reprise_via_api(
    app_simulation: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Pause ouvre la reprise en main : saisir la volée de l'unité proposée renvoie 200."""
    with TestClient(app_simulation) as client:
        connecter_admin(client)
        tournoi_id = _tournoi_simulable(client)
        session_id = client.post(
            "/api/v1/simulations", json={"tournoi_id": tournoi_id, "graine": 1}
        ).json()["session_id"]

        pause = client.post(f"/api/v1/simulations/{session_id}/pause")
        assert pause.status_code == 200, pause.text
        unite = pause.json()["prochaine_unite"]
        assert unite["genre"] == "volee"
        volee = unite["volee"]
        valeurs = [volee["zones"][0]] * volee["nb_fleches"]

        saisie = client.post(
            f"/api/v1/simulations/{session_id}/saisir-volee",
            json={
                "archer_id": volee["archer_id"],
                "numero_volee": volee["numero_volee"],
                "valeurs": valeurs,
            },
        )
        assert saisie.status_code == 200, saisie.text
        assert saisie.json()["progression"]["volees_faites"] == 1

        # Vue archer : la volée saisie à la main y figure, marquée « Manuel ».
        detail = client.get(f"/api/v1/simulations/{session_id}/archers/{volee['archer_id']}")
        assert detail.status_code == 200, detail.text
        volees = detail.json()["volees"]
        assert any(v["validee_par"] == "Manuel" for v in volees)

        assert client.post(f"/api/v1/simulations/{session_id}/reprendre").status_code == 200


def test_saisie_hors_pause_renvoie_409(
    app_simulation: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_simulation) as client:
        connecter_admin(client)
        tournoi_id = _tournoi_simulable(client)
        etat = client.post(
            "/api/v1/simulations", json={"tournoi_id": tournoi_id, "graine": 1}
        ).json()
        volee = etat["prochaine_unite"]["volee"]
        reponse = client.post(
            f"/api/v1/simulations/{etat['session_id']}/saisir-volee",
            json={
                "archer_id": volee["archer_id"],
                "numero_volee": volee["numero_volee"],
                "valeurs": [volee["zones"][0]] * volee["nb_fleches"],
            },
        )
        assert reponse.status_code == 409, reponse.text
        assert reponse.json()["code"] == "pilotage_simulation_invalide"


def test_session_inconnue_renvoie_404(
    app_simulation: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_simulation) as client:
        connecter_admin(client)
        reponse = client.get("/api/v1/simulations/4242")
        assert reponse.status_code == 404, reponse.text
        assert reponse.json()["code"] == "session_simulation_introuvable"


def test_arreter_est_idempotent(app_simulation: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_simulation) as client:
        connecter_admin(client)
        tournoi_id = _tournoi_simulable(client)
        session_id = client.post(
            "/api/v1/simulations", json={"tournoi_id": tournoi_id, "graine": 1}
        ).json()["session_id"]
        assert client.delete(f"/api/v1/simulations/{session_id}").status_code == 204
        assert client.delete(f"/api/v1/simulations/{session_id}").status_code == 204  # idempotent
        assert client.get(f"/api/v1/simulations/{session_id}").status_code == 404


def test_simulation_exige_admin(app_simulation: FastAPI) -> None:
    """Sans session admin, les routes de simulation renvoient 401."""
    with TestClient(app_simulation) as client:
        assert client.post("/api/v1/simulations", json={"tournoi_id": 1}).status_code == 401
        assert client.get("/api/v1/simulations/1").status_code == 401
        assert client.post("/api/v1/simulations/1/avancer", json={}).status_code == 401


def test_canal_de_diffusion_isole(app_simulation: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Le canal `/ws/simulation` reçoit les signaux de simulation ; le canal réel `/ws` ne fuit pas.

    On prouve l'**isolement structurel** (deux broadcasters, ADR-0055 §5) : abonné au canal
    **réel**, on démarre une simulation (qui ne doit rien y pousser) puis on provoque une **vraie
    écriture** ; le premier message reçu sur `/ws` est celui de l'écriture réelle, jamais le signal
    de simulation.
    """
    with TestClient(app_simulation) as client:
        connecter_admin(client)
        tournoi_id = _tournoi_simulable(client)

        # Le canal simulé reçoit bien le signal de démarrage.
        with client.websocket_connect("/ws/simulation") as ws_sim:
            assert ws_sim.receive_json()["type"] == "connected"
            client.post("/api/v1/simulations", json={"tournoi_id": tournoi_id, "graine": 1})
            assert ws_sim.receive_json()["type"] == "simulation_modifiee"

        # Le canal réel ne reçoit **pas** le signal de simulation : abonné, on démarre une
        # simulation (silencieuse pour lui) puis on écrit pour de vrai — le 1er message est
        # l'écriture réelle.
        with client.websocket_connect("/ws") as ws_reel:
            assert ws_reel.receive_json()["type"] == "connected"
            client.post("/api/v1/simulations", json={"tournoi_id": tournoi_id, "graine": 2})
            client.post("/api/v1/tournois", json={"nom": "Vrai", "date": "2026-03-14"})
            message = ws_reel.receive_json()
            assert message["type"] != "simulation_modifiee"
