"""Test bout-en-bout de l'API de saisie en duels (E04US013).

Traverse HTTP → service → moteur → repositories, après avoir semé un tournoi jouable : deux archers
**classés** (séries validées), une phase d'élimination, un scoreur. On valide le **câblage** des
routes, l'auth scoreur et le mapping d'erreurs — la logique (scoring, reconstruction) est couverte
par `test_domain_duel` / `test_service_saisie_duels` / `test_duel_repository`. Écrit **après**
l'implémentation (règle 9 : API/câblage, pas d'oracle en jeu).

Bracket **à deux archers** : `construire_tableau` produit un unique match — la **finale**. On y
saisit trois manches, on valide, et le tableau reflète le vainqueur (progression transmise).
"""

from __future__ import annotations

import datetime
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from domain.archer import Archer
from domain.bareme import BaremeQualification
from domain.blason import Blason, ZoneScore
from domain.categorie import Categorie, SexeCategorie
from domain.depart import Depart
from domain.duel import BaremeDuel, ModeDuel, ReglageBaremeDuel
from domain.equipe import Equipe, TypeEquipe
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
from infrastructure.db.repositories.equipes import EquipeRepositorySQL
from infrastructure.horloge import HorlogeSysteme
from tests.base_migree import preparer_base
from tests.conftest import ConnecterAdmin, poser_phase_sql

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)


def _migrer(url: str) -> None:
    preparer_base(url)


class Scenario:
    """Un tournoi à deux archers classés, une phase d'élimination, un scoreur (code)."""

    def __init__(self, app: FastAPI, reglage: ReglageBaremeDuel | None = None) -> None:
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
        depart = DepartRepositorySQL(db.session_factory).ajouter(
            Depart.creer(tournoi_id=self.tournoi_id, numero=1, tarif_centimes=800, horaire="09:00")
        )
        assert depart.id is not None
        self.depart_id = depart.id
        _depart_id = depart.id
        inscriptions = InscriptionRepositorySQL(
            db.session_factory, AuditRepositorySQL(db.session_factory)
        )
        self.archers: list[int] = []
        # E05US025 : ce decor ne posait que le tableau (ordre 2). Une feuille de marque pend
        # desormais a sa phase, et le classement qui ensemence le tableau se lit sur la
        # **qualification** : il faut donc la poser, a l'ordre 1, avant de semer les scores.
        qualif = poser_phase_sql(
            db.session_factory, Phase.qualification(_depart_id, BaremeQualification.creer(1, 3))
        )
        assert qualif.id is not None
        self.qualif_id = qualif.id
        for valeurs in (("10", "10", "10"), ("9", "9", "9")):  # scores décroissants → rang 1, 2
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
                    phase_id=self.qualif_id,
                )
            )
            # C'est l'**inscription** qui fait entrer l'archer au classement du créneau
            # (ADR-0075) — sans elle, le tableau s'ensemencerait sur zéro participant.
            inscriptions.ajouter(Inscription(archer.id, _depart_id))
            self.archers.append(archer.id)
        phase = poser_phase_sql(
            db.session_factory,
            replace(Phase.creer(_depart_id, 2, TypePhase.ELIMINATION_DIRECTE), bareme_duel=reglage),
        )
        assert phase.id is not None
        self.phase_id = phase.id


