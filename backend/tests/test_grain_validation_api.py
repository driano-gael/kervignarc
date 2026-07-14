"""Test bout-en-bout de l'API grain de validation (E01US015, `D-11`).

Traverse toutes les couches — DTO Pydantic → file d'écriture → service → repository → DB, puis
relecture — et vérifie le **mapping des erreurs typées** à la frontière :
- absence de qualification → `null` en lecture, 404 en écriture ; preset `fin de série` à la
  création du barème ; définition (PUT) puis relecture ;
- lecture publique ; définition réservée à l'admin (401) ;
- tournoi inconnu → 404 ; grain ou cadence hors règle → 422 ; corps invalide → 400.
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
def app_grain(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _creer_tournoi(client: TestClient) -> int:
    """Crée un tournoi via l'API (admin déjà connecté) et renvoie son identifiant."""
    reponse = client.post("/api/v1/tournois", json={"nom": "Kervignarc", "date": "2026-03-14"})
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def _creer_tournoi_avec_bareme(client: TestClient, nb_volees: int = 20) -> int:
    """Crée un tournoi **et** son barème : la phase de qualification existe donc."""
    tournoi_id = _creer_tournoi(client)
    reponse = client.put(
        f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
        json={"nb_volees": nb_volees, "nb_fleches_par_volee": 3},
    )
    assert reponse.status_code == 200, reponse.text
    return tournoi_id


