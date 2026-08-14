"""Endpoints REST du **Big Shoot Off** (E05US028) — câblage de bout en bout.

Tests **après** l'implémentation, et c'est le régime prescrit par la règle 9 : « API, repository,
câblage : tests après l'implémentation — il n'y a pas d'oracle en jeu ». La règle métier, elle, est
gardée un étage plus bas (`test_domain_big_shoot_off.py`, écrit **depuis le CA** avant le moteur).

Ce que ce fichier éprouve et qu'aucun test de service ne peut voir :

- le routeur est **réellement monté** dans `create_app` (un oubli ne casserait rien ailleurs) ;
- les **droits** sont ceux annoncés — la projection est admin, l'état et la saisie sont scoreur ;
- le réglage **traverse la frontière** dans les deux sens, en base comprise ;
- une volée saisie puis validée **élimine**, sur la vraie chaîne (file d'écriture incluse).
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
from domain.big_shoot_off import ConfigurationBigShootOff
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

_DATE = datetime.date(2026, 3, 14)


class Scenario:
    """Quatre finalistes classés, et un Big Shoot Off qui en sort deux puis un."""

    def __init__(self, app: FastAPI, *, effectif: int = 4) -> None:
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
        depart = DepartRepositorySQL(db.session_factory).ajouter(
            Depart.creer(tournoi_id=self.tournoi_id, numero=1, tarif_centimes=800, horaire="09:00")
        )
        assert depart.id is not None
        self.depart_id = depart.id
        qualif = poser_phase_sql(
            db.session_factory, Phase.qualification(self.depart_id, BaremeQualification.creer(1, 3))
        )
        assert qualif.id is not None
        self.qualif_id = qualif.id
        archers = ArcherRepositorySQL(db.session_factory)
        series = SerieRepositorySQL(
            db.session_factory, AuditRepositorySQL(db.session_factory), HorlogeSysteme()
        )
        inscriptions = InscriptionRepositorySQL(
            db.session_factory, AuditRepositorySQL(db.session_factory)
        )
        self.archers: list[int] = []
        for rang in range(effectif):
            archer = archers.ajouter(
                Archer(
                    nom=f"N{rang}",
                    prenom="P",
                    tournoi_id=self.tournoi_id,
                    categorie_id=categorie.id,
                )
            )
            assert archer.id is not None
            # Scores strictement décroissants : le rang scratch est prévisible, donc la population
            # prélevée l'est aussi.
            valeur = str(max(1, 10 - rang))
            series.enregistrer(
                Serie(
                    tournoi_id=self.tournoi_id,
                    archer_id=archer.id,
                    volees=(Volee(numero=1, valeurs=(ZoneScore(valeur),) * 3, validee_par="S"),),
                    phase_id=self.qualif_id,
                )
            )
            inscriptions.ajouter(Inscription.creer(archer.id, self.depart_id))
            self.archers.append(archer.id)
        phase = poser_phase_sql(
            db.session_factory,
            Phase(
                depart_id=self.depart_id,
                ordre=2,
                type=TypePhase.BIG_SHOOT_OFF,
                big_shoot_off=ConfigurationBigShootOff(eliminations=(2, 1)),
            ),
        )
        assert phase.id is not None
        self.phase_id = phase.id


@pytest.fixture
def app_bso(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    preparer_base(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _scoreur(
    client: TestClient, tournoi_id: int, connecter_admin: ConnecterAdmin
) -> dict[str, str]:
    """Crée un scoreur (admin) et ouvre sa session ; renvoie l'en-tête `X-Jeton-Scoreur`."""
    connecter_admin(client)
    reponse = client.post(f"/api/v1/tournois/{tournoi_id}/scoreurs", json={"nom": "ROUX"})
    assert reponse.status_code in (200, 201), reponse.text
    code = reponse.json()["code"]
    jeton = client.post("/api/v1/scoreurs/session", json={"code": code}).json()["jeton"]
    return {"X-Jeton-Scoreur": jeton}


