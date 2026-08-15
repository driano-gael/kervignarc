"""E05US026 — le système suisse par HTTP, de bout en bout.

Écrit **après** l'implémentation (règle 9 : API et câblage, il n'y a pas d'oracle en jeu).

⚠️ Ce fichier couvre aussi le **branchement du composition root**, qui n'a pas d'autre garde : le
port `LecteurClassementDePhase` est câblé après construction, donc son oubli ne casserait aucune
compilation — seulement, en salle, un prélèvement visant un suisse qui redeviendrait inerte.
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
from domain.depart import Depart
from domain.inscription import Inscription
from domain.phase import Phase, TypePhase
from domain.serie import Serie, Volee
from domain.suisse import ConfigurationSuisse
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

_DATE = datetime.date(2026, 3, 1)


class Scenario:
    """Un tournoi, un créneau, `effectif` archers classés, une phase de **système suisse**."""

    def __init__(self, app: FastAPI, *, effectif: int = 4, nb_rondes: int = 3) -> None:
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
            # Scores strictement décroissants : le rang scratch est prévisible, donc l'appariement
            # de la ronde 1 (fort contre faible) l'est aussi.
            valeur = str(max(6, 10 - rang))
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
                type=TypePhase.SUISSE,
                suisse=ConfigurationSuisse(nb_rondes=nb_rondes),
            ),
        )
        assert phase.id is not None
        self.phase_id = phase.id


@pytest.fixture
def app_suisse(tmp_path: Path) -> Iterator[FastAPI]:
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


def _gagner(
    client: TestClient, entetes: dict[str, str], scn: Scenario, numero: int, *, le_bas: bool
) -> None:
    """Fait gagner un camp d'une rencontre par HTTP, puis la valide."""
    fort = ["10", "10", "10"]
    faible = ["6", "6", "6"]
    for manche in (1, 2, 3):
        reponse = client.post(
            "/api/v1/suisse/manches",
            json={
                "tournoi_id": scn.tournoi_id,
                "phase_id": scn.phase_id,
                "numero": numero,
                "manche": manche,
                "valeurs_haut": faible if le_bas else fort,
                "valeurs_bas": fort if le_bas else faible,
            },
            headers=entetes,
        )
        assert reponse.status_code == 200, reponse.text
    reponse = client.post(
        "/api/v1/suisse/validations",
        json={"tournoi_id": scn.tournoi_id, "phase_id": scn.phase_id, "numero": numero},
        headers=entetes,
    )
    assert reponse.status_code == 200, reponse.text


def test_letat_expose_la_premiere_ronde_et_la_borne_de_rondes(app_suisse: FastAPI) -> None:
    """La photo telle que l'écran la consomme : rondes appariées, borne, classement.

    À 4 archers, la borne vaut 3 (chacun n'a que 3 adversaires) : c'est le CA « le maximum que
    l'effectif autorise affiché en clair », rendu par le service et non recalculé côté écran.
    """
    with TestClient(app_suisse) as client:
        scn = Scenario(app_suisse)

        reponse = client.get(f"/api/v1/suisse/etat/{scn.tournoi_id}/{scn.phase_id}")

    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["phase_id"] == scn.phase_id
    assert corps["effectif"] == 4
    assert corps["nb_rondes"] == 3
    assert corps["rondes_maximales"] == 3
    assert len(corps["rondes"]) == 1
    assert corps["rondes"][0]["close"] is False
    assert [r["numero"] for r in corps["rondes"][0]["rencontres"]] == [1, 2]


def test_la_ronde_suivante_apparait_quand_la_precedente_est_close(
    app_suisse: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """**Le CA de l'US, par HTTP.** Il n'y a pas de geste « ronde suivante » : elle se déduit.

    On fait gagner les **mal classés** en ronde 1 (1 vs 3 et 2 vs 4, le bas l'emporte) : la ronde 2
    doit opposer les deux vainqueurs entre eux et les deux perdants entre eux — ordre qu'aucune
    lecture du classement de qualification ne produirait.
    """
    with TestClient(app_suisse) as client:
        scn = Scenario(app_suisse)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)

        _gagner(client, entetes, scn, 1, le_bas=True)
        # Une seule rencontre validée : la ronde reste ouverte, la suivante n'existe pas.
        corps = client.get(f"/api/v1/suisse/etat/{scn.tournoi_id}/{scn.phase_id}").json()
        assert len(corps["rondes"]) == 1
        assert corps["rondes"][0]["close"] is False

        _gagner(client, entetes, scn, 2, le_bas=True)
        corps = client.get(f"/api/v1/suisse/etat/{scn.tournoi_id}/{scn.phase_id}").json()

    assert len(corps["rondes"]) == 2
    assert corps["rondes"][0]["close"] is True
    paires = {
        tuple(sorted((r["haut"]["archer_id"], r["bas"]["archer_id"])))
        for r in corps["rondes"][1]["rencontres"]
    }
    assert paires == {
        tuple(sorted((scn.archers[2], scn.archers[3]))),
        tuple(sorted((scn.archers[0], scn.archers[1]))),
    }


