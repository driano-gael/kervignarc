"""Test bout-en-bout de l'API catégories (E01US003).

Traverse toutes les couches — DTO Pydantic → file d'écriture → service → repository → DB,
puis relecture/listing — et vérifie le **mapping des erreurs typées** à la frontière :
- création (avec attributs) puis listing d'une catégorie ;
- édition (PUT) et suppression (204) ;
- catégorie/tournoi introuvable → 404 ; libellé vide → 422 ; corps invalide → 400.
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
def app_categories(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _creer_tournoi(client: TestClient) -> int:
    """Crée un tournoi et renvoie son identifiant (client déjà authentifié admin)."""
    reponse = client.post("/api/v1/tournois", json={"nom": "Trophée", "date": "2026-03-14"})
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def _creer_blason(client: TestClient, tournoi_id: int) -> int:
    """Crée un blason dans un tournoi et renvoie son identifiant."""
    reponse = client.post(
        f"/api/v1/tournois/{tournoi_id}/blasons",
        json={"nom": "Trispot 40", "taille": 0.5, "capacite": 3},
    )
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def test_creer_puis_lister_une_categorie(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """POST crée la catégorie (via la file) ; GET la liste avec ses attributs."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        creation = client.post(
            f"/api/v1/tournois/{tournoi_id}/categories",
            json={
                "libelle": "Senior H Classique",
                "arme": "classique",
                "ages": ["S1"],
                "sexe": "H",
            },
        )
        assert creation.status_code == 201
        cree = creation.json()
        assert cree["libelle"] == "Senior H Classique"
        assert cree["arme"] == "classique"
        assert cree["ages"] == ["S1"]
        assert cree["sexe"] == "H"
        assert cree["tournoi_id"] == tournoi_id
        assert isinstance(cree["id"], int)

        liste = client.get(f"/api/v1/tournois/{tournoi_id}/categories")
        assert liste.status_code == 200
        assert liste.json() == [cree]


def test_creer_avec_plusieurs_tranches_normalisees(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """E01US013 : `ages` accepte plusieurs tranches ; la réponse est dédoublonnée et ordonnée."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        cree = client.post(
            f"/api/v1/tournois/{tournoi_id}/categories",
            json={"libelle": "Arc Nu U18 H", "arme": "Arc Nu", "ages": ["U18", "U15", "U18"]},
        )
        assert cree.status_code == 201, cree.text
        assert cree.json()["ages"] == ["U15", "U18"]


def test_creer_tranche_hors_enum_400(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """E01US013 : une tranche hors des huit valeurs FFTA est rejetée à la frontière (400)."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/categories",
            json={"libelle": "X", "ages": ["senior"]},
        )
    assert reponse.status_code == 400
    assert reponse.json()["code"] == "requete_invalide"


def test_creer_defauts_attributs_facultatifs(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Sans arme/ages/sexe/blason : arme/sexe/blason à None, `ages` liste vide (jamais null)."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        cree = client.post(
            f"/api/v1/tournois/{tournoi_id}/categories", json={"libelle": "Libre"}
        ).json()
    assert cree["arme"] is None
    assert cree["ages"] == []
    assert cree["sexe"] is None
    assert cree["blason_id"] is None


