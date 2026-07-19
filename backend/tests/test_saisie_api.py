"""Test bout-en-bout de l'API de saisie de qualification (E04US002, tranche exposition PR2b).

Traverse HTTP → services → moteur → repositories, après avoir semé un tournoi jouable : un poste
rattaché à sa cible, un archer **placé** sur cette cible pour un départ, une phase de qualification
avec barème et blason. On valide le **câblage** des routes et le mapping d'erreurs — la logique du
moteur/garde est couverte par `test_service_saisie` / `test_serie_repository`. Écrit **après**
l'implémentation (règle 9 : API/câblage, pas d'oracle en jeu).

Le scaffolding métier (catégorie/blason, archer, départ, inscription, placement, phase) est semé par
les repositories, pour **placer l'archer sur une cible connue** (le placement auto ne se cible pas).
La session de poste et la saisie passent par HTTP — c'est ce qu'on teste.
"""

from __future__ import annotations

import datetime
from collections.abc import Iterator
from dataclasses import dataclass
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
from domain.depart import Depart
from domain.gabarit_salle import GabaritSalle
from domain.grain_validation import GrainValidation
from domain.inscription import Inscription
from domain.phase import Phase
from domain.placement import Affectation
from domain.tournoi import Tournoi
from infrastructure.db import (
    ArcherRepositorySQL,
    BlasonRepositorySQL,
    CategorieRepositorySQL,
    Database,
    DepartRepositorySQL,
    GabaritSalleRepositorySQL,
    InscriptionRepositorySQL,
    PhaseRepositorySQL,
    PlacementRepositorySQL,
    TournoiRepositorySQL,
)
from tests.conftest import ConnecterAdmin

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


