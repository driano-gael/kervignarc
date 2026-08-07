"""Test bout-en-bout de l'endpoint public des tableaux (E07US005) — écrit **après** l'impl.

Il n'y a pas d'oracle métier à la frontière (règle 9) : la règle vit dans
`test_service_tableaux_publics.py`. Ce qui se vérifie ici est propre à la couche API, et un point y
pèse plus que tous les autres :

- **ce que le DTO public ne dit pas** (règle 6). Le même `EtatTableau` sert le scoreur avec chaque
  flèche de chaque manche et le **nom du bénévole qui a validé** ; ici il ne doit rester que ce
  qu'un spectateur vient lire. Un champ oublié dans la projection ne fait échouer aucun autre test
  du dépôt et fuite en silence sur une route **non authentifiée** — c'est précisément ce que le
  verrou ci-dessous existe pour empêcher ;
- la lecture est **publique** (le spectateur n'a pas de session, l'écran de salle non plus) ;
- un tournoi inconnu rend `404`, pas une page vide qui ferait croire à un tournoi sans tableau.

Le décor est celui d'E04US018 (`test_routage_api._preparer`) : c'est le même arbre reconstruit.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from tests.base_migree import preparer_base
from tests.conftest import ConnecterAdmin
from tests.test_placement_api import _appliquer_gabarit, _creer_depart, _creer_tournoi
from tests.test_placement_duels_api import (
    _phase_elimination,
    _premier_depart,
    _quatre_archers_classes,
)


@pytest.fixture
def app_tableaux(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    preparer_base(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _preparer(app: FastAPI, client: TestClient) -> tuple[int, int, int]:
    """Tournoi peuplé : gabarit, 4 archers classés, phase de tableau, plan de duels posé.

    Rend `(tournoi_id, depart_id, phase_id)` : la lecture publique des tableaux s'adresse au
    **créneau** depuis ADR-0075, il faut donc son identifiant — et il n'est *pas* égal à celui du
    tournoi dès qu'une base porte plus d'une édition.
    """
    tournoi_id = _creer_tournoi(client)
    _appliquer_gabarit(client, tournoi_id, nb_cibles=2)
    _quatre_archers_classes(app, client, tournoi_id)
    phase_id = _phase_elimination(app, tournoi_id)
    depart_id = _premier_depart(app, tournoi_id)
    regen = client.post(f"/api/v1/tournois/{tournoi_id}/phases/{phase_id}/plan-de-duels/regenerer")
    assert regen.status_code == 200, regen.text
    return tournoi_id, depart_id, phase_id


def _entete_scoreur(client: TestClient, tournoi_id: int) -> dict[str, str]:
    """En-tête `X-Jeton-Scoreur` — **le client est déjà connecté en admin**.

    Variante locale de `test_saisie_duels_api._scoreur`, qui ouvre lui-même la session admin :
    l'appeler ici lèverait `409 acces_deja_configure`, le décor de cette US ayant besoin de l'admin
    **avant** (créer le tournoi, le gabarit, les archers, la phase). C'est la seule différence.
    """
    reponse = client.post(f"/api/v1/tournois/{tournoi_id}/scoreurs", json={"nom": "ROUX"})
    assert reponse.status_code in (200, 201), reponse.text
    code = reponse.json()["code"]
    jeton = client.post("/api/v1/scoreurs/session", json={"code": code}).json()["jeton"]
    return {"X-Jeton-Scoreur": jeton}


def _manche(numero: int, tournoi_id: int, phase_id: int) -> dict[str, object]:
    """Une manche gagnée 30-18 par le camp haut du match n°1 — de quoi trancher en trois sets."""
    return {
        "tournoi_id": tournoi_id,
        "phase_id": phase_id,
        "match_numero": 1,
        "numero": numero,
        "valeurs_haut": ["10", "10", "10"],
        "valeurs_bas": ["6", "6", "6"],
    }


def test_les_tableaux_du_tournoi_sont_rendus_avec_leurs_matchs(
    app_tableaux: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La forme attendue par le front : une liste de tableaux, chacun avec ses duels et son type."""
    with TestClient(app_tableaux) as client:
        connecter_admin(client)
        tournoi_id, depart_id, phase_id = _preparer(app_tableaux, client)

        reponse = client.get(f"/api/v1/tableaux/departs/{depart_id}")

        assert reponse.status_code == 200, reponse.text
        corps = reponse.json()
        assert corps["depart_id"] == depart_id
        assert len(corps["tableaux"]) == 1
        tableau = corps["tableaux"][0]
        assert tableau["phase_id"] == phase_id
        assert tableau["type"] == "elimination_directe"
        assert tableau["effectif"] == 4
        assert tableau["duels"], "un tableau de 4 a des matchs"
        assert all(duel["haut"] is not None for duel in tableau["duels"] if duel["tour"] == 1)


