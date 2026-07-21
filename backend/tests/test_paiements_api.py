"""Test bout-en-bout de l'API paiements (E08US002).

Traverse toutes les couches — DTO Pydantic → (file d'écriture) → service → repository → DB — sur les
routes `/api/v1/tournois/{id}/paiements/...`, et vérifie le mapping des erreurs typées :
- vue par archer (dû / payé / reste), vue par club (totaux + bucket « sans club ») ;
- marquage groupé par archer et par club (PUT), avec relecture des vues ;
- 404 (tournoi / archer / club inconnus) et garde admin (401) ;
- la trace d'audit `PAIEMENT` apparaît dans le journal après un marquage.

Test **après** implémentation (règle 9 : API/câblage, pas d'oracle en jeu).
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
def app_paiements(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _preparer(client: TestClient) -> dict[str, int]:
    """Monte un tournoi complet : 1 club, 2 archers (dont 1 sans club), 2 départs, inscriptions.

    - archer A (club Rennes) inscrit sur dép1 (810, payé) et dép2 (1000, non payé) ;
    - archer B (sans club) inscrit sur dép1 (810, non payé).
    Renvoie les identifiants utiles.
    """
    tid = client.post("/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14"}).json()[
        "id"
    ]
    categorie_id = client.post(
        f"/api/v1/tournois/{tid}/categories", json={"libelle": "Senior 1 H"}
    ).json()["id"]
    club_id = client.post("/api/v1/clubs", json={"nom": "Arc Rennes"}).json()["id"]
    archer_a = client.post(
        f"/api/v1/tournois/{tid}/archers",
        json={"nom": "Un", "prenom": "Alice", "categorie_id": categorie_id, "club_id": club_id},
    ).json()["id"]
    archer_b = client.post(
        f"/api/v1/tournois/{tid}/archers",
        json={"nom": "Deux", "prenom": "Bob", "categorie_id": categorie_id},
    ).json()["id"]
    dep1 = client.post(f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": 810}).json()["id"]
    dep2 = client.post(f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": 1000}).json()[
        "id"
    ]
    ins_a1 = client.post(
        f"/api/v1/archers/{archer_a}/inscriptions", json={"depart_id": dep1}
    ).json()["id"]
    client.post(f"/api/v1/archers/{archer_a}/inscriptions", json={"depart_id": dep2})
    client.post(f"/api/v1/archers/{archer_b}/inscriptions", json={"depart_id": dep1})
    client.put(f"/api/v1/inscriptions/{ins_a1}", json={"paye": True})  # A a réglé le dép1
    return {"tid": tid, "club_id": club_id, "archer_a": archer_a, "archer_b": archer_b}


def test_vue_par_archer(app_paiements: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """GET .../paiements/archers renvoie dû/payé/reste par archer, trié par nom."""
    with TestClient(app_paiements) as client:
        connecter_admin(client)
        ids = _preparer(client)
        lignes = client.get(f"/api/v1/tournois/{ids['tid']}/paiements/archers")
        assert lignes.status_code == 200, lignes.text
        corps = lignes.json()

    par_id = {ligne["archer_id"]: ligne for ligne in corps}
    a = par_id[ids["archer_a"]]["recap"]
    assert (a["du_centimes"], a["paye_centimes"], a["reste_centimes"]) == (1810, 810, 1000)
    b = par_id[ids["archer_b"]]["recap"]
    assert (b["du_centimes"], b["paye_centimes"], b["reste_centimes"]) == (810, 0, 810)
    # Trié par nom : « Deux » avant « Un ».
    assert [ligne["nom"] for ligne in corps] == ["Deux", "Un"]


def test_vue_par_club_avec_bucket_sans_club(
    app_paiements: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """GET .../paiements/clubs agrège par club et place les sans-club en dernier."""
    with TestClient(app_paiements) as client:
        connecter_admin(client)
        ids = _preparer(client)
        recaps = client.get(f"/api/v1/tournois/{ids['tid']}/paiements/clubs").json()

    assert [r["nom"] for r in recaps] == ["Arc Rennes", "Sans club"]
    rennes = recaps[0]
    assert rennes["club_id"] == ids["club_id"]
    assert (rennes["recap"]["du_centimes"], rennes["recap"]["paye_centimes"]) == (1810, 810)
    sans_club = recaps[1]
    assert sans_club["club_id"] is None
    assert sans_club["recap"]["du_centimes"] == 810
    assert [a["prenom"] for a in sans_club["archers"]] == ["Bob"]


def test_marquer_archer_regle_tout(app_paiements: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """PUT .../paiements/archers/{id} marque toutes ses inscriptions (reste tombe à 0)."""
    with TestClient(app_paiements) as client:
        connecter_admin(client)
        ids = _preparer(client)
        maj = client.put(
            f"/api/v1/tournois/{ids['tid']}/paiements/archers/{ids['archer_a']}",
            json={"paye": True},
        )
        assert maj.status_code == 200, maj.text
        assert maj.json()["recap"]["reste_centimes"] == 0

        lignes = client.get(f"/api/v1/tournois/{ids['tid']}/paiements/archers").json()
    a = next(ligne for ligne in lignes if ligne["archer_id"] == ids["archer_a"])
    assert a["recap"]["paye_centimes"] == 1810


def test_marquer_club_regle_ses_archers(
    app_paiements: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """PUT .../paiements/clubs/{id} marque les inscriptions des archers du club."""
    with TestClient(app_paiements) as client:
        connecter_admin(client)
        ids = _preparer(client)
        maj = client.put(
            f"/api/v1/tournois/{ids['tid']}/paiements/clubs/{ids['club_id']}",
            json={"paye": True},
        )
        assert maj.status_code == 200, maj.text
        assert maj.json()["recap"]["reste_centimes"] == 0
        # L'archer sans club (Bob) n'est pas dans ce club : son reste demeure.
        lignes = client.get(f"/api/v1/tournois/{ids['tid']}/paiements/archers").json()
    b = next(ligne for ligne in lignes if ligne["archer_id"] == ids["archer_b"])
    assert b["recap"]["reste_centimes"] == 810


def test_marquer_alimente_le_journal_d_audit(
    app_paiements: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un marquage groupé laisse une entrée `PAIEMENT` dans le journal d'audit (E10US005)."""
    with TestClient(app_paiements) as client:
        connecter_admin(client)
        ids = _preparer(client)
        client.put(
            f"/api/v1/tournois/{ids['tid']}/paiements/archers/{ids['archer_a']}",
            json={"paye": True},
        )
        journal = client.get(f"/api/v1/tournois/{ids['tid']}/audit").json()
    actions = [entree["action"] for entree in journal]
    assert "paiement" in actions


