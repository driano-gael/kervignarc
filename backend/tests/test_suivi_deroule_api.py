"""Test bout-en-bout de l'endpoint de suivi du déroulé (E07US004) — écrit **après** l'impl.

Ce qui se vérifie ici est propre à la frontière :

- la **lecture est publique** (l'écran de salle est public, il ne porte aucun jeton admin) ;
- rien de sensible ne transite (ni nom, ni code de poste, ni donnée de paiement) ;
- la forme des blocs est **celle du diagnostic d'atelier** (E01US024), plus un calque `avancement` —
  c'est ce qui permet au front de n'avoir qu'un seul composant de dessin ;
- un tournoi sans phase répond, il ne casse pas.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from domain.phase import TypePhase
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


def _depart(client: TestClient, tournoi_id: int) -> int:
    """Le créneau porteur de la séquence (ADR-0075) — les phases y pendent, pas au tournoi."""
    reponse = client.post(
        f"/api/v1/tournois/{tournoi_id}/departs",
        json={"horaire": "09:00", "tarif_centimes": 800},
    )
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def test_un_tournoi_sans_phase_repond_un_suivi_vide(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Avant qu'un format soit appliqué, il n'y a rien à suivre — ce n'est pas une erreur."""
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        depart_id = _depart(client, tournoi_id)

        reponse = client.get(f"/api/v1/departs/{depart_id}/suivi-deroule")

        assert reponse.status_code == 200, reponse.text
        assert reponse.json() == {
            "effectif": 0,
            "ordre_courant": None,
            "blocs": [],
            "avancement": [],
        }


