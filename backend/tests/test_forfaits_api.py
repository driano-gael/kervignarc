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
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from domain.archer import Archer
from domain.bareme import BaremeQualification
from domain.blason import Blason, ZoneScore
from domain.categorie import Categorie
from domain.depart import Depart
from domain.inscription import Inscription
from domain.phase import Phase, TypePhase
from domain.serie import Serie, Volee
from domain.tournoi import Tournoi
from infrastructure.db import (
    ArcherRepositorySQL,
    AuditRepositorySQL,
    BlasonRepositorySQL,
    CategorieRepositorySQL,
    Database,
    DepartRepositorySQL,
    InscriptionRepositorySQL,
    SerieRepositorySQL,
    TournoiRepositorySQL,
)
from infrastructure.horloge import HorlogeSysteme
from tests.base_migree import preparer_base
from tests.conftest import ConnecterAdmin, poser_phase_sql

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)


def _migrer(url: str) -> None:
    preparer_base(url)


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
        depart = DepartRepositorySQL(db.session_factory).ajouter(
            Depart.creer(tournoi_id=self.tournoi_id, numero=1, tarif_centimes=800, horaire="09:00")
        )
        assert depart.id is not None
        self.depart_id = depart.id
        _depart_id = depart.id
        inscriptions = InscriptionRepositorySQL(
            db.session_factory, AuditRepositorySQL(db.session_factory)
        )
        self.archers: list[int] = []
        # E05US025 : la feuille pend a sa phase (`serie.phase_id`, NOT NULL) — la qualification
        # se pose donc avant les series, et non apres comme ce decor le faisait.
        qualif = poser_phase_sql(
            db.session_factory, Phase.qualification(_depart_id, BaremeQualification.creer(1, 3))
        )
        assert qualif.id is not None
        self.qualif_id = qualif.id
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
                    phase_id=self.qualif_id,
                )
            )
            # C'est l'**inscription** qui fait entrer l'archer au classement du créneau
            # (ADR-0075) — sans elle, le tableau s'ensemencerait sur zéro participant.
            inscriptions.ajouter(Inscription.creer(archer.id, _depart_id))
            self.archers.append(archer.id)
        tableau = poser_phase_sql(
            db.session_factory, Phase.creer(_depart_id, 2, TypePhase.ELIMINATION_DIRECTE)
        )
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


def _classement(client: TestClient, depart_id: int) -> dict[int, dict[str, object]]:
    reponse = client.get(f"/api/v1/departs/{depart_id}/classement")
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

        lignes = _classement(client, scn.depart_id)
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
        retabli = _classement(client, scn.depart_id)
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
        lignes = _classement(client, scn.depart_id)
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
        assert reponse.status_code == 401, reponse.text


def test_forfait_duel_declarable_par_l_admin(
    app_forfaits: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """E16US008 : l'organisateur déclare un forfait de duel **sans** jeton de scoreur, et la trace
    porte le rôle admin (`declare_par`) — pas un nom de personne."""
    with TestClient(app_forfaits) as client:
        scn = Scenario(app_forfaits)
        # ⚠️ `_scoreur` ouvre AUSSI la session admin (`connecter_admin`) : c'est elle qui autorise
        # le POST ci-dessous. Le jeton scoreur, lui, n'est joint qu'à la relecture du tableau.
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
        )
        assert reponse.status_code == 200, reponse.text
        assert reponse.json()["declare_par"] == "Administrateur"

        tableau = client.get(
            f"/api/v1/duels/tableau/{scn.tournoi_id}/{scn.phase_id}", headers=entete
        ).json()
        assert tableau["est_termine"] is True
        assert {p["rang"]: p["duelliste"]["archer_id"] for p in tableau["podium"]}[1] == fort


