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

from application.forfaits import AUTEUR_ADMIN
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


# Bearer admin mis de côté par `_scoreur`, par client de test. ⚠️ **Mécanisme, pas convention** :
# `connecter_admin` n'est pas idempotent (409 `acces_deja_configure`), donc un test qui veut
# redevenir admin ne peut pas la rappeler — il restaure le jeton par `_redevenir_admin`.
_BEARERS_ADMIN: dict[int, str] = {}


def _redevenir_admin(client: TestClient) -> None:
    """Rétablit l'identité admin retirée par `_scoreur` — le chemin admin se redemande."""
    bearer = _BEARERS_ADMIN.get(id(client))
    assert bearer is not None, "`_redevenir_admin` suppose un `_scoreur` préalable."
    client.headers["Authorization"] = bearer


def _scoreur(
    client: TestClient, tournoi_id: int, connecter_admin: ConnecterAdmin
) -> dict[str, str]:
    connecter_admin(client)
    reponse = client.post(f"/api/v1/tournois/{tournoi_id}/scoreurs", json={"nom": "ROUX"})
    assert reponse.status_code in (200, 201), reponse.text
    code = reponse.json()["code"]
    jeton = client.post("/api/v1/scoreurs/session", json={"code": code}).json()["jeton"]
    # ⚠️ **Le Bearer admin est retiré ICI**, pas laissé à la vigilance de l'appelant : depuis
    # E16US007 `autoriser_forfait` retient l'admin, **testé en premier**, donc un client qui garde
    # les deux identités emprunte le chemin admin en silence — la branche scoreur pourrait être
    # supprimée sans rien faire rougir. Un test qui veut l'admin **le redemande explicitement**
    # (`connecter_admin(client)`), ce qui se lit ; l'oubli inverse, lui, ne se lisait pas.
    # Mécanisé en 2ᵉ passe de revue (axe C2) — la 1ʳᵉ correction était un commentaire recopié
    # sur trois sites d'appel sur huit, soit la convention tenue à la main que le registre
    # de dette documente déjà trois fois.
    bearer = client.headers.pop("Authorization", None)
    if bearer is not None:
        _BEARERS_ADMIN[id(client)] = bearer
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
        # ⚠️ **La TRACE, pas seulement l'autorisation** : `_auteur` rend `AUTEUR_ADMIN` ou le nom
        # du scoreur. Sans cette ligne, le muter en `return AUTEUR_ADMIN` laissait toute la suite
        # verte — le journal d'audit `FORFAIT` cessait de distinguer les deux origines (ADR-0050,
        # DETTE-017). Relevé en 2ᵉ passe de revue, axes B et D.
        assert reponse.json()["declare_par"] == "ROUX", reponse.text

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
        # Chemin ADMIN, redemandé explicitement : `_scoreur` rend un client en identité scoreur.
        _redevenir_admin(client)
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
        # Chemin ADMIN, redemandé explicitement : `_scoreur` rend un client en identité scoreur.
        _redevenir_admin(client)
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


def test_forfait_qualification_ouvert_a_l_admin(
    app_forfaits: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La qualification accepte l'admin depuis le 30/08/2026 (décision du commanditaire).

    ⚠️ Ce test **remplace** son inverse, qui épinglait la borne d'E16US008 (« l'élargissement est
    borné aux duels, faute d'écran admin qui le demande »). L'écran existe désormais — la fiche
    d'archer du pilotage —, donc la borne tombe. La **trace** reste le point à garder : un forfait
    déclaré par l'organisateur s'inscrit au nom du rôle admin, jamais d'un scoreur (`DETTE-017`).
    """
    with TestClient(app_forfaits) as client:
        scn = Scenario(app_forfaits)
        connecter_admin(client)
        reponse = client.post(
            "/api/v1/forfaits/qualification",
            json={"tournoi_id": scn.tournoi_id, "archer_id": scn.archers[0], "nature": "abandon"},
        )

        assert reponse.status_code == 200, reponse.text
        assert reponse.json()["declare_par"] == AUTEUR_ADMIN

        annulation = client.post(
            "/api/v1/forfaits/qualification/annulation",
            json={"tournoi_id": scn.tournoi_id, "archer_id": scn.archers[0]},
        )
        assert annulation.status_code == 200, annulation.text


def test_forfait_qualification_refuse_un_scoreur_d_un_autre_tournoi(
    app_forfaits: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La garde de tournoi survit au passage `_exiger_meme_tournoi` → `_garder_tournoi`.

    ⚠️ Le jumeau existait pour le duel, pas pour la qualification — et c'est justement la garde
    que le diff d'E16US007 a réécrite (le scoreur y devient `Scoreur | None`). Relevé en revue.
    """
    with TestClient(app_forfaits) as client:
        scn = Scenario(app_forfaits)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)
        # L'autre tournoi se crée en admin ; on repasse ensuite en identité scoreur pour l'attaque.
        _redevenir_admin(client)
        autre = client.post("/api/v1/tournois", json={"nom": "Autre", "date": "2026-04-01"})
        assert autre.status_code == 201, autre.text
        client.headers.pop("Authorization", None)

        declaration = client.post(
            "/api/v1/forfaits/qualification",
            json={
                "tournoi_id": int(autre.json()["id"]),
                "archer_id": scn.archers[0],
                "nature": "abandon",
            },
            headers=entetes,
        )

        assert declaration.status_code == 403, declaration.text
        assert declaration.json()["code"] == "scoreur_hors_tournoi"


def test_forfait_qualification_refuse_sans_session(app_forfaits: FastAPI) -> None:
    """Élargir n'est pas ouvrir : sans aucune identité, la route reste fermée (401)."""
    with TestClient(app_forfaits) as client:
        scn = Scenario(app_forfaits)
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
    `_exiger_phase_de_tableau`. Sans elle, l'admin **déferait** par la route des duels un forfait de
    qualification déclaré par un scoreur — le contournement d'`exiger_scoreur`, en sens inverse."""
    with TestClient(app_forfaits) as client:
        scn = Scenario(app_forfaits)
        entete = _scoreur(client, scn.tournoi_id, connecter_admin)
        # Chemin ADMIN, redemandé explicitement : `_scoreur` rend un client en identité scoreur.
        _redevenir_admin(client)
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
