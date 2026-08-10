"""Test bout-en-bout de l'API des **poules** (E05US023, ADR-0083).

Traverse HTTP → `ServicePoules` → moteur → repositories, sur un tournoi jouable : une salle, six
archers **classés** (séries validées), une phase de poules réglée, un scoreur. On valide le
**câblage** des routes, l'auth, la pose du plan et la saisie d'une rencontre — la logique (moteur de
poule, placement en blocs, classement de phase) est couverte par `test_domain_poule`,
`test_domain_placement_poules`, `test_domain_classement_de_poules` et `test_service_poules`.

Écrit **après** l'implémentation (règle 9 : API et câblage, il n'y a pas d'oracle en jeu).

⚠️ Ce fichier couvre aussi le **branchement du composition root**, qui n'a pas d'autre garde : le
port `LecteurClassementPoules` est câblé après construction, donc son oubli ne casserait aucune
compilation — seulement, en salle, un prélèvement visant des poules qui redeviendrait inerte.
"""

from __future__ import annotations

import datetime
import json
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
from domain.poule import ReglageDePoules
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
from tests.test_placement_api import _appliquer_gabarit

_DATE = datetime.date(2026, 3, 14)


class Scenario:
    """Six archers classés, une salle de deux cibles, une phase de poules de 3."""

    def __init__(self, app: FastAPI, *, effectif: int = 6, taille: int = 3) -> None:
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
            # Scores strictement décroissants : le rang scratch est prévisible, donc la composition
            # au serpent l'est aussi (le 1ᵉʳ en poule 1, le 2ᵉ en poule 2, …).
            valeur = str(max(1, 10 - rang))
            series.enregistrer(
                Serie(
                    tournoi_id=self.tournoi_id,
                    archer_id=archer.id,
                    volees=(
                        Volee(
                            numero=1,
                            valeurs=(ZoneScore(valeur),) * 3,
                            validee_par="Scoreur",
                        ),
                    ),
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
                type=TypePhase.POULES,
                poules=ReglageDePoules(taille_visee=taille),
            ),
        )
        assert phase.id is not None
        self.phase_id = phase.id


@pytest.fixture
def app_poules(tmp_path: Path) -> Iterator[FastAPI]:
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


def test_la_repartition_se_lit_sans_salle_ni_plan(app_poules: FastAPI) -> None:
    """CA — « la répartition obtenue est montrée avant d'être validée ».

    Aucun gabarit appliqué, aucun plan posé : l'atelier doit malgré tout pouvoir afficher ce que le
    réglage produit, sinon l'organisateur ne pourrait pas régler ses poules avant d'avoir fait sa
    salle.
    """
    with TestClient(app_poules) as client:
        scn = Scenario(app_poules)

        reponse = client.get(f"/api/v1/poules/repartition/{scn.tournoi_id}/{scn.phase_id}")

    assert reponse.status_code == 200, reponse.text
    assert reponse.json() == {
        "effectif": 6,
        "taille_visee": 3,
        "nb_poules": 2,
        "tailles": [3, 3],
    }


def test_letat_expose_les_groupes_leurs_rencontres_et_leur_classement(app_poules: FastAPI) -> None:
    """La photo complète, telle que l'écran de salle la consomme.

    Deux poules de 3 → trois rencontres par groupe (round-robin complet), soit six rencontres
    numérotées de 1 à 6 sur toute la phase.
    """
    with TestClient(app_poules) as client:
        scn = Scenario(app_poules)

        reponse = client.get(f"/api/v1/poules/etat/{scn.tournoi_id}/{scn.phase_id}")

    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["phase_id"] == scn.phase_id
    assert [poule["numero"] for poule in corps["poules"]] == [1, 2]
    assert [len(poule["rencontres"]) for poule in corps["poules"]] == [3, 3]
    numeros = [r["numero"] for poule in corps["poules"] for r in poule["rencontres"]]
    assert numeros == [1, 2, 3, 4, 5, 6]
    # Plan non posé : les couloirs ne s'inventent pas, et le conflit est **rapporté**.
    assert corps["poules"][0]["bloc"] is None
    assert [c["raison"] for c in corps["conflits"]] == ["non_posee", "non_posee"]