@pytest.fixture
def app_duels(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _scoreur(
    client: TestClient, tournoi_id: int, connecter_admin: ConnecterAdmin
) -> dict[str, str]:
    """Crée un scoreur (admin) et ouvre sa session ; renvoie l'en-tête `X-Jeton-Scoreur`."""
    connecter_admin(client)  # authentifie le client en admin (en place)
    reponse = client.post(f"/api/v1/tournois/{tournoi_id}/scoreurs", json={"nom": "ROUX"})
    assert reponse.status_code in (200, 201), reponse.text
    code = reponse.json()["code"]
    jeton = client.post("/api/v1/scoreurs/session", json={"code": code}).json()["jeton"]
    return {"X-Jeton-Scoreur": jeton}


def _manche(
    numero: int, haut: tuple[str, ...], bas: tuple[str, ...], phase_id: int, tid: int
) -> dict[str, object]:
    return {
        "tournoi_id": tid,
        "phase_id": phase_id,
        "match_numero": 1,
        "numero": numero,
        "valeurs_haut": list(haut),
        "valeurs_bas": list(bas),
    }


def test_saisir_valider_un_duel_fait_avancer_le_tableau(
    app_duels: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Câblage complet : GET tableau, saisir, valider → le vainqueur est le mieux classé."""
    with TestClient(app_duels) as client:
        scn = Scenario(app_duels)
        entete = _scoreur(client, scn.tournoi_id, connecter_admin)

        tableau = client.get(
            f"/api/v1/duels/tableau/{scn.tournoi_id}/{scn.phase_id}", headers=entete
        )
        assert tableau.status_code == 200, tableau.text
        finale = next(d for d in tableau.json()["duels"] if d["place_en_jeu"] == [1, 2])
        assert finale["numero"] == 1
        vainqueur_attendu = finale["haut"]["archer_id"]  # tête de série n°1 en haut
        # Le pavé du front est dimensionné dès la lecture, avant tout tir (arc classique → sets).
        assert finale["mode"] == "sets"
        assert finale["nb_manches"] == 5
        assert finale["nb_fleches_par_volee"] == 3
        assert finale["points_pour_gagner"] == 6
        # Zones du blason (par défaut ici) : pavé non vide contenant le tirable saisi.
        assert finale["zones"], "le pavé du match jouable expose les zones légales du blason"
        assert {"10", "9"} <= set(finale["zones"])

        for numero in (1, 2, 3):
            reponse = client.post(
                "/api/v1/duels/manches",
                json=_manche(
                    numero, ("10", "10", "10"), ("9", "9", "9"), scn.phase_id, scn.tournoi_id
                ),
                headers=entete,
            )
            assert reponse.status_code == 200, reponse.text

        valide = client.post(
            "/api/v1/duels/validations",
            json={"tournoi_id": scn.tournoi_id, "phase_id": scn.phase_id, "match_numero": 1},
            headers=entete,
        )
        assert valide.status_code == 200, valide.text
        assert valide.json()["resultat"]["vainqueur"] == "haut"
        assert valide.json()["validee_par"] == "ROUX"

        apres = client.get(
            f"/api/v1/duels/tableau/{scn.tournoi_id}/{scn.phase_id}", headers=entete
        ).json()
        assert apres["est_termine"] is True
        podium = {place["rang"]: place["duelliste"]["archer_id"] for place in apres["podium"]}
        assert podium[1] == vainqueur_attendu


def test_code_de_zone_ou_camp_invalide_refuse(
    app_duels: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """DTO typés `ZoneScore`/`Cote` : un code inconnu est rejeté par Pydantic (400), pas 500.

    Cohérence de frontière avec E04US002 : `RequestValidationError → 400 requete_invalide`.
    """
    with TestClient(app_duels) as client:
        scn = Scenario(app_duels)
        entete = _scoreur(client, scn.tournoi_id, connecter_admin)
        manche = client.post(
            "/api/v1/duels/manches",
            json={
                "tournoi_id": scn.tournoi_id,
                "phase_id": scn.phase_id,
                "match_numero": 1,
                "numero": 1,
                "valeurs_haut": ["42", "10", "10"],  # 42 n'est pas une ZoneScore
                "valeurs_bas": ["9", "9", "9"],
            },
            headers=entete,
        )
        assert manche.status_code == 400, manche.text
        barrage = client.post(
            "/api/v1/duels/barrages",
            json={
                "tournoi_id": scn.tournoi_id,
                "phase_id": scn.phase_id,
                "match_numero": 1,
                "fleches_haut": ["10"],
                "fleches_bas": ["10"],
                "gagnant_designe": "milieu",  # n'est pas une Cote (haut/bas)
            },
            headers=entete,
        )
        assert barrage.status_code == 400, barrage.text


def test_saisie_sans_session_scoreur_refusee(app_duels: FastAPI) -> None:
    """Sans en-tête scoreur, la saisie est refusée (401)."""
    with TestClient(app_duels) as client:
        scn = Scenario(app_duels)
        reponse = client.post(
            "/api/v1/duels/manches",
            json=_manche(1, ("10", "10", "10"), ("9", "9", "9"), scn.phase_id, scn.tournoi_id),
        )
        assert reponse.status_code == 401, reponse.text


def test_scoreur_d_un_autre_tournoi_refuse(
    app_duels: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un scoreur n'officie que dans **son** tournoi (403 scoreur_hors_tournoi)."""
    with TestClient(app_duels) as client:
        scn = Scenario(app_duels)
        entete = _scoreur(client, scn.tournoi_id, connecter_admin)
        # Un autre tournoi, dont ce scoreur n'est pas.
        autre = TournoiRepositorySQL(app_duels.state.database.session_factory).ajouter(
            Tournoi.creer("Autre", _DATE)
        )
        assert autre.id is not None
        reponse = client.get(f"/api/v1/duels/tableau/{autre.id}/{scn.phase_id}", headers=entete)
        assert reponse.status_code == 403, reponse.text


def _egaliser(client: TestClient, scn: Scenario, entete: dict[str, str], nb_manches: int) -> None:
    for numero in range(1, nb_manches + 1):
        reponse = client.post(
            "/api/v1/duels/manches",
            json=_manche(numero, ("9", "9", "9"), ("9", "9", "9"), scn.phase_id, scn.tournoi_id),
            headers=entete,
        )
        assert reponse.status_code == 200, reponse.text


def _barrage(scn: Scenario, haut: list[str], bas: list[str]) -> dict[str, object]:
    return {
        "tournoi_id": scn.tournoi_id,
        "phase_id": scn.phase_id,
        "match_numero": 1,
        "fleches_haut": haut,
        "fleches_bas": bas,
    }


def test_barrage_individuel_a_une_fleche_de_bout_en_bout(
    app_duels: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """E13US003 CA 2-3 : sans réglage, le barrage reste à une flèche, servie en liste."""
    with TestClient(app_duels) as client:
        scn = Scenario(app_duels)
        entete = _scoreur(client, scn.tournoi_id, connecter_admin)
        _egaliser(client, scn, entete, 5)

        reponse = client.post(
            "/api/v1/duels/barrages", json=_barrage(scn, ["10"], ["9"]), headers=entete
        )

        assert reponse.status_code == 200, reponse.text
        duel = reponse.json()
        assert duel["nb_fleches_barrage"] == 1
        assert duel["barrage"]["haut"] == ["10"]
        assert duel["resultat"]["points_haut"] == 6


def test_barrage_d_equipe_a_trois_fleches_relu_depuis_la_base(
    app_duels: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """E13US003 CA 3, 6 : barème à 3 flèches de barrage — 1 flèche refusée, 3 au total tranchent,
    et le tir relu par GET garde ses trois flèches (aller-retour JSON de la colonne `barrage`)."""
    equipe = BaremeDuel(ModeDuel.SETS, 4, 3, 5, nb_fleches_barrage=3)
    with TestClient(app_duels) as client:
        scn = Scenario(app_duels, ReglageBaremeDuel(par_defaut=equipe))
        entete = _scoreur(client, scn.tournoi_id, connecter_admin)
        _egaliser(client, scn, entete, 4)

        trop = client.post(
            "/api/v1/duels/barrages", json=_barrage(scn, ["10"] * 13, ["9"] * 13), headers=entete
        )
        assert trop.status_code == 400, trop.text  # borné à la frontière, avant la file d'écriture
        refus = client.post(
            "/api/v1/duels/barrages", json=_barrage(scn, ["10"], ["9"]), headers=entete
        )
        assert refus.status_code == 422, refus.text
        assert refus.json()["code"] == "nombre_fleches_volee_invalide"

        reponse = client.post(
            "/api/v1/duels/barrages",
            json=_barrage(scn, ["9", "9", "9"], ["10", "8", "8"]),
            headers=entete,
        )
        assert reponse.status_code == 200, reponse.text
        assert reponse.json()["resultat"]["points_haut"] == 5  # 4-4 → 5-4 (§7)

        tableau = client.get(
            f"/api/v1/duels/tableau/{scn.tournoi_id}/{scn.phase_id}", headers=entete
        ).json()
        finale = next(d for d in tableau["duels"] if d["numero"] == 1)
        assert finale["nb_fleches_barrage"] == 3
        assert finale["barrage"]["haut"] == ["9", "9", "9"]
        assert finale["barrage"]["bas"] == ["10", "8", "8"]


def _tableau_d_equipes(app: FastAPI) -> tuple[int, int]:
    """Deux équipes conformes de trois et une incomplète, une phase réglée par équipes (E13US004).

    Rend `(tournoi_id, phase_id)`. Toutes les catégories portent arme **et** sexe : sans eux, la
    composition serait « non vérifiable » et l'équipe écartée.
    """
    db: Database = app.state.database
    tournoi = TournoiRepositorySQL(db.session_factory).ajouter(Tournoi.creer("Salle", _DATE))
    assert tournoi.id is not None
    blason = BlasonRepositorySQL(db.session_factory).ajouter(
        Blason.creer(tournoi.id, "Triple", taille=0.25, capacite=1)
    )
    categorie = CategorieRepositorySQL(db.session_factory).ajouter(
        Categorie.creer(
            tournoi.id, "CLH", arme="Classique", sexe=SexeCategorie.HOMME, blason_id=blason.id
        )
    )
    depart = DepartRepositorySQL(db.session_factory).ajouter(
        Depart.creer(tournoi_id=tournoi.id, numero=1, tarif_centimes=800, horaire="09:00")
    )
    assert depart.id is not None and categorie.id is not None
    qualif = poser_phase_sql(
        db.session_factory, Phase.qualification(depart.id, BaremeQualification.creer(1, 3))
    )
    assert qualif.id is not None
    series = SerieRepositorySQL(
        db.session_factory, AuditRepositorySQL(db.session_factory), HorlogeSysteme()
    )
    inscriptions = InscriptionRepositorySQL(
        db.session_factory, AuditRepositorySQL(db.session_factory)
    )
    archers: list[int] = []
    for valeur in ("10", "10", "10", "9", "9", "9", "8", "8"):
        archer = ArcherRepositorySQL(db.session_factory).ajouter(
            Archer(nom="N", prenom="P", tournoi_id=tournoi.id, categorie_id=categorie.id)
        )
        assert archer.id is not None
        series.enregistrer(
            Serie(
                tournoi_id=tournoi.id,
                archer_id=archer.id,
                volees=(Volee(numero=1, valeurs=(ZoneScore(valeur),) * 3, validee_par="S"),),
                phase_id=qualif.id,
            )
        )
        inscriptions.ajouter(Inscription(archer.id, depart.id))
        archers.append(archer.id)
    equipes = EquipeRepositorySQL(db.session_factory)
    for nom, membres in (("A", archers[0:3]), ("B", archers[3:6]), ("C", archers[6:8])):
        equipes.enregistrer(
            Equipe(tournoi.id, nom, TypeEquipe.STANDARD, effectif_attendu=3, membres=tuple(membres))
        )
    phase = poser_phase_sql(
        db.session_factory,
        replace(
            Phase.creer(depart.id, 2, TypePhase.ELIMINATION_DIRECTE), equipes=TypeEquipe.STANDARD
        ),
    )
    assert phase.id is not None
    return tournoi.id, phase.id


def test_un_tableau_d_equipes_se_lit_et_se_saisit_de_bout_en_bout(
    app_duels: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """E13US004 : camps nommés par l'équipe, équipe écartée listée, manche de 6 flèches par camp."""
    with TestClient(app_duels) as client:
        tournoi_id, phase_id = _tableau_d_equipes(app_duels)
        entete = _scoreur(client, tournoi_id, connecter_admin)

        tableau = client.get(f"/api/v1/duels/tableau/{tournoi_id}/{phase_id}", headers=entete)

        assert tableau.status_code == 200, tableau.text
        corps = tableau.json()
        (finale,) = corps["duels"]
        assert (finale["haut"]["nom"], finale["haut"]["archer_id"]) == ("A", None)
        assert finale["haut"]["equipe_id"] is not None
        assert len(finale["haut"]["membres"]) == 3
        assert finale["nb_fleches_par_volee"] == 6
        assert corps["equipes_ecartees"] == [
            {
                "equipe_id": corps["equipes_ecartees"][0]["equipe_id"],
                "nom": "C",
                "ecarts": ["effectif_insuffisant"],
                "membres_hors_course": [],
            }
        ]
        manche = client.post(
            "/api/v1/duels/manches",
            json=_manche(1, ("10",) * 6, ("9",) * 6, phase_id, tournoi_id),
            headers=entete,
        )
        assert manche.status_code == 200, manche.text
