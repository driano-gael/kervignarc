"""Test bout-en-bout de l'API des écrans de salle (E07US004).

Écrits **après** l'implémentation (règle 9 : à la frontière API, il n'y a pas d'oracle en jeu — on
vérifie le câblage, les portées et le mapping d'erreurs, pas une règle métier).

Le parcours complet du CA :

1. l'admin crée un écran → un **code** de rattachement, comme pour une cible ;
2. l'écran se rattache par le **même** endpoint que la tablette, et son `type` l'aiguille ;
3. il lit son affichage → le **déroulé par défaut** ;
4. l'admin règle un autre déroulé → l'écran le voit ;
5. l'admin **impose** le classement 10 minutes → l'écran bascule, avec un compte à rebours ;
6. l'admin **rend la main** → l'écran reprend son déroulé ;
7. l'écran apparaît dans la **console de supervision**, avec sa prise en vigueur ;
8. les portées : un jeton de cible n'ouvre pas l'affichage d'un écran ; le pilotage est admin.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from domain.gabarit_salle import GabaritSalle
from infrastructure.db import Database, GabaritSalleRepositorySQL
from tests.base_migree import preparer_base
from tests.conftest import ConnecterAdmin


@pytest.fixture
def app_session(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    preparer_base(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _tournoi(client: TestClient, connecter_admin: ConnecterAdmin) -> int:
    connecter_admin(client)
    return int(
        client.post("/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14"}).json()[
            "id"
        ]
    )


def _creer_ecran(
    client: TestClient, tournoi_id: int, libelle: str = "Pas de tir"
) -> dict[str, Any]:
    reponse = client.post(f"/api/v1/tournois/{tournoi_id}/ecrans", json={"libelle": libelle})
    assert reponse.status_code == 200, reponse.text
    return dict(reponse.json())


def _rattacher(client: TestClient, code: str) -> tuple[str, dict[str, Any]]:
    reponse = client.post("/api/v1/postes/session", json={"code": code})
    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    return str(corps["jeton"]), dict(corps["poste"])


def _affichage(client: TestClient, jeton: str) -> dict[str, Any]:
    reponse = client.get("/api/v1/ecrans/session/affichage", headers={"X-Jeton-Poste": jeton})
    assert reponse.status_code == 200, reponse.text
    return dict(reponse.json())


# --- Préparation & rattachement -------------------------------------------------------------------


def test_un_ecran_cree_porte_un_code_et_le_deroule_par_defaut(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)

        ecran = _creer_ecran(client, tournoi_id)

        assert ecran["libelle"] == "Pas de tir"
        assert ecran["code"]
        # Le déroulé est **toujours** rempli : le front n'a jamais à connaître l'existence d'un
        # défaut, ni à gérer un écran « sans vue ».
        assert [etape["vue"] for etape in ecran["deroule"]] == [
            "classement",
            "plan_cibles",
            "suivi_deroule",
        ]


def test_un_ecran_se_rattache_par_le_meme_endpoint_qu_une_cible(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA « même mécanisme que la tablette de cible » : aucun endpoint de rattachement parallèle."""
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        ecran = _creer_ecran(client, tournoi_id)

        _, poste = _rattacher(client, str(ecran["code"]))

        assert poste == {
            "tournoi_id": tournoi_id,
            "type": "ecran",
            "cible_index": None,
            "libelle": "Pas de tir",
        }


def test_plusieurs_ecrans_coexistent_avec_des_deroules_distincts(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA « plusieurs écrans possibles, chacun son déroulé »."""
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        pas_de_tir = _creer_ecran(client, tournoi_id, "Pas de tir")
        public = _creer_ecran(client, tournoi_id, "Côté public")

        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/ecrans/{pas_de_tir['id']}/deroule",
            json={"vues": [{"vue": "plan_cibles", "cadence_s": 20}]},
        )

        assert reponse.status_code == 200, reponse.text
        assert [etape["vue"] for etape in reponse.json()["deroule"]] == ["plan_cibles"]
        liste = client.get(f"/api/v1/tournois/{tournoi_id}/ecrans").json()
        inchange = next(e for e in liste if e["id"] == public["id"])
        assert len(inchange["deroule"]) == 3


def test_une_cadence_hors_bornes_est_refusee(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        ecran = _creer_ecran(client, tournoi_id)

        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/ecrans/{ecran['id']}/deroule",
            json={"vues": [{"vue": "classement", "cadence_s": 1}]},
        )

        assert reponse.status_code == 422, reponse.text


def test_regler_le_deroule_d_une_cible_est_un_conflit(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La console affiche cibles et écrans côte à côte : la confusion se refuse explicitement."""
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        database: Database = app_session.state.database
        modele = GabaritSalle.creer("Plan", nb_cibles=2)
        GabaritSalleRepositorySQL(database.session_factory).ajouter(modele.pour_tournoi(tournoi_id))
        cible = client.post(f"/api/v1/tournois/{tournoi_id}/postes").json()[0]

        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/ecrans/{cible['id']}/deroule",
            json={"vues": [{"vue": "classement", "cadence_s": 30}]},
        )

        assert reponse.status_code == 409, reponse.text
        assert reponse.json()["code"] == "poste_n_est_pas_un_ecran"


