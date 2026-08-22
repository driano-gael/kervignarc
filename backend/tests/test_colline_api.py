"""E05US027 — la colline par HTTP, de bout en bout.

Écrit **après** l'implémentation (règle 9 : API et câblage, il n'y a pas d'oracle en jeu).

⚠️ Ce fichier couvre aussi les **quatre branchements du composition root**, qui n'ont pas d'autre
garde : les ports `LecteurClassementDePhase`, `LecteurRencontresARouter`, `LecteurAvancementDePhase`
et le déclencheur d'arrêts sont câblés **après** construction, donc leur oubli ne casserait aucune
compilation. Il ne se verrait qu'en salle — un prélèvement inerte, un panneau de routage muet, une
phase qui n'annonce jamais sa manche, ou une pause programmée qui ne tombe jamais.
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
from domain.colline import ConfigurationColline
from domain.depart import Depart
from domain.inscription import Inscription
from domain.phase import Phase, SourcePhase, StatutPhase, TypePhase
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

_DATE = datetime.date(2026, 3, 1)


class Scenario:
    """Un tournoi, un créneau, `effectif` archers classés, une phase de **colline**."""

    def __init__(
        self,
        app: FastAPI,
        *,
        effectif: int = 4,
        nb_manches: int = 3,
        portee_de_defi: int = 1,
        statut: StatutPhase = StatutPhase.A_VENIR,
    ) -> None:
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
            # Scores strictement décroissants : le rang scratch est prévisible, donc **l'ordre
            # initial de la colline** l'est aussi — c'est le classement amont (référentiel §10.1).
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
                type=TypePhase.COLLINE,
                colline=ConfigurationColline(nb_manches=nb_manches, portee_de_defi=portee_de_defi),
                statut=statut,
            ),
        )
        assert phase.id is not None
        self.phase_id = phase.id


@pytest.fixture
def app_colline(tmp_path: Path) -> Iterator[FastAPI]:
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
    """Fait gagner un camp d'un défi par HTTP, puis le valide.

    `le_bas=True` fait gagner le **challenger** — celui qui monte. C'est le cas discriminant : il
    change l'ordre de la colline, donc l'appariement de la manche suivante.
    """
    fort = ["10", "10", "10"]
    faible = ["6", "6", "6"]
    for manche in (1, 2, 3):
        reponse = client.post(
            "/api/v1/colline/manches",
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
        "/api/v1/colline/validations",
        json={"tournoi_id": scn.tournoi_id, "phase_id": scn.phase_id, "numero": numero},
        headers=entetes,
    )
    assert reponse.status_code == 200, reponse.text


def test_letat_expose_la_premiere_manche_et_la_borne_de_portee(app_colline: FastAPI) -> None:
    """La photo telle que l'écran la consomme : manches appariées, borne de portée, colline.

    À 4 archers, la borne vaut 3 (un défi ne peut pas porter au-delà du dernier rang) : c'est
    l'équivalent du « maximum que l'effectif autorise » du suisse, rendu par le service et non
    recalculé côté écran.
    """
    with TestClient(app_colline) as client:
        scn = Scenario(app_colline)

        reponse = client.get(f"/api/v1/colline/etat/{scn.tournoi_id}/{scn.phase_id}")

    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["phase_id"] == scn.phase_id
    assert corps["effectif"] == 4
    assert corps["nb_manches"] == 3
    assert corps["portee_de_defi"] == 1
    assert corps["portee_maximale"] == 3
    assert len(corps["manches"]) == 1
    assert corps["manches"][0]["close"] is False
    assert [d["numero"] for d in corps["manches"][0]["defis"]] == [1, 2]
    # Manche 1 à portée 1 : tout le monde tire, personne ne se repose.
    assert corps["manches"][0]["au_repos"] == []
    # Le classement **est** la colline, dans son ordre initial.
    assert [r["archer_id"] for r in corps["classement"]] == scn.archers


def test_la_manche_suivante_apparait_quand_la_precedente_est_close(
    app_colline: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """**Le CA de l'US, par HTTP.** Il n'y a pas de geste « manche suivante » : elle se déduit.

    Les deux challengers gagnent la manche 1, donc la colline `1 2 3 4` devient `2 1 4 3`. La
    manche 2 décale d'un cran et n'apparie que les positions 2 et 3 — soit **l'archer 1 contre
    l'archer 4**, couple qu'aucune lecture du classement amont ne produirait.
    """
    with TestClient(app_colline) as client:
        scn = Scenario(app_colline)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)

        _gagner(client, entetes, scn, 1, le_bas=True)
        # Un seul défi validé : la manche reste ouverte, la suivante n'existe pas.
        corps = client.get(f"/api/v1/colline/etat/{scn.tournoi_id}/{scn.phase_id}").json()
        assert len(corps["manches"]) == 1
        assert corps["manches"][0]["close"] is False

        _gagner(client, entetes, scn, 2, le_bas=True)
        corps = client.get(f"/api/v1/colline/etat/{scn.tournoi_id}/{scn.phase_id}").json()

    assert len(corps["manches"]) == 2
    assert corps["manches"][0]["close"] is True
    # Le gagnant monte : la colline s'est inversée deux par deux.
    assert [r["archer_id"] for r in corps["classement"]] == [
        scn.archers[1],
        scn.archers[0],
        scn.archers[3],
        scn.archers[2],
    ]
    manche2 = corps["manches"][1]
    assert [(d["haut"]["archer_id"], d["bas"]["archer_id"]) for d in manche2["defis"]] == [
        (scn.archers[0], scn.archers[3])
    ]
    # Les extrémités se reposent, et l'état le **dit** plutôt que de les laisser disparaître.
    assert [d["archer_id"] for d in manche2["au_repos"]] == [scn.archers[1], scn.archers[2]]


def test_une_phase_avale_preleve_dans_la_colline(
    app_colline: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """**Le branchement `LecteurClassementDePhase` du composition root**, sans autre garde.

    Le port est câblé après construction : son oubli ne casserait aucune compilation. Sans lui, un
    prélèvement visant une colline resterait **inerte** et la phase avale recevrait *tous* les
    archers en lice — une population bien formée, plausible et fausse.
    """
    with TestClient(app_colline) as client:
        scn = Scenario(app_colline, nb_manches=1)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)
        db: Database = app_colline.state.database
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
    # Les deux **premiers de la colline** après la manche, et non les deux premiers de la
    # qualification.
    assert tableaux[aval.id]["effectif"] == 2


def test_la_pose_du_plan_donne_ses_couloirs_a_chaque_defi(
    app_colline: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """3ᵉ question du contrat (ADR-0083 §3), par HTTP — un seul bloc pour toute la phase.

    Une manche apparie sur **tout le plateau** : il n'y a pas de groupes à séparer, donc pas un bloc
    par groupe comme en poules. À 4 archers, deux défis côte à côte sur les quatre premiers
    couloirs.
    """
    with TestClient(app_colline) as client:
        scn = Scenario(app_colline)
        connecter_admin(client)
        _appliquer_gabarit(client, scn.tournoi_id, nb_cibles=4)

        reponse = client.post(f"/api/v1/colline/plan/{scn.tournoi_id}/{scn.phase_id}")

    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert [d["couloirs"] for d in corps["manches"][0]["defis"]] == [
        [[1, "A"], [1, "B"]],
        [[1, "C"], [1, "D"]],
    ]
    assert corps["conflits"] == []


def test_sans_plan_pose_les_couloirs_sont_nuls_et_le_manque_est_dit(
    app_colline: FastAPI,
) -> None:
    """Un plan non posé se **voit** non posé : l'écran doit dire « générez-le », pas inventer.

    Le manque est rapporté **en lecture** et pas seulement après une pose — c'est le correctif de
    revue d'E05US030, repris ici d'emblée : sans lui, le message de l'écran scoreur serait une
    branche morte et le scoreur verrait ses défis sans aucune cible ni explication.
    """
    with TestClient(app_colline) as client:
        scn = Scenario(app_colline)

        corps = client.get(f"/api/v1/colline/etat/{scn.tournoi_id}/{scn.phase_id}").json()

    assert all(d["couloirs"] is None for d in corps["manches"][0]["defis"])
    assert corps["conflits"] != []


def test_la_pose_du_plan_est_reservee_a_l_admin(app_colline: FastAPI) -> None:
    """Poser un plan est un geste d'organisateur, pas de scoreur (E10US001)."""
    with TestClient(app_colline) as client:
        scn = Scenario(app_colline)

        reponse = client.post(f"/api/v1/colline/plan/{scn.tournoi_id}/{scn.phase_id}")

    assert reponse.status_code in (401, 403), reponse.text


