"""Test bout-en-bout de l'API des forfaits (E04US015, ADR-0050).

Traverse HTTP → service → repositories après avoir semé un tournoi jouable (deux archers classés,
une phase de qualification, une phase d'élimination, un scoreur). On valide le **câblage** des
routes, l'auth scoreur et l'effet **observable** : un abandon relègue au classement, une DSQ l'en
sort, un forfait en duels fait passer l'adversaire, l'annulation rétablit. La logique fine est
couverte par les tests de domaine/service. Écrit **après** l'implémentation (règle 9 : API/câblage).
"""

from __future__ import annotations

import datetime
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from domain.archer import Archer
from domain.bareme import BaremeQualification
from domain.blason import Blason, ZoneScore
from domain.categorie import Categorie
from domain.phase import Phase, TypePhase
from domain.serie import Serie, Volee
from domain.tournoi import Tournoi
from infrastructure.db import (
    ArcherRepositorySQL,
    AuditRepositorySQL,
    BlasonRepositorySQL,
    CategorieRepositorySQL,
    Database,
    PhaseRepositorySQL,
    SerieRepositorySQL,
    TournoiRepositorySQL,
)
from infrastructure.horloge import HorlogeSysteme
from tests.conftest import ConnecterAdmin

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


class Scenario:
    """Deux archers classés (rang 1 : fort ; rang 2 : faible), phase de qualif + d'élimination."""

    def __init__(self, app: FastAPI) -> None:
        db: Database = app.state.database
        tournoi = TournoiRepositorySQL(db.session_factory).ajouter(Tournoi.creer("Salle", _DATE))
        assert tournoi.id is not None
        self.tournoi_id = tournoi.id
        blason = BlasonRepositorySQL(db.session_factory).ajouter(
            Blason.creer(self.tournoi_id, "Triple", taille=0.25, capacite=1)
        )
        categorie = CategorieRepositorySQL(db.session_factory).ajouter(
            Categorie.creer(self.tournoi_id, "Cat", arme="Arc Classique", blason_id=blason.id)
        )
        assert categorie.id is not None
        archers = ArcherRepositorySQL(db.session_factory)
        series = SerieRepositorySQL(
            db.session_factory, AuditRepositorySQL(db.session_factory), HorlogeSysteme()
        )
        self.archers: list[int] = []
        for valeurs in (("10", "10", "10"), ("8", "8", "8")):  # rang 1 (fort), rang 2 (faible)
            archer = archers.ajouter(
                Archer(nom="N", prenom="P", tournoi_id=self.tournoi_id, categorie_id=categorie.id)
            )
            assert archer.id is not None
            series.enregistrer(
                Serie(
                    tournoi_id=self.tournoi_id,
                    archer_id=archer.id,
                    volees=(
                        Volee(
                            numero=1,
                            valeurs=tuple(ZoneScore(v) for v in valeurs),
                            validee_par="Scoreur",
                        ),
                    ),
                )
            )
            self.archers.append(archer.id)
        phases = PhaseRepositorySQL(db.session_factory)
        qualif = phases.ajouter(
            Phase.qualification(self.tournoi_id, BaremeQualification.creer(1, 3))
        )
        assert qualif.id is not None
        self.qualif_id = qualif.id
        tableau = phases.ajouter(Phase.creer(self.tournoi_id, 2, TypePhase.ELIMINATION_DIRECTE))
        assert tableau.id is not None
        self.phase_id = tableau.id