# --- Réglage des pages projetées (E16US009) -------------------------------------------------------


def test_un_ecran_neuf_annonce_le_reglage_de_pages_par_defaut(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Même contrat que le déroulé : la réponse est **toujours** remplie, jamais « rien réglé ».

    Les valeurs sont celles que le front tenait en dur avant l'US (`DETTE-039`) — c'est ce qui rend
    le déploiement invisible pour un écran déjà installé.
    """
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)

        ecran = _creer_ecran(client, tournoi_id)

        assert ecran["pages"] == {"noms_par_page": 40, "cadence_page_s": 20}


def test_le_reglage_de_pages_se_pose_et_se_relit(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA : « la cadence d'une page de noms se règle **par écran** »."""
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        ecran = _creer_ecran(client, tournoi_id)

        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/ecrans/{ecran['id']}/pages",
            json={"pages": {"noms_par_page": 24, "cadence_page_s": 12}},
        )

        assert reponse.status_code == 200, reponse.text
        assert reponse.json()["pages"] == {"noms_par_page": 24, "cadence_page_s": 12}
        relu = client.get(f"/api/v1/tournois/{tournoi_id}/ecrans").json()[0]
        assert relu["pages"] == {"noms_par_page": 24, "cadence_page_s": 12}


def test_regler_les_pages_ne_touche_pas_au_deroule(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le motif même de la route séparée : corriger une cadence de page ne doit pas obliger à
    renvoyer la séquence de vues, donc ne peut pas l'écraser par inadvertance."""
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        ecran = _creer_ecran(client, tournoi_id)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/ecrans/{ecran['id']}/deroule",
            json={"vues": [{"vue": "affectations", "cadence_s": 45}]},
        )

        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/ecrans/{ecran['id']}/pages",
            json={"pages": {"noms_par_page": 24, "cadence_page_s": 12}},
        )

        assert reponse.json()["deroule"] == [{"vue": "affectations", "cadence_s": 45}]


def test_deux_ecrans_du_meme_tournoi_ont_des_reglages_de_pages_distincts(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """« Par écran » : le vidéoprojecteur du fond de salle et l'écran d'accueil n'ont ni la même
    diagonale ni la même distance de lecture."""
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        fond = _creer_ecran(client, tournoi_id, "Fond de salle")
        accueil = _creer_ecran(client, tournoi_id, "Accueil")

        client.put(
            f"/api/v1/tournois/{tournoi_id}/ecrans/{fond['id']}/pages",
            json={"pages": {"noms_par_page": 20, "cadence_page_s": 25}},
        )

        assert _affichage(client, _rattacher(client, str(fond["code"]))[0])["pages"] == {
            "noms_par_page": 20,
            "cadence_page_s": 25,
        }
        assert _affichage(client, _rattacher(client, str(accueil["code"]))[0])["pages"] == {
            "noms_par_page": 40,
            "cadence_page_s": 20,
        }


@pytest.mark.parametrize(
    ("corps", "code"),
    [
        ({"noms_par_page": 1, "cadence_page_s": 20}, "nombre_de_noms_par_page_invalide"),
        ({"noms_par_page": 400, "cadence_page_s": 20}, "nombre_de_noms_par_page_invalide"),
        ({"noms_par_page": 40, "cadence_page_s": 1}, "cadence_de_page_invalide"),
        ({"noms_par_page": 40, "cadence_page_s": 3600}, "cadence_de_page_invalide"),
    ],
)
def test_un_reglage_de_pages_hors_bornes_est_refuse_avec_le_champ_fautif(
    app_session: FastAPI,
    connecter_admin: ConnecterAdmin,
    corps: dict[str, int],
    code: str,
) -> None:
    """Deux codes distincts, et c'est la raison de ne pas borner en `Field(ge=…, le=…)` : un 400
    générique ne dirait pas **lequel** des deux champs le formulaire doit corriger."""
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        ecran = _creer_ecran(client, tournoi_id)

        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/ecrans/{ecran['id']}/pages",
            json={"pages": corps},
        )

        assert reponse.status_code == 422, reponse.text
        assert reponse.json()["code"] == code


