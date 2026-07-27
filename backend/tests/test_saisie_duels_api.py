"""Test bout-en-bout de l'API de saisie en duels (E04US013).

Traverse HTTP → service → moteur → repositories, après avoir semé un tournoi jouable : deux archers
**classés** (séries validées), une phase d'élimination, un scoreur. On valide le **câblage** des
routes, l'auth scoreur et le mapping d'erreurs — la logique (scoring, reconstruction) est couverte
par `test_domain_duel` / `test_service_saisie_duels` / `test_duel_repository`. Écrit **après**
l'implémentation (règle 9 : API/câblage, pas d'oracle en jeu).

Bracket **à deux archers** : `construire_tableau` produit un unique match — la **finale**. On y
saisit trois manches, on valide, et le tableau reflète le vainqueur (progression transmise).
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
    """Un tournoi à deux archers classés, une phase d'élimination, un scoreur (code)."""

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
        for valeurs in (("10", "10", "10"), ("9", "9", "9")):  # scores décroissants → rang 1, 2
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
        phase = PhaseRepositorySQL(db.session_factory).ajouter(
            Phase.creer(self.tournoi_id, 2, TypePhase.ELIMINATION_DIRECTE)
        )
        assert phase.id is not None
        self.phase_id = phase.id


@pytest.fixture
def app_duels(tmp_path: Path) -> Iterator[FastAPI]:
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
    """Crée un scoreur (admin) et ouvre sa session ; renvoie l'en-tête `X-Jeton-Scoreur`."""
    connecter_admin(client)  # authentifie le client en admin (en place)
    reponse = client.post(f"/api/v1/tournois/{tournoi_id}/scoreurs", json={"nom": "ROUX"})
    assert reponse.status_code in (200, 201), reponse.text
    code = reponse.json()["code"]
    jeton = client.post("/api/v1/scoreurs/session", json={"code": code}).json()["jeton"]
    return {"X-Jeton-Scoreur": jeton}


def _manche(
    numero: int, haut: tuple[str, ...], bas: tuple[str, ...], phase_id: int, tid: int
) -> dict[str, object]:
    return {
        "tournoi_id": tid,
        "phase_id": phase_id,
        "match_numero": 1,
        "numero": numero,
        "valeurs_haut": list(haut),
        "valeurs_bas": list(bas),
    }


def test_saisir_valider_un_duel_fait_avancer_le_tableau(
    app_duels: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Câblage complet : GET tableau, saisir, valider → le vainqueur est le mieux classé."""
    with TestClient(app_duels) as client:
        scn = Scenario(app_duels)
        entete = _scoreur(client, scn.tournoi_id, connecter_admin)

        tableau = client.get(
            f"/api/v1/duels/tableau/{scn.tournoi_id}/{scn.phase_id}", headers=entete
        )
        assert tableau.status_code == 200, tableau.text
        finale = next(d for d in tableau.json()["duels"] if d["place_en_jeu"] == [1, 2])
        assert finale["numero"] == 1
        vainqueur_attendu = finale["haut"]["archer_id"]  # tête de série n°1 en haut

        for numero in (1, 2, 3):
            reponse = client.post(
                "/api/v1/duels/manches",
                json=_manche(
                    numero, ("10", "10", "10"), ("9", "9", "9"), scn.phase_id, scn.tournoi_id
                ),
                headers=entete,
            )
            assert reponse.status_code == 200, reponse.text

        valide = client.post(
            "/api/v1/duels/validations",
            json={"tournoi_id": scn.tournoi_id, "phase_id": scn.phase_id, "match_numero": 1},
            headers=entete,
        )
        assert valide.status_code == 200, valide.text
        assert valide.json()["resultat"]["vainqueur"] == "haut"
        assert valide.json()["validee_par"] == "ROUX"

        apres = client.get(
            f"/api/v1/duels/tableau/{scn.tournoi_id}/{scn.phase_id}", headers=entete
        ).json()
        assert apres["est_termine"] is True
        podium = {place["rang"]: place["duelliste"]["archer_id"] for place in apres["podium"]}
        assert podium[1] == vainqueur_attendu


def test_code_de_zone_ou_camp_invalide_refuse(
    app_duels: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """DTO typés `ZoneScore`/`Cote` : un code inconnu est rejeté par Pydantic (400), pas 500.

    Cohérence de frontière avec E04US002 : `RequestValidationError → 400 requete_invalide`.
    """
    with TestClient(app_duels) as client:
        scn = Scenario(app_duels)
        entete = _scoreur(client, scn.tournoi_id, connecter_admin)
        manche = client.post(
            "/api/v1/duels/manches",
            json={
                "tournoi_id": scn.tournoi_id,
                "phase_id": scn.phase_id,
                "match_numero": 1,
                "numero": 1,
                "valeurs_haut": ["42", "10", "10"],  # 42 n'est pas une ZoneScore
                "valeurs_bas": ["9", "9", "9"],
            },
            headers=entete,
        )
        assert manche.status_code == 400, manche.text
        barrage = client.post(
            "/api/v1/duels/barrages",
            json={
                "tournoi_id": scn.tournoi_id,
                "phase_id": scn.phase_id,
                "match_numero": 1,
                "fleche_haut": "10",
                "fleche_bas": "10",
                "gagnant_designe": "milieu",  # n'est pas une Cote (haut/bas)
            },
            headers=entete,
        )
        assert barrage.status_code == 400, barrage.text


def test_saisie_sans_session_scoreur_refusee(app_duels: FastAPI) -> None:
    """Sans en-tête scoreur, la saisie est refusée (401)."""
    with TestClient(app_duels) as client:
        scn = Scenario(app_duels)
        reponse = client.post(
            "/api/v1/duels/manches",
            json=_manche(1, ("10", "10", "10"), ("9", "9", "9"), scn.phase_id, scn.tournoi_id),
        )
        assert reponse.status_code == 401, reponse.text


def test_scoreur_d_un_autre_tournoi_refuse(
    app_duels: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un scoreur n'officie que dans **son** tournoi (403 scoreur_hors_tournoi)."""
    with TestClient(app_duels) as client:
        scn = Scenario(app_duels)
        entete = _scoreur(client, scn.tournoi_id, connecter_admin)
        # Un autre tournoi, dont ce scoreur n'est pas.
        autre = TournoiRepositorySQL(app_duels.state.database.session_factory).ajouter(
            Tournoi.creer("Autre", _DATE)
        )
        assert autre.id is not None
        reponse = client.get(f"/api/v1/duels/tableau/{autre.id}/{scn.phase_id}", headers=entete)
        assert reponse.status_code == 403, reponse.text