def test_grain_null_tant_que_le_bareme_nest_pas_defini(
    app_grain: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Sans phase de qualification, la lecture renvoie `null` (pas une erreur)."""
    with TestClient(app_grain) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        assert client.get(f"/api/v1/tournois/{tournoi_id}/grain-validation").json() is None


def test_definir_le_bareme_pose_le_preset_fin_de_serie(
    app_grain: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La phase naît avec le preset de son type : la qualification valide en fin de série."""
    with TestClient(app_grain) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi_avec_bareme(client)

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/grain-validation")
        assert reponse.status_code == 200
        assert reponse.json() == {"grain": "fin_de_serie", "n_volees": None}


def test_definir_puis_relire(app_grain: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """PUT définit le grain (via la file) ; GET le relit, cadence comprise."""
    with TestClient(app_grain) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi_avec_bareme(client)

        definition = client.put(
            f"/api/v1/tournois/{tournoi_id}/grain-validation",
            json={"grain": "toutes_les_n_volees", "n_volees": 2},
        )
        assert definition.status_code == 200, definition.text
        assert definition.json() == {"grain": "toutes_les_n_volees", "n_volees": 2}
        assert (
            client.get(f"/api/v1/tournois/{tournoi_id}/grain-validation").json()
            == definition.json()
        )


def test_revenir_a_fin_de_serie_efface_la_cadence(
    app_grain: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Repasser à un grain de fin abandonne la cadence : elle ne serait plus jamais lue."""
    with TestClient(app_grain) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi_avec_bareme(client)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/grain-validation",
            json={"grain": "toutes_les_n_volees", "n_volees": 2},
        )

        retour = client.put(
            f"/api/v1/tournois/{tournoi_id}/grain-validation",
            json={"grain": "fin_de_serie"},
        )
        assert retour.status_code == 200
        assert retour.json() == {"grain": "fin_de_serie", "n_volees": None}


def test_definir_le_grain_preserve_le_bareme(
    app_grain: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Les deux politiques vivent sur la même phase sans se marcher dessus."""
    with TestClient(app_grain) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi_avec_bareme(client)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/grain-validation",
            json={"grain": "toutes_les_n_volees", "n_volees": 4},
        )

        bareme = client.get(f"/api/v1/tournois/{tournoi_id}/bareme-qualification").json()
        assert bareme["nb_volees"] == 20
        assert bareme["score_max"] == 600


def test_lire_est_public(app_grain: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Le grain d'un tournoi est lisible sans session (lecture publique)."""
    with TestClient(app_grain) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi_avec_bareme(client)
    with TestClient(app_grain) as anonyme:
        reponse = anonyme.get(f"/api/v1/tournois/{tournoi_id}/grain-validation")
    assert reponse.status_code == 200
    assert reponse.json()["grain"] == "fin_de_serie"


def test_definir_sans_jeton_401(app_grain: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Définir le grain est une action admin : refusée sans session (401)."""
    with TestClient(app_grain) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi_avec_bareme(client)
    with TestClient(app_grain) as anonyme:
        reponse = anonyme.put(
            f"/api/v1/tournois/{tournoi_id}/grain-validation",
            json={"grain": "fin_de_serie"},
        )
    assert reponse.status_code == 401
    assert reponse.json()["code"] == "non_authentifie"


def test_definir_sans_bareme_404(app_grain: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Régler le grain avant le barème → 404 `phase_qualification_absente` (E01US015)."""
    with TestClient(app_grain) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/grain-validation",
            json={"grain": "fin_de_serie"},
        )
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "phase_qualification_absente"


def test_definir_tournoi_inconnu_404(app_grain: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_grain) as client:
        connecter_admin(client)
        reponse = client.put(
            "/api/v1/tournois/999/grain-validation",
            json={"grain": "fin_de_serie"},
        )
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"


def test_lire_tournoi_inconnu_404(app_grain: FastAPI) -> None:
    with TestClient(app_grain) as client:
        reponse = client.get("/api/v1/tournois/999/grain-validation")
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"


def test_fin_de_duel_sur_une_qualification_422(
    app_grain: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """« Fin de duel » n'a pas de sens sur une qualification → 422 avec le code métier."""
    with TestClient(app_grain) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi_avec_bareme(client)
        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/grain-validation",
            json={"grain": "fin_de_duel"},
        )
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "grain_incompatible_avec_type_phase"


def test_cadence_manquante_422(app_grain: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """« Toutes les N volées » sans N → 422 avec le code métier."""
    with TestClient(app_grain) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi_avec_bareme(client)
        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/grain-validation",
            json={"grain": "toutes_les_n_volees"},
        )
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "nombre_volees_par_validation_manquant"


def test_cadence_nulle_422(app_grain: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_grain) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi_avec_bareme(client)
        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/grain-validation",
            json={"grain": "toutes_les_n_volees", "n_volees": 0},
        )
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "nombre_volees_par_validation_invalide"


def test_cadence_au_dela_du_bareme_422(app_grain: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Valider toutes les 30 volées d'une qualification de 20 → 422 (aucune validation n'aurait
    lieu)."""
    with TestClient(app_grain) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi_avec_bareme(client, nb_volees=20)
        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/grain-validation",
            json={"grain": "toutes_les_n_volees", "n_volees": 30},
        )
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "cadence_validation_superieure_au_bareme"


def test_reduire_le_bareme_sous_la_cadence_422(
    app_grain: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Contrepartie de l'invariant : l'endpoint **barème** (E01US009) refuse aussi l'incohérence.

    L'admin doit élargir son grain avant de réduire son barème.
    """
    with TestClient(app_grain) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi_avec_bareme(client, nb_volees=20)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/grain-validation",
            json={"grain": "toutes_les_n_volees", "n_volees": 10},
        )

        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 5, "nb_fleches_par_volee": 3},
        )
        assert reponse.status_code == 422
        assert reponse.json()["code"] == "cadence_validation_superieure_au_bareme"
        # Le barème n'a pas bougé.
        assert (
            client.get(f"/api/v1/tournois/{tournoi_id}/bareme-qualification").json()["nb_volees"]
            == 20
        )


def test_definir_corps_invalide_400(app_grain: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Un grain hors énumération → 400 (le DTO rejette avant le domaine)."""
    with TestClient(app_grain) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi_avec_bareme(client)
        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/grain-validation",
            json={"grain": "quand_ca_arrange"},
        )
    assert reponse.status_code == 400
    assert reponse.json()["code"] == "requete_invalide"
