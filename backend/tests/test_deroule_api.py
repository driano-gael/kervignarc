"""Test bout-en-bout de l'endpoint **public** du déroulé du tour (E07US009, ADR-0039).

Traverse HTTP → `ServiceSaisie.etat_serie` → `SerieRepositorySQL` sur une vraie base migrée. On sème
directement une `Serie` (deux volées, la 2ᵉ validée) par le repository — le chemin de saisie complet
(config phase/blason, poste, placement) est couvert par `test_saisie_api` ; ici on éprouve la
**projection publique** : statut par volée, cumul validé, et surtout la **frontière de
confidentialité** (règle 6 : ni identité du scoreur, ni donnée sensible). Écrit **après**
l'implémentation (règle 9 : API/projection, pas d'oracle en jeu).
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
from domain.blason import ZoneScore
from domain.categorie import Categorie
from domain.serie import Serie, Volee
from domain.tournoi import Tournoi
from infrastructure.db import (
    ArcherRepositorySQL,
    AuditRepositorySQL,
    CategorieRepositorySQL,
    Database,
    SerieRepositorySQL,
    TournoiRepositorySQL,
)
from infrastructure.horloge import HorlogeSysteme

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)
_SCOREUR = "DURAND Jean"


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


def _serie(tournoi_id: int, archer_id: int) -> Serie:
    """État d'en-cours **réaliste** : la volée 1 est **validée**, la volée 2 vient d'être saisie et
    reste **en attente**.

    La validation avance dans l'ordre (grain de validation, E01US015) : à mi-tour, les premières
    volées sont verrouillées et la dernière saisie attend encore le scoreur — jamais l'inverse. On
    sème donc V1 validée / V2 en attente (et non V2 validée sur V1 non validée, un état que le
    domaine ne produit pas). Chaque volée porte `saisie_par`/`validee_par` = le nom du scoreur :
    c'est précisément ce que la projection publique doit **taire** (règle 6).
    """
    return Serie(
        tournoi_id=tournoi_id,
        archer_id=archer_id,
        volees=(
            Volee(
                numero=1,
                valeurs=(ZoneScore("10"), ZoneScore("9"), ZoneScore("8")),
                saisie_par=_SCOREUR,
                validee_par=_SCOREUR,
            ),
            Volee(
                numero=2,
                valeurs=(ZoneScore("7"), ZoneScore("6"), ZoneScore("M")),
                saisie_par=_SCOREUR,
            ),
        ),
    )


@pytest.fixture
def app_deroule(tmp_path: Path) -> Iterator[tuple[FastAPI, int, int]]:
    """App montée sur une base semée d'un tournoi + un archer + sa série (2 volées, 1 validée)."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    tournoi = TournoiRepositorySQL(db.session_factory).ajouter(Tournoi.creer("Salle 18m", _DATE))
    assert tournoi.id is not None
    categorie = CategorieRepositorySQL(db.session_factory).ajouter(
        Categorie.creer(tournoi.id, "Senior 1 H")
    )
    assert categorie.id is not None
    archer = ArcherRepositorySQL(db.session_factory).ajouter(
        Archer.creer("Martin", "Alice", tournoi.id, categorie.id)
    )
    assert archer.id is not None
    SerieRepositorySQL(
        db.session_factory, AuditRepositorySQL(db.session_factory), HorlogeSysteme()
    ).enregistrer(_serie(tournoi.id, archer.id))
    db.engine.dispose()

    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app, tournoi.id, archer.id
    finally:
        app.state.database.engine.dispose()


def test_deroule_expose_volees_et_statut_par_volee(
    app_deroule: tuple[FastAPI, int, int],
) -> None:
    """Le déroulé rend chaque volée avec ses valeurs, son total et son statut attente/validé."""
    app, tournoi_id, archer_id = app_deroule
    with TestClient(app) as client:
        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/archers/{archer_id}/deroule")

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["tournoi_id"] == tournoi_id
    assert corps["archer_id"] == archer_id
    volees = corps["volees"]
    assert [v["numero"] for v in volees] == [1, 2]
    assert volees[0]["valeurs"] == ["10", "9", "8"]
    assert volees[0]["points"] == 27
    assert volees[0]["statut"] == "valide"  # verrouillée par le scoreur
    assert volees[1]["valeurs"] == ["7", "6", "M"]
    assert volees[1]["points"] == 13  # le manqué vaut 0
    assert volees[1]["statut"] == "en_attente"  # saisie, pas encore validée


def test_deroule_cumul_ne_compte_que_le_valide(app_deroule: tuple[FastAPI, int, int]) -> None:
    """Le cumul ne somme que le **validé**, alors que le déroulé, lui, montre aussi le provisoire.

    Volées non vides (V1 validée, V2 en attente) : le cumul vaut les seuls points de V1 (27), pas
    27 + 13. C'est ce qui distingue « total 0 car rien de saisi » de « total partiel car tout n'est
    pas validé » — le nerf du statut provisoire (ADR-0039)."""
    app, tournoi_id, archer_id = app_deroule
    with TestClient(app) as client:
        corps = client.get(f"/api/v1/tournois/{tournoi_id}/archers/{archer_id}/deroule").json()
    # Seule la volée 1 (validée) compte : 10 + 9 + 8 = 27 ; la volée 2 (en attente, 13) est exclue.
    assert corps["cumul"] == 27
    assert corps["volees"], "le cumul est jugé avec des volées présentes, pas sur un déroulé vide"


def test_deroule_ne_fuite_pas_l_identite_du_scoreur(
    app_deroule: tuple[FastAPI, int, int],
) -> None:
    """Garantie ADR-0039 / règle 6 : ni marqueurs de scoreur, ni son nom, ne sortent du DTO."""
    app, tournoi_id, archer_id = app_deroule
    with TestClient(app) as client:
        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/archers/{archer_id}/deroule")

    assert _SCOREUR not in reponse.text  # le nom du scoreur n'apparaît nulle part
    # Liste blanche des clés exposées : la garantie ne repose pas sur l'omission constatée de deux
    # champs (fragile — un futur ajout passerait) mais sur l'ensemble **exact** du DTO. Ajouter
    # demain un champ sensible (code de cible, IP, marqueur de scoreur) fera échouer ce test.
    champs_publics = {"numero", "valeurs", "points", "statut", "horodatage"}
    for volee in reponse.json()["volees"]:
        assert set(volee.keys()) == champs_publics


def test_deroule_archer_sans_saisie_rend_vide_pas_404(
    app_deroule: tuple[FastAPI, int, int],
) -> None:
    """Un archer sans rien de saisi (id inexistant) rend un déroulé vide en 200, pas un 404."""
    app, tournoi_id, _ = app_deroule
    with TestClient(app) as client:
        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/archers/9999/deroule")

    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["volees"] == []
    assert corps["cumul"] == 0


def test_deroule_accessible_sans_jeton(app_deroule: tuple[FastAPI, int, int]) -> None:
    """Lecture publique (E10US001) : aucune authentification requise (jamais 401)."""
    app, tournoi_id, archer_id = app_deroule
    with TestClient(app) as client:
        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/archers/{archer_id}/deroule")

    assert reponse.status_code != 401