def test_le_dto_public_ne_porte_ni_identite_de_scoreur_ni_detail_de_tir(
    app_tableaux: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """**Le verrou de règle 6 de cette US.**

    Le tableau du scoreur (`/api/v1/duels/tableau/...`) rend `manches`, `barrage`, `zones`, `mode`,
    `nb_manches`, `nb_fleches_par_volee`, `points_pour_gagner` et surtout `validee_par` — le **nom**
    de la personne qui a validé. Sur une route publique du réseau local, ces champs n'ont aucun
    destinataire et un seul effet possible : la fuite.

    ⚠️ **Liste blanche, et non liste noire** (correctif de revue, axe adversarial). Un premier jet
    asserait `not (interdits & set(joue))` sur six noms — un contrôle par **exclusion**,
    c'est-à-dire exactement le mode d'échec que le choix d'un DTO **distinct** (plutôt qu'un
    `exclude`) visait à éviter : l'argument était juste pour le DTO et abandonné pour son
    test. Cette liste ratait trois champs réels du DTO scoreur (`mode`,
    `nb_fleches_par_volee`, `points_pour_gagner`) et en protégeait un **fantôme**
    (`bareme` n'est le nom d'aucun champ). Elle n'inspectait pas non plus
    `DuellisteReponse` : une US future ajoutant `club` ou `licence` pour départager les homonymes
    aurait publié le champ sans faire échouer un seul test du dépôt, sur un LAN ouvert, mineurs
    compris. L'égalité de clés ferme les deux trous d'un coup.

    Le score de sets (`points_haut`/`points_bas`) reste, lui : c'est **le** résultat d'un duel, et
    l'afficher est le sujet même de l'US.
    """
    with TestClient(app_tableaux) as client:
        connecter_admin(client)
        tournoi_id, depart_id, phase_id = _preparer(app_tableaux, client)
        entete = _entete_scoreur(client, tournoi_id)
        for manche in (1, 2, 3):
            saisie = client.post(
                "/api/v1/duels/manches",
                json=_manche(manche, tournoi_id, phase_id),
                headers=entete,
            )
            assert saisie.status_code == 200, saisie.text
        valide = client.post(
            "/api/v1/duels/validations",
            json={"tournoi_id": tournoi_id, "phase_id": phase_id, "match_numero": 1},
            headers=entete,
        )
        assert valide.status_code == 200, valide.text

        duels: list[dict[str, Any]] = client.get(f"/api/v1/tableaux/departs/{depart_id}").json()[
            "tableaux"
        ][0]["duels"]

        joue = next(duel for duel in duels if duel["numero"] == 1)
        assert joue["validee"] is True
        assert joue["termine"] is True
        assert (joue["points_haut"], joue["points_bas"]) == (6, 0)
        assert set(joue) == {
            "numero",
            "tour",
            "libelle",
            "place_en_jeu",
            "plage",
            "haut",
            "bas",
            "est_bye",
            "points_haut",
            "points_bas",
            "vainqueur",
            "termine",
            "validee",
        }, f"champs inattendus sur la route publique : {sorted(joue)}"
        assert set(joue["haut"]) == {"archer_id", "nom", "prenom"}, sorted(joue["haut"])
        # **L'enveloppe aussi** (correctif de la 2ᵉ passe) : le verrou ne couvrait que le duel
        # et son duelliste, alors que le commit affirmait fermer « les deux trous d'un coup ».
        # Un champ ajouté à `TableauPublicReponse` partirait sur le LAN sans casser un test.
        tableau = client.get(f"/api/v1/tableaux/departs/{depart_id}").json()["tableaux"][0]
        assert set(tableau) == {
            "phase_id",
            "ordre",
            "type",
            "effectif",
            "taille",
            "nb_tours",
            "est_termine",
            "duels",
            "podium",
        }, f"champs inattendus sur l'enveloppe publique : {sorted(tableau)}"


def test_un_resultat_non_valide_n_est_pas_annonce_comme_acquis(
    app_tableaux: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`termine` et `validee` disent deux choses différentes, et la vue publique doit pouvoir les
    distinguer : tant que le scoreur n'a pas scellé, le tableau n'avance pas, donc annoncer le
    vainqueur comme acquis ferait mentir l'arbre affiché juste en dessous."""
    with TestClient(app_tableaux) as client:
        connecter_admin(client)
        tournoi_id, depart_id, phase_id = _preparer(app_tableaux, client)
        entete = _entete_scoreur(client, tournoi_id)
        for manche in (1, 2, 3):
            client.post(
                "/api/v1/duels/manches",
                json=_manche(manche, tournoi_id, phase_id),
                headers=entete,
            )

        duels = client.get(f"/api/v1/tableaux/departs/{depart_id}").json()["tableaux"][0]["duels"]

        joue = next(duel for duel in duels if duel["numero"] == 1)
        assert joue["termine"] is True
        assert joue["validee"] is False


def test_lecture_publique_sans_authentification(
    app_tableaux: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Les deux destinataires de l'US n'ont **aucune** session : le téléphone du spectateur et
    l'écran de salle. Protéger cette route les éteindrait tous les deux."""
    with TestClient(app_tableaux) as client:
        connecter_admin(client)
        _, depart_id, _ = _preparer(app_tableaux, client)

    with TestClient(app_tableaux) as anonyme:
        reponse = anonyme.get(f"/api/v1/tableaux/departs/{depart_id}")

        assert reponse.status_code == 200, reponse.text
        assert reponse.json()["tableaux"]


def test_creneau_inconnu_rend_404(app_tableaux: FastAPI) -> None:
    """Un identifiant inventé n'est pas un créneau sans tableau : le dire évite d'afficher une vue
    vide plausible pour une adresse fausse."""
    with TestClient(app_tableaux) as client:
        reponse = client.get("/api/v1/tableaux/departs/4242")

        assert reponse.status_code == 404, reponse.text
        assert reponse.json()["code"] == "depart_introuvable"


def test_un_creneau_sans_phase_rend_une_liste_vide(
    app_tableaux: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """L'onglet s'ouvre à 8 h du matin : « pas encore de tableau » est une réponse, pas une
    panne."""
    with TestClient(app_tableaux) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        depart_id = _creer_depart(client, tournoi_id)

        reponse = client.get(f"/api/v1/tableaux/departs/{depart_id}")

        assert reponse.status_code == 200, reponse.text
        assert reponse.json()["tableaux"] == []