@pytest.fixture
def app_forfaits(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _scoreur(
    client: TestClient, tournoi_id: int, connecter_admin: ConnecterAdmin
) -> dict[str, str]:
    connecter_admin(client)
    reponse = client.post(f"/api/v1/tournois/{tournoi_id}/scoreurs", json={"nom": "ROUX"})
    assert reponse.status_code in (200, 201), reponse.text
    code = reponse.json()["code"]
    jeton = client.post("/api/v1/scoreurs/session", json={"code": code}).json()["jeton"]
    return {"X-Jeton-Scoreur": jeton}


def _classement(client: TestClient, tournoi_id: int) -> dict[int, dict[str, object]]:
    reponse = client.get(f"/api/v1/tournois/{tournoi_id}/classement")
    assert reponse.status_code == 200, reponse.text
    return {ligne["archer_id"]: ligne for ligne in reponse.json()["lignes"]}


def test_abandon_qualif_relegue_puis_annulation_retablit(
    app_forfaits: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Déclarer un abandon du **mieux classé** le relègue en fin (statut abandon), score conservé ;
    l'annulation le rétablit en tête."""
    with TestClient(app_forfaits) as client:
        scn = Scenario(app_forfaits)
        entete = _scoreur(client, scn.tournoi_id, connecter_admin)
        fort, faible = scn.archers

        reponse = client.post(
            "/api/v1/forfaits/qualification",
            json={"tournoi_id": scn.tournoi_id, "archer_id": fort, "nature": "abandon"},
            headers=entete,
        )
        assert reponse.status_code == 200, reponse.text

        lignes = _classement(client, scn.tournoi_id)
        assert lignes[faible]["rang_scratch"] == 1  # le faible passe devant
        assert lignes[fort]["statut"] == "abandon"
        assert lignes[fort]["rang_scratch"] == 2  # relégué, mais rangé
        assert lignes[fort]["total"] == 30  # flèches préservées

        annul = client.post(
            "/api/v1/forfaits/qualification/annulation",
            json={"tournoi_id": scn.tournoi_id, "archer_id": fort},
            headers=entete,
        )
        assert annul.status_code == 200, annul.text
        retabli = _classement(client, scn.tournoi_id)
        assert retabli[fort]["rang_scratch"] == 1
        assert retabli[fort]["statut"] == "en_lice"


def test_dsq_qualif_sort_du_classement(
    app_forfaits: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Une disqualification sort l'archer du classement (rang `null`), score conservé."""
    with TestClient(app_forfaits) as client:
        scn = Scenario(app_forfaits)
        entete = _scoreur(client, scn.tournoi_id, connecter_admin)
        fort, _faible = scn.archers

        reponse = client.post(
            "/api/v1/forfaits/qualification",
            json={"tournoi_id": scn.tournoi_id, "archer_id": fort, "nature": "disqualification"},
            headers=entete,
        )
        assert reponse.status_code == 200, reponse.text
        lignes = _classement(client, scn.tournoi_id)
        assert lignes[fort]["statut"] == "disqualifie"
        assert lignes[fort]["rang_scratch"] is None
        assert lignes[fort]["total"] == 30


def test_forfait_duel_fait_passer_l_adversaire(
    app_forfaits: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """En duels, déclarer un forfait fait gagner l'adversaire d'office (finale à deux)."""
    with TestClient(app_forfaits) as client:
        scn = Scenario(app_forfaits)
        entete = _scoreur(client, scn.tournoi_id, connecter_admin)
        fort, faible = scn.archers

        reponse = client.post(
            "/api/v1/forfaits/duel",
            json={
                "tournoi_id": scn.tournoi_id,
                "phase_id": scn.phase_id,
                "archer_id": faible,
                "nature": "abandon",
            },
            headers=entete,
        )
        assert reponse.status_code == 200, reponse.text

        tableau = client.get(
            f"/api/v1/duels/tableau/{scn.tournoi_id}/{scn.phase_id}", headers=entete
        ).json()
        assert tableau["est_termine"] is True
        podium = {p["rang"]: p["duelliste"]["archer_id"] for p in tableau["podium"]}
        assert podium[1] == fort  # l'adversaire du forfaitaire passe


def test_declaration_sans_scoreur_refusee(
    app_forfaits: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Sans jeton de scoreur, la déclaration est refusée (auth requise)."""
    with TestClient(app_forfaits) as client:
        scn = Scenario(app_forfaits)
        reponse = client.post(
            "/api/v1/forfaits/qualification",
            json={"tournoi_id": scn.tournoi_id, "archer_id": scn.archers[0], "nature": "abandon"},
        )
        assert reponse.status_code in (401, 403), reponse.text