def test_la_pose_du_plan_donne_un_bloc_de_couloirs_contigus_a_chaque_poule(
    app_poules: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA — « une poule occupe un bloc de couloirs contigus », et la salle se remplit sans trou.

    Une poule de 3 n'occupe que **deux** couloirs (le cercle ne fait tirer qu'une rencontre par
    tour, le troisième membre se repose) : les deux poules tiennent donc sur une seule cible de 4.
    """
    with TestClient(app_poules) as client:
        scn = Scenario(app_poules)
        connecter_admin(client)
        _appliquer_gabarit(client, scn.tournoi_id, nb_cibles=2)

        reponse = client.post(f"/api/v1/poules/plan/{scn.tournoi_id}/{scn.phase_id}/regenerer")

    assert reponse.status_code == 200, reponse.text
    poules = reponse.json()["poules"]
    assert [poule["bloc"] for poule in poules] == [[[1, "A"], [1, "B"]], [[1, "C"], [1, "D"]]]
    assert reponse.json()["conflits"] == []


def test_la_pose_du_plan_est_refusee_a_un_client_non_admin(app_poules: FastAPI) -> None:
    """Poser un plan est un geste d'organisateur : sans jeton admin, 401."""
    with TestClient(app_poules) as client:
        scn = Scenario(app_poules)

        reponse = client.post(f"/api/v1/poules/plan/{scn.tournoi_id}/{scn.phase_id}/regenerer")

    assert reponse.status_code == 401, reponse.text


def test_une_rencontre_se_saisit_et_se_valide_comme_un_duel_ordinaire(
    app_poules: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA — « les rencontres se saisissent comme des duels ordinaires » (ADR-0083 §7).

    Le corps est celui du pavé d'E04US013, la réponse porte le **même** DTO `duel`, et la rencontre
    validée entre au classement de sa poule — c'est ce qui ferme la chaîne saisie → classement.
    """
    with TestClient(app_poules) as client:
        scn = Scenario(app_poules)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)
        corps = {"tournoi_id": scn.tournoi_id, "phase_id": scn.phase_id, "numero": 1}

        for manche in (1, 2, 3):
            saisie = client.post(
                "/api/v1/poules/manches",
                json={
                    **corps,
                    "manche": manche,
                    "valeurs_haut": ["10", "10", "10"],
                    "valeurs_bas": ["8", "8", "8"],
                },
                headers=entetes,
            )
            assert saisie.status_code == 200, saisie.text

        validation = client.post("/api/v1/poules/validations", json=corps, headers=entetes)
        assert validation.status_code == 200, validation.text
        assert validation.json()["duel"]["validee_par"] == "ROUX"

        etat = client.get(f"/api/v1/poules/etat/{scn.tournoi_id}/{scn.phase_id}").json()

    classement = etat["poules"][0]["classement"]
    # Le vainqueur de la rencontre 1 a marqué ses points de match ; le classement de poule bouge.
    assert classement[0]["points_match"] == 3
    assert classement[0]["ex_aequo"] is False


def test_une_rencontre_inconnue_est_un_404(
    app_poules: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`RencontreIntrouvable` désigne une ressource absente, pas un conflit d'état : 404.

    Le service la levait déjà ; c'est le mapping HTTP qui la traitait en 409 par défaut, à rebours
    de sa propre docstring. Corrigé en même temps que l'exposition (`api/erreurs.py`).
    """
    with TestClient(app_poules) as client:
        scn = Scenario(app_poules)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)

        reponse = client.post(
            "/api/v1/poules/validations",
            json={"tournoi_id": scn.tournoi_id, "phase_id": scn.phase_id, "numero": 99},
            headers=entetes,
        )

    assert reponse.status_code == 404, reponse.text
    assert reponse.json()["code"] == "rencontre_introuvable"