def test_le_panneau_de_routage_annonce_le_defi_et_sa_cible(
    app_colline: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """**Le branchement `LecteurRencontresARouter`** — service, route et composition root d'un coup.

    `route_l_archer` est déclaré `True` au registre de contrat ; une capacité déclarée dont le
    porteur nommé ne porte rien est le mode de défaillance d'ADR-0017.
    """
    with TestClient(app_colline) as client:
        scn = Scenario(app_colline)
        connecter_admin(client)
        _appliquer_gabarit(client, scn.tournoi_id, nb_cibles=4)
        client.post(f"/api/v1/colline/plan/{scn.tournoi_id}/{scn.phase_id}")

        reponse = client.get(
            f"/api/v1/routage/departs/{scn.depart_id}",
            params={"archer_id": scn.archers, "phase_id": scn.phase_id},
        )

    assert reponse.status_code == 200, reponse.text
    lignes = {ligne["archer_id"]: ligne for ligne in reponse.json()["archers"]}
    assert all(ligne["issue"] == "prochain_duel" for ligne in lignes.values())
    premier = lignes[scn.archers[0]]["prochain"]
    assert premier["libelle"] == "Manche 1"
    # La cible **est** donnée, à la différence du Big Shoot Off (`DETTE-059`) : le plan est posé.
    assert (premier["cible"], premier["position"]) == (1, "A")
    assert premier["manque"] is None


def test_un_archer_au_repos_est_dit_en_attente_et_non_termine(
    app_colline: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """⚠️ **Le régime ordinaire de la colline**, pas son cas limite (ADR-0087).

    À portée 1, les deux extrémités se reposent une manche sur deux, **quel que soit** l'effectif —
    là où un suisse ne met un archer en attente qu'à effectif impair. Sans `EN_ATTENTE`, la moitié
    du plateau passerait pour « terminée » sur le panneau public à chaque manche.
    """
    with TestClient(app_colline) as client:
        scn = Scenario(app_colline)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)
        _appliquer_gabarit(client, scn.tournoi_id, nb_cibles=4)
        client.post(f"/api/v1/colline/plan/{scn.tournoi_id}/{scn.phase_id}")

        _gagner(client, entetes, scn, 1, le_bas=True)
        _gagner(client, entetes, scn, 2, le_bas=True)
        reponse = client.get(
            f"/api/v1/routage/departs/{scn.depart_id}",
            params={"archer_id": scn.archers, "phase_id": scn.phase_id},
        )

    assert reponse.status_code == 200, reponse.text
    lignes = {ligne["archer_id"]: ligne["issue"] for ligne in reponse.json()["archers"]}
    # La colline est `2 1 4 3` : la manche 2 oppose les positions 2 et 3 (archers 1 et 4).
    assert lignes[scn.archers[0]] == "prochain_duel"
    assert lignes[scn.archers[3]] == "prochain_duel"
    # Les extrémités attendent — elles ne sont **pas** terminées, elles rejouent la manche suivante.
    assert lignes[scn.archers[1]] == "en_attente"
    assert lignes[scn.archers[2]] == "en_attente"


def test_l_ecran_de_salle_lit_les_affectations_d_une_colline(
    app_colline: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La bifurcation jumelle, sur `affectations` — son absence a été un bloquant sur le suisse.

    Faire entrer un type dans `TYPES_ROUTES` le rend cible **implicite** de `_phase_de_tableau` :
    sans bifurcation, cette route tombe dans `_grille` et rend **409 sur une route publique non
    authentifiée**, éteignant l'écran de salle pendant la phase même qu'il sert.
    """
    with TestClient(app_colline) as client:
        scn = Scenario(app_colline)
        connecter_admin(client)
        _appliquer_gabarit(client, scn.tournoi_id, nb_cibles=4)
        client.post(f"/api/v1/colline/plan/{scn.tournoi_id}/{scn.phase_id}")

        reponse = client.get(f"/api/v1/routage/departs/{scn.depart_id}/affectations")

    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["phase_id"] == scn.phase_id


def test_le_suivi_du_deroule_annonce_la_manche_courante(
    app_colline: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """**Le branchement `LecteurAvancementDePhase`** (ADR-0090 §5) — « Manche 2 sur 3 ».

    ⚠️ Il fait plus qu'afficher : `TYPES_ARRETABLES` dérive d'`avancement_lisible` (ADR-0093), donc
    c'est lui qui rend la colline réellement **arrêtable**. Sans cette ligne au composition root,
    une pause programmée serait acceptée à l'atelier et définitivement muette le jour J.

    ⚠️ **La phase doit être démarrée**, et ce n'est pas un artifice de décor : `_avancement_lu`
    n'interroge le lecteur que sur un statut de `STATUTS_DEMARRES`. C'est voulu — un *compte* de
    tours est structurel, mais un *tour courant* est la conséquence d'un geste de l'organisateur, et
    une phase à venir n'en a aucun.
    """
    with TestClient(app_colline) as client:
        scn = Scenario(app_colline, statut=StatutPhase.EN_COURS)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)

        _gagner(client, entetes, scn, 1, le_bas=True)
        _gagner(client, entetes, scn, 2, le_bas=True)
        reponse = client.get(f"/api/v1/departs/{scn.depart_id}/suivi-deroule")

    assert reponse.status_code == 200, reponse.text
    # La colline est la 2ᵉ étape du déroulé (la qualification est la 1ʳᵉ).
    avancement = {bloc["ordre"]: bloc for bloc in reponse.json()["avancement"]}[2]
    assert avancement["nb_tours"] == 3
    assert avancement["tour_courant"] == 2
    # Le **mot du métier** vient du contrat de phase (`UniteDeTour.RONDE`), pas d'un littéral :
    # c'est ADR-0090 qui sépare l'unité d'avancement générique de son nom à l'écran.
    assert avancement["libelle_tour_courant"] == "Ronde 2"


def test_l_etat_public_ne_sert_pas_le_pave_de_saisie(app_colline: FastAPI) -> None:
    """Restriction de contenu (règle 6) — servie **rédigée** d'emblée.

    Le routeur du suisse a dû faire cette scission **en correctif de revue**, après l'avoir recopiée
    d'`api/v1/poules.py` sans la leçon qu'elle portait : la forme complète expose chaque flèche de
    chaque volée, le barrage, les zones, le barème, et `validee_par` — le **nom du bénévole** qui a
    validé. Rien de cela n'a de raison d'être lu hors de la saisie.
    """
    with TestClient(app_colline) as client:
        scn = Scenario(app_colline)

        reponse = client.get(f"/api/v1/colline/etat/{scn.tournoi_id}/{scn.phase_id}")

    assert reponse.status_code == 200, reponse.text
    defi = reponse.json()["manches"][0]["defis"][0]
    assert "duel" not in defi
    assert set(defi) == {
        "numero",
        "manche",
        "position_haute",
        "position_basse",
        "couloirs",
        "haut",
        "bas",
        "points_haut",
        "points_bas",
        "vainqueur",
        "termine",
        "validee",
        "desynchronisee",
    }


def test_le_pave_de_saisie_reste_accessible_au_scoreur(
    app_colline: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La contrepartie : le scoreur de **ce** tournoi lit bien l'état complet, et lui seul."""
    with TestClient(app_colline) as client:
        scn = Scenario(app_colline)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)

        anonyme = client.get(f"/api/v1/colline/saisie/{scn.tournoi_id}/{scn.phase_id}")
        reponse = client.get(
            f"/api/v1/colline/saisie/{scn.tournoi_id}/{scn.phase_id}", headers=entetes
        )

    assert anonyme.status_code in (401, 403), anonyme.text
    assert reponse.status_code == 200, reponse.text
    assert "duel" in reponse.json()["manches"][0]["defis"][0]


def test_un_defi_dune_manche_non_appariee_est_introuvable(
    app_colline: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un défi de la manche 2 n'existe pas tant que la manche 1 n'est pas close — 404, pas 500.

    C'est exact et non défensif : les **positions** qu'il opposerait ne sont pas encore fixées.
    """
    with TestClient(app_colline) as client:
        scn = Scenario(app_colline)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)

        reponse = client.post(
            "/api/v1/colline/validations",
            json={"tournoi_id": scn.tournoi_id, "phase_id": scn.phase_id, "numero": 3},
            headers=entetes,
        )

    assert reponse.status_code == 404, reponse.text


def test_une_saisie_hors_tournoi_est_refusee(
    app_colline: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un scoreur n'officie que dans **son** tournoi (`DETTE-065`, 7ᵉ copie du garde)."""
    with TestClient(app_colline) as client:
        scn = Scenario(app_colline)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)

        reponse = client.post(
            "/api/v1/colline/validations",
            json={"tournoi_id": scn.tournoi_id + 99, "phase_id": scn.phase_id, "numero": 1},
            headers=entetes,
        )

    assert reponse.status_code == 403, reponse.text


def test_le_panneau_degrade_au_lieu_de_tomber_sur_un_reglage_hors_borne(
    app_colline: FastAPI,
) -> None:
    """Une portée supérieure à ce que l'effectif permet ne fait tomber **aucune** route publique.

    Le domaine refuse une portée ≥ à l'effectif (« ce n'est plus ni un King of the Hill ni un
    Ladder »), mais `EtapeDeroule` ne le vérifie qu'à effectif **déclaré**. Le service borne donc à
    la lecture au lieu de lever — sans quoi le palmarès public, son PDF et le panneau de routage
    sortiraient en 422 sur une phase que l'atelier a acceptée. C'est le défaut qu'E05US026 a dû
    corriger en revue, reproduit par trois axes.
    """
    with TestClient(app_colline) as client:
        scn = Scenario(app_colline, effectif=3, nb_manches=2, portee_de_defi=5)

        etat = client.get(f"/api/v1/colline/etat/{scn.tournoi_id}/{scn.phase_id}")
        routage = client.get(f"/api/v1/routage/departs/{scn.depart_id}/affectations")

    assert etat.status_code == 200, etat.text
    assert routage.status_code == 200, routage.text
    corps = etat.json()
    # Les deux nombres coexistent : l'atelier **montre** l'écart au lieu de le subir.
    assert corps["portee_de_defi"] == 5
    assert corps["portee_maximale"] == 2


def test_une_colline_non_reglee_refuse_de_se_lire(app_colline: FastAPI) -> None:
    """Une phase composée mais pas encore réglée est un état licite (brouillon d'ADR-0063) → 409."""
    with TestClient(app_colline) as client:
        scn = Scenario(app_colline)
        db: Database = app_colline.state.database
        nue = poser_phase_sql(
            db.session_factory,
            Phase(depart_id=scn.depart_id, ordre=4, type=TypePhase.COLLINE),
        )
        assert nue.id is not None

        reponse = client.get(f"/api/v1/colline/etat/{scn.tournoi_id}/{nue.id}")

    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["code"] == "phase_pas_reglee"


def test_une_phase_dun_autre_type_est_refusee_par_la_route_colline(app_colline: FastAPI) -> None:
    """Lire une qualification par cette porte est un contresens → 409 nommé, pas un 500."""
    with TestClient(app_colline) as client:
        scn = Scenario(app_colline)

        reponse = client.get(f"/api/v1/colline/etat/{scn.tournoi_id}/{scn.qualif_id}")

    assert reponse.status_code == 409, reponse.text
    assert reponse.json()["code"] == "phase_pas_une_colline"
