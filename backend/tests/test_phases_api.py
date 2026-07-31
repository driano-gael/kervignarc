"""Test bout-en-bout de l'API de la séquence de phases (E05US001).

Traverse toutes les couches — DTO Pydantic → file d'écriture → service → repository → DB — et
vérifie le **mapping des erreurs typées** à la frontière : composition (ajout/liste/édition),
réordonnancement, suppression, cycle de vie, lecture publique / écritures admin (401), tournoi ou
phase inconnus (404), cohérence de séquence (422), conflits d'état (409), corps invalide (400).
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
def app_phases(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _creer_tournoi(client: TestClient) -> int:
    reponse = client.post("/api/v1/tournois", json={"nom": "Kervignarc", "date": "2026-03-14"})
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def test_composer_editer_et_lister(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Ajout de deux phases, édition de la source de la seconde, relecture ordonnée."""
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"

        assert client.get(base).json() == []

        qualif = client.post(base, json={"type": "placement", "effectif": 40})
        assert qualif.status_code == 201, qualif.text
        assert qualif.json()["ordre"] == 1

        elim = client.post(base, json={"type": "elimination_directe"})
        assert elim.status_code == 201
        elim_id = elim.json()["id"]

        modifiee = client.put(
            f"{base}/{elim_id}",
            json={
                "type": "elimination_directe",
                "sources": [{"ordre_source": 1, "rang_debut": 1, "rang_fin": 16}],
                "effectif": 16,
            },
        )
        assert modifiee.status_code == 200, modifiee.text
        assert modifiee.json()["sources"] == [
            {
                "ordre_source": 1,
                "nature": "rangs",
                "rang_debut": 1,
                "rang_fin": 16,
                "tour": None,
                "issue": None,
            }
        ]

        phases = client.get(base).json()
        assert [p["ordre"] for p in phases] == [1, 2]
        assert [p["type"] for p in phases] == ["placement", "elimination_directe"]


def test_reordonner(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        p1 = client.post(base, json={"type": "elimination_directe"}).json()
        p2 = client.post(base, json={"type": "placement"}).json()

        reponse = client.post(f"{base}/reordonner", json={"phases": [p2["id"], p1["id"]]})
        assert reponse.status_code == 200, reponse.text
        ordres = {p["id"]: p["ordre"] for p in reponse.json()}
        assert ordres == {p2["id"]: 1, p1["id"]: 2}


def test_supprimer(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        p1 = client.post(base, json={"type": "elimination_directe"}).json()
        client.post(base, json={"type": "placement"})

        assert client.delete(f"{base}/{p1['id']}").status_code == 204

        restantes = client.get(base).json()
        assert [p["type"] for p in restantes] == ["placement"]
        assert restantes[0]["ordre"] == 1  # recompacté


def test_cycle_de_vie(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        phase = client.post(base, json={"type": "elimination_directe"}).json()
        statut_url = f"{base}/{phase['id']}/statut"

        assert (
            client.post(statut_url, json={"transition": "demarrer"}).json()["statut"] == "en_cours"
        )
        assert (
            client.post(statut_url, json={"transition": "mettre_en_pause"}).json()["statut"]
            == "en_pause"
        )
        assert (
            client.post(statut_url, json={"transition": "reprendre"}).json()["statut"] == "en_cours"
        )
        assert (
            client.post(statut_url, json={"transition": "terminer"}).json()["statut"] == "terminee"
        )


def test_transition_illegale_409(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        phase = client.post(base, json={"type": "elimination_directe"}).json()

        reponse = client.post(
            f"{base}/{phase['id']}/statut", json={"transition": "mettre_en_pause"}
        )
        assert reponse.status_code == 409
        assert reponse.json()["code"] == "transition_statut_invalide"


def test_source_incoherente_422(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Une source qui prélève au-delà de l'effectif de sa source → 422 (règle du domaine)."""
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        client.post(base, json={"type": "placement", "effectif": 32})

        reponse = client.post(
            base,
            json={
                "type": "elimination_directe",
                "sources": [{"ordre_source": 1, "rang_debut": 1, "rang_fin": 40}],
            },
        )
        assert reponse.status_code == 422
        assert reponse.json()["code"] == "rangs_source_inexistants"


def test_supprimer_source_referencee_409(
    app_phases: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        source = client.post(base, json={"type": "placement", "effectif": 40}).json()
        conso = client.post(base, json={"type": "elimination_directe"}).json()
        client.put(
            f"{base}/{conso['id']}",
            json={
                "type": "elimination_directe",
                "sources": [{"ordre_source": 1, "rang_debut": 1, "rang_fin": 16}],
                "effectif": 16,
            },
        )

        reponse = client.delete(f"{base}/{source['id']}")
        assert reponse.status_code == 409
        assert reponse.json()["code"] == "phase_source_referencee"


def test_lecture_publique(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        client.post(f"/api/v1/tournois/{tournoi_id}/phases", json={"type": "elimination_directe"})
    with TestClient(app_phases) as anonyme:
        reponse = anonyme.get(f"/api/v1/tournois/{tournoi_id}/phases")
    assert reponse.status_code == 200
    assert len(reponse.json()) == 1


def test_ajouter_sans_jeton_401(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
    with TestClient(app_phases) as anonyme:
        reponse = anonyme.post(
            f"/api/v1/tournois/{tournoi_id}/phases", json={"type": "elimination_directe"}
        )
    assert reponse.status_code == 401
    assert reponse.json()["code"] == "non_authentifie"


def test_ajouter_tournoi_inconnu_404(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_phases) as client:
        connecter_admin(client)
        reponse = client.post("/api/v1/tournois/999/phases", json={"type": "elimination_directe"})
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"


def test_modifier_phase_inconnue_404(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/phases/999",
            json={"type": "placement", "sources": [], "effectif": None},
        )
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "phase_introuvable"


def test_definir_bareme_apres_ajout_place_la_qualification_en_tete(
    app_phases: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Régression bout-en-bout (revue axe D) : ajouter une phase **avant** de définir le barème ne
    crée pas deux « ordre 1 » — la qualification s'insère en tête, l'élimination descend en 2, et la
    composition se poursuit sans blocage 422."""
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        elim = client.post(base, json={"type": "elimination_directe"})
        assert elim.status_code == 201 and elim.json()["ordre"] == 1

        # Définir le barème crée la phase de qualification (via l'écran « Barème & validation »).
        definir = client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 20, "nb_fleches_par_volee": 3},
        )
        assert definir.status_code == 200, definir.text

        phases = client.get(base).json()
        assert [(p["ordre"], p["type"]) for p in phases] == [
            (1, "qualification"),
            (2, "elimination_directe"),
        ]
        # La composition n'est pas bloquée : on peut ajouter une phase de plus.
        suite = client.post(base, json={"type": "placement"})
        assert suite.status_code == 201 and suite.json()["ordre"] == 3


def test_supprimer_la_qualification_409(
    app_phases: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La qualification se gère via le barème : la supprimer par l'API des phases → 409."""
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 20, "nb_fleches_par_volee": 3},
        )
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        qualif = next(p for p in client.get(base).json() if p["type"] == "qualification")

        reponse = client.delete(f"{base}/{qualif['id']}")
        assert reponse.status_code == 409
        assert reponse.json()["code"] == "phase_qualification_non_supprimable"


def test_type_inconnu_400(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Un type hors énumération est rejeté par Pydantic → 400 (corps invalide)."""
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/phases", json={"type": "poules_magiques"}
        )
    assert reponse.status_code == 400
    assert reponse.json()["code"] == "requete_invalide"