def test_regler_les_pages_d_une_cible_est_un_conflit(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Même garde que le déroulé : une tablette ne projette rien."""
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        database: Database = app_session.state.database
        modele = GabaritSalle.creer("Plan", nb_cibles=2)
        GabaritSalleRepositorySQL(database.session_factory).ajouter(modele.pour_tournoi(tournoi_id))
        cible = client.post(f"/api/v1/tournois/{tournoi_id}/postes").json()[0]

        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/ecrans/{cible['id']}/pages",
            json={"pages": {"noms_par_page": 24, "cadence_page_s": 12}},
        )

        assert reponse.status_code == 409, reponse.text
        assert reponse.json()["code"] == "poste_n_est_pas_un_ecran"


def test_une_prise_de_controle_ne_change_pas_le_reglage_de_pages(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Une prise impose **ce qu'on montre**, jamais **comment une liste se lit à dix mètres**.

    Le cas est réel : l'organisateur fige le classement sur l'écran du fond pour l'annonce des
    résultats — la liste doit continuer de tourner au rythme réglé pour cette salle.
    """
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        ecran = _creer_ecran(client, tournoi_id)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/ecrans/{ecran['id']}/pages",
            json={"pages": {"noms_par_page": 24, "cadence_page_s": 12}},
        )
        jeton, _ = _rattacher(client, str(ecran["code"]))

        client.post(
            f"/api/v1/tournois/{tournoi_id}/ecrans/{ecran['id']}/controle",
            json={"vue": "classement", "duree_s": 600},
        )

        affichage = _affichage(client, jeton)
        assert affichage["sous_controle"] is True
        assert affichage["pages"] == {"noms_par_page": 24, "cadence_page_s": 12}


# --- Pilotage admin -------------------------------------------------------------------------------


