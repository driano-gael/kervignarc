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
from tests.test_placement_api import _appliquer_gabarit

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


def test_la_pose_du_plan_donne_ses_couloirs_a_chaque_rencontre(
    app_suisse: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA « le plan de cibles suit », par HTTP — un seul bloc pour toute la phase.

    Une ronde apparie **tout le plateau** : il n'y a pas de groupes à séparer, donc pas un bloc par
    groupe comme en poules. À 4 archers, deux rencontres côte à côte sur les quatre premiers
    couloirs.
    """
    with TestClient(app_suisse) as client:
        scn = Scenario(app_suisse)
        connecter_admin(client)
        _appliquer_gabarit(client, scn.tournoi_id, nb_cibles=4)

        reponse = client.post(f"/api/v1/suisse/plan/{scn.tournoi_id}/{scn.phase_id}")

    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert [r["couloirs"] for r in corps["rondes"][0]["rencontres"]] == [
        [[1, "A"], [1, "B"]],
        [[1, "C"], [1, "D"]],
    ]
    assert corps["conflits"] == []


def test_sans_plan_pose_les_couloirs_sont_nuls(app_suisse: FastAPI) -> None:
    """Un plan non posé se **voit** non posé : l'écran doit dire « générez-le », pas inventer."""
    with TestClient(app_suisse) as client:
        scn = Scenario(app_suisse)

        corps = client.get(f"/api/v1/suisse/etat/{scn.tournoi_id}/{scn.phase_id}").json()

    assert all(r["couloirs"] is None for r in corps["rondes"][0]["rencontres"])


def test_la_pose_du_plan_est_reservee_a_l_admin(app_suisse: FastAPI) -> None:
    """Poser un plan est un geste d'organisateur, pas de scoreur (E10US001)."""
    with TestClient(app_suisse) as client:
        scn = Scenario(app_suisse)

        reponse = client.post(f"/api/v1/suisse/plan/{scn.tournoi_id}/{scn.phase_id}")

    assert reponse.status_code == 401, reponse.text


# --- CA « le palmarès » : décerne si rien ne prélève dedans (arbitrage du 15/08/2026) -------------


def _palmares(client: TestClient, tournoi_id: int) -> dict[int, dict[str, object]]:
    reponse = client.get(f"/api/v1/tournois/{tournoi_id}/palmares")
    assert reponse.status_code == 200, reponse.text
    return {ligne["archer_id"]: ligne for ligne in reponse.json()["lignes"]}


def test_un_suisse_terminal_decerne_ses_rangs(
    app_suisse: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """**Le CA du palmarès.** Rien ne prélève dans cette phase : elle titre.

    C'est le format club décrit par le commanditaire — une cascade dont la dernière phase n'est pas
    un tableau. L'intuition « une phase à rencontres ne titre jamais » est fausse : ici le vainqueur
    du suisse **est** le vainqueur du tournoi, et `decerne` doit le dire.

    ⚠️ **Il faut deux rondes, et c'est instructif.** Après une seule, les deux vainqueurs sont à
    égalité parfaite — mêmes points, même Buchholz, même décompte — donc le classement les déclare
    *ex æquo* et le palmarès rend une **fourchette** 1ᵉʳ-2ᵉ, sans médaille. Être terminale ne suffit
    pas à décerner : encore faut-il avoir tranché (ADR-0081). La 2ᵉ ronde oppose les deux vainqueurs
    et sépare enfin la tête.
    """
    with TestClient(app_suisse) as client:
        scn = Scenario(app_suisse, nb_rondes=2)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)

        _gagner(client, entetes, scn, 1, le_bas=True)
        _gagner(client, entetes, scn, 2, le_bas=True)
        # Ronde 2 : les deux vainqueurs s'affrontent, les deux perdants aussi.
        _gagner(client, entetes, scn, 3, le_bas=True)
        _gagner(client, entetes, scn, 4, le_bas=True)
        lignes = _palmares(client, scn.tournoi_id)

    premier = next(a for a, ligne in lignes.items() if ligne["rang_min"] == 1)
    assert lignes[premier]["rang_max"] == 1
    assert lignes[premier]["decerne"] is True


def test_un_suisse_consomme_classe_sans_titrer(
    app_suisse: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Une phase **prélevée** contribue ses rangs sans médaille — l'autre moitié de la règle.

    Le tableau aval n'a pas encore été joué : personne ne doit porter de médaille, alors même que le
    suisse a fini et que ses rangs sont exacts. Sans le critère structurel, les vainqueurs de la
    ronde recevraient l'or **avant le moindre duel du tableau** — exactement le défaut
    qu'`OriginePalmares` a été créé pour fermer sur les qualifications multiples.

    ⚠️ Les rangs, eux, sont bien versés : c'est le gain de cette règle pour les **non-qualifiés**,
    qui étaient jusqu'ici renvoyés à leur rang de qualification.
    """
    from domain.phase import SourcePhase

    with TestClient(app_suisse) as client:
        scn = Scenario(app_suisse, nb_rondes=1)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)
        db: Database = app_suisse.state.database
        poser_phase_sql(
            db.session_factory,
            Phase(
                depart_id=scn.depart_id,
                ordre=3,
                type=TypePhase.ELIMINATION_DIRECTE,
                sources=(SourcePhase.par_rangs(ordre_source=2, rang_debut=1, rang_fin=2),),
            ),
        )

        _gagner(client, entetes, scn, 1, le_bas=True)
        _gagner(client, entetes, scn, 2, le_bas=True)
        lignes = _palmares(client, scn.tournoi_id)

    assert not any(ligne["decerne"] for ligne in lignes.values())


# --- Correctifs de revue : routage, sécurité et palmarès, de bout en bout ------------------------


def test_le_panneau_de_routage_annonce_la_rencontre_et_sa_cible(
    app_suisse: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """**Bloquant de revue.** `route_l_archer` basculait à `True` sans qu'aucun test ne l'exerce.

    Ce test couvre les trois maillons d'un coup — le service, la route et le **branchement du
    composition root**. C'est le garde-fou que le commentaire de `composition.py` réclame : « une
    capacité déclarée dont le porteur nommé ne porte rien » est le mode de défaillance d'ADR-0017.
    """
    with TestClient(app_suisse) as client:
        scn = Scenario(app_suisse)
        connecter_admin(client)
        _appliquer_gabarit(client, scn.tournoi_id, nb_cibles=4)
        client.post(f"/api/v1/suisse/plan/{scn.tournoi_id}/{scn.phase_id}")

        reponse = client.get(
            f"/api/v1/routage/departs/{scn.depart_id}",
            params={"archer_id": scn.archers, "phase_id": scn.phase_id},
        )

    assert reponse.status_code == 200, reponse.text
    lignes = {ligne["archer_id"]: ligne for ligne in reponse.json()["archers"]}
    assert all(ligne["issue"] == "prochain_duel" for ligne in lignes.values())
    premier = lignes[scn.archers[0]]["prochain"]
    assert premier["libelle"] == "Ronde 1"
    # La cible **est** donnée, à la différence du Big Shoot Off (`DETTE-059`) : le plan est posé.
    assert (premier["cible"], premier["position"]) == (1, "A")
    assert premier["manque"] is None


def test_l_ecran_de_salle_lit_les_affectations_d_une_phase_a_rencontres(
    app_suisse: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """**Bloquant de revue — régression.** `affectations()` n'avait pas reçu la bifurcation.

    Faire entrer le suisse et les poules dans `TYPES_ROUTES` les rend cibles **implicites** de
    `_phase_de_tableau`. Sans bifurcation, cette route tombait dans `_grille` et rendait **409 sur
    une route publique non authentifiée** : le canal n°2 (écran de salle, table d'organisation)
    s'éteignait exactement pendant la phase qu'il sert, et pour tout créneau à poules déjà livré.

    Le test n'envoie **aucun** identifiant — c'est toute la différence avec `routage`, et c'est ce
    qui éprouve que la population vient de la phase et non des rencontres restantes.
    """
    with TestClient(app_suisse) as client:
        scn = Scenario(app_suisse)
        connecter_admin(client)
        _appliquer_gabarit(client, scn.tournoi_id, nb_cibles=4)
        client.post(f"/api/v1/suisse/plan/{scn.tournoi_id}/{scn.phase_id}")

        reponse = client.get(f"/api/v1/routage/departs/{scn.depart_id}/affectations")

    assert reponse.status_code == 200, reponse.text
    assert {ligne["archer_id"] for ligne in reponse.json()["archers"]} == set(scn.archers)


def test_un_archer_dont_la_rencontre_est_validee_n_est_pas_dit_termine(
    app_suisse: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """**Bloquant de revue.** « Terminé » était dit à qui a encore des rondes devant lui.

    Après la seule rencontre 1 validée, ses deux tireurs n'ont plus rien à tirer *pour l'instant* :
    la ronde 2 n'existe pas tant que la ronde 1 n'est pas close. Leur annoncer `termine` les envoie
    ranger leur arc. Le panneau doit dire « pas maintenant ».
    """
    with TestClient(app_suisse) as client:
        scn = Scenario(app_suisse)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)
        _gagner(client, entetes, scn, 1, le_bas=True)

        reponse = client.get(
            f"/api/v1/routage/departs/{scn.depart_id}",
            params={"archer_id": scn.archers, "phase_id": scn.phase_id},
        )

    lignes = {ligne["archer_id"]: ligne for ligne in reponse.json()["archers"]}
    joues = [lignes[scn.archers[0]], lignes[scn.archers[2]]]
    assert all(ligne["issue"] != "termine" for ligne in joues)
    assert all("pas encore appariée" in (ligne["motif"] or "") for ligne in joues)


def test_le_panneau_degrade_au_lieu_de_tomber_sur_un_reglage_hors_borne(
    app_suisse: FastAPI,
) -> None:
    """**Bloquant de revue.** Le réglage par défaut faisait rendre 422 à trois surfaces publiques.

    `nb_rondes=5` à 4 archers dépasse la borne ; `apparier_ronde` levait une **erreur de domaine**
    que ni le routage ni le palmarès n'absorbaient. Les deux docstrings promettaient pourtant de
    dégrader. On borne désormais à la lecture, si bien qu'il n'y a plus rien à absorber ici.
    """
    with TestClient(app_suisse) as client:
        scn = Scenario(app_suisse, nb_rondes=5)

        etat = client.get(f"/api/v1/suisse/etat/{scn.tournoi_id}/{scn.phase_id}")
        routage = client.get(f"/api/v1/routage/departs/{scn.depart_id}/affectations")
        palmares = client.get(f"/api/v1/tournois/{scn.tournoi_id}/palmares")

    assert etat.status_code == 200, etat.text
    assert etat.json()["rondes_maximales"] == 3
    assert routage.status_code == 200, routage.text
    assert palmares.status_code == 200, palmares.text


def test_l_etat_public_ne_sert_pas_le_pave_de_saisie(app_suisse: FastAPI) -> None:
    """**Bloquant de revue — sécurité.** La route ouverte servait le DTO du scoreur.

    Chaque flèche de chaque volée, le barrage, les zones, le barème, et `validee_par` — le **nom du
    bénévole** qui a validé. Rien de cela n'a de raison d'être lu hors de la saisie ;
    `api/v1/poules.py` avait dû faire la même scission en revue d'E05US023, et sa docstring en porte
    le récit. Le défaut a été recopié avec la structure du fichier, sans la leçon qu'elle portait.
    """
    with TestClient(app_suisse) as client:
        scn = Scenario(app_suisse)

        reponse = client.get(f"/api/v1/suisse/etat/{scn.tournoi_id}/{scn.phase_id}")

    assert reponse.status_code == 200, reponse.text
    rencontre = reponse.json()["rondes"][0]["rencontres"][0]
    assert "duel" not in rencontre
    assert set(rencontre) == {
        "numero",
        "ronde",
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
    app_suisse: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La contrepartie : le scoreur de **ce** tournoi lit bien l'état complet, et lui seul."""
    with TestClient(app_suisse) as client:
        scn = Scenario(app_suisse)
        entetes = _scoreur(client, scn.tournoi_id, connecter_admin)

        ouverte = client.get(f"/api/v1/suisse/saisie/{scn.tournoi_id}/{scn.phase_id}")
        reponse = client.get(
            f"/api/v1/suisse/saisie/{scn.tournoi_id}/{scn.phase_id}", headers=entetes
        )

    assert ouverte.status_code == 401, ouverte.text
    assert reponse.status_code == 200, reponse.text
    assert "duel" in reponse.json()["rondes"][0]["rencontres"][0]


def test_un_suisse_non_commence_ne_decerne_aucune_medaille(app_suisse: FastAPI) -> None:
    """**Bloquant de revue.** Un podium était décerné avant la première flèche.

    `_resultat_classant` posait `origine=DUELS` et `en_lice=False` dès que la phase était terminale,
    sans notion d'avancement — or le classement d'une phase à rencontres est **complet dès la
    composition**, dérivé du classement amont. Le podium affiché venait donc de la qualification du
    matin, présenté comme issu des duels. C'est le défaut qu'`OriginePalmares` a été créé pour
    fermer, rouvert par un autre chemin.
    """
    with TestClient(app_suisse) as client:
        scn = Scenario(app_suisse)

        reponse = client.get(f"/api/v1/tournois/{scn.tournoi_id}/palmares")

    assert reponse.status_code == 200, reponse.text
    assert not any(ligne["decerne"] for ligne in reponse.json()["lignes"])
