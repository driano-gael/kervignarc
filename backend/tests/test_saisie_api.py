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
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from domain.archer import Archer
from domain.bareme import BaremeQualification
from domain.blason import Blason, ZoneScore
from domain.categorie import Categorie
from domain.depart import Depart
from domain.entree_audit import ActionAuditee
from domain.gabarit_salle import GabaritSalle
from domain.grain_validation import GrainValidation
from domain.inscription import Inscription
from domain.phase import Phase
from domain.placement import Affectation
from domain.tournoi import Tournoi
from infrastructure.db import (
    ArcherRepositorySQL,
    AuditRepositorySQL,
    BlasonRepositorySQL,
    CategorieRepositorySQL,
    Database,
    DepartRepositorySQL,
    GabaritSalleRepositorySQL,
    InscriptionRepositorySQL,
    PlacementRepositorySQL,
    TournoiRepositorySQL,
)
from tests.base_migree import preparer_base
from tests.conftest import ConnecterAdmin, poser_phase_sql

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)


def _migrer(url: str) -> None:
    preparer_base(url)


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
    inscription = InscriptionRepositorySQL(sf, AuditRepositorySQL(sf)).ajouter(
        Inscription.creer(archer.id, depart_id)
    )
    assert inscription.id is not None
    PlacementRepositorySQL(sf, AuditRepositorySQL(sf)).poser_plusieurs(
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
    # ⚠️ **Un tournoi témoin d'abord** (2ᵉ correctif de revue E05US025). `TournoiId`, `DepartId` et
    # `PhaseId` sont trois alias d'`int` (`DETTE-044`) : sur une base neuve, le premier tournoi, son
    # premier créneau et sa première phase reçoivent tous l'identifiant 1, et **toute** confusion
    # entre eux passe au vert. C'est ce qui a laissé ce fichier — celui qui couvre les trois routes
    # d'écriture de la saisie — ne rien prouver du « quand » lu sur `serie.phase_id`.
    TournoiRepositorySQL(sf).ajouter(Tournoi.creer("Témoin", _DATE))
    tournoi = TournoiRepositorySQL(sf).ajouter(Tournoi.creer("Salle 18m", _DATE))
    assert tournoi.id is not None and tournoi.id != 1
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
    depart = DepartRepositorySQL(sf).ajouter(
        Depart.creer(tournoi.id, 1, tarif_centimes=1000, horaire="09:00")
    )
    assert depart.id is not None
    poser_phase_sql(
        sf,
        Phase.qualification(
            depart_id=depart.id,
            bareme=BaremeQualification.creer(2, 3),
            validation=GrainValidation.fin_de_serie(),
        ),
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
            {
                "position": "A",
                "archer_id": s.archer_id,
                "nom": "CIBLE1A",
                "prenom": "Alice",
                # CA « pavé » : les zones du blason de l'archer, ordre canonique centre→extérieur.
                "zones": [z.value for z in ZoneScore],
                # E04US018 : l'archer n'a ni abandonné ni été disqualifié — sa série peut encore
                # se compléter. Le client s'en sert pour savoir quand la cible a **fini** de tirer.
                "forfait": False,
            }
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
            Depart.creer(autre.id, 1, tarif_centimes=1000, horaire="09:00")
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
        assert all(v["saisie_le"] is not None for v in corps["volees"])  # le « quand » remonte
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


def _traces(app: FastAPI, tournoi_id: int, action: ActionAuditee) -> int:
    """Nombre d'entrées d'audit d'une action donnée pour un tournoi (tests d'idempotence)."""
    audit = AuditRepositorySQL(app.state.database.session_factory)
    return sum(1 for e in audit.par_tournoi(tournoi_id) if e.action is action)


def test_valider_deux_fois_le_meme_identifiant_ne_double_pas_la_trace(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Idempotence sur le seul acte qui compte : un rejeu de **validation** n'empile pas 2 traces.

    La saisie est déjà idempotente par upsert ; c'est la validation (trace d'audit en ajout seul)
    que le mécanisme (ADR-0036) doit dédoublonner. Sans dédup : 2 traces VALIDATION ; avec : 1.
    """
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _saisir_serie_complete(client, s)
        entete = _connecter_scoreur(client, s.scoreur_code)
        corps = {
            "tournoi_id": s.tournoi_id,
            "archer_id": s.archer_id,
            "identifiant_saisie": "val-1",
        }

        premier = client.post("/api/v1/saisie/validations", json=corps, headers=entete)
        rejeu = client.post("/api/v1/saisie/validations", json=corps, headers=entete)

        assert premier.status_code == 200 and rejeu.status_code == 200
        assert premier.json() == rejeu.json()
        assert _traces(app_saisie, s.tournoi_id, ActionAuditee.VALIDATION) == 1


def test_corriger_deux_fois_le_meme_identifiant_ne_double_pas_la_trace(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un rejeu de **correction** (acte non idempotent par nature) n'empile pas 2 traces."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _saisir_serie_complete(client, s)
        entete = _connecter_scoreur(client, s.scoreur_code)
        client.post(
            "/api/v1/saisie/validations",
            json={"tournoi_id": s.tournoi_id, "archer_id": s.archer_id},
            headers=entete,
        )
        corps = {
            "tournoi_id": s.tournoi_id,
            "archer_id": s.archer_id,
            "numero": 1,
            "valeurs": ["10", "10", "10"],
            "identifiant_saisie": "corr-1",
        }

        premier = client.post("/api/v1/saisie/corrections", json=corps, headers=entete)
        rejeu = client.post("/api/v1/saisie/corrections", json=corps, headers=entete)

        assert premier.status_code == 200 and rejeu.status_code == 200
        assert premier.json() == rejeu.json()
        assert _traces(app_saisie, s.tournoi_id, ActionAuditee.CORRECTION_SCORE) == 1


def test_meme_identifiant_deux_archers_ecrit_les_deux(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Clé scopée (ADR-0036 §4) : le même identifiant réutilisé sur deux archers écrit les DEUX.

    Avec une clé **globale** (avant correctif), la 2ᵉ saisie ferait cache-hit sur la 1ʳᵉ et
    renverrait la série de l'archer 1 — l'écriture de l'archer 2 **perdue en silence**. Ce test
    échoue si la clé n'est plus scopée par archer.
    """
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)  # admin connecté : contexte=None
        db: Database = app_saisie.state.database
        cat = CategorieRepositorySQL(db.session_factory).par_tournoi(s.tournoi_id)[0].id
        assert cat is not None
        archer_b = _placer_archer(db, s.tournoi_id, s.depart_id, cat, cible_index=2, position="A")
        base = {
            "tournoi_id": s.tournoi_id,
            "numero": 1,
            "valeurs": ["10", "9", "8"],
            "identifiant_saisie": "collision",
        }

        r1 = client.post("/api/v1/saisie/volees", json={**base, "archer_id": s.archer_id})
        r2 = client.post("/api/v1/saisie/volees", json={**base, "archer_id": archer_b})

        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["archer_id"] == s.archer_id
        assert r2.json()["archer_id"] == archer_b  # PAS le cache de l'archer 1 → clé scopée


def test_meme_identifiant_deux_numeros_ecrit_les_deux(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Clé scopée par **numéro** : même identifiant sur les volées 1 puis 2 → deux volées écrites.

    Sans le `:numero:` dans la clé, la volée 2 ferait cache-hit sur la 1 et ne s'écrirait jamais.
    """
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)  # admin : contexte=None
        base = {
            "tournoi_id": s.tournoi_id,
            "archer_id": s.archer_id,
            "valeurs": ["10", "9", "8"],
            "identifiant_saisie": "meme-id",
        }

        client.post("/api/v1/saisie/volees", json={**base, "numero": 1})
        r2 = client.post("/api/v1/saisie/volees", json={**base, "numero": 2})

        assert r2.status_code == 200, r2.text
        assert {v["numero"] for v in r2.json()["volees"]} == {1, 2}  # la volée 2 n'a pas été sautée


# --- Annulation d'une validation (E16US019) -------------------------------------------------


def _valider(client: TestClient, s: Scenario, entete: dict[str, str]) -> None:
    """Valide la série complète au nom du scoreur — préalable à toute annulation."""
    reponse = client.post(
        "/api/v1/saisie/validations",
        json={"tournoi_id": s.tournoi_id, "archer_id": s.archer_id},
        headers=entete,
    )
    assert reponse.status_code == 200, reponse.text


def test_annuler_rouvre_la_volee_sans_toucher_au_cumul(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le scoreur annule : la volée se rouvre à l'écriture, le total reste au classement."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _saisir_serie_complete(client, s)
        entete = _connecter_scoreur(client, s.scoreur_code)
        _valider(client, s, entete)

        reponse = client.post(
            "/api/v1/saisie/annulations",
            json={"tournoi_id": s.tournoi_id, "archer_id": s.archer_id, "numero": 1},
            headers=entete,
        )

        assert reponse.status_code == 200, reponse.text
        corps = reponse.json()
        assert corps["cumul"] == 54  # le score d'origine tient jusqu'à la ressaisie
        assert all(not v["verrouillee"] for v in corps["volees"])  # lot de fin de série
        assert all(v["en_correction"] for v in corps["volees"])
        assert all(v["validee_par"] == "ROUX" for v in corps["volees"])


def test_annuler_puis_ressaisir_au_poste_puis_revalider(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le parcours complet de S08 : *annuler → ressaisir sur la tablette → revalider*."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _saisir_serie_complete(client, s)
        entete = _connecter_scoreur(client, s.scoreur_code)
        _valider(client, s, entete)
        client.post(
            "/api/v1/saisie/annulations",
            json={"tournoi_id": s.tournoi_id, "archer_id": s.archer_id, "numero": 1},
            headers=entete,
        )

        # ⚠️ En-tête de poste **explicite**, et session admin retirée : sans cela c'est l'admin
        # de `_semer` qui écrivait, et le test promettait une garde qu'il ne traversait pas
        # (relevé en revue). Le chemin poste est celui qui passe par `ContexteSaisie` — et il
        # exige que la tablette ait choisi son départ courant (ADR-0034), ce que la version admin
        # du test contournait sans le dire.
        client.headers.pop("Authorization", None)
        depart = client.post(
            "/api/v1/saisie/depart-courant",
            json={"depart_id": s.depart_id},
            headers=_entete(s.jeton),
        )
        assert depart.status_code == 200, depart.text
        ressaisie = client.post(
            "/api/v1/saisie/volees",
            json={
                "tournoi_id": s.tournoi_id,
                "archer_id": s.archer_id,
                "numero": 1,
                "valeurs": ["6", "6", "6"],
                "saisie_par": "DURAND",
            },
            headers=_entete(s.jeton),
        )
        revalidation = client.post(
            "/api/v1/saisie/refermetures",
            json={"tournoi_id": s.tournoi_id, "archer_id": s.archer_id, "numero": 1},
            headers=entete,
        )

        assert ressaisie.status_code == 200, ressaisie.text
        assert revalidation.status_code == 200, revalidation.text
        corps = revalidation.json()
        assert corps["cumul"] == 45  # (6+6+6) + (9+9+9)
        assert all(v["verrouillee"] and not v["en_correction"] for v in corps["volees"])


def test_annuler_est_ouvert_a_l_admin(app_saisie: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """CA S08 : *« oui, par admin et scoreur »* — élargi, pas doublé (pas de route parallèle)."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _saisir_serie_complete(client, s)
        entete = _connecter_scoreur(client, s.scoreur_code)
        _valider(client, s, entete)

        # Sans en-tête scoreur : la session admin ouverte par `_semer` suffit.
        reponse = client.post(
            "/api/v1/saisie/annulations",
            json={"tournoi_id": s.tournoi_id, "archer_id": s.archer_id, "numero": 1},
        )

        assert reponse.status_code == 200, reponse.text
        assert _traces(app_saisie, s.tournoi_id, ActionAuditee.ANNULATION_VALIDATION) == 1


def test_annuler_par_un_scoreur_d_un_autre_tournoi_rend_403(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le scoreur reste borné à **son** tournoi, y compris pour annuler."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _saisir_serie_complete(client, s)
        _valider(client, s, _connecter_scoreur(client, s.scoreur_code))
        autre = TournoiRepositorySQL(app_saisie.state.database.session_factory).ajouter(
            Tournoi.creer("Extérieur", _DATE)
        )
        assert autre.id is not None
        code_autre = client.post(
            f"/api/v1/tournois/{autre.id}/scoreurs", json={"nom": "PICARD"}
        ).json()["code"]
        # ⚠️ Sans cela, la session admin ouverte par `_semer` satisferait la garde AVANT même
        # qu'elle regarde le jeton scoreur : le test passerait sans rien prouver.
        client.headers.pop("Authorization", None)

        reponse = client.post(
            "/api/v1/saisie/annulations",
            json={"tournoi_id": s.tournoi_id, "archer_id": s.archer_id, "numero": 1},
            headers=_connecter_scoreur(client, code_autre),
        )

        assert reponse.status_code == 403, reponse.text
        assert reponse.json()["code"] == "scoreur_hors_tournoi"


def test_annuler_deux_fois_le_meme_identifiant_ne_double_pas_la_trace(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un rejeu d'annulation n'empile pas deux traces (ADR-0036), comme validation et correction."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _saisir_serie_complete(client, s)
        entete = _connecter_scoreur(client, s.scoreur_code)
        _valider(client, s, entete)
        corps = {
            "tournoi_id": s.tournoi_id,
            "archer_id": s.archer_id,
            "numero": 1,
            "identifiant_saisie": "ann-1",
        }

        premier = client.post("/api/v1/saisie/annulations", json=corps, headers=entete)
        rejeu = client.post("/api/v1/saisie/annulations", json=corps, headers=entete)

        assert premier.status_code == 200 and rejeu.status_code == 200
        assert premier.json() == rejeu.json()
        assert _traces(app_saisie, s.tournoi_id, ActionAuditee.ANNULATION_VALIDATION) == 1


def test_le_scoreur_lit_la_feuille_de_son_tournoi(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """E16US019 : l'écran qui valide doit pouvoir afficher la feuille qu'il agit."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _saisir_serie_complete(client, s)
        entete = _connecter_scoreur(client, s.scoreur_code)
        client.headers.pop("Authorization", None)  # sans quoi c'est l'admin qui serait testé

        reponse = client.get(f"/api/v1/saisie/series/{s.tournoi_id}/{s.archer_id}", headers=entete)

        assert reponse.status_code == 200, reponse.text
        assert len(reponse.json()["volees"]) == 2


def test_le_scoreur_ne_lit_pas_la_feuille_d_un_autre_tournoi(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Élargir n'est pas ouvrir : le scoreur reste borné à **son** tournoi, en lecture aussi."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _saisir_serie_complete(client, s)
        autre = TournoiRepositorySQL(app_saisie.state.database.session_factory).ajouter(
            Tournoi.creer("Extérieur", _DATE)
        )
        assert autre.id is not None
        code_autre = client.post(
            f"/api/v1/tournois/{autre.id}/scoreurs", json={"nom": "PICARD"}
        ).json()["code"]
        entete = _connecter_scoreur(client, code_autre)
        client.headers.pop("Authorization", None)

        reponse = client.get(f"/api/v1/saisie/series/{s.tournoi_id}/{s.archer_id}", headers=entete)

        assert reponse.status_code == 403, reponse.text
        assert reponse.json()["code"] == "scoreur_hors_tournoi"


def test_un_poste_de_cible_ne_peut_pas_annuler_une_validation(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Élargir n'est pas ouvrir : l'annulation reste fermée à la tablette.

    ⚠️ **Oracle de non-garde** : la garde est `_admin_ou_scoreur`, qui ne regarde jamais le jeton
    de poste — donc le refus est vrai *par construction* et rien ne l'épingle. Or le réflexe, sur
    ce routeur, est de monter `autoriser_saisie` (la garde des routes voisines) : ce test est ce
    qui rougirait si quelqu'un le faisait, ouvrant l'annulation à toute tablette de la salle.
    """
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _saisir_serie_complete(client, s)
        _valider(client, s, _connecter_scoreur(client, s.scoreur_code))
        client.headers.pop("Authorization", None)

        reponse = client.post(
            "/api/v1/saisie/annulations",
            json={"tournoi_id": s.tournoi_id, "archer_id": s.archer_id, "numero": 1},
            headers=_entete(s.jeton),
        )

        assert reponse.status_code == 401, reponse.text


def test_valider_refuse_de_deviner_quel_lot_refermer(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """⚠️ **Oracle du bloquant de 3ᵉ passe** : `POST /validations` ne reçoit aucune cible.

    Deux rédactions successives l'ont laissé deviner — « toutes les corrections », puis « la plus
    ancienne » — et les deux re-signaient « valides » des volées que le scoreur n'avait jamais
    relues, sous **son** nom, dans le registre qu'on ouvre en contestation. Refuser est la seule
    réponse honnête : le lot se referme par `POST /refermetures`, qui le **nomme**.
    """
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _saisir_serie_complete(client, s)
        entete = _connecter_scoreur(client, s.scoreur_code)
        _valider(client, s, entete)
        client.post(
            "/api/v1/saisie/annulations",
            json={"tournoi_id": s.tournoi_id, "archer_id": s.archer_id, "numero": 1},
            headers=entete,
        )

        reponse = client.post(
            "/api/v1/saisie/validations",
            json={"tournoi_id": s.tournoi_id, "archer_id": s.archer_id},
            headers=entete,
        )

        assert reponse.status_code == 422, reponse.text
        assert reponse.json()["code"] == "correction_ouverte"


def test_refermer_une_correction_est_reserve_au_scoreur(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Refermer fait **avancer** le tour : même garde que valider, pas celle d'annuler."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _saisir_serie_complete(client, s)
        entete = _connecter_scoreur(client, s.scoreur_code)
        _valider(client, s, entete)
        client.post(
            "/api/v1/saisie/annulations",
            json={"tournoi_id": s.tournoi_id, "archer_id": s.archer_id, "numero": 1},
            headers=entete,
        )

        # La session admin de `_semer` est encore ouverte : elle ne doit pas suffire.
        reponse = client.post(
            "/api/v1/saisie/refermetures",
            json={"tournoi_id": s.tournoi_id, "archer_id": s.archer_id, "numero": 1},
        )

        assert reponse.status_code == 401, reponse.text


# --- Préséance de rôle (E16US020, ADR-0107) ---


def _corps_volee(s: Scenario, valeurs: list[str]) -> dict[str, object]:
    """Le corps d'une saisie de la volée 1 ; sans `identifiant_saisie`, donc sans déduplication."""
    return {
        "tournoi_id": s.tournoi_id,
        "archer_id": s.archer_id,
        "numero": 1,
        "valeurs": valeurs,
    }


def test_un_poste_ne_peut_pas_ecraser_la_saisie_de_l_organisateur(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """E16US020 bout en bout : rôle inférieur → **409** `ecriture_de_role_inferieur`."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _fixer_depart(client, s)
        premier = client.post("/api/v1/saisie/volees", json=_corps_volee(s, ["10", "9", "8"]))
        assert premier.status_code == 200, premier.text  # l'admin écrit d'abord
        client.headers.pop("Authorization", None)  # puis le poste tente d'écraser

        reponse = client.post(
            "/api/v1/saisie/volees",
            json=_corps_volee(s, ["6", "6", "6"]),
            headers=_entete(s.jeton),
        )

        assert reponse.status_code == 409, reponse.text
        assert reponse.json()["code"] == "ecriture_de_role_inferieur"
        # ⚠️ Le CA exige que le refus dise QUI a écrit. Sans cette ligne, remplacer le message par
        # « Écriture refusée. » laissait tout vert et l'écran affichait un refus anonyme — le
        # « refus muet » que le CA écarte. Relevé en revue (axe B).
        assert "l'organisateur" in reponse.json()["message"], reponse.text


def test_l_organisateur_ecrase_la_saisie_d_un_poste(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le sens montant passe : la hiérarchie **arbitre**, elle ne fige pas la volée."""
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _fixer_depart(client, s)
        entete_admin = dict(client.headers)
        client.headers.pop("Authorization", None)
        poste = client.post(
            "/api/v1/saisie/volees",
            json=_corps_volee(s, ["6", "6", "6"]),
            headers=_entete(s.jeton),
        )
        assert poste.status_code == 200, poste.text
        client.headers["Authorization"] = entete_admin["authorization"]

        reponse = client.post("/api/v1/saisie/volees", json=_corps_volee(s, ["10", "9", "8"]))

        assert reponse.status_code == 200, reponse.text
        (volee,) = reponse.json()["volees"]
        assert volee["valeurs"] == ["10", "9", "8"]
        # ⚠️ Sans cette 2ᵉ moitié le test serait un placebo : une restauration ratée de l'en-tête
        # d'admin ferait réécrire le POSTE, à rôle égal, avec le même 200 et les mêmes valeurs.
        client.headers.pop("Authorization", None)
        refus = client.post(
            "/api/v1/saisie/volees",
            json=_corps_volee(s, ["1", "1", "1"]),
            headers=_entete(s.jeton),
        )
        assert refus.status_code == 409, refus.text


def test_un_scoreur_n_est_pas_une_identite_de_saisie_de_qualification(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Garde-fou du rang du MILIEU : `autoriser_saisie` n'admet que l'admin et le poste.

    ⚠️ Ce test rougira le jour où cette route s'ouvrira au scoreur — et c'est son office :
    `_role_de_saisie` lit `contexte is None` comme « admin », donc l'élargir sans faire porter le
    rôle par `ContexteSaisie` donnerait au scoreur la préséance de l'organisateur (ADR-0107).
    """
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        entete = _connecter_scoreur(client, s.scoreur_code)
        client.headers.pop("Authorization", None)

        reponse = client.post(
            "/api/v1/saisie/volees", json=_corps_volee(s, ["10", "9", "8"]), headers=entete
        )

        assert reponse.status_code == 401, reponse.text


def test_deux_postes_se_succedent_sans_conflit(
    app_saisie: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA « à rôles ÉGAUX » au niveau HTTP : le second gagne, **200**, aucun 409.

    ⚠️ Le CA écrit ce test en toutes lettres (« deux postes écrivent successivement : le second
    gagne, `200`, aucun `409` »). Le renoncement est prouvé au service ; le `200` littéral, lui,
    ne l'était nulle part — et c'est le cas le plus fréquent en salle.
    """
    with TestClient(app_saisie) as client:
        s = _semer(app_saisie, client, connecter_admin)
        _fixer_depart(client, s)
        client.headers.pop("Authorization", None)
        premier = client.post(
            "/api/v1/saisie/volees",
            json=_corps_volee(s, ["6", "6", "6"]),
            headers=_entete(s.jeton),
        )
        assert premier.status_code == 200, premier.text

        reponse = client.post(
            "/api/v1/saisie/volees",
            json=_corps_volee(s, ["10", "10", "10"]),
            headers=_entete(s.jeton),
        )

        assert reponse.status_code == 200, reponse.text
        (volee,) = reponse.json()["volees"]
        assert volee["valeurs"] == ["10", "10", "10"]