def test_le_classement_se_lit_des_la_premiere_ronde_close(
    app_suisse: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Les vainqueurs mènent — le classement suit les points, pas le rang de qualification."""
    with TestClient(app_suisse) as client:
        scn = Scenario(app_suisse)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)

        _gagner(client, entetes, scn, 1, le_bas=True)
        _gagner(client, entetes, scn, 2, le_bas=True)
        corps = client.get(f"/api/v1/suisse/etat/{scn.tournoi_id}/{scn.phase_id}").json()

    tetes = {ligne["archer_id"] for ligne in corps["classement"][:2]}
    assert tetes == {scn.archers[2], scn.archers[3]}
    assert all(ligne["points"] == 2 for ligne in corps["classement"][:2])


def test_une_saisie_hors_tournoi_est_refusee(
    app_suisse: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un scoreur n'officie que dans **son** tournoi (403), comme sur les deux autres décors."""
    with TestClient(app_suisse) as client:
        scn = Scenario(app_suisse)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)

        reponse = client.post(
            "/api/v1/suisse/validations",
            json={"tournoi_id": scn.tournoi_id + 999, "phase_id": scn.phase_id, "numero": 1},
            headers=entetes,
        )

    assert reponse.status_code == 403, reponse.text


def test_une_rencontre_dune_ronde_non_appariee_est_introuvable(
    app_suisse: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Une rencontre de la ronde 2 n'existe pas tant que la ronde 1 n'est pas close — 404.

    C'est exact et non un contournement : le moteur **refuse** d'apparier par-dessus une ronde en
    cours, donc la rencontre n'a pas encore de duellistes. Le message le dit plutôt que de laisser
    croire à une phase mal composée.
    """
    with TestClient(app_suisse) as client:
        scn = Scenario(app_suisse)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)

        reponse = client.post(
            "/api/v1/suisse/validations",
            json={"tournoi_id": scn.tournoi_id, "phase_id": scn.phase_id, "numero": 3},
            headers=entetes,
        )

    assert reponse.status_code == 404, reponse.text


def test_une_phase_avale_preleve_dans_le_suisse(
    app_suisse: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """**Le branchement du composition root**, et il n'a pas d'autre garde.

    Le port est câblé après construction : son oubli ne casserait aucune compilation. Sans lui, un
    prélèvement visant un suisse resterait **inerte** et la phase avale recevrait *tous* les archers
    en lice — une population bien formée, plausible et fausse, exactement le défaut d'avant
    E05US024.
    """
    from domain.phase import SourcePhase

    with TestClient(app_suisse) as client:
        scn = Scenario(app_suisse, nb_rondes=1)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)
        db: Database = app_suisse.state.database
        aval = poser_phase_sql(
            db.session_factory,
            Phase(
                depart_id=scn.depart_id,
                ordre=3,
                type=TypePhase.ELIMINATION_DIRECTE,
                sources=(SourcePhase.par_rangs(ordre_source=2, rang_debut=1, rang_fin=2),),
            ),
        )
        assert aval.id is not None

        _gagner(client, entetes, scn, 1, le_bas=True)
        _gagner(client, entetes, scn, 2, le_bas=True)
        reponse = client.get(f"/api/v1/tableaux/departs/{scn.depart_id}")

    assert reponse.status_code == 200, reponse.text
    tableaux = {t["phase_id"]: t for t in reponse.json()["tableaux"]}
    assert aval.id in tableaux
    # Les deux **vainqueurs** de la ronde, pas les deux premiers de la qualification.
    assert tableaux[aval.id]["effectif"] == 2