def test_creer_avec_blason_par_defaut(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """E01US006 : on rattache un blason du tournoi ; la réponse porte `blason_id`."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        blason_id = _creer_blason(client, tournoi_id)
        cree = client.post(
            f"/api/v1/tournois/{tournoi_id}/categories",
            json={"libelle": "Senior H", "blason_id": blason_id},
        )
        assert cree.status_code == 201, cree.text
        assert cree.json()["blason_id"] == blason_id


def test_modifier_attache_puis_detache_le_blason(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """E01US006 : PUT pose un blason par défaut, puis le retire (`blason_id` null)."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        blason_id = _creer_blason(client, tournoi_id)
        cree = client.post(
            f"/api/v1/tournois/{tournoi_id}/categories", json={"libelle": "Libre"}
        ).json()
        attachee = client.put(
            f"/api/v1/categories/{cree['id']}",
            json={"libelle": "Libre", "blason_id": blason_id},
        )
        assert attachee.status_code == 200
        assert attachee.json()["blason_id"] == blason_id
        detachee = client.put(
            f"/api/v1/categories/{cree['id']}", json={"libelle": "Libre", "blason_id": None}
        )
        assert detachee.json()["blason_id"] is None


def test_creer_avec_blason_d_un_autre_tournoi_409(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """E01US006 : rattacher un blason d'un autre tournoi → 409 typé (`blason_hors_tournoi`)."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_a = _creer_tournoi(client)
        tournoi_b = _creer_tournoi(client)
        blason_b = _creer_blason(client, tournoi_b)
        reponse = client.post(
            f"/api/v1/tournois/{tournoi_a}/categories",
            json={"libelle": "Senior H", "blason_id": blason_b},
        )
    assert reponse.status_code == 409
    assert reponse.json()["code"] == "blason_hors_tournoi"


def test_lister_categories_d_un_tournoi(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """GET liste les catégories du tournoi, dans l'ordre de création."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        assert client.get(f"/api/v1/tournois/{tournoi_id}/categories").json() == []
        client.post(f"/api/v1/tournois/{tournoi_id}/categories", json={"libelle": "A"})
        client.post(f"/api/v1/tournois/{tournoi_id}/categories", json={"libelle": "B"})
        libelles = [
            c["libelle"] for c in client.get(f"/api/v1/tournois/{tournoi_id}/categories").json()
        ]
    assert libelles == ["A", "B"]


def test_modifier_une_categorie(app_categories: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """PUT édite les attributs ; la relecture reflète la modification."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        cree = client.post(
            f"/api/v1/tournois/{tournoi_id}/categories", json={"libelle": "Ancien"}
        ).json()
        modif = client.put(
            f"/api/v1/categories/{cree['id']}",
            json={"libelle": "Nouveau", "arme": "poulie", "ages": ["S2", "S3"], "sexe": "F"},
        )
        assert modif.status_code == 200
        corps = modif.json()
        assert corps["libelle"] == "Nouveau"
        assert corps["arme"] == "poulie"
        assert corps["ages"] == ["S2", "S3"]
        assert corps["sexe"] == "F"
        assert client.get(f"/api/v1/tournois/{tournoi_id}/categories").json() == [corps]


def test_supprimer_une_categorie(app_categories: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """DELETE → 204 ; la catégorie disparaît de la liste du tournoi."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        cree = client.post(
            f"/api/v1/tournois/{tournoi_id}/categories", json={"libelle": "Libre"}
        ).json()
        assert client.delete(f"/api/v1/categories/{cree['id']}").status_code == 204
        assert client.get(f"/api/v1/tournois/{tournoi_id}/categories").json() == []


def test_precharger_ffta_puis_lister(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """POST precharger-ffta crée le jeu officiel (201) ; GET liste les 32 catégories."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.post(f"/api/v1/tournois/{tournoi_id}/categories/precharger-ffta")
        assert reponse.status_code == 201, reponse.text
        creees = reponse.json()
        assert len(creees) == 32
        assert all(c["tournoi_id"] == tournoi_id for c in creees)
        assert "Arc Classique U11 Homme" in {c["libelle"] for c in creees}
        # E01US013 : les regroupements arc nu sont restitués par l'API en tranches multiples.
        ages_par_libelle = {c["libelle"]: c["ages"] for c in creees}
        assert ages_par_libelle["Arc Nu U18 Homme"] == ["U15", "U18"]
        assert ages_par_libelle["Arc Nu Scratch Homme"] == ["U21", "S1", "S2", "S3"]
        liste = client.get(f"/api/v1/tournois/{tournoi_id}/categories").json()
        assert len(liste) == 32


def test_precharger_ffta_idempotent(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un second pré-chargement ne recrée rien (201, liste vide) ; le total reste 32."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        client.post(f"/api/v1/tournois/{tournoi_id}/categories/precharger-ffta")
        rejeu = client.post(f"/api/v1/tournois/{tournoi_id}/categories/precharger-ffta")
        assert rejeu.status_code == 201
        assert rejeu.json() == []
        assert len(client.get(f"/api/v1/tournois/{tournoi_id}/categories").json()) == 32


def test_precharger_ffta_categorie_modifiable_et_supprimable(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA : une catégorie pré-chargée est éditable (PUT) et supprimable (DELETE)."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        creees = client.post(f"/api/v1/tournois/{tournoi_id}/categories/precharger-ffta").json()
        modif = client.put(
            f"/api/v1/categories/{creees[0]['id']}", json={"libelle": "Ma catégorie"}
        )
        assert modif.status_code == 200
        assert modif.json()["libelle"] == "Ma catégorie"
        assert client.delete(f"/api/v1/categories/{creees[1]['id']}").status_code == 204
        assert len(client.get(f"/api/v1/tournois/{tournoi_id}/categories").json()) == 31


def test_precharger_ffta_sans_jeton_401(app_categories: FastAPI) -> None:
    """Le pré-chargement est une action admin : refusé sans session (401)."""
    with TestClient(app_categories) as client:
        reponse = client.post("/api/v1/tournois/1/categories/precharger-ffta")
    assert reponse.status_code == 401
    assert reponse.json()["code"] == "non_authentifie"


def test_precharger_ffta_tournoi_introuvable(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Pré-charger dans un tournoi inconnu → 404 typé."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        reponse = client.post("/api/v1/tournois/999/categories/precharger-ffta")
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"


def test_creer_dans_tournoi_introuvable(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Créer une catégorie dans un tournoi inconnu → 404 typé."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        reponse = client.post("/api/v1/tournois/999/categories", json={"libelle": "X"})
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"


def test_modifier_categorie_introuvable(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """PUT sur une catégorie inconnue → 404 typé."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        reponse = client.put("/api/v1/categories/999", json={"libelle": "X"})
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "categorie_introuvable"


def test_creer_libelle_vide_erreur_domaine(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un libellé vide → 422 avec le code métier (règle du domaine)."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.post(f"/api/v1/tournois/{tournoi_id}/categories", json={"libelle": "   "})
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "libelle_categorie_invalide"


def test_creer_requete_invalide_erreur_400(
    app_categories: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un corps invalide (sexe hors énumération) → 400 avec le détail."""
    with TestClient(app_categories) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/categories",
            json={"libelle": "X", "sexe": "autre"},
        )
    assert reponse.status_code == 400
    corps = reponse.json()
    assert corps["code"] == "requete_invalide"
    assert "details" in corps
