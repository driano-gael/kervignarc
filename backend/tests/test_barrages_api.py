"""Test bout-en-bout de l'API du barrage de places (E06US003, ADR-0066).

Traverse HTTP → service → repositories sur un tournoi semé avec **deux archers parfaitement ex
æquo** (même total, mêmes 10, mêmes 9). On valide le **câblage** et l'effet **observable** — la
logique fine est couverte par le domaine (`test_domain_barrage_de_places.py`) et l'adapter
(`test_barrage_repository.py`). Écrit **après** l'implémentation (règle 9 : API/câblage).

Le fil conducteur est celui du CA : sans seuil réglé, **rien ne change** ; un seuil réglé signale
l'égalité ; on annonce, on fait tirer, et le classement affiche des rangs consécutifs.
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
from domain.blason import Blason, ZoneScore
from domain.categorie import Categorie
from domain.phase import Phase
from domain.serie import Serie, Volee
from domain.tournoi import Tournoi
from infrastructure.db import (
    ArcherRepositorySQL,
    AuditRepositorySQL,
    BlasonRepositorySQL,
    CategorieRepositorySQL,
    Database,
    PhaseRepositorySQL,
    SerieRepositorySQL,
    TournoiRepositorySQL,
)
from infrastructure.horloge import HorlogeSysteme
from tests.base_migree import preparer_base
from tests.conftest import ConnecterAdmin

_DATE = datetime.date(2026, 3, 14)


class Scenario:
    """Trois archers : un premier détaché, puis **deux parfaitement ex æquo** au rang 2."""

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
        self.archers: list[int] = []
        # Le 1er est devant ; les deux suivants ont le **même** total, les mêmes 10 et les mêmes 9 :
        # §8.1 est épuisé, c'est exactement le cas que le barrage vient trancher.
        for valeurs in (("10", "10", "10"), ("10", "9", "8"), ("10", "9", "8")):
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
                )
            )
            self.archers.append(archer.id)
        phases = PhaseRepositorySQL(db.session_factory)
        qualif = phases.ajouter(
            Phase.qualification(self.tournoi_id, BaremeQualification.creer(1, 3))
        )
        assert qualif.id is not None
        self.qualif_id = qualif.id


@pytest.fixture
def app_barrages(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    preparer_base(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _classement(client: TestClient, tournoi_id: int) -> dict[str, object]:
    reponse = client.get(f"/api/v1/tournois/{tournoi_id}/classement")
    assert reponse.status_code == 200, reponse.text
    corps: dict[str, object] = reponse.json()
    return corps


def _rangs(client: TestClient, tournoi_id: int) -> dict[int, int | None]:
    lignes = _classement(client, tournoi_id)["lignes"]
    assert isinstance(lignes, list)
    return {ligne["archer_id"]: ligne["rang_scratch"] for ligne in lignes}


def _regler_le_seuil(client: TestClient, scenario: Scenario, jusqu_au: int | None) -> None:
    """Règle (ou efface) le seuil de barrage sur la phase de qualification."""
    reponse = client.put(
        f"/api/v1/tournois/{scenario.tournoi_id}/phases/{scenario.qualif_id}",
        json={"type": "qualification", "sources": [], "barrage_jusqu_au": jusqu_au},
    )
    assert reponse.status_code == 200, reponse.text


def test_sans_seuil_le_classement_est_celui_d_e06us001(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le défaut est **inchangé** : rang partagé, aucune égalité signalée, aucun barrage proposé."""
    scenario = Scenario(app_barrages)
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        corps = _classement(client, scenario.tournoi_id)

        assert corps["egalites_a_departager"] == []
        assert _rangs(client, scenario.tournoi_id) == {
            scenario.archers[0]: 1,
            scenario.archers[1]: 2,
            scenario.archers[2]: 2,
        }