def test_le_suivi_est_une_lecture_publique(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """L'écran de salle n'a pas de jeton admin : sans lecture publique, il n'affiche rien."""
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        depart_id = _depart(client, tournoi_id)

    with TestClient(app_session) as anonyme:
        reponse = anonyme.get(f"/api/v1/departs/{depart_id}/suivi-deroule")

    assert reponse.status_code == 200, reponse.text


def test_un_creneau_inconnu_est_un_404(app_session: FastAPI) -> None:
    """La garde porte sur le **créneau** : c'est lui que la route désigne depuis ADR-0075."""
    with TestClient(app_session) as client:
        reponse = client.get("/api/v1/departs/9999/suivi-deroule")

        assert reponse.status_code == 404
        assert reponse.json()["code"] == "depart_introuvable"


def test_les_phases_apparaissent_avec_leur_statut(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le calque `avancement` s'apparie aux `blocs` par `ordre` — la clé du dessin superposé."""
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        depart_id = _depart(client, tournoi_id)
        creation = client.post(
            f"/api/v1/tournois/{tournoi_id}/phases", json={"type": "placement", "effectif": 8}
        )
        assert creation.status_code == 201, creation.text

        corps = client.get(f"/api/v1/departs/{depart_id}/suivi-deroule").json()

        assert [bloc["ordre"] for bloc in corps["blocs"]] == [1]
        assert [av["ordre"] for av in corps["avancement"]] == [1]
        assert corps["avancement"][0]["statut"] == "a_venir"
        assert corps["avancement"][0]["tour_courant"] is None
        assert corps["ordre_courant"] is None
        # Les braquets sont dessinés (« duels attendus ») alors que rien n'est joué : c'est
        # exactement le CA — le schéma existe d'abord, il se **remplit** ensuite.
        assert corps["avancement"][0]["duels_attendus"] == 7
        assert corps["avancement"][0]["duels_joues"] == 0
        assert [tour["duels"] for tour in corps["blocs"][0]["tours"]] == [4, 2, 1]


def test_le_tour_en_cours_est_servi_avec_le_mot_de_la_salle(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """E05US032 — le DTO porte le **libellé** du tour, pas seulement son numéro (ADR-0090 §4).

    Test d'API, donc écrit **après** l'implémentation (règle 9 : il n'y a pas d'oracle en jeu, la
    règle métier est testée dans `test_domain_tour_de_phase.py`). Ce qu'il garde est le **contrat de
    frontière** : le front ne doit pas avoir à redériver « à rebours de la finale », faute de quoi
    `DETTE-020` gagne un domicile de plus.

    Un tableau de 8 non démarré n'annonce aucun tour, mais **compte** ses trois tours : c'est la
    séparation posée par l'ADR — le nombre est structurel, le tour courant dépend du statut.
    """
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        depart_id = _depart(client, tournoi_id)
        creation = client.post(
            f"/api/v1/tournois/{tournoi_id}/phases",
            json={"type": "elimination_directe", "effectif": 8},
        )
        assert creation.status_code == 201, creation.text

        avancement = client.get(f"/api/v1/departs/{depart_id}/suivi-deroule").json()["avancement"][
            0
        ]

        assert avancement["nb_tours"] == 3
        assert avancement["tour_courant"] is None
        assert avancement["libelle_tour_courant"] is None


def test_une_phase_sans_braquet_compte_un_tour_plutot_que_zero(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """E05US032 — une qualification **avance** elle aussi, même si elle ne classe qu'à la fin.

    C'est le défaut que l'US corrige : `nb_tours` se dérivait des braquets, donc toute phase hors
    tableau s'affichait à zéro tour. Un est **vrai** — la phase entière en est un — et le réglage
    « diviser en x tours » arrive avec `E05US034` (annoncé pour `E05US033`, reporté d'une tranche le
    19/08/2026 : lire l'avancement réel d'une qualification demande sa population, son plan de
    cibles et ses forfaits).
    """
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        depart_id = _depart(client, tournoi_id)
        creation = client.post(
            f"/api/v1/tournois/{tournoi_id}/phases",
            json={"type": "qualification", "effectif": 8},
        )
        assert creation.status_code == 201, creation.text

        avancement = client.get(f"/api/v1/departs/{depart_id}/suivi-deroule").json()["avancement"][
            0
        ]

        assert avancement["nb_tours"] == 1
        assert avancement["tours"] == []


def test_le_libelle_du_tour_est_servi_dans_le_mot_de_la_salle(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """E05US032 — le **contrat de frontière** : le front ne redérive pas « à rebours de la finale ».

    ⚠️ Ce test naît d'un relevé de revue (axe B), et le défaut vaut d'être nommé : le test d'API
    d'origine s'appelait « le tour en cours est servi avec le mot de la salle » et n'observait que
    **trois `None`**, sur une phase non démarrée. La branche non nulle de la résolution — celle qui
    porte tout l'intérêt de l'US — n'était exercée à **aucune** couche. Une régression qui aurait
    résolu le mauvais type de phase, ou passé `bloc.ordre` au lieu de `bloc.tour_courant`, laissait
    la suite entière verte.

    Un tableau de 8 démarré est au **quart de finale** : la salle ne dit pas « tour 1 ».
    """
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        depart_id = _depart(client, tournoi_id)
        creation = client.post(
            f"/api/v1/tournois/{tournoi_id}/phases",
            json={"type": "elimination_directe", "effectif": 8},
        )
        assert creation.status_code == 201, creation.text
        phase_id = creation.json()["id"]
        demarrage = client.post(
            f"/api/v1/departs/{depart_id}/phases/{phase_id}/statut",
            json={"transition": "demarrer"},
        )
        assert demarrage.status_code == 200, demarrage.text

        avancement = client.get(f"/api/v1/departs/{depart_id}/suivi-deroule").json()["avancement"][
            0
        ]

        assert avancement["tour_courant"] == 1
        assert avancement["libelle_tour_courant"] == "Quart de finale"


def test_un_tableau_de_placement_ne_s_annonce_pas_finale(
    app_session: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """E05US032 — un tour dont la tranche ne part pas du rang 1 se nomme par sa **plage**.

    ⚠️ Défaut trouvé par l'axe adversarial, et c'était une **régression de véracité** introduite par
    l'US : en ne passant pas `plage` à `libelle_tour`, une phase de placement alimentée par les
    perdants d'un tableau s'annonçait « Finale » pour le match des places 7-8. Avant l'US, l'écran
    disait « tour 2 » — neutre et vrai. C'est nommément le défaut que `libelle_tour` porte dans ses
    propres encarts (« trois "Finale" simultanées sur le panneau de routage »).
    """
    with TestClient(app_session) as client:
        tournoi_id = _tournoi(client, connecter_admin)
        depart_id = _depart(client, tournoi_id)
        principal = client.post(
            f"/api/v1/tournois/{tournoi_id}/phases",
            json={"type": "elimination_directe", "effectif": 8},
        )
        assert principal.status_code == 201, principal.text
        placement = client.post(
            f"/api/v1/tournois/{tournoi_id}/phases",
            json={
                "type": "placement",
                "effectif": 4,
                "sources": [{"nature": "rangs", "ordre_source": 1, "rang_debut": 5, "rang_fin": 8}],
            },
        )
        assert placement.status_code == 201, placement.text
        demarrage = client.post(
            f"/api/v1/departs/{depart_id}/phases/{placement.json()['id']}/statut",
            json={"transition": "demarrer"},
        )
        assert demarrage.status_code == 200, demarrage.text

        corps = client.get(f"/api/v1/departs/{depart_id}/suivi-deroule").json()
        bloc = next(av for av in corps["avancement"] if av["ordre"] == 2)

        # Valeur exacte, pas un `!= "Finale"` : une assertion négative passerait aussi bien si le
        # libellé était `None`, et c'est précisément le genre de test que la revue vient de nous
        # reprocher. Sans le correctif, ce tour 1 sur 2 s'annonçait « Demi-finale ».
        assert bloc["libelle_tour_courant"] == "Places 5 à 8"


def test_chaque_lecteur_d_avancement_est_branche_sur_le_service_de_son_format(
    app_session: FastAPI,
) -> None:
    """E05US032 — l'appariement type→service du composition root, **prouvé** (ADR-0090 §5).

    ⚠️ Relevé en revue (axe A) : le câblage était explicite et au bon endroit, mais sa correction
    n'était garantie **par rien**. Les variables annotées ne prouvent pas la conformité au Protocol
    — mypy accepte silencieusement l'affectation d'une expression `Any` (`app.state.*`) à une
    variable annotée —, et les tests de service passent par une doublure. Un `TypePhase.POULES`
    branché sur `ServiceSuisse` aurait franchi **toutes** les portes et ne se serait vu que le jour
    J, sur l'écran projeté, sous la forme d'une phase qui n'annonce jamais sa ronde.

    Le test touche un attribut privé, et c'est assumé : le composition root n'expose pas sa table de
    résolution, et ce qu'on veut garder est précisément ce câblage-là.
    """
    branches = app_session.state.service_suivi_deroule._avancements

    assert branches[TypePhase.POULES] is app_session.state.service_poules
    assert branches[TypePhase.SUISSE] is app_session.state.service_suisse
    assert branches[TypePhase.BIG_SHOOT_OFF] is app_session.state.service_big_shoot_off
    # E05US035 : la **qualification** rejoint la table, portée par le service qui la fait jouer —
    # `ServiceSaisie`, comme `ServicePoules` porte les poules (ADR-0093).
    assert branches[TypePhase.QUALIFICATION] is app_session.state.service_saisie
    # Le reste du catalogue n'a **aucun** lecteur, et c'est le contrat d'ADR-0090 §3 : ces types
    # comptent un tour, sauf la colline dont le manque est assumé (`DETTE-028`).
    assert set(branches) == {
        TypePhase.QUALIFICATION,
        TypePhase.POULES,
        TypePhase.SUISSE,
        TypePhase.BIG_SHOOT_OFF,
    }
