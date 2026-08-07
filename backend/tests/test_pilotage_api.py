"""Test bout-en-bout de l'API du pilotage d'un tour (E12US002, ADR-0056).

Traverse les couches — HTTP → `ServicePilotageTour` → saisie/placement de duels → repositories —
après avoir peuplé le tournoi (gabarit, catégorie, départ, 4 archers **classés**) et une phase
d'élimination directe. Vérifie le **câblage** : le feu vert renvoie l'état par duel, le lancement
émet et **trace** (`LANCEMENT` lisible par l'audit), les mappings 409 (`aucun_duel_a_lancer`,
`phase_pas_un_tableau`) / 404 / 401. Logique métier couverte par `test_service_pilotage_tour`.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from domain.bareme import BaremeQualification
from domain.phase import Phase
from infrastructure.db import DepartRepositorySQL
from tests.base_migree import preparer_base
from tests.conftest import ConnecterAdmin, poser_phase_sql
from tests.test_placement_api import _appliquer_gabarit, _creer_tournoi
from tests.test_placement_duels_api import _phase_elimination, _quatre_archers_classes

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _migrer(url: str) -> None:
    preparer_base(url)


def _premier_depart(app: FastAPI, tournoi_id: int) -> int:
    """Le créneau du tournoi — porteur des phases depuis ADR-0075.

    Le décor en pose déjà un ; on le relit plutôt que d'en inventer un second, qui fausserait les
    comptes de placement.
    """
    departs = DepartRepositorySQL(app.state.database.session_factory).par_tournoi(tournoi_id)
    assert departs and departs[0].id is not None, "Le décor doit poser au moins un créneau."
    return departs[0].id


@pytest.fixture
def app_pilotage(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _preparer(app: FastAPI, client: TestClient, *, placer: bool = True) -> tuple[int, int]:
    """Crée un tournoi peuplé (gabarit, 4 archers classés, phase de tableau), place si demandé."""
    tournoi_id = _creer_tournoi(client)
    _appliquer_gabarit(client, tournoi_id, nb_cibles=2)
    _quatre_archers_classes(app, client, tournoi_id)
    phase_id = _phase_elimination(app, tournoi_id)
    if placer:
        regen = client.post(
            f"/api/v1/tournois/{tournoi_id}/phases/{phase_id}/plan-de-duels/regenerer"
        )
        assert regen.status_code == 200, regen.text
    return tournoi_id, phase_id


def test_feu_vert_expose_l_etat_des_duels(
    app_pilotage: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Câblage : après placement, le feu vert liste les prêts (tour 1) et les bloqués (tour 2)."""
    with TestClient(app_pilotage) as client:
        connecter_admin(client)
        tournoi_id, phase_id = _preparer(app_pilotage, client)

        reponse = client.get(f"/api/v1/pilotage/feu-vert/{tournoi_id}/{phase_id}")

    assert reponse.status_code == 200, reponse.text
    feu = reponse.json()
    assert feu["phase_id"] == phase_id
    assert feu["nb_prets"] == 2
    tour1 = [d for d in feu["duels"] if d["tour"] == 1]
    assert tour1 and all(d["pret_a_lancer"] and d["cible_attribuee"] for d in tour1)
    tour2 = [d for d in feu["duels"] if d["tour"] == 2]
    assert tour2 and all(not d["pret_a_lancer"] for d in tour2)


def test_lancer_chiffre_et_laisse_une_trace(
    app_pilotage: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Câblage : le lancement renvoie le décompte chiffré **et** écrit une trace d'audit `LANCEMENT`
    (via la file → post-commit) lisible par l'endpoint d'audit admin."""
    with TestClient(app_pilotage) as client:
        connecter_admin(client)
        tournoi_id, phase_id = _preparer(app_pilotage, client)

        lance = client.post(
            "/api/v1/pilotage/lancer", json={"tournoi_id": tournoi_id, "phase_id": phase_id}
        )
        assert lance.status_code == 200, lance.text
        resume = lance.json()
        assert resume["nb_duels"] == 2
        assert resume["nb_archers"] == 4
        assert resume["numeros"] == [1, 2]

        audit = client.get(f"/api/v1/tournois/{tournoi_id}/audit")

    assert audit.status_code == 200, audit.text
    actions = [entree["action"] for entree in audit.json()]
    assert "lancement" in actions


def test_lancer_sans_duel_pret_renvoie_409(
    app_pilotage: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Sans placement, aucun duel n'est prêt → 409 `aucun_duel_a_lancer` (mapping frontière)."""
    with TestClient(app_pilotage) as client:
        connecter_admin(client)
        tournoi_id, phase_id = _preparer(app_pilotage, client, placer=False)

        lance = client.post(
            "/api/v1/pilotage/lancer", json={"tournoi_id": tournoi_id, "phase_id": phase_id}
        )

    assert lance.status_code == 409, lance.text
    assert lance.json()["code"] == "aucun_duel_a_lancer"


def test_feu_vert_sur_qualification_renvoie_409(
    app_pilotage: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le feu vert n'a de sens que pour un tableau → 409 `phase_pas_un_tableau`."""
    with TestClient(app_pilotage) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        _appliquer_gabarit(client, tournoi_id, nb_cibles=2)
        # Ce test n'a pas besoin d'archers : un créneau nu suffit à porter la qualification dont
        # il vérifie le refus.
        client.post(
            f"/api/v1/tournois/{tournoi_id}/departs",
            json={"horaire": "09:00", "tarif_centimes": 800},
        )
        qualif = poser_phase_sql(
            app_pilotage.state.database.session_factory,
            Phase.qualification(
                _premier_depart(app_pilotage, tournoi_id),
                BaremeQualification.creer(2, 3),
            ),
        )
        assert qualif.id is not None

        reponse = client.get(f"/api/v1/pilotage/feu-vert/{tournoi_id}/{qualif.id}")

    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["code"] == "phase_pas_un_tableau"


def test_feu_vert_exige_l_admin(app_pilotage: FastAPI) -> None:
    """Le pilotage est un acte d'organisateur : sans session admin, 401."""
    with TestClient(app_pilotage) as client:
        reponse = client.get("/api/v1/pilotage/feu-vert/1/1")
    assert reponse.status_code == 401, reponse.text