def test_forfait_duel_annulable_par_l_admin(
    app_forfaits: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Réversibilité (`D-15`) : qui peut déclarer peut annuler — sinon une faute de frappe admin
    resterait irréparable sans aller chercher un scoreur."""
    with TestClient(app_forfaits) as client:
        scn = Scenario(app_forfaits)
        entete = _scoreur(client, scn.tournoi_id, connecter_admin)
        corps = {
            "tournoi_id": scn.tournoi_id,
            "phase_id": scn.phase_id,
            "archer_id": scn.archers[1],
        }
        declaration = client.post("/api/v1/forfaits/duel", json={**corps, "nature": "abandon"})
        assert declaration.status_code == 200, declaration.text

        annulation = client.post("/api/v1/forfaits/duel/annulation", json=corps)
        assert annulation.status_code == 200, annulation.text
        tableau = client.get(
            f"/api/v1/duels/tableau/{scn.tournoi_id}/{scn.phase_id}", headers=entete
        ).json()
        assert tableau["est_termine"] is False


def test_forfait_duel_refuse_sans_aucune_identite(app_forfaits: FastAPI) -> None:
    """L'élargissement ajoute une identité, il n'en retire pas la garde : anonyme = refusé."""
    with TestClient(app_forfaits) as client:
        scn = Scenario(app_forfaits)
        reponse = client.post(
            "/api/v1/forfaits/duel",
            json={
                "tournoi_id": scn.tournoi_id,
                "phase_id": scn.phase_id,
                "archer_id": scn.archers[1],
                "nature": "abandon",
            },
        )
        assert reponse.status_code == 401, reponse.text


def test_forfait_qualification_reste_ferme_a_l_admin(
    app_forfaits: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """L'élargissement est **borné aux duels** : la qualification reste au scoreur seul, faute
    d'écran admin qui le demande (E16US008 — on n'ouvre pas une autorisation sans appelant)."""
    with TestClient(app_forfaits) as client:
        scn = Scenario(app_forfaits)
        connecter_admin(client)
        reponse = client.post(
            "/api/v1/forfaits/qualification",
            json={"tournoi_id": scn.tournoi_id, "archer_id": scn.archers[0], "nature": "abandon"},
        )
        assert reponse.status_code == 401, reponse.text


def test_forfait_duel_refuse_une_phase_de_qualification(
    app_forfaits: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La route des duels est bornée aux **tableaux** (`TYPES_EN_TABLEAU_JOUE`) : sans ce filtre,
    un `phase_id` de qualification posté ici écrirait un forfait relu par le classement de
    qualification — en contournant `exiger_scoreur`, seule garde de l'autre route."""
    with TestClient(app_forfaits) as client:
        scn = Scenario(app_forfaits)
        connecter_admin(client)
        reponse = client.post(
            "/api/v1/forfaits/duel",
            json={
                "tournoi_id": scn.tournoi_id,
                "phase_id": scn.qualif_id,
                "archer_id": scn.archers[1],
                "nature": "abandon",
            },
        )
        # 409 et non 404 : la phase EXISTE, c'est un conflit d'état (`PhasePasUnTableau`).
        assert reponse.status_code == 409, reponse.text
        assert reponse.json()["code"] == "phase_pas_un_tableau"
        # La preuve que le refus mord : sans lui, l'archer serait relégué au classement de qualif.
        assert _classement(client, scn.depart_id)[scn.archers[1]]["statut"] == "en_lice"


def test_forfait_duel_refuse_un_scoreur_d_un_autre_tournoi(
    app_forfaits: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`_garder_tournoi` ne relâche la garde que pour l'**admin** : un scoreur reste borné à son
    tournoi. La garde a été réécrite par E16US008 sans qu'aucun test ne couvre ces deux routes."""
    with TestClient(app_forfaits) as client:
        scn = Scenario(app_forfaits)
        autre = Scenario(app_forfaits)
        entete = _scoreur(client, autre.tournoi_id, connecter_admin)
        client.headers.pop("Authorization", None)
        corps = {
            "tournoi_id": scn.tournoi_id,
            "phase_id": scn.phase_id,
            "archer_id": scn.archers[1],
        }
        declaration = client.post(
            "/api/v1/forfaits/duel", json={**corps, "nature": "abandon"}, headers=entete
        )
        assert declaration.status_code == 403, declaration.text
        assert declaration.json()["code"] == "scoreur_hors_tournoi"

        annulation = client.post("/api/v1/forfaits/duel/annulation", json=corps, headers=entete)
        assert annulation.status_code == 403, annulation.text
        assert annulation.json()["code"] == "scoreur_hors_tournoi"


def test_annulation_de_duel_refuse_une_phase_de_qualification(
    app_forfaits: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La garde de type couvre les DEUX routes : `annuler_en_duel` passe par le même
    `_phase_de_tableau`. Sans elle, l'admin **déferait** par la route des duels un forfait de
    qualification déclaré par un scoreur — le contournement d'`exiger_scoreur`, en sens inverse."""
    with TestClient(app_forfaits) as client:
        scn = Scenario(app_forfaits)
        entete = _scoreur(client, scn.tournoi_id, connecter_admin)
        declaration = client.post(
            "/api/v1/forfaits/qualification",
            json={
                "tournoi_id": scn.tournoi_id,
                "archer_id": scn.archers[0],
                "nature": "abandon",
            },
            headers=entete,
        )
        assert declaration.status_code == 200, declaration.text

        annulation = client.post(
            "/api/v1/forfaits/duel/annulation",
            json={
                "tournoi_id": scn.tournoi_id,
                "phase_id": scn.qualif_id,
                "archer_id": scn.archers[0],
            },
        )
        assert annulation.status_code == 409, annulation.text
        assert annulation.json()["code"] == "phase_pas_un_tableau"
        # Le forfait de qualification tient toujours : le refus a bien protégé l'écriture.
        assert _classement(client, scn.depart_id)[scn.archers[0]]["statut"] == "abandon"
