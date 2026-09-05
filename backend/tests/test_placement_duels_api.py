"""Test bout-en-bout de l'API du plan de duels (E03US009, ADR-0048).

Traverse les couches — HTTP → `ServicePlacementDuels` → classement + arbre + moteur → repositories —
après avoir peuplé le tournoi (gabarit, catégorie, départ, archers **classés**) et inséré une phase
d'élimination directe. Vérifie la forme de la réponse (cibles, réserve, `duels_separes`,
`adjacence_non_garantie`), le placement côte à côte de bout en bout, et les mappings 404
(phase inconnue) / 409 (`phase_pas_un_tableau`). La logique métier est couverte par
`test_service_placement_duels` ; ici on valide le **câblage** de la route.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from domain.bareme import BaremeQualification
from domain.blason import ZoneScore
from domain.phase import Phase, TypePhase
from domain.serie import Serie, Volee
from infrastructure.db import (
    AuditRepositorySQL,
    DepartRepositorySQL,
    SerieRepositorySQL,
)
from infrastructure.horloge import HorlogeSysteme
from tests.base_migree import preparer_base
from tests.conftest import ConnecterAdmin, poser_phase_sql
from tests.test_placement_api import (
    _appliquer_gabarit,
    _creer_categorie,
    _creer_depart,
    _creer_tournoi,
    _inscrire_archer,
)

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
def app_duels(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _phase_qualification(app: FastAPI, tournoi_id: int) -> int:
    """Pose la qualification (ordre 1) du premier créneau et renvoie son id.

    E05US025 : une feuille de marque pend à sa phase (`serie.phase_id`, NOT NULL), et le classement
    qui ensemence le plan de duels se lit sur **cette** phase. Ce décor ne posait que le tableau.
    """
    phase = poser_phase_sql(
        app.state.database.session_factory,
        Phase.qualification(_premier_depart(app, tournoi_id), BaremeQualification.creer(1, 3)),
    )
    assert phase.id is not None
    return phase.id


def _semer(
    app: FastAPI, tournoi_id: int, archer_id: int, valeurs: tuple[ZoneScore, ...], phase_id: int
) -> None:
    """Insère une volée validée pour un archer (directement par le repository) → il est classé."""
    sf = app.state.database.session_factory
    SerieRepositorySQL(sf, AuditRepositorySQL(sf), HorlogeSysteme()).enregistrer(
        Serie(
            tournoi_id=tournoi_id,
            archer_id=archer_id,
            volees=(Volee(numero=1, valeurs=valeurs, validee_par="Scoreur"),),
            phase_id=phase_id,
        )
    )


def _phase_elimination(app: FastAPI, tournoi_id: int) -> int:
    """Insère une phase d'élimination directe (ordre 2) et renvoie son id."""
    phase = poser_phase_sql(
        app.state.database.session_factory,
        Phase.creer(_premier_depart(app, tournoi_id), 2, TypePhase.ELIMINATION_DIRECTE),
    )
    assert phase.id is not None
    return phase.id


def _quatre_archers_classes(app: FastAPI, client: TestClient, tournoi_id: int) -> list[int]:
    """Crée 4 archers inscrits, aux scores décroissants → rangs scratch 1, 2, 3, 4."""
    categorie_id = _creer_categorie(client, tournoi_id)
    depart_id = _creer_depart(client, tournoi_id)
    prenoms = ("Guillaume", "Walter", "Robin", "Petit-Jean")
    scores = (
        (ZoneScore.DIX, ZoneScore.DIX),  # 20 → rang 1
        (ZoneScore.NEUF, ZoneScore.NEUF),  # 18 → rang 2
        (ZoneScore.HUIT, ZoneScore.HUIT),  # 16 → rang 3
        (ZoneScore.SEPT, ZoneScore.SEPT),  # 14 → rang 4
    )
    qualif_id = _phase_qualification(app, tournoi_id)
    archers = []
    for prenom, valeurs in zip(prenoms, scores, strict=True):
        archer_id, _ = _inscrire_archer(client, tournoi_id, categorie_id, depart_id, prenom=prenom)
        _semer(app, tournoi_id, archer_id, valeurs, qualif_id)
        archers.append(archer_id)
    return archers


