"""Test bout-en-bout de l'API du plan de cibles (E03US001).

Traverse toutes les couches en **lecture** — HTTP → `ServicePlacement` → moteur pur → repositories
— après avoir peuplé le tournoi via les endpoints existants (blason, catégorie, gabarit appliqué,
départ, archers, inscriptions). Vérifie la forme de la réponse et le **mapping des 404** (tournoi /
départ / gabarit absent). La logique de placement elle-même est couverte par `test_domain_placement`
et `test_service_placement` ; ici on valide le **câblage** de la route.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from domain.blason import ZoneScore
from domain.serie import Serie, Volee
from infrastructure.db import AuditRepositorySQL, SerieRepositorySQL
from infrastructure.horloge import HorlogeSysteme
from tests.conftest import ConnecterAdmin

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _semer_score(app: FastAPI, tournoi_id: int, archer_id: int) -> None:
    """Insère une série (une volée saisie) pour un archer — il « a des scores » (impact E12US007).

    Directement par le repository (comme test_saisie_api sème un placement) : passer par la saisie
    HTTP exigerait barème, grain, session scoreur/poste — hors sujet pour tester le **câblage** de
    l'alerte d'impact."""
    sf = app.state.database.session_factory
    # Volée **validée** (`validee_par`) : « a des scores » au sens du CA = tir validé, pas une
    # simple saisie provisoire (cf. `Serie.nb_fleches_validees`, arbitrage daté).
    serie = Serie(
        tournoi_id=tournoi_id,
        archer_id=archer_id,
        volees=(
            Volee(
                numero=1,
                valeurs=(ZoneScore.DIX, ZoneScore.DIX, ZoneScore.DIX),
                validee_par="Scoreur",
            ),
        ),
    )
    SerieRepositorySQL(sf, AuditRepositorySQL(sf), HorlogeSysteme()).enregistrer(serie)


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


@pytest.fixture
def app_placement(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _creer_tournoi(client: TestClient) -> int:
    reponse = client.post("/api/v1/tournois", json={"nom": "Trophée", "date": "2026-03-14"})
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def _appliquer_gabarit(client: TestClient, tournoi_id: int, nb_cibles: int) -> None:
    modele = client.post("/api/v1/gabarits", json={"nom": "Salle", "nb_cibles": nb_cibles})
    assert modele.status_code == 201, modele.text
    applique = client.put(
        f"/api/v1/tournois/{tournoi_id}/gabarit", json={"modele_id": modele.json()["id"]}
    )
    assert applique.status_code == 200, applique.text


def _creer_categorie(client: TestClient, tournoi_id: int) -> int:
    blason = client.post(
        f"/api/v1/tournois/{tournoi_id}/blasons",
        json={"nom": "Blason", "taille": 0.5, "capacite": 1},
    )
    assert blason.status_code == 201, blason.text
    categorie = client.post(
        f"/api/v1/tournois/{tournoi_id}/categories",
        json={"libelle": "Senior", "blason_id": blason.json()["id"], "hauteur_cm": 130},
    )
    assert categorie.status_code == 201, categorie.text
    return int(categorie.json()["id"])


def _creer_depart(client: TestClient, tournoi_id: int) -> int:
    reponse = client.post(f"/api/v1/tournois/{tournoi_id}/departs", json={"tarif_centimes": 0})
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def _inscrire_archer(
    client: TestClient, tournoi_id: int, categorie_id: int, depart_id: int, prenom: str
) -> tuple[int, int]:
    """Crée un archer et l'inscrit au départ ; renvoie `(archer_id, inscription_id)`."""
    # Prénoms distincts : deux archers de mêmes nom/prénom/club déclencheraient le garde-fou
    # homonyme (E02US002, 409), hors sujet ici.
    archer = client.post(
        f"/api/v1/tournois/{tournoi_id}/archers",
        json={"nom": "Tell", "prenom": prenom, "categorie_id": categorie_id},
    )
    assert archer.status_code == 201, archer.text
    archer_id = int(archer.json()["id"])
    inscription = client.post(
        f"/api/v1/archers/{archer_id}/inscriptions", json={"depart_id": depart_id}
    )
    assert inscription.status_code == 201, inscription.text
    return archer_id, int(inscription.json()["id"])


def _regenerer(client: TestClient, tournoi_id: int, depart_id: int) -> dict[str, Any]:
    """Génère (matérialise) le plan auto du départ et renvoie la réponse JSON."""
    reponse = client.post(
        f"/api/v1/tournois/{tournoi_id}/departs/{depart_id}/plan-de-cibles/regenerer"
    )
    assert reponse.status_code == 200, reponse.text
    return dict(reponse.json())