def test_la_projection_se_lit_sans_le_moindre_tir(
    app_bso: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA « réglages à l'atelier » : l'organisateur voit ce que sa liste donne avant de composer.

    Quatre finalistes, liste `[2, 1]` : la manche 1 en sort 2, la manche 2 en sort 1, il en reste 1.
    """
    with TestClient(app_bso) as client:
        scn = Scenario(app_bso)
        connecter_admin(client)

        reponse = client.get(f"/api/v1/big-shoot-off/projection/{scn.tournoi_id}/{scn.phase_id}")

    assert reponse.status_code == 200, reponse.text
    # ⚠️ Assertion **exhaustive** du corps, et non champ par champ : c'est elle qui a fait tomber
    # l'ajout de `volees` / `fleches_par_volee` au moment où l'écran de saisie en a eu besoin. Un
    # `assert corps["restants"] == 1` n'aurait rien vu — et un champ ajouté au contrat public sans
    # que rien ne le signale est exactement ce qu'on veut voir passer sous les yeux.
    assert reponse.json() == {
        "effectif": 4,
        "eliminations": [2, 1],
        "paliers": [2, 1],
        "volees": 1,
        "fleches_par_volee": 3,
        "restants": 1,
        "manches_jouables": 2,
        "manches_ignorees": 0,
    }


def test_la_projection_est_reservee_a_l_admin(app_bso: FastAPI) -> None:
    """C'est un écran d'**atelier**, pas un panneau de salle : sans session admin, 401."""
    with TestClient(app_bso) as client:
        scn = Scenario(app_bso)

        reponse = client.get(f"/api/v1/big-shoot-off/projection/{scn.tournoi_id}/{scn.phase_id}")

    assert reponse.status_code == 401, reponse.text


def test_l_etat_est_reserve_au_scoreur(app_bso: FastAPI) -> None:
    """L'état porte les scores manche par manche : le public n'a pas à les lire avant validation."""
    with TestClient(app_bso) as client:
        scn = Scenario(app_bso)

        reponse = client.get(f"/api/v1/big-shoot-off/etat/{scn.tournoi_id}/{scn.phase_id}")

    assert reponse.status_code == 401, reponse.text


def test_une_manche_saisie_puis_validee_elimine_sur_la_vraie_chaine(
    app_bso: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le bout en bout : file d'écriture, base, rejeu de la phase depuis les volées validées.

    ⚠️ **La saisie seule n'élimine personne** — il faut la validation. C'est ce qui empêche
    l'élimination de bouger à chaque flèche, et un archer d'apparaître sorti puis rentré sous les
    yeux du juge.
    """
    with TestClient(app_bso) as client:
        scn = Scenario(app_bso)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)
        for archer_id, zone in zip(scn.archers, ("10", "9", "8", "7"), strict=True):
            saisie = client.post(
                "/api/v1/big-shoot-off/volees",
                json={
                    "tournoi_id": scn.tournoi_id,
                    "phase_id": scn.phase_id,
                    "archer_id": archer_id,
                    "numero": 1,
                    "valeurs": [zone, zone, zone],
                },
                headers=entetes,
            )
            assert saisie.status_code == 200, saisie.text
        # Avant validation, personne n'est sorti.
        assert all(tireur["en_lice"] for tireur in saisie.json()["tireurs"])

        for archer_id in scn.archers:
            validation = client.post(
                "/api/v1/big-shoot-off/validations",
                json={
                    "tournoi_id": scn.tournoi_id,
                    "phase_id": scn.phase_id,
                    "archer_id": archer_id,
                },
                headers=entetes,
            )
            assert validation.status_code == 200, validation.text

    corps = validation.json()
    sorts = {t["archer_id"]: (t["en_lice"], t["rang"]) for t in corps["tireurs"]}
    # Les deux plus faibles sortent, classés entre eux au score de la manche.
    assert sorts[scn.archers[3]] == (False, 4)
    assert sorts[scn.archers[2]] == (False, 3)
    assert sorts[scn.archers[0]] == (True, None)
    assert corps["manches"][0]["jouee"] is True


def test_le_reglage_traverse_la_frontiere_dans_les_deux_sens(
    app_bso: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le réglage se pose par l'API de composition et se relit — base comprise, sans migration.

    ⚠️ **Pas de champ « restants »**, et c'est le cœur de l'élargissement du 14/08/2026 : K se déduit
    de ce que la liste n'élimine pas. En publier un aurait laissé deux champs se contredire.
    """
    with TestClient(app_bso) as client:
        scn = Scenario(app_bso)
        connecter_admin(client)

        ajout = client.post(
            f"/api/v1/tournois/{scn.tournoi_id}/phases",
            json={
                "type": "big_shoot_off",
                "sources": [],
                "big_shoot_off": {
                    "eliminations": [4, 2, 1],
                    "volees": 2,
                    "cumul_des_manches": True,
                    "departage_les_sortants": True,
                },
            },
        )
        assert ajout.status_code == 201, ajout.text
        relu = client.get(f"/api/v1/tournois/{scn.tournoi_id}/phases")

    assert relu.status_code == 200, relu.text
    etape = next(e for e in relu.json() if e["id"] == ajout.json()["id"])
    assert etape["big_shoot_off"] == {
        "eliminations": [4, 2, 1],
        "volees": 2,
        "fleches_par_volee": 3,
        "cumul_des_manches": True,
        "departage_les_sortants": True,
    }