def test_une_phase_qui_nest_pas_des_poules_est_un_409(
    app_poules: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Demander l'état de poules d'une qualification est un conflit d'état, pas une absence."""
    with TestClient(app_poules) as client:
        scn = Scenario(app_poules)

        reponse = client.get(f"/api/v1/poules/etat/{scn.tournoi_id}/{scn.qualif_id}")

    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["code"] == "phase_pas_des_poules"


def test_un_reglage_de_poules_se_compose_et_se_relit_par_lapi(
    app_poules: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA — « choisir le type poules ouvre une fiche de réglages » : le champ traverse la frontière.

    Sans ce câblage, l'atelier n'a nulle part où poser la taille de poule : le type était
    sélectionnable et son réglage n'allait nulle part (`DETTE-028`).
    """
    with TestClient(app_poules) as client:
        scn = Scenario(app_poules)
        connecter_admin(client)

        ajout = client.post(
            f"/api/v1/tournois/{scn.tournoi_id}/phases",
            json={
                "type": "poules",
                "sources": [],
                "poules": {
                    "taille_visee": 4,
                    "bareme": {"victoire": 2, "nul": 1, "defaite": 0},
                    "nb_qualifies": 2,
                    "departage_inter_poules": True,
                },
            },
        )
        assert ajout.status_code == 201, ajout.text

        relu = client.get(f"/api/v1/tournois/{scn.tournoi_id}/phases")

    assert relu.status_code == 200, relu.text
    etape = next(e for e in relu.json() if e["id"] == ajout.json()["id"])
    assert etape["poules"] == {
        "taille_visee": 4,
        "bareme": {"victoire": 2, "nul": 1, "defaite": 0},
        "nb_qualifies": 2,
        "rencontres_par_archer": None,
        "departage_inter_poules": True,
    }


def test_un_reglage_de_poules_sur_un_autre_type_est_refuse(
    app_poules: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`ReglageDePoulesInvalide` → 422 : un réglage que rien ne lira est pire qu'absent.

    Contrairement à `profondeur` — dont l'incompatibilité de type n'est refusée qu'à l'application
    du format —, `Phase.__post_init__` refuse ici tout de suite, parce qu'une phase de tournoi est
    déjà une phase réelle, pas un brouillon de bibliothèque.
    """
    with TestClient(app_poules) as client:
        scn = Scenario(app_poules)
        connecter_admin(client)

        reponse = client.post(
            f"/api/v1/tournois/{scn.tournoi_id}/phases",
            json={
                "type": "elimination_directe",
                "sources": [],
                "poules": {"taille_visee": 4},
            },
        )

    assert reponse.status_code == 422, reponse.text
    assert reponse.json()["code"] == "reglage_de_poules_invalide"


def _jouer_toute_la_phase(
    client: TestClient, scn: Scenario, entetes: dict[str, str]
) -> list[list[int]]:
    """Fait tirer **toutes** les rencontres, le mieux classé l'emportant à chaque fois.

    C'est ce qui rend le classement de poule sans ex æquo, donc les blocs de rang du classement de
    phase lisibles. On lit l'état pour savoir qui est de quel côté : l'orientation des rencontres
    vient de la méthode du cercle, pas du rang, donc faire gagner « le haut » produirait selon les
    cas un cycle à trois où chacun gagne une fois — un ex æquo, et un test au verdict variable.

    Rend, poule par poule, les archers dans l'ordre du classement obtenu.
    """
    # `/saisie` et non `/etat` : c'est la route **scoreur** qui porte le duel entier. `/etat` est la
    # consultation, à contenu restreint (correctif de revue — l'anonyme n'a à voir ni les flèches ni
    # le nom du validateur).
    etat = client.get(
        f"/api/v1/poules/saisie/{scn.tournoi_id}/{scn.phase_id}", headers=entetes
    ).json()
    for poule in etat["poules"]:
        for rencontre in poule["rencontres"]:
            duel = rencontre["duel"]
            haut_gagne = duel["haut"]["archer_id"] < duel["bas"]["archer_id"]
            corps = {
                "tournoi_id": scn.tournoi_id,
                "phase_id": scn.phase_id,
                "numero": rencontre["numero"],
            }
            for manche in range(1, duel["nb_manches"] + 1):
                saisie = client.post(
                    "/api/v1/poules/manches",
                    json={
                        **corps,
                        "manche": manche,
                        "valeurs_haut": ["10", "10", "10"] if haut_gagne else ["8", "8", "8"],
                        "valeurs_bas": ["8", "8", "8"] if haut_gagne else ["10", "10", "10"],
                    },
                    headers=entetes,
                )
                assert saisie.status_code == 200, saisie.text
                # En sets, le duel est **tranché avant** d'avoir joué toutes ses manches : insister
                # rendrait `422 duel_deja_tranche`. On s'arrête où le pavé s'arrête.
                if saisie.json()["duel"]["resultat"]["termine"]:
                    break
            validation = client.post("/api/v1/poules/validations", json=corps, headers=entetes)
            assert validation.status_code == 200, validation.text
    final = client.get(f"/api/v1/poules/etat/{scn.tournoi_id}/{scn.phase_id}").json()
    return [[ligne["archer_id"] for ligne in p["classement"]] for p in final["poules"]]


def test_un_tableau_aval_est_ensemence_par_ce_que_les_poules_ont_qualifie(
    app_poules: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA — « la phase avale consomme les qualifiés », de bout en bout et par HTTP.

    C'est le seul test qui éprouve le **branchement tardif** du composition root : le port
    `LecteurClassementPoules` est câblé après construction, donc son oubli ne casserait aucune
    compilation. Sans lui, le tableau serait ensemencé avec les **six** archers en lice — une
    population bien formée, plausible et fausse, exactement le défaut d'avant E05US024.

    « Les rangs 1 à 2 » sur deux poules prend le **bloc entier** des vainqueurs : ADR-0081 l'honore
    parce que la fenêtre le contient, ex æquo ou non.
    """
    with TestClient(app_poules) as client:
        scn = Scenario(app_poules)
        # `_scoreur` authentifie déjà le client en admin (en place) : le rappeler ferait
        # `409 acces_deja_configure`. On l'ouvre donc en premier, et les écritures admin suivent.
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)
        ajout = client.post(
            f"/api/v1/tournois/{scn.tournoi_id}/phases",
            json={
                "type": "elimination_directe",
                "sources": [{"ordre_source": 2, "nature": "rangs", "rang_debut": 1, "rang_fin": 2}],
            },
        )
        assert ajout.status_code == 201, ajout.text
        classements = _jouer_toute_la_phase(client, scn, entetes)

        phases = client.get(f"/api/v1/departs/{scn.depart_id}/phases").json()
        tableau_id = next(p["id"] for p in phases if p["ordre"] == 3)
        tableau = client.get(
            f"/api/v1/duels/tableau/{scn.tournoi_id}/{tableau_id}", headers=entetes
        )

    assert tableau.status_code == 200, tableau.text
    corps = tableau.json()
    assert corps["effectif"] == 2, "sans le port, les six archers en lice seraient entrés"
    finale = corps["duels"][-1]
    vainqueurs = {classement[0] for classement in classements}
    assert {finale["haut"]["archer_id"], finale["bas"]["archer_id"]} == vainqueurs


def test_un_prelevement_dans_des_poules_non_jouees_est_mis_en_attente(
    app_poules: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA — « un prélèvement qui coupe un bloc de poules est refusé ».

    Avant le premier tir, **tout** est un seul bloc.

    Aucune rencontre tirée : les trois membres de chaque poule sont à zéro partout, donc ex æquo, et
    l'égalité interne soude les blocs de rang les uns aux autres. Dire qui sont « les rangs 1 à 2 »
    reviendrait alors à qualifier sur l'ordre de composition. Le refus est **typé et annoncé**, pas
    un tableau plausible et faux (ADR-0081).
    """
    with TestClient(app_poules) as client:
        scn = Scenario(app_poules)
        # `_scoreur` authentifie déjà le client en admin (en place) : le rappeler ferait
        # `409 acces_deja_configure`. On l'ouvre donc en premier, et les écritures admin suivent.
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)
        ajout = client.post(
            f"/api/v1/tournois/{scn.tournoi_id}/phases",
            json={
                "type": "elimination_directe",
                "sources": [{"ordre_source": 2, "nature": "rangs", "rang_debut": 1, "rang_fin": 2}],
            },
        )
        assert ajout.status_code == 201, ajout.text
        phases = client.get(f"/api/v1/departs/{scn.depart_id}/phases").json()
        tableau_id = next(p["id"] for p in phases if p["ordre"] == 3)

        reponse = client.get(
            f"/api/v1/duels/tableau/{scn.tournoi_id}/{tableau_id}", headers=entetes
        )

    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["code"] == "prelevement_en_attente"


# --------------------------------------------------------------------------------------------
# Sécurité — la scission `/etat` (public restreint) / `/saisie` (scoreur)
# --------------------------------------------------------------------------------------------
#
# ⚠️ Ces trois tests sont la **porte** du correctif de sécurité, et ils manquaient : la première
# version servait `DuelReponse` en entier — nom du bénévole validateur, chaque flèche, barrage,
# zones et barème — sur une route **anonyme**. Sans eux, remettre `response_model=EtatPoulesReponse`
# sur `/etat` repasserait toute la suite au vert, et l'argument « un DTO distinct, pas un `exclude`
# »
# n'aurait aucune porte. C'est la décision d'`api/v1/tableaux.py`, qui a les siens.


def test_la_lecture_ouverte_ne_publie_pas_le_detail_de_saisie(
    app_poules: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`/etat` est ouvert, donc il ne porte **ni** flèches, **ni** identité de bénévole.

    On tire et on valide **d'abord** : un état vide ne prouverait rien, puisque les champs à ne pas
    fuir n'existeraient de toute façon pas encore.
    """
    with TestClient(app_poules) as client:
        scn = Scenario(app_poules)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)
        _jouer_toute_la_phase(client, scn, entetes)

        reponse = client.get(f"/api/v1/poules/etat/{scn.tournoi_id}/{scn.phase_id}")

    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    rencontres = [r for poule in corps["poules"] for r in poule["rencontres"]]
    assert rencontres, "le décor doit avoir produit des rencontres, sinon le test ne prouve rien"
    assert all("duel" not in rencontre for rencontre in rencontres)
    brut = json.dumps(corps)
    for interdit in ("validee_par", "manches", "zones", "bareme", "ROUX"):
        assert interdit not in brut, f"« {interdit} » n'a rien à faire dans une lecture ouverte"
    # …et ce que le public **doit** lire y est bien : l'avancement, pas le détail.
    assert all("validee" in rencontre for rencontre in rencontres)
    assert any(rencontre["termine"] for rencontre in rencontres)


def test_la_lecture_de_saisie_exige_une_session_scoreur(app_poules: FastAPI) -> None:
    """`/saisie` porte le duel entier : sans jeton scoreur, 401 — comme `duels/tableau`."""
    with TestClient(app_poules) as client:
        scn = Scenario(app_poules)

        reponse = client.get(f"/api/v1/poules/saisie/{scn.tournoi_id}/{scn.phase_id}")

    assert reponse.status_code == 401, reponse.text


def test_la_lecture_de_saisie_est_bornee_au_tournoi_du_scoreur(
    app_poules: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un scoreur n'officie que dans **son** tournoi : ailleurs, 403 `scoreur_hors_tournoi`.

    Le jeton seul ne suffit pas — sans cette borne, un scoreur du tournoi du matin lirait le détail
    de saisie de celui de l'après-midi. C'est la garde que porte déjà chaque écriture de ce routeur.
    """
    with TestClient(app_poules) as client:
        scn = Scenario(app_poules)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)
        autre = Scenario(app_poules)

        reponse = client.get(
            f"/api/v1/poules/saisie/{autre.tournoi_id}/{autre.phase_id}", headers=entetes
        )

    assert reponse.status_code == 403, reponse.text
    assert reponse.json()["code"] == "scoreur_hors_tournoi"


def test_le_drapeau_de_desynchronisation_traverse_les_deux_vues(
    app_poules: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`desynchronisee` est servi **par les deux routes**, et il est faux sur une phase saine.

    C'est le câblage qui manquait : le drapeau existait au service et n'était asserté sur
    aucune des deux surfaces. La vue publique le porte aussi — un écran de salle qui
    afficherait « à tirer » sur une rencontre bloquée ferait attendre des archers pour rien.
    """
    with TestClient(app_poules) as client:
        scn = Scenario(app_poules)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)

        publique = client.get(f"/api/v1/poules/etat/{scn.tournoi_id}/{scn.phase_id}").json()
        saisie = client.get(
            f"/api/v1/poules/saisie/{scn.tournoi_id}/{scn.phase_id}", headers=entetes
        ).json()

    for corps in (publique, saisie):
        rencontres = [r for poule in corps["poules"] for r in poule["rencontres"]]
        assert rencontres, "le décor doit produire des rencontres"
        assert all(
            r["desynchronisee"] is False for r in rencontres
        ), "aucune rencontre n'a encore été tirée : rien ne peut être désynchronisé"