def test_regenerer_puis_lire_place_les_duellistes_cote_a_cote(
    app_duels: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Câblage complet : régénérer place les duellistes, le GET relit le plan persisté."""
    with TestClient(app_duels) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        _appliquer_gabarit(client, tournoi_id, nb_cibles=2)
        archers = _quatre_archers_classes(app_duels, client, tournoi_id)
        phase_id = _phase_elimination(app_duels, tournoi_id)

        regen = client.post(
            f"/api/v1/tournois/{tournoi_id}/phases/{phase_id}/plan-de-duels/regenerer"
        )
        assert regen.status_code == 200, regen.text

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/phases/{phase_id}/plan-de-duels")

    assert reponse.status_code == 200, reponse.text
    plan = reponse.json()
    assert plan["phase_id"] == phase_id
    places = {p["archer_id"] for cible in plan["cibles"] for p in cible["placements"]}
    assert places == set(archers)  # les 4 duellistes sont posés
    assert plan["conflits"] == []
    assert plan["duels_separes"] == []  # tout le monde côte à côte
    assert all(not cible["adjacence_non_garantie"] for cible in plan["cibles"])


def test_phase_de_qualification_refuse_le_plan_de_duels(
    app_duels: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Une phase qui n'est pas un tableau → 409 `phase_pas_un_tableau` (mapping à la frontière)."""
    with TestClient(app_duels) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        _appliquer_gabarit(client, tournoi_id, nb_cibles=2)
        # Un créneau nu : ce test ne vérifie qu'un refus, aucun archer n'est nécessaire.
        client.post(
            f"/api/v1/tournois/{tournoi_id}/departs",
            json={"horaire": "09:00", "tarif_centimes": 800},
        )
        qualif = poser_phase_sql(
            app_duels.state.database.session_factory,
            Phase.qualification(
                _premier_depart(app_duels, tournoi_id), BaremeQualification.creer(2, 3)
            ),
        )
        assert qualif.id is not None

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/phases/{qualif.id}/plan-de-duels")

    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["code"] == "phase_pas_un_tableau"


def test_phase_inconnue_renvoie_404(app_duels: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Une phase inexistante dans ce tournoi → 404 (le service lève `PhaseIntrouvable`)."""
    with TestClient(app_duels) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        _appliquer_gabarit(client, tournoi_id, nb_cibles=2)

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/phases/999/plan-de-duels")

    assert reponse.status_code == 404, reponse.text


def test_les_deux_services_qui_tranchent_un_duel_signalent_la_pose_du_tour(
    app_duels: FastAPI,
) -> None:
    """Le branchement du poseur de tour sur les **deux** chemins d'écriture, prouvé (ADR-0106 §5).

    ⚠️ **C'est le seul garde-fou du mode de panne** : un branchement oublié rend la pose automatique
    muette sans qu'une ligne rougisse (`DETTE-028`, déjà vécu sur les arrêts programmés, où la
    première livraison n'avait branché que deux services sur six).

    ⚠️ **Le forfait est le second, et c'est celui qu'on oublie** : un walkover tranche un duel sans
    qu'aucun score soit saisi, donc sans passer par la validation. Un tour qui se termine sur un
    forfait — cas banal le jour J — n'aurait jamais reçu ses cibles.

    Il touche un attribut privé, comme son voisin d'E05US033 sur les arrêts, pour la même raison :
    le composition root n'expose pas ce qu'il a branché, et c'est ce branchement qu'on veut garder.
    """
    attendu = app_duels.state.service_placement_duels
    for service in (app_duels.state.service_saisie_duels, app_duels.state.service_forfait):
        nom = type(service).__name__
        assert (
            service._pose_de_tour._poseur is attendu
        ), f"{nom} n'est pas branché : la pose automatique du tour serait inerte."