@pytest.fixture
def app_saisie(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


@dataclass
class Scenario:
    """Poignées d'un tournoi jouable : le poste (jeton, cible), son départ, l'archer placé.

    `scoreur_code` permet de connecter un scoreur du tournoi pour valider/corriger.
    """

    tournoi_id: int
    depart_id: int
    archer_id: int
    cible_index: int
    jeton: str
    scoreur_code: str


def _placer_archer(
    db: Database,
    tournoi_id: int,
    depart_id: int,
    categorie_id: int,
    cible_index: int,
    position: str,
) -> int:
    """Crée un archer, l'inscrit au départ, le place sur `(cible, position)` ; renvoie son id."""
    sf = db.session_factory
    suffixe = f"{cible_index}{position}"
    archer = ArcherRepositorySQL(sf).ajouter(
        Archer.creer(f"CIBLE{suffixe}", "Alice", tournoi_id, categorie_id)
    )
    assert archer.id is not None
    inscription = InscriptionRepositorySQL(sf).ajouter(Inscription.creer(archer.id, depart_id))
    assert inscription.id is not None
    PlacementRepositorySQL(sf).poser_plusieurs(
        depart_id, [Affectation(inscription.id, cible_index, position)]
    )
    return archer.id


def _semer(
    app: FastAPI, client: TestClient, connecter_admin: ConnecterAdmin, nb_cibles: int = 2
) -> Scenario:
    """Sème un tournoi jouable et rattache un poste à la cible 1 (archer placé en 1/A)."""
    connecter_admin(client)
    db: Database = app.state.database
    sf = db.session_factory
    tournoi = TournoiRepositorySQL(sf).ajouter(Tournoi.creer("Salle 18m", _DATE))
    assert tournoi.id is not None
    GabaritSalleRepositorySQL(sf).ajouter(
        GabaritSalle.creer("Plan", nb_cibles=nb_cibles).pour_tournoi(tournoi.id)
    )
    blason = BlasonRepositorySQL(sf).ajouter(
        Blason(tournoi_id=tournoi.id, nom="Simple", taille=1.0, capacite=1, zones=tuple(ZoneScore))
    )
    assert blason.id is not None
    categorie = CategorieRepositorySQL(sf).ajouter(
        Categorie.creer(tournoi.id, "Senior H", blason_id=blason.id)
    )
    assert categorie.id is not None
    depart = DepartRepositorySQL(sf).ajouter(Depart.creer(tournoi.id, 1, tarif_centimes=1000))
    assert depart.id is not None
    PhaseRepositorySQL(sf).ajouter(
        Phase.qualification(
            tournoi_id=tournoi.id,
            bareme=BaremeQualification.creer(2, 3),
            validation=GrainValidation.fin_de_serie(),
        )
    )
    archer_id = _placer_archer(db, tournoi.id, depart.id, categorie.id, cible_index=1, position="A")
    # Prépare les codes de cible (admin) et rattache la tablette à la cible 1.
    postes = client.post(f"/api/v1/tournois/{tournoi.id}/postes").json()
    code_cible_1 = next(p["code"] for p in postes if p["cible_index"] == 1)
    jeton = client.post("/api/v1/postes/session", json={"code": code_cible_1}).json()["jeton"]
    # Un scoreur du tournoi (admin), pour valider/corriger.
    scoreur = client.post(f"/api/v1/tournois/{tournoi.id}/scoreurs", json={"nom": "ROUX"}).json()
    return Scenario(
        tournoi_id=tournoi.id,
        depart_id=depart.id,
        archer_id=archer_id,
        cible_index=1,
        jeton=jeton,
        scoreur_code=scoreur["code"],
    )


def _entete(jeton: str) -> dict[str, str]:
    return {"X-Jeton-Poste": jeton}


# --- Départ courant ---


def test_fixer_depart_courant_puis_lister_les_archers(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le poste fixe son départ, puis sa grille remonte l'archer placé sur sa cible (A..D)."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)

        fixe = client.post(
            "/api/v1/saisie/depart-courant",
            json={"depart_id": s.depart_id},
            headers=_entete(s.jeton),
        )
        assert fixe.status_code == 200, fixe.text
        assert fixe.json()["depart_id"] == s.depart_id

        grille = client.get("/api/v1/saisie/archers", headers=_entete(s.jeton))
        assert grille.status_code == 200, grille.text
        assert grille.json() == [
            {"position": "A", "archer_id": s.archer_id, "nom": "CIBLE1A", "prenom": "Alice"}
        ]


def test_lister_les_archers_sans_depart_courant_rend_409(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """ADR-0034 §1 : sans départ fixé, le poste ne sait pas qui afficher → refus explicite (409)."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)

        reponse = client.get("/api/v1/saisie/archers", headers=_entete(s.jeton))

        assert reponse.status_code == 409, reponse.text
        assert reponse.json()["code"] == "depart_courant_non_defini"


def test_fixer_depart_courant_sans_jeton_rend_401(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)

        reponse = client.post("/api/v1/saisie/depart-courant", json={"depart_id": s.depart_id})

        assert reponse.status_code == 401, reponse.text


def test_fixer_un_depart_d_un_autre_tournoi_rend_404(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """ADR-0034 §4 : un départ hors tournoi du poste n'existe pas pour lui (404)."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        db: Database = app_saisie.state.database
        autre = TournoiRepositorySQL(db.session_factory).ajouter(Tournoi.creer("Extérieur", _DATE))
        assert autre.id is not None
        depart_autre = DepartRepositorySQL(db.session_factory).ajouter(
            Depart.creer(autre.id, 1, tarif_centimes=1000)
        )
        assert depart_autre.id is not None

        reponse = client.post(
            "/api/v1/saisie/depart-courant",
            json={"depart_id": depart_autre.id},
            headers=_entete(s.jeton),
        )

        assert reponse.status_code == 404, reponse.text
        assert reponse.json()["code"] == "depart_introuvable"


# --- Saisie ---


def _fixer_depart(client: TestClient, s: Scenario) -> None:
    reponse = client.post(
        "/api/v1/saisie/depart-courant", json={"depart_id": s.depart_id}, headers=_entete(s.jeton)
    )
    assert reponse.status_code == 200, reponse.text


def test_saisir_une_volee_pour_son_archer(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Saisie nominale par le **poste marqueur** : volée persistée, renvoyée avec son « quand »."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _fixer_depart(client, s)
        client.headers.pop("Authorization", None)  # le poste saisit, pas l'admin (chemin marqueur)

        reponse = client.post(
            "/api/v1/saisie/volees",
            json={
                "tournoi_id": s.tournoi_id,
                "archer_id": s.archer_id,
                "numero": 1,
                "valeurs": ["10", "9", "8"],
                "saisie_par": "DURAND",
            },
            headers=_entete(s.jeton),
        )

        assert reponse.status_code == 200, reponse.text
        corps = reponse.json()
        assert corps["cumul"] == 0  # non validée : le cumul ne compte pas encore
        (volee,) = corps["volees"]
        assert volee["numero"] == 1
        assert volee["valeurs"] == ["10", "9", "8"]
        assert volee["saisie_par"] == "DURAND"
        assert volee["verrouillee"] is False
        assert volee["saisie_le"] is not None  # le « quand » (ex-017) est bien porté


def test_saisir_pour_un_archer_hors_de_sa_cible_rend_403(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Garde ADR-0033 §3 bout en bout : un archer d'une autre cible → 403 saisie_hors_cible."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _fixer_depart(client, s)
        db: Database = app_saisie.state.database
        categorie_id = CategorieRepositorySQL(db.session_factory).par_tournoi(s.tournoi_id)[0].id
        assert categorie_id is not None
        # Un archer placé sur la cible 2 (pas celle du poste, qui sert la cible 1).
        archer_cible_2 = _placer_archer(
            db, s.tournoi_id, s.depart_id, categorie_id, cible_index=2, position="A"
        )
        client.headers.pop("Authorization", None)  # le poste seul : la garde de cible doit mordre

        reponse = client.post(
            "/api/v1/saisie/volees",
            json={
                "tournoi_id": s.tournoi_id,
                "archer_id": archer_cible_2,
                "numero": 1,
                "valeurs": ["10", "9", "8"],
            },
            headers=_entete(s.jeton),
        )

        assert reponse.status_code == 403, reponse.text
        assert reponse.json()["code"] == "saisie_hors_cible"


def test_saisir_sans_session_rend_401(app_saisie: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Aucune session (ni admin ni poste) : la saisie est fermée au public (garde-fou écriture)."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        client.headers.pop("Authorization", None)

        reponse = client.post(
            "/api/v1/saisie/volees",
            json={
                "tournoi_id": s.tournoi_id,
                "archer_id": s.archer_id,
                "numero": 1,
                "valeurs": ["10", "9", "8"],
            },
        )

        assert reponse.status_code == 401, reponse.text


def test_saisir_une_valeur_hors_enum_rend_400(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Une valeur qui n'est pas une zone de score connue est rejetée à la frontière (400)."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _fixer_depart(client, s)

        reponse = client.post(
            "/api/v1/saisie/volees",
            json={
                "tournoi_id": s.tournoi_id,
                "archer_id": s.archer_id,
                "numero": 1,
                "valeurs": ["10", "42", "8"],  # « 42 » n'est pas une ZoneScore
            },
            headers=_entete(s.jeton),
        )

        assert reponse.status_code == 400, reponse.text


def test_saisir_deux_fois_le_meme_identifiant_ne_double_pas(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Idempotence (ADR-0036) : rejouer la même saisie (même identifiant) laisse une seule volée."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _fixer_depart(client, s)
        client.headers.pop("Authorization", None)  # chemin poste marqueur
        corps = {
            "tournoi_id": s.tournoi_id,
            "archer_id": s.archer_id,
            "numero": 1,
            "valeurs": ["10", "9", "8"],
            "identifiant_saisie": "geste-42",
        }

        premier = client.post("/api/v1/saisie/volees", json=corps, headers=_entete(s.jeton))
        rejeu = client.post("/api/v1/saisie/volees", json=corps, headers=_entete(s.jeton))

        assert premier.status_code == 200 and rejeu.status_code == 200
        assert premier.json() == rejeu.json()  # même état renvoyé
        assert len(rejeu.json()["volees"]) == 1  # pas de doublon


def test_lire_serie_vierge_rend_une_serie_vide(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un archer sans rien de saisi renvoie une série vide (200), pas un 404 (pavé vierge front)."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)

        reponse = client.get(
            f"/api/v1/saisie/series/{s.tournoi_id}/{s.archer_id}", headers=_entete(s.jeton)
        )

        assert reponse.status_code == 200, reponse.text
        assert reponse.json() == {
            "tournoi_id": s.tournoi_id,
            "archer_id": s.archer_id,
            "cumul": 0,
            "volees": [],
        }


def test_lire_serie_apres_saisie_porte_le_quand(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La relecture d'une série saisie porte les volées et le « quand » de chacune (ex-017)."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _fixer_depart(client, s)
        client.post(
            "/api/v1/saisie/volees",
            json={
                "tournoi_id": s.tournoi_id,
                "archer_id": s.archer_id,
                "numero": 1,
                "valeurs": ["10", "9", "8"],
                "saisie_par": "DURAND",
            },
            headers=_entete(s.jeton),
        )

        reponse = client.get(
            f"/api/v1/saisie/series/{s.tournoi_id}/{s.archer_id}", headers=_entete(s.jeton)
        )

        assert reponse.status_code == 200, reponse.text
        (volee,) = reponse.json()["volees"]
        assert volee["saisie_par"] == "DURAND"
        assert volee["saisie_le"] is not None


# --- Validation & correction (scoreur) ---


def _connecter_scoreur(client: TestClient, code: str) -> dict[str, str]:
    """Ouvre une session scoreur par code et renvoie l'en-tête `X-Jeton-Scoreur`."""
    jeton = client.post("/api/v1/scoreurs/session", json={"code": code}).json()["jeton"]
    return {"X-Jeton-Scoreur": jeton}


def _saisir_serie_complete(client: TestClient, s: Scenario) -> None:
    """Saisit les 2 volées du barème (chemin admin, seeding) : préalable à une validation."""
    for numero, valeurs in ((1, ["10", "9", "8"]), (2, ["9", "9", "9"])):
        reponse = client.post(
            "/api/v1/saisie/volees",
            json={
                "tournoi_id": s.tournoi_id,
                "archer_id": s.archer_id,
                "numero": numero,
                "valeurs": valeurs,
                "saisie_par": "DURAND",
            },
        )
        assert reponse.status_code == 200, reponse.text


def test_valider_verrouille_la_serie_au_nom_du_scoreur(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le scoreur valide : les volées se verrouillent à son nom, le cumul est arrêté (ex-007/8)."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _saisir_serie_complete(client, s)
        entete = _connecter_scoreur(client, s.scoreur_code)

        reponse = client.post(
            "/api/v1/saisie/validations",
            json={"tournoi_id": s.tournoi_id, "archer_id": s.archer_id},
            headers=entete,
        )

        assert reponse.status_code == 200, reponse.text
        corps = reponse.json()
        assert all(v["verrouillee"] for v in corps["volees"])
        assert all(v["validee_par"] == "ROUX" for v in corps["volees"])
        assert corps["cumul"] == 54  # (10+9+8) + (9+9+9)


def test_valider_par_un_scoreur_d_un_autre_tournoi_rend_403(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le scoreur est itinérant **dans son tournoi** : valider ailleurs → 403 (hors tournoi)."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _saisir_serie_complete(client, s)
        # Un scoreur d'un AUTRE tournoi (créé en admin).
        autre = TournoiRepositorySQL(app_saisie.state.database.session_factory).ajouter(
            Tournoi.creer("Extérieur", _DATE)
        )
        assert autre.id is not None
        code_autre = client.post(
            f"/api/v1/tournois/{autre.id}/scoreurs", json={"nom": "PICARD"}
        ).json()["code"]
        entete = _connecter_scoreur(client, code_autre)

        reponse = client.post(
            "/api/v1/saisie/validations",
            json={"tournoi_id": s.tournoi_id, "archer_id": s.archer_id},
            headers=entete,
        )

        assert reponse.status_code == 403, reponse.text
        assert reponse.json()["code"] == "scoreur_hors_tournoi"


def test_valider_sans_session_scoreur_rend_401(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La validation est réservée au scoreur : sans jeton scoreur → 401 (même avec l'admin)."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _saisir_serie_complete(client, s)

        reponse = client.post(
            "/api/v1/saisie/validations",
            json={"tournoi_id": s.tournoi_id, "archer_id": s.archer_id},
        )

        assert reponse.status_code == 401, reponse.text


def test_corriger_une_volee_verrouillee_recalcule_le_cumul(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Après validation, le scoreur corrige une volée verrouillée : valeurs et cumul suivent."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _saisir_serie_complete(client, s)
        entete = _connecter_scoreur(client, s.scoreur_code)
        client.post(
            "/api/v1/saisie/validations",
            json={"tournoi_id": s.tournoi_id, "archer_id": s.archer_id},
            headers=entete,
        )

        reponse = client.post(
            "/api/v1/saisie/corrections",
            json={
                "tournoi_id": s.tournoi_id,
                "archer_id": s.archer_id,
                "numero": 1,
                "valeurs": ["10", "10", "10"],
            },
            headers=entete,
        )

        assert reponse.status_code == 200, reponse.text
        corps = reponse.json()
        volee_1 = next(v for v in corps["volees"] if v["numero"] == 1)
        assert volee_1["valeurs"] == ["10", "10", "10"]
        assert corps["cumul"] == 57  # (10+10+10) + (9+9+9)