def test_vue_tournoi_inconnu_404(app_paiements: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Consulter les paiements d'un tournoi inexistant → 404 `tournoi_introuvable`."""
    with TestClient(app_paiements) as client:
        connecter_admin(client)
        rejet = client.get("/api/v1/tournois/999/paiements/archers")
    assert rejet.status_code == 404
    assert rejet.json()["code"] == "tournoi_introuvable"


def test_marquer_archer_inconnu_404(
    app_paiements: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Marquer un archer inexistant → 404 `archer_introuvable`."""
    with TestClient(app_paiements) as client:
        connecter_admin(client)
        ids = _preparer(client)
        rejet = client.put(
            f"/api/v1/tournois/{ids['tid']}/paiements/archers/999", json={"paye": True}
        )
    assert rejet.status_code == 404
    assert rejet.json()["code"] == "archer_introuvable"


def test_marquer_club_inconnu_404(app_paiements: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Marquer un club inexistant → 404 `club_introuvable`."""
    with TestClient(app_paiements) as client:
        connecter_admin(client)
        ids = _preparer(client)
        rejet = client.put(
            f"/api/v1/tournois/{ids['tid']}/paiements/clubs/999", json={"paye": True}
        )
    assert rejet.status_code == 404
    assert rejet.json()["code"] == "club_introuvable"


def test_consultation_sans_session_admin_401(app_paiements: FastAPI) -> None:
    """Consulter les paiements sans être connecté admin → 401 (données non publiques)."""
    with TestClient(app_paiements) as client:
        rejet = client.get("/api/v1/tournois/1/paiements/archers")
    assert rejet.status_code == 401