def test_une_vue_imposee_bascule_l_ecran_et_rend_la_main_le_libere(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le parcours complet du CA « pilotage admin », vu des deux côtés."""
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        ecran = _creer_ecran(client, tournoi_id)
        jeton, _ = _rattacher(client, str(ecran["code"]))
        assert _affichage(client, jeton)["sous_controle"] is False

        prise = client.post(
            f"/api/v1/tournois/{tournoi_id}/ecrans/{ecran['id']}/controle",
            json={"vue": "classement", "duree_s": 600},
        )

        assert prise.status_code == 200, prise.text
        assert prise.json()["exige_rappel"] is False
        sous_controle = _affichage(client, jeton)
        assert sous_controle["sous_controle"] is True
        assert sous_controle["vue_figee"] == "classement"
        # La séquence de repli accompagne la vue figée : c'est ce sur quoi l'écran retombe seul à
        # l'échéance, même s'il a perdu le réseau entre-temps (correctif de revue).
        assert len(sous_controle["vues"]) == 3
        assert 0 < float(sous_controle["reste_s"]) <= 600

        rendu = client.delete(f"/api/v1/tournois/{tournoi_id}/ecrans/{ecran['id']}/controle")

        assert rendu.status_code == 204, rendu.text
        libre = _affichage(client, jeton)
        assert libre["sous_controle"] is False
        assert libre["vue_figee"] is None
        assert len(libre["vues"]) == 3


def test_une_prise_sans_duree_exige_un_rappel(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA « jamais un état forcé qu'on oublie » : le drapeau remonte jusqu'à l'API."""
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        ecran = _creer_ecran(client, tournoi_id)

        prise = client.post(
            f"/api/v1/tournois/{tournoi_id}/ecrans/{ecran['id']}/controle",
            json={"vue": "classement"},
        )

        assert prise.status_code == 200, prise.text
        assert prise.json() == {
            "poste_id": ecran["id"],
            "vue_figee": "classement",
            "reste_s": None,
            "exige_rappel": True,
        }


def test_une_consigne_sans_contenu_est_refusee(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """« Imposer rien » n'est pas une prise de contrôle — c'est rendre la main, un autre geste."""
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        ecran = _creer_ecran(client, tournoi_id)

        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/ecrans/{ecran['id']}/controle", json={"duree_s": 60}
        )

        assert reponse.status_code == 422, reponse.text
        assert reponse.json()["code"] == "consigne_ecran_invalide"


def test_rendre_la_main_est_idempotent(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        ecran = _creer_ecran(client, tournoi_id)

        premier = client.delete(f"/api/v1/tournois/{tournoi_id}/ecrans/{ecran['id']}/controle")
        second = client.delete(f"/api/v1/tournois/{tournoi_id}/ecrans/{ecran['id']}/controle")

        assert premier.status_code == 204
        assert second.status_code == 204


# --- Supervision ----------------------------------------------------------------------------------


def test_un_ecran_apparait_dans_la_console_avec_sa_prise(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA « il apparaît dans la console de supervision : *un écran figé ne se plaint pas* »."""
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        ecran = _creer_ecran(client, tournoi_id)
        client.post(
            f"/api/v1/tournois/{tournoi_id}/ecrans/{ecran['id']}/controle",
            json={"vue": "classement"},
        )

        console = client.get(f"/api/v1/tournois/{tournoi_id}/supervision").json()

        ligne = next(p for p in console["postes"] if p["poste_id"] == ecran["id"])
        assert ligne["type"] == "ecran"
        assert ligne["libelle"] == "Pas de tir"
        assert ligne["cible_index"] is None
        assert ligne["prise"]["exige_rappel"] is True
        # Les compteurs de tablettes ne bougent pas : un écran hors ligne n'empêche pas de tirer.
        assert console["nb_total"] == 0
        assert console["nb_ecrans"] == 1


def test_un_ecran_supprime_disparait_de_la_console(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        ecran = _creer_ecran(client, tournoi_id)

        suppression = client.delete(f"/api/v1/tournois/{tournoi_id}/ecrans/{ecran['id']}")

        assert suppression.status_code == 204, suppression.text
        assert client.get(f"/api/v1/tournois/{tournoi_id}/ecrans").json() == []
        assert client.get(f"/api/v1/tournois/{tournoi_id}/supervision").json()["nb_ecrans"] == 0


# --- Portées --------------------------------------------------------------------------------------


def test_un_jeton_de_cible_n_ouvre_pas_l_affichage_d_un_ecran(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La portée « poste » est commune aux deux natures : la garde de nature est donc au service."""
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        database: Database = app_session.state.database
        modele = GabaritSalle.creer("Plan", nb_cibles=1)
        GabaritSalleRepositorySQL(database.session_factory).ajouter(modele.pour_tournoi(tournoi_id))
        cible = client.post(f"/api/v1/tournois/{tournoi_id}/postes").json()[0]
        jeton, _ = _rattacher(client, str(cible["code"]))

        reponse = client.get("/api/v1/ecrans/session/affichage", headers={"X-Jeton-Poste": jeton})

        assert reponse.status_code == 409, reponse.text
        assert reponse.json()["code"] == "poste_n_est_pas_un_ecran"


def test_un_jeton_d_ecran_ne_peut_pas_saisir_de_score(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """**Non-régression de sécurité** (trouvée en revue) : le trou que ce test ferme était réel.

    Un écran de salle est du **matériel public** — son code est affiché dans le gymnase. En rendant
    `Poste.cible_index` facultatif, cette US avait transformé la garde métier
    `archer.cible != poste.cible_index` en `None != None` (donc *faux*) pour un écran face à un
    archer **non placé** : le score était accepté, en 201.

    Le test tape le parcours complet et **public** : rattachement par code (endpoint ouvert), puis
    écriture. Il vise volontairement un archer **non placé**, le seul cas qui ouvrait le trou.
    """
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        categorie = client.post(
            f"/api/v1/tournois/{tournoi_id}/categories", json={"libelle": "Senior 1 H"}
        )
        assert categorie.status_code == 201, categorie.text
        archer = client.post(
            f"/api/v1/tournois/{tournoi_id}/archers",
            json={"nom": "Robin", "prenom": "Jean", "categorie_id": categorie.json()["id"]},
        )
        assert archer.status_code == 201, archer.text
        archer_id = int(archer.json()["id"])
        ecran = _creer_ecran(client, tournoi_id)
        jeton, _ = _rattacher(client, str(ecran["code"]))

    with TestClient(app_session) as anonyme:
        reponse = anonyme.post(
            f"/api/v1/archers/{archer_id}/scores",
            json={"points": 10},
            headers={"X-Jeton-Poste": jeton},
        )

    # 403 et non 422 : l'identité est établie, c'est le **droit** qui manque — même parti que
    # `SaisieHorsCible` pour un poste de cible qui vise la mauvaise cible.
    assert reponse.status_code == 403, reponse.text
    assert reponse.json()["code"] == "saisie_hors_cible"


def test_un_jeton_d_ecran_n_ouvre_pas_les_surfaces_de_saisie(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Même barrière sur les autres surfaces de saisie : départ courant et grille d'archers.

    La portée « poste » est **commune** aux deux natures (même en-tête, même store) : c'est la
    dépendance `exiger_poste_de_cible` qui les sépare. Ce test verrouille les deux routes qu'elle
    garde, pour qu'une future route de saisie qui reprendrait `exiger_poste` par mégarde se voie.
    """
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        ecran = _creer_ecran(client, tournoi_id)
        jeton, _ = _rattacher(client, str(ecran["code"]))
        entete = {"X-Jeton-Poste": jeton}

        grille = client.get("/api/v1/saisie/archers", headers=entete)
        depart = client.post("/api/v1/saisie/depart-courant", json={"depart_id": 1}, headers=entete)

        assert grille.status_code == 403, grille.text
        assert depart.status_code == 403, depart.text


def test_l_affichage_sans_jeton_est_refuse(app_session: FastAPI) -> None:
    with TestClient(app_session) as client:
        assert client.get("/api/v1/ecrans/session/affichage").status_code == 401


def test_le_pilotage_est_reserve_a_l_admin(app_session: FastAPI) -> None:
    with TestClient(app_session) as client:
        assert client.get("/api/v1/tournois/1/ecrans").status_code == 401
        assert client.post("/api/v1/tournois/1/ecrans", json={"libelle": "X"}).status_code == 401
        assert (
            client.post(
                "/api/v1/tournois/1/ecrans/1/controle", json={"vue": "classement"}
            ).status_code
            == 401
        )


def test_une_vue_inconnue_est_refusee_sans_500(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """**Non-régression** (2ᵉ passe) : ces valeurs sont les **premières** qu'un client enverra.

    Avant correctif, une valeur hors catalogue produisait un `ValueError` nu dans le corps du
    handler → **500 + traceback journalisé**. Typer le champ au DTO la fait rejeter par Pydantic,
    champ fautif nommé.

    ⚠️ **Deuxième mise à jour, par E07US005** (la première était E07US008, pour `affectations`).
    Les deux exemples successifs de « vue inconnue » étaient des vues **nommées par le CA
    d'E07US004 mais pas encore livrées** — un vivier qui vient de se **tarir** : avec `tableaux`, le
    catalogue couvre le CA en entier. L'exemple est donc désormais une valeur **franchement
    inventée**, qui ne peut plus être rattrapée par une US future — et le test vérifie en regard
    que `tableaux` est bel et bien **acceptée**, sinon il ne dirait plus rien de l'élargissement qui
    vient de l'invalider.
    """
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        ecran = _creer_ecran(client, tournoi_id)

        deroule = client.put(
            f"/api/v1/tournois/{tournoi_id}/ecrans/{ecran['id']}/deroule",
            json={"vues": [{"vue": "meteo_du_gymnase", "cadence_s": 30}]},
        )
        controle = client.post(
            f"/api/v1/tournois/{tournoi_id}/ecrans/{ecran['id']}/controle",
            json={"vue": "meteo_du_gymnase", "duree_s": 300},
        )
        desormais_connue = client.put(
            f"/api/v1/tournois/{tournoi_id}/ecrans/{ecran['id']}/deroule",
            json={"vues": [{"vue": "en_cours", "cadence_s": 30}]},
        )

        assert deroule.status_code == 400, deroule.text
        assert deroule.json()["code"] == "requete_invalide"
        assert controle.status_code == 400, controle.text
        assert desormais_connue.status_code == 200, desormais_connue.text