def test_un_seuil_regle_signale_l_egalite(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    scenario = Scenario(app_barrages)
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        _regler_le_seuil(client, scenario, 8)

        egalites = _classement(client, scenario.tournoi_id)["egalites_a_departager"]

        assert egalites == [{"rang": 2, "archer_ids": [scenario.archers[1], scenario.archers[2]]}]


def test_le_seuil_se_relit_sur_la_phase(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le réglage voyage dans `config.policies.tiebreak` (ADR-0046) : il doit survivre au retour."""
    scenario = Scenario(app_barrages)
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        _regler_le_seuil(client, scenario, 8)

        phases = client.get(f"/api/v1/tournois/{scenario.tournoi_id}/phases").json()

        assert phases[0]["barrage_jusqu_au"] == 8


def test_le_barrage_tire_rend_les_rangs_consecutifs(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le parcours complet du CA : signaler → annoncer → faire tirer → le classement suit."""
    scenario = Scenario(app_barrages)
    _, second, troisieme = scenario.archers
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        _regler_le_seuil(client, scenario, 8)

        annonce = client.post(f"/api/v1/tournois/{scenario.tournoi_id}/barrages", json={"rang": 2})
        assert annonce.status_code == 201, annonce.text
        barrage_id = annonce.json()["id"]
        assert annonce.json()["est_resolu"] is False

        manche = client.put(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages/{barrage_id}/manche",
            json={
                "tirs": [
                    {"archer_id": second, "score": 8},
                    {"archer_id": troisieme, "score": 10},
                ]
            },
        )
        assert manche.status_code == 200, manche.text
        assert manche.json()["est_resolu"] is True
        assert manche.json()["ordre"] == [troisieme, second]

        assert _rangs(client, scenario.tournoi_id) == {
            scenario.archers[0]: 1,
            troisieme: 2,
            second: 3,
        }
        # L'égalité tranchée ne doit plus être réclamée, sans quoi l'écran redemanderait un barrage
        # qui vient d'être tiré.
        assert _classement(client, scenario.tournoi_id)["egalites_a_departager"] == []


def test_un_barrage_non_resolu_laisse_le_rang_partage(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Deux flèches égales sans mesure : rien n'est publié, il faut retirer."""
    scenario = Scenario(app_barrages)
    _, second, troisieme = scenario.archers
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        _regler_le_seuil(client, scenario, 8)
        barrage_id = client.post(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages", json={"rang": 2}
        ).json()["id"]

        manche = client.put(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages/{barrage_id}/manche",
            json={
                "tirs": [
                    {"archer_id": second, "score": 9},
                    {"archer_id": troisieme, "score": 9},
                ]
            },
        )

        assert manche.json()["est_resolu"] is False
        assert manche.json()["groupes_a_rejouer"] == [[second, troisieme]]
        assert _rangs(client, scenario.tournoi_id)[second] == 2
        assert _rangs(client, scenario.tournoi_id)[troisieme] == 2


def test_clore_un_barrage_indecis_est_refuse(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    scenario = Scenario(app_barrages)
    _, second, troisieme = scenario.archers
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        _regler_le_seuil(client, scenario, 8)
        barrage_id = client.post(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages", json={"rang": 2}
        ).json()["id"]
        client.put(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages/{barrage_id}/manche",
            json={
                "tirs": [
                    {"archer_id": second, "score": 9},
                    {"archer_id": troisieme, "score": 9},
                ]
            },
        )

        cloture = client.post(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages/{barrage_id}/cloture"
        )

        assert cloture.status_code == 409
        assert cloture.json()["code"] == "egalite_non_departageable"


def test_annoncer_sur_un_rang_sans_egalite_est_refuse(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    scenario = Scenario(app_barrages)
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        _regler_le_seuil(client, scenario, 8)

        reponse = client.post(f"/api/v1/tournois/{scenario.tournoi_id}/barrages", json={"rang": 1})

        assert reponse.status_code == 409
        assert reponse.json()["code"] == "egalite_non_departageable"


def test_annoncer_deux_fois_ne_cree_qu_un_barrage(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Idempotence : un double clic sur « faire tirer » ne doit pas ouvrir deux barrages."""
    scenario = Scenario(app_barrages)
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        _regler_le_seuil(client, scenario, 8)

        premier = client.post(f"/api/v1/tournois/{scenario.tournoi_id}/barrages", json={"rang": 2})
        second = client.post(f"/api/v1/tournois/{scenario.tournoi_id}/barrages", json={"rang": 2})

        assert premier.json()["id"] == second.json()["id"]
        liste = client.get(f"/api/v1/tournois/{scenario.tournoi_id}/barrages").json()
        assert len(liste) == 1


def test_un_tireur_etranger_au_barrage_est_refuse(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le moteur ne peut pas l'attraper — il ne connaît que les tirs qu'on lui donne. Sans cette
    garde, un tiers serait classé à une place qu'il n'a pas disputée."""
    scenario = Scenario(app_barrages)
    premier, second, troisieme = scenario.archers
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        _regler_le_seuil(client, scenario, 8)
        barrage_id = client.post(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages", json={"rang": 2}
        ).json()["id"]

        reponse = client.put(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages/{barrage_id}/manche",
            json={
                "tirs": [
                    {"archer_id": second, "score": 9},
                    {"archer_id": troisieme, "score": 8},
                    {"archer_id": premier, "score": 10},
                ]
            },
        )

        assert reponse.status_code == 422


def test_les_ecritures_du_barrage_exigent_l_admin(app_barrages: FastAPI) -> None:
    """Annoncer un barrage change le classement publié : c'est un acte d'organisation."""
    scenario = Scenario(app_barrages)
    with TestClient(app_barrages) as client:
        reponse = client.post(f"/api/v1/tournois/{scenario.tournoi_id}/barrages", json={"rang": 2})

        assert reponse.status_code == 401