def test_regenerer_puis_lire_place_les_inscrits(
    app_placement: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Après régénération, le GET renvoie le plan **persisté** : inscrits posés, sans conflit."""
    with TestClient(app_placement) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        _appliquer_gabarit(client, tournoi_id, nb_cibles=2)
        categorie_id = _creer_categorie(client, tournoi_id)
        depart_id = _creer_depart(client, tournoi_id)
        a1, _ = _inscrire_archer(client, tournoi_id, categorie_id, depart_id, prenom="Guillaume")
        a2, _ = _inscrire_archer(client, tournoi_id, categorie_id, depart_id, prenom="Walter")

        _regenerer(client, tournoi_id, depart_id)
        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/departs/{depart_id}/plan-de-cibles")

    assert reponse.status_code == 200, reponse.text
    plan = reponse.json()
    assert plan["depart_id"] == depart_id
    assert len(plan["cibles"]) == 2
    places = {p["archer_id"] for cible in plan["cibles"] for p in cible["placements"]}
    assert places == {a1, a2}
    assert plan["conflits"] == []


def test_avant_generation_les_inscrits_sont_en_reserve(
    app_placement: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """ADR-0024 : sans génération, le GET renvoie des cibles vides et les inscrits en réserve."""
    with TestClient(app_placement) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        _appliquer_gabarit(client, tournoi_id, nb_cibles=2)
        categorie_id = _creer_categorie(client, tournoi_id)
        depart_id = _creer_depart(client, tournoi_id)
        a1, i1 = _inscrire_archer(client, tournoi_id, categorie_id, depart_id, prenom="Guillaume")

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/departs/{depart_id}/plan-de-cibles")

    assert reponse.status_code == 200, reponse.text
    plan = reponse.json()
    assert all(cible["placements"] == [] for cible in plan["cibles"])
    assert plan["conflits"] == [{"archer_id": a1, "raison": "en_reserve", "inscription_id": i1}]


def test_plan_de_cibles_expose_les_conflits(
    app_placement: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un départ en surnombre expose des conflits `non_place` sérialisés en JSON (enum → valeur)."""
    with TestClient(app_placement) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        _appliquer_gabarit(client, tournoi_id, nb_cibles=1)  # une seule cible
        categorie_id = _creer_categorie(client, tournoi_id)  # blason taille 0.5 → 2 cartons/cible
        depart_id = _creer_depart(client, tournoi_id)
        _inscrire_archer(client, tournoi_id, categorie_id, depart_id, prenom="Guillaume")
        _inscrire_archer(client, tournoi_id, categorie_id, depart_id, prenom="Walter")
        a3, i3 = _inscrire_archer(client, tournoi_id, categorie_id, depart_id, prenom="Wilhelm")

        plan = _regenerer(client, tournoi_id, depart_id)

    conflits = plan["conflits"]
    assert conflits == [{"archer_id": a3, "raison": "non_place", "inscription_id": i3}]


def test_deplacer_un_archer_vers_une_case_libre(
    app_placement: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """PUT déplace un inscrit sur une case libre ; le plan renvoyé reflète le déplacement."""
    with TestClient(app_placement) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        _appliquer_gabarit(client, tournoi_id, nb_cibles=2)
        categorie_id = _creer_categorie(client, tournoi_id)
        depart_id = _creer_depart(client, tournoi_id)
        a1, _ = _inscrire_archer(client, tournoi_id, categorie_id, depart_id, prenom="Guillaume")
        a2, i2 = _inscrire_archer(client, tournoi_id, categorie_id, depart_id, prenom="Walter")
        _regenerer(client, tournoi_id, depart_id)

        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/departs/{depart_id}/plan-de-cibles/inscriptions/{i2}",
            json={"cible_index": 2, "position": "A"},
        )

    assert reponse.status_code == 200, reponse.text
    cible_de = {
        p["archer_id"]: cible["index"]
        for cible in reponse.json()["cibles"]
        for p in cible["placements"]
    }
    assert cible_de[a1] == 1
    assert cible_de[a2] == 2


def test_mettre_en_reserve_via_cible_null(
    app_placement: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """PUT avec `cible_index` null met l'inscrit en réserve (retiré des cibles)."""
    with TestClient(app_placement) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        _appliquer_gabarit(client, tournoi_id, nb_cibles=1)
        categorie_id = _creer_categorie(client, tournoi_id)
        depart_id = _creer_depart(client, tournoi_id)
        a1, i1 = _inscrire_archer(client, tournoi_id, categorie_id, depart_id, prenom="Guillaume")
        _regenerer(client, tournoi_id, depart_id)

        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/departs/{depart_id}/plan-de-cibles/inscriptions/{i1}",
            json={"cible_index": None},
        )

    assert reponse.status_code == 200, reponse.text
    plan = reponse.json()
    assert all(cible["placements"] == [] for cible in plan["cibles"])
    assert plan["conflits"] == [{"archer_id": a1, "raison": "en_reserve", "inscription_id": i1}]


def test_deplacement_invalide_renvoie_409(
    app_placement: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un déplacement violant la hauteur → 409 `deplacement_invalide` (état inchangé)."""
    with TestClient(app_placement) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        _appliquer_gabarit(client, tournoi_id, nb_cibles=2)
        blason = client.post(
            f"/api/v1/tournois/{tournoi_id}/blasons",
            json={"nom": "B", "taille": 0.25, "capacite": 1},
        )
        u11 = client.post(
            f"/api/v1/tournois/{tournoi_id}/categories",
            json={"libelle": "U11", "blason_id": blason.json()["id"], "hauteur_cm": 110},
        ).json()["id"]
        adulte = client.post(
            f"/api/v1/tournois/{tournoi_id}/categories",
            json={"libelle": "Senior", "blason_id": blason.json()["id"], "hauteur_cm": 130},
        ).json()["id"]
        depart_id = _creer_depart(client, tournoi_id)
        a_u11, i_u11 = _inscrire_archer(client, tournoi_id, u11, depart_id, prenom="Enfant")
        _inscrire_archer(client, tournoi_id, adulte, depart_id, prenom="Walter")
        plan = _regenerer(client, tournoi_id, depart_id)
        cible_adulte = next(
            cible["index"]
            for cible in plan["cibles"]
            for p in cible["placements"]
            if p["archer_id"] != a_u11  # la cible occupée par l'adulte (autre hauteur)
        )

        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/departs/{depart_id}/plan-de-cibles/inscriptions/{i_u11}",
            json={"cible_index": cible_adulte, "position": "B"},
        )

    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["code"] == "deplacement_invalide"


def test_placer_les_restants_endpoint(
    app_placement: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """POST placer-restants repose la réserve dans les trous ; plus personne en réserve ensuite."""
    with TestClient(app_placement) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        _appliquer_gabarit(client, tournoi_id, nb_cibles=1)
        categorie_id = _creer_categorie(client, tournoi_id)
        depart_id = _creer_depart(client, tournoi_id)
        a1, _ = _inscrire_archer(client, tournoi_id, categorie_id, depart_id, prenom="Guillaume")
        a2, i2 = _inscrire_archer(client, tournoi_id, categorie_id, depart_id, prenom="Walter")
        _regenerer(client, tournoi_id, depart_id)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/departs/{depart_id}/plan-de-cibles/inscriptions/{i2}",
            json={"cible_index": None},
        )

        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/departs/{depart_id}/plan-de-cibles/placer-restants"
        )

    assert reponse.status_code == 200, reponse.text
    plan = reponse.json()
    places = {p["archer_id"] for cible in plan["cibles"] for p in cible["placements"]}
    assert places == {a1, a2}
    assert plan["conflits"] == []


def test_regenerer_exige_l_admin(app_placement: FastAPI) -> None:
    """La régénération est une écriture réservée à l'admin : 401 sans session."""
    with TestClient(app_placement) as client:
        reponse = client.post("/api/v1/tournois/1/departs/1/plan-de-cibles/regenerer")
    assert reponse.status_code == 401, reponse.text


# --- Alerte par calcul d'impact (E12US007, ADR-0040) — câblage de la route -----------------------


def _base_plan(tournoi_id: int, depart_id: int) -> str:
    return f"/api/v1/tournois/{tournoi_id}/departs/{depart_id}/plan-de-cibles"


def test_impact_regeneration_chiffre_selon_les_scores(
    app_placement: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """GET impact : `confirmation` (placés, sans score) puis `massif` dès qu'un score existe."""
    with TestClient(app_placement) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        _appliquer_gabarit(client, tournoi_id, nb_cibles=1)
        categorie_id = _creer_categorie(client, tournoi_id)
        depart_id = _creer_depart(client, tournoi_id)
        a1, _ = _inscrire_archer(client, tournoi_id, categorie_id, depart_id, prenom="Guillaume")
        _inscrire_archer(client, tournoi_id, categorie_id, depart_id, prenom="Walter")
        _regenerer(client, tournoi_id, depart_id)

        sans_score = client.get(f"{_base_plan(tournoi_id, depart_id)}/impact-regeneration")
        _semer_score(app_placement, tournoi_id, a1)
        avec_score = client.get(f"{_base_plan(tournoi_id, depart_id)}/impact-regeneration")

    assert sans_score.status_code == 200, sans_score.text
    assert sans_score.json() == {
        "niveau": "confirmation",
        "archers_deplaces": 2,
        "cibles_avec_scores": 0,
    }
    assert avec_score.json() == {
        "niveau": "massif",
        "archers_deplaces": 2,
        "cibles_avec_scores": 1,
    }


def test_regenerer_massif_sans_confirmation_renvoie_409_chiffre(
    app_placement: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """POST regenerer d'un plan massif **sans** `confirme` → 409 `replacement_non_confirme`,
    chiffré.

    Le décompte voyage dans `details` (première utilisation du canal `{code, message,
    details?}`)."""
    with TestClient(app_placement) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        _appliquer_gabarit(client, tournoi_id, nb_cibles=1)
        categorie_id = _creer_categorie(client, tournoi_id)
        depart_id = _creer_depart(client, tournoi_id)
        a1, _ = _inscrire_archer(client, tournoi_id, categorie_id, depart_id, prenom="Guillaume")
        _inscrire_archer(client, tournoi_id, categorie_id, depart_id, prenom="Walter")
        _regenerer(client, tournoi_id, depart_id)
        _semer_score(app_placement, tournoi_id, a1)

        reponse = client.post(f"{_base_plan(tournoi_id, depart_id)}/regenerer")

    assert reponse.status_code == 409, reponse.text
    corps = reponse.json()
    assert corps["code"] == "replacement_non_confirme"
    assert corps["details"] == {"archers_deplaces": 2, "cibles_avec_scores": 1}


def test_regenerer_massif_confirme_ecrase_le_plan(
    app_placement: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """POST regenerer `{confirme:true}` sur un plan massif → 200, le plan est régénéré."""
    with TestClient(app_placement) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        _appliquer_gabarit(client, tournoi_id, nb_cibles=1)
        categorie_id = _creer_categorie(client, tournoi_id)
        depart_id = _creer_depart(client, tournoi_id)
        a1, _ = _inscrire_archer(client, tournoi_id, categorie_id, depart_id, prenom="Guillaume")
        a2, _ = _inscrire_archer(client, tournoi_id, categorie_id, depart_id, prenom="Walter")
        _regenerer(client, tournoi_id, depart_id)
        _semer_score(app_placement, tournoi_id, a1)

        reponse = client.post(
            f"{_base_plan(tournoi_id, depart_id)}/regenerer", json={"confirme": True}
        )

    assert reponse.status_code == 200, reponse.text
    places = {p["archer_id"] for cible in reponse.json()["cibles"] for p in cible["placements"]}
    assert places == {a1, a2}


def test_impact_regeneration_exige_l_admin(app_placement: FastAPI) -> None:
    """La prévisualisation d'impact est réservée à l'admin : 401 sans session."""
    with TestClient(app_placement) as client:
        reponse = client.get("/api/v1/tournois/1/departs/1/plan-de-cibles/impact-regeneration")
    assert reponse.status_code == 401, reponse.text


def test_plan_de_cibles_tournoi_inconnu_404(
    app_placement: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un tournoi inexistant → 404."""
    with TestClient(app_placement) as client:
        connecter_admin(client)
        reponse = client.get("/api/v1/tournois/999999/departs/1/plan-de-cibles")
    assert reponse.status_code == 404, reponse.text


def test_plan_de_cibles_depart_inconnu_404(
    app_placement: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un départ inexistant dans un tournoi valide → 404."""
    with TestClient(app_placement) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        _appliquer_gabarit(client, tournoi_id, nb_cibles=1)
        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/departs/999999/plan-de-cibles")
    assert reponse.status_code == 404, reponse.text


def test_plan_de_cibles_sans_gabarit_404(
    app_placement: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Sans gabarit appliqué au tournoi, pas de cible → 404 `gabarit_du_tournoi_absent`."""
    with TestClient(app_placement) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        depart_id = _creer_depart(client, tournoi_id)
        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/departs/{depart_id}/plan-de-cibles")
    assert reponse.status_code == 404, reponse.text
    assert reponse.json()["code"] == "gabarit_du_tournoi_absent"
