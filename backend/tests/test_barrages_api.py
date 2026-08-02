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
    BarrageTirORM,
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
        self.categorie_id = categorie.id
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


def _ajouter_archer(app: FastAPI, scenario: Scenario, valeurs: tuple[str, ...]) -> int:
    """Ajoute un archer **avec sa série validée** — sert à faire bouger le classement en cours de
    scénario (volée validée en retard, correction de score)."""
    db: Database = app.state.database
    archer = ArcherRepositorySQL(db.session_factory).ajouter(
        Archer(
            nom="Tardif",
            prenom="P",
            tournoi_id=scenario.tournoi_id,
            categorie_id=scenario.categorie_id,
        )
    )
    assert archer.id is not None
    SerieRepositorySQL(
        db.session_factory, AuditRepositorySQL(db.session_factory), HorlogeSysteme()
    ).enregistrer(
        Serie(
            tournoi_id=scenario.tournoi_id,
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
    return archer.id


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


# --- correctifs de revue -------------------------------------------------------------------------


def test_une_manche_refusee_ne_laisse_aucune_trace_et_le_classement_reste_lisible(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le défaut le plus coûteux trouvé en revue : la manche était **écrite puis** validée.

    La requête était refusée *et* la ligne persistée ; ensuite, chaque lecture rejouait le moteur
    et levait — donc `GET /classement`, **public et projeté en salle**, tombait en 422 pour tout le
    tournoi, panneau d'organisation compris : plus aucun écran pour réparer.
    """
    scenario = Scenario(app_barrages)
    _, second, _ = scenario.archers
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        _regler_le_seuil(client, scenario, 8)
        barrage_id = client.post(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages", json={"rang": 2}
        ).json()["id"]

        # Deux tirs, mais du **même** archer : la manche passe le DTO (deux entrées) et échoue au
        # domaine — le troisième tireur annoncé manque, et un participant figure deux fois. C'est
        # exactement le chemin qui écrivait avant de valider.
        refus = client.put(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages/{barrage_id}/manche",
            json={
                "tirs": [
                    {"archer_id": second, "score": 9},
                    {"archer_id": second, "score": 8},
                ]
            },
        )

        assert refus.status_code == 422, refus.text
        # Rien n'a été écrit…
        barrages = client.get(f"/api/v1/tournois/{scenario.tournoi_id}/barrages").json()
        assert barrages[0]["manches"] == []
        # …et les deux lectures restent saines.
        assert client.get(f"/api/v1/tournois/{scenario.tournoi_id}/classement").status_code == 200


def test_corriger_la_manche_1_tronque_les_suivantes(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Réécrire la manche 1 change la partition : les retirs qui en découlaient n'ont plus d'objet.

    Les garder produisait un agrégat que le moteur refuse à la relecture — donc, à nouveau, un
    classement en 422 permanent.
    """
    scenario = Scenario(app_barrages)
    _, second, troisieme = scenario.archers
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        _regler_le_seuil(client, scenario, 8)
        barrage_id = client.post(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages", json={"rang": 2}
        ).json()["id"]
        url = f"/api/v1/tournois/{scenario.tournoi_id}/barrages/{barrage_id}/manche"
        client.put(
            url,
            json={
                "tirs": [
                    {"archer_id": second, "score": 9},
                    {"archer_id": troisieme, "score": 9},
                ]
            },
        )
        client.put(
            url,
            json={
                "tirs": [
                    {"archer_id": second, "score": 8},
                    {"archer_id": troisieme, "score": 10},
                ]
            },
        )

        corrige = client.put(
            url,
            json={
                "manche": 1,
                "tirs": [
                    {"archer_id": second, "score": 10},
                    {"archer_id": troisieme, "score": 8},
                ],
            },
        )

        assert corrige.status_code == 200, corrige.text
        assert len(corrige.json()["manches"]) == 1
        assert corrige.json()["ordre"] == [second, troisieme]
        assert client.get(f"/api/v1/tournois/{scenario.tournoi_id}/classement").status_code == 200


def test_annuler_un_barrage_libere_le_rang(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Sans annulation, un barrage ouvert par erreur restait définitif et bloquait son rang."""
    scenario = Scenario(app_barrages)
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        _regler_le_seuil(client, scenario, 8)
        barrage_id = client.post(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages", json={"rang": 2}
        ).json()["id"]

        annulation = client.delete(f"/api/v1/tournois/{scenario.tournoi_id}/barrages/{barrage_id}")

        assert annulation.status_code == 204
        assert client.get(f"/api/v1/tournois/{scenario.tournoi_id}/barrages").json() == []
        # Le rang est de nouveau annonçable.
        assert (
            client.post(
                f"/api/v1/tournois/{scenario.tournoi_id}/barrages", json={"rang": 2}
            ).status_code
            == 201
        )


def test_un_barrage_d_un_autre_tournoi_est_introuvable(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Deux tournois tournent en parallèle par conception : un identifiant deviné ne doit pas
    permettre d'écrire dans le barrage du voisin."""
    scenario = Scenario(app_barrages)
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        _regler_le_seuil(client, scenario, 8)
        barrage_id = client.post(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages", json={"rang": 2}
        ).json()["id"]
        autre = client.post("/api/v1/tournois", json={"nom": "Autre", "date": "2026-03-15"}).json()[
            "id"
        ]

        reponse = client.delete(f"/api/v1/tournois/{autre}/barrages/{barrage_id}")

        assert reponse.status_code == 404
        assert reponse.json()["code"] == "barrage_introuvable"


def test_corriger_un_barrage_clos_le_rouvre(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Corriger une flèche d'un barrage **déjà acté** doit rester possible.

    Une première version gardait les deux portes — `saisir_manche` refusait un barrage clos en
    renvoyant vers l'annulation, `annuler` le refusait en renvoyant vers la correction — et la
    ré-annonce échouait parce que le verdict faux avait éclaté l'égalité. Les trois issues étaient
    fermées : un verdict inversé sur la dernière place qualificative envoyait le mauvais archer au
    tableau, définitivement.
    """
    scenario = Scenario(app_barrages)
    _, second, troisieme = scenario.archers
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        _regler_le_seuil(client, scenario, 8)
        barrage_id = client.post(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages", json={"rang": 2}
        ).json()["id"]
        url = f"/api/v1/tournois/{scenario.tournoi_id}/barrages/{barrage_id}/manche"
        client.put(
            url,
            json={
                "tirs": [
                    {"archer_id": second, "score": 8},
                    {"archer_id": troisieme, "score": 10},
                ]
            },
        )
        client.post(f"/api/v1/tournois/{scenario.tournoi_id}/barrages/{barrage_id}/cloture")

        # Le juge s'aperçoit qu'il a inversé les scores : il corrige la manche 1.
        reponse = client.put(
            url,
            json={
                "manche": 1,
                "tirs": [
                    {"archer_id": second, "score": 10},
                    {"archer_id": troisieme, "score": 8},
                ],
            },
        )

        assert reponse.status_code == 200, reponse.text
        assert reponse.json()["clos"] is False
        assert reponse.json()["ordre"] == [second, troisieme]
        assert _rangs(client, scenario.tournoi_id)[second] == 2


def test_le_verdict_survit_a_l_effacement_du_seuil(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Promesse de l'étape 7 de la recette : les archers **ont** tiré, leur résultat n'est pas
    annulé par un changement de réglage."""
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
                    {"archer_id": second, "score": 8},
                    {"archer_id": troisieme, "score": 10},
                ]
            },
        )

        _regler_le_seuil(client, scenario, None)

        assert _classement(client, scenario.tournoi_id)["egalites_a_departager"] == []
        assert _rangs(client, scenario.tournoi_id) == {
            scenario.archers[0]: 1,
            troisieme: 2,
            second: 3,
        }


def test_un_score_hors_bareme_est_refuse(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Une flèche vaut au plus 10. Un `100` mal tapé gagnait le barrage et modifiait le podium.

    Borné au DTO, donc **400** (entrée invalide) et non 422 : la convention du projet distingue la
    requête mal formée de la règle métier violée."""
    scenario = Scenario(app_barrages)
    _, second, troisieme = scenario.archers
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
                    {"archer_id": second, "score": 100},
                    {"archer_id": troisieme, "score": 9},
                ]
            },
        )

        assert reponse.status_code == 400


# --- les trois portées (extension de périmètre du 02/08/2026) ------------------------------------
#
# En qualification les tireurs sont **dérivés** du classement ; en poule et en Big Shoot Off ils
# sont **désignés**, faute de classement calculé où les lire (DETTE-028). Ce sont donc les gardes
# du service qui remplacent ici ce que le classement garantissait gratuitement.


def test_un_barrage_de_poule_se_declare_avec_ses_tireurs(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Aucun seuil n'est requis : une poule ne passe pas par `egalites_a_departager`."""
    scenario = Scenario(app_barrages)
    premier, second, _ = scenario.archers
    with TestClient(app_barrages) as client:
        connecter_admin(client)

        annonce = client.post(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages",
            json={
                "portee": "poule",
                "archer_ids": [premier, second],
                "phase_id": scenario.qualif_id,
                "reference": "Poule A",
            },
        )

        assert annonce.status_code == 201, annonce.text
        assert annonce.json()["portee"] == "poule"
        assert annonce.json()["rang_dispute"] is None
        assert annonce.json()["participants"] == [premier, second]


def test_un_barrage_de_poule_se_tire_et_rend_son_verdict(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le moteur est le même : manches, absents, distance au centre, correction."""
    scenario = Scenario(app_barrages)
    premier, second, _ = scenario.archers
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        barrage_id = client.post(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages",
            json={"portee": "poule", "archer_ids": [premier, second], "reference": "Poule A"},
        ).json()["id"]

        manche = client.put(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages/{barrage_id}/manche",
            json={
                "tirs": [
                    {"archer_id": premier, "score": 7},
                    {"archer_id": second, "score": 10},
                ]
            },
        )

        assert manche.status_code == 200, manche.text
        assert manche.json()["est_resolu"] is True
        assert manche.json()["ordre"] == [second, premier]


def test_un_barrage_de_poule_ne_touche_pas_le_classement_de_qualification(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La limite exacte de l'extension, et elle est **voulue** : un barrage de poule départage une
    poule, pas le classement général. L'y appliquer réordonnerait la qualification sur un tir qui ne
    la concerne pas."""
    scenario = Scenario(app_barrages)
    premier, second, troisieme = scenario.archers
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        avant = _rangs(client, scenario.tournoi_id)
        barrage_id = client.post(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages",
            json={"portee": "poule", "archer_ids": [second, troisieme], "reference": "Poule A"},
        ).json()["id"]
        client.put(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages/{barrage_id}/manche",
            json={
                "tirs": [
                    {"archer_id": second, "score": 10},
                    {"archer_id": troisieme, "score": 8},
                ]
            },
        )

        assert _rangs(client, scenario.tournoi_id) == avant
        assert premier in avant


def test_un_big_shoot_off_se_declare_sans_rang(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Son égalité désigne un **sortant**, pas une place : il n'a pas de rang à disputer."""
    scenario = Scenario(app_barrages)
    premier, second, _ = scenario.archers
    with TestClient(app_barrages) as client:
        connecter_admin(client)

        annonce = client.post(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages",
            json={
                "portee": "big_shoot_off",
                "archer_ids": [premier, second],
                "reference": "manche 3",
            },
        )

        assert annonce.status_code == 201, annonce.text
        assert annonce.json()["rang_dispute"] is None
        # Sans rang, le verdict n'a rien à éclater : c'est `resultat()` qui donne le sortant.
        assert annonce.json()["est_resolu"] is False


def test_un_barrage_designe_exige_deux_archers_distincts(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    scenario = Scenario(app_barrages)
    premier, _, _ = scenario.archers
    with TestClient(app_barrages) as client:
        connecter_admin(client)

        reponse = client.post(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages",
            json={"portee": "poule", "archer_ids": [premier, premier]},
        )

        assert reponse.status_code == 409
        assert reponse.json()["code"] == "tireurs_designes_invalides"


def test_deux_poules_distinctes_ne_se_confondent_pas(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """L'idempotence porte sur le quadruplet (portée, phase, référence, rang) : deux poules du même
    tournoi disputent des places distinctes."""
    scenario = Scenario(app_barrages)
    premier, second, troisieme = scenario.archers
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        url = f"/api/v1/tournois/{scenario.tournoi_id}/barrages"

        a = client.post(
            url, json={"portee": "poule", "archer_ids": [premier, second], "reference": "Poule A"}
        )
        b = client.post(
            url,
            json={"portee": "poule", "archer_ids": [second, troisieme], "reference": "Poule B"},
        )
        bis = client.post(
            url, json={"portee": "poule", "archer_ids": [premier, second], "reference": "Poule A"}
        )

        assert a.json()["id"] != b.json()["id"]
        # Même référence = même barrage : l'annonce reste idempotente.
        assert bis.json()["id"] == a.json()["id"]
        assert len(client.get(url).json()) == 2


def test_un_barrage_de_qualification_sans_rang_est_refuse(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    scenario = Scenario(app_barrages)
    with TestClient(app_barrages) as client:
        connecter_admin(client)

        reponse = client.post(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages", json={"portee": "qualification"}
        )

        # 400 : le DTO refuse le régime incohérent avant même d'atteindre le service.
        assert reponse.status_code == 400


# --- correctifs de 2ᵉ passe ----------------------------------------------------------------------


def test_deux_egalites_de_poule_sans_repere_ne_se_confondent_pas(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """**Le cas par défaut de l'écran**, et celui que la 1ʳᵉ version écrasait.

    Le formulaire n'envoie ni rang, ni phase, et laisse le repère vide : les quatre composantes de
    l'ancienne clé d'identité étaient donc nulles. Le second appel rendait le **premier** barrage,
    l'écran vidait la sélection, et la deuxième égalité n'avait pas de barrage sans que rien ne le
    dise. Le test précédent utilisait « Poule A » / « Poule B » — la fixture choisissait exactement
    les valeurs qui contournaient la borne.
    """
    scenario = Scenario(app_barrages)
    premier, second, troisieme = scenario.archers
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        url = f"/api/v1/tournois/{scenario.tournoi_id}/barrages"

        a = client.post(url, json={"portee": "poule", "archer_ids": [premier, second]})
        b = client.post(url, json={"portee": "poule", "archer_ids": [second, troisieme]})

        assert a.status_code == 201 and b.status_code == 201, b.text
        assert a.json()["id"] != b.json()["id"]
        assert b.json()["participants"] == [second, troisieme]
        assert len(client.get(url).json()) == 2


def test_reannoncer_les_memes_tireurs_reste_idempotent(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    scenario = Scenario(app_barrages)
    premier, second, _ = scenario.archers
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        url = f"/api/v1/tournois/{scenario.tournoi_id}/barrages"

        a = client.post(url, json={"portee": "poule", "archer_ids": [premier, second]})
        bis = client.post(url, json={"portee": "poule", "archer_ids": [second, premier]})

        assert a.json()["id"] == bis.json()["id"]


def test_un_barrage_perime_est_refuse_au_lieu_d_etre_rendu(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un barrage annoncé sur deux archers, puis un troisième rejoint l'égalité.

    L'ancien barrage ne départage plus le bon groupe et son verdict sera écarté. Avant correctif,
    la ré-annonce le **rendait** en silence : l'organisateur faisait tirer deux archers sur trois,
    actait, et le classement ne bougeait pas.
    """
    scenario = Scenario(app_barrages)
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        _regler_le_seuil(client, scenario, 8)
        url = f"/api/v1/tournois/{scenario.tournoi_id}/barrages"
        assert client.post(url, json={"rang": 2}).status_code == 201

        # Un 4ᵉ archer, dont la volée est validée en retard, rejoint l'égalité du rang 2.
        _ajouter_archer(app_barrages, scenario, ("10", "9", "8"))

        reponse = client.post(url, json={"rang": 2})

        assert reponse.status_code == 409
        assert reponse.json()["code"] == "barrage_perime"


def test_la_qualification_refuse_les_champs_du_regime_designe(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`phase_id`/`reference` entraient dans la clé d'identité : les accepter en qualification
    permettait **deux** barrages au même rang, aux verdicts contradictoires, le dernier gagnant."""
    scenario = Scenario(app_barrages)
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        _regler_le_seuil(client, scenario, 8)
        url = f"/api/v1/tournois/{scenario.tournoi_id}/barrages"
        assert client.post(url, json={"rang": 2}).status_code == 201

        reponse = client.post(url, json={"rang": 2, "reference": "x"})

        assert reponse.status_code == 400
        assert reponse.json()["code"] == "requete_invalide"


def test_un_barrage_incoherent_n_emporte_pas_le_panneau(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le filet avait été posé sur le classement, pas sur les barrages.

    Un seul agrégat illisible mettait **tout** le panneau d'organisation en 422 — donc les boutons
    « Annuler » et « Corriger » qui seraient la réparation. On dégrade : le barrage reste listé et
    actionnable, marqué incohérent.
    """
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
                    {"archer_id": troisieme, "score": 10},
                ]
            },
        )
        # On corrompt l'agrégat comme le ferait une écriture directe en base : un tir de trop.
        db = app_barrages.state.database
        with db.session_factory() as session:
            session.add(BarrageTirORM(barrage_id=barrage_id, manche=2, archer_id=second, score=7))
            session.commit()

        liste = client.get(f"/api/v1/tournois/{scenario.tournoi_id}/barrages")

        assert liste.status_code == 200, liste.text
        assert liste.json()[0]["incoherent"] is True
        assert liste.json()[0]["est_resolu"] is False
        # …et le barrage reste annulable, donc réparable depuis l'écran.
        assert (
            client.delete(
                f"/api/v1/tournois/{scenario.tournoi_id}/barrages/{barrage_id}"
            ).status_code
            == 204
        )


def test_annuler_exige_l_admin(app_barrages: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """La route la plus destructive de l'US n'avait aucun test d'autorisation."""
    scenario = Scenario(app_barrages)
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        _regler_le_seuil(client, scenario, 8)
        barrage_id = client.post(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages", json={"rang": 2}
        ).json()["id"]
        client.cookies.clear()
        client.headers.pop("Authorization", None)

    with TestClient(app_barrages) as anonyme:
        reponse = anonyme.delete(f"/api/v1/tournois/{scenario.tournoi_id}/barrages/{barrage_id}")

    assert reponse.status_code == 401


def test_un_archer_d_un_vrai_autre_tournoi_est_refuse(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La version précédente passait `99999` : elle prouvait « identifiant inconnu », pas
    « archer d'un autre tournoi » — le scénario de sécurité que la docstring invoque."""
    scenario = Scenario(app_barrages)
    premier, _, _ = scenario.archers
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        voisin = Scenario(app_barrages)

        reponse = client.post(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages",
            json={"portee": "poule", "archer_ids": [premier, voisin.archers[0]]},
        )

        assert reponse.status_code == 409
        assert reponse.json()["code"] == "tireurs_designes_invalides"


def test_une_phase_d_un_vrai_autre_tournoi_est_refusee(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    scenario = Scenario(app_barrages)
    premier, second, _ = scenario.archers
    with TestClient(app_barrages) as client:
        connecter_admin(client)
        voisin = Scenario(app_barrages)

        reponse = client.post(
            f"/api/v1/tournois/{scenario.tournoi_id}/barrages",
            json={
                "portee": "poule",
                "archer_ids": [premier, second],
                "phase_id": voisin.qualif_id,
            },
        )

        assert reponse.status_code == 409
        assert reponse.json()["code"] == "tireurs_designes_invalides"


def test_le_verdict_est_visible_du_classement_que_consomme_le_placement(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le classement **que consomme le placement** porte bien l'ordre issu du barrage.

    ⚠️ **Portée exacte de ce test, parce que son nom précédent mentait.** Il vérifie que le
    classement rendu par l'API reflète le verdict ; il ne traverse **pas** `ServicePlacementDuels`
    et ne monte aucune phase d'élimination directe. La couture complète seuil → classement →
    composition du tableau reste donc **non exercée** : elle demande un décor de tableau, qui
    appartient à E06US004 (podium & agrégation des rangs). L'oracle 120 et les tests d'E06US001
    passent tous par le chemin par défaut (sans seuil, sans verdict) et ne peuvent rien en dire —
    c'est un angle mort connu, inscrit au registre plutôt que masqué par un nom flatteur.
    """
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
                    {"archer_id": second, "score": 7},
                    {"archer_id": troisieme, "score": 10},
                ]
            },
        )

        # Le classement que consomme le placement voit bien l'ordre issu du barrage.
        rangs = _rangs(client, scenario.tournoi_id)
        assert rangs[troisieme] == 2
        assert rangs[second] == 3


def test_un_barrage_acte_devient_perime_si_le_groupe_change(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """**Un barrage clos peut être périmé** — l'exclure était une présomption fausse.

    Le domaine écarte un verdict dès que le groupe d'ex æquo a changé, sans jamais regarder `clos`.
    Un archer qu'une volée validée en retard amène à l'égalité *après* la clôture fait donc écarter
    le verdict : les rangs redeviennent partagés. Sans ce signal, l'écran affichait « Départagé »
    en vert pendant que le classement disait le contraire, sans un mot.
    """
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
                    {"archer_id": second, "score": 8},
                    {"archer_id": troisieme, "score": 10},
                ]
            },
        )
        client.post(f"/api/v1/tournois/{scenario.tournoi_id}/barrages/{barrage_id}/cloture")
        assert _rangs(client, scenario.tournoi_id)[troisieme] == 2

        # Un 4ᵉ archer rejoint l'égalité : le verdict clos ne décrit plus le bon groupe.
        _ajouter_archer(app_barrages, scenario, ("10", "9", "8"))

        barrage = client.get(f"/api/v1/tournois/{scenario.tournoi_id}/barrages").json()[0]
        assert barrage["clos"] is True
        assert barrage["perime"] is True, "un barrage clos dont le groupe a changé est périmé"
        # …et le classement confirme : le verdict est écarté, les rangs sont repartagés — **les
        # trois**, arrivant compris. Sans cette dernière assertion, une variante où l'arrivant
        # serait mal classé tout en repartageant les deux autres passerait inaperçue.
        rangs = _rangs(client, scenario.tournoi_id)
        assert rangs[second] == 2
        assert rangs[troisieme] == 2
        assert sorted(rang for rang in rangs.values() if rang is not None) == [1, 2, 2, 2]


def test_un_barrage_acte_dont_le_verdict_tient_n_est_pas_perime(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le contre-test qui évite la sur-correction : sans lui, retirer le court-circuit `clos`
    aurait pu marquer périmés **tous** les barrages achevés."""
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
                    {"archer_id": second, "score": 8},
                    {"archer_id": troisieme, "score": 10},
                ]
            },
        )
        client.post(f"/api/v1/tournois/{scenario.tournoi_id}/barrages/{barrage_id}/cloture")

        barrage = client.get(f"/api/v1/tournois/{scenario.tournoi_id}/barrages").json()[0]

        assert barrage["clos"] is True
        assert barrage["perime"] is False


def test_un_barrage_acte_est_perime_meme_si_le_groupe_glisse_de_rang(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """**Premier cas que le proxy manquait** : l'arrivant passe DEVANT le groupe.

    L'égalité ne se signale alors plus au rang 2 mais au rang 3 — donc une péremption déduite de
    « y a-t-il une égalité **à mon rang** ? » répondait non, pendant que le domaine écartait bien le
    verdict et repartageait les rangs. L'écran affichait « Départagé » en vert au-dessus de rangs
    partagés.
    """
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
                    {"archer_id": second, "score": 8},
                    {"archer_id": troisieme, "score": 10},
                ]
            },
        )
        client.post(f"/api/v1/tournois/{scenario.tournoi_id}/barrages/{barrage_id}/cloture")

        # 28 > 27 : l'arrivant se place **devant** la paire, qui glisse du rang 2 au rang 3.
        _ajouter_archer(app_barrages, scenario, ("10", "10", "8"))

        barrage = client.get(f"/api/v1/tournois/{scenario.tournoi_id}/barrages").json()[0]
        rangs = _rangs(client, scenario.tournoi_id)
        assert rangs[second] == rangs[troisieme], "le verdict est écarté, les rangs sont repartagés"
        assert barrage["perime"] is True, "…et l'écran doit le dire"


def test_un_barrage_acte_est_perime_meme_si_le_seuil_est_efface(
    app_barrages: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """**Second cas que le proxy manquait**, et c'est l'étape 7 de la recette.

    Le seuil effacé, plus **aucune** égalité n'est signalée : la péremption déduite des égalités
    répondait donc non pour tout le monde. Or si le groupe a changé entre-temps, le verdict reste
    écarté et les rangs partagés — écran vert, tableau contradictoire, aucun signal.
    """
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
                    {"archer_id": second, "score": 8},
                    {"archer_id": troisieme, "score": 10},
                ]
            },
        )
        client.post(f"/api/v1/tournois/{scenario.tournoi_id}/barrages/{barrage_id}/cloture")
        _ajouter_archer(app_barrages, scenario, ("10", "9", "8"))

        _regler_le_seuil(client, scenario, None)

        assert _classement(client, scenario.tournoi_id)["egalites_a_departager"] == []
        barrage = client.get(f"/api/v1/tournois/{scenario.tournoi_id}/barrages").json()[0]
        assert (
            _rangs(client, scenario.tournoi_id)[second]
            == _rangs(client, scenario.tournoi_id)[troisieme]
        )
        assert barrage["perime"] is True
