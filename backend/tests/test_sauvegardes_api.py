"""Test bout-en-bout de l'API des sauvegardes (E11US006) — câblage, écrit après la route.

HTTP → file d'écriture → `ServiceSauvegardes` → `MagasinSauvegardesSQLite`, sur une base migrée
réelle : la restauration se vérifie par ce que les **autres** routes relisent ensuite.
"""

from __future__ import annotations

import datetime
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from infrastructure.backup.sauvegarde import SauvegardeSQLite
from tests.base_migree import preparer_base
from tests.conftest import ConnecterAdmin

_SAUVEGARDE = "kervignarc-20261003-090000.db"


class _Horloge9h:
    def maintenant(self) -> datetime.datetime:
        return datetime.datetime(2026, 10, 3, 9, 0, tzinfo=datetime.UTC)


@pytest.fixture
def base(tmp_path: Path) -> Path:
    chemin = tmp_path / "kervignarc.db"
    preparer_base(f"sqlite:///{chemin.as_posix()}")
    return chemin


@pytest.fixture
def dossier(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    chemin = tmp_path / "backups"
    monkeypatch.setenv("KERVIGNARC_BACKUP_DIR", str(chemin))
    return chemin


@pytest.fixture
def app(base: Path, dossier: Path, tmp_path: Path) -> Iterator[FastAPI]:
    application = create_app(f"sqlite:///{base.as_posix()}", admin_env_path=tmp_path / ".env")
    try:
        yield application
    finally:
        application.state.database.engine.dispose()


@pytest.fixture
def client(app: FastAPI, connecter_admin: ConnecterAdmin) -> Iterator[TestClient]:
    with TestClient(app) as client:
        connecter_admin(client)
        yield client


def _clubs(client: TestClient) -> list[str]:
    return [c["nom"] for c in client.get("/api/v1/clubs").json()]


def test_restaurer_revient_a_l_etat_de_la_sauvegarde_et_en_garde_une_copie(
    client: TestClient, base: Path, dossier: Path
) -> None:
    assert client.post("/api/v1/clubs", json={"nom": "Avant"}).status_code == 201
    SauvegardeSQLite(base, dossier, 5, _Horloge9h()).sauvegarder()
    assert client.post("/api/v1/clubs", json={"nom": "Après"}).status_code == 201

    liste = client.get("/api/v1/sauvegardes")
    assert liste.status_code == 200
    assert [(s["nom"], s["nature"]) for s in liste.json()] == [(_SAUVEGARDE, "periodique")]

    verification = client.post(f"/api/v1/sauvegardes/{_SAUVEGARDE}/verification")
    assert verification.json() == {"nom": _SAUVEGARDE, "verdict": "restaurable"}

    restauration = client.post(f"/api/v1/sauvegardes/{_SAUVEGARDE}/restauration")

    assert restauration.status_code == 200, restauration.text
    copie = restauration.json()["copie_de_securite"]
    assert copie.startswith("avant-restauration-")
    assert _clubs(client) == ["Avant"]
    natures = {s["nom"]: s["nature"] for s in client.get("/api/v1/sauvegardes").json()}
    assert natures == {_SAUVEGARDE: "periodique", copie: "avant_restauration"}

    # CA 4 : restaurer la copie annule la restauration.
    assert client.post(f"/api/v1/sauvegardes/{copie}/restauration").status_code == 200
    assert sorted(_clubs(client)) == ["Après", "Avant"]


def test_restaurer_oublie_sessions_scoreur_et_idempotence_mais_pas_l_admin(
    client: TestClient, app: FastAPI, base: Path, dossier: Path
) -> None:
    tournoi = client.post("/api/v1/tournois", json={"nom": "T", "date": "2026-10-03"}).json()
    scoreur = client.post(f"/api/v1/tournois/{tournoi['id']}/scoreurs", json={"nom": "Lou"})
    SauvegardeSQLite(base, dossier, 5, _Horloge9h()).sauvegarder()
    session = client.post("/api/v1/scoreurs/session", json={"code": scoreur.json()["code"]})
    jeton = session.json()["jeton"]
    # Une saisie déjà traitée : son rejeu après restauration doit s'exécuter de nouveau.
    idempotence = app.state.registre_idempotence
    idempotence.executer("volee-1", lambda: "premiere")

    assert client.post(f"/api/v1/sauvegardes/{_SAUVEGARDE}/restauration").status_code == 200

    assert idempotence.executer("volee-1", lambda: "rejouee") == "rejouee"

    deconnexion = client.post(
        "/api/v1/scoreurs/session/deconnexion", headers={"X-Jeton-Scoreur": jeton}
    )
    assert deconnexion.status_code == 401
    assert client.get("/api/v1/sauvegardes").status_code == 200  # l'admin reste connecté


def test_un_nom_inconnu_est_introuvable(client: TestClient) -> None:
    for action in ("verification", "restauration"):
        reponse = client.post(f"/api/v1/sauvegardes/kervignarc.db/{action}")
        assert reponse.status_code == 404
        assert reponse.json()["code"] == "sauvegarde_introuvable"


def test_une_sauvegarde_corrompue_est_refusee_sans_rien_toucher(
    client: TestClient, dossier: Path
) -> None:
    assert client.post("/api/v1/clubs", json={"nom": "Intact"}).status_code == 201
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / _SAUVEGARDE).write_bytes(b"pas une base" * 500)

    verification = client.post(f"/api/v1/sauvegardes/{_SAUVEGARDE}/verification")
    restauration = client.post(f"/api/v1/sauvegardes/{_SAUVEGARDE}/restauration")

    assert verification.json()["verdict"] == "corrompue"
    assert restauration.status_code == 400
    assert restauration.json()["details"] == {"verdict": "corrompue"}
    assert _clubs(client) == ["Intact"]
    assert [s["nom"] for s in client.get("/api/v1/sauvegardes").json()] == [_SAUVEGARDE]


def test_les_routes_sont_reservees_a_l_admin(app: FastAPI) -> None:
    with TestClient(app) as anonyme:
        assert anonyme.get("/api/v1/sauvegardes").status_code == 401
        assert anonyme.post(f"/api/v1/sauvegardes/{_SAUVEGARDE}/restauration").status_code == 401
