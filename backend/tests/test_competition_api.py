"""Test bout-en-bout de la tranche verticale (E00US011).

Déroule le fil rouge du walking skeleton à travers toutes les couches — créer un tournoi →
inscrire un archer → le placer sur une cible → saisir des scores → consulter le classement —
et vérifie qu'**après chaque écriture, un événement est diffusé en direct** aux abonnés
WebSocket (mécanisme de mise à jour temps réel de l'écran de classement). Contrôle aussi le
mapping des erreurs typées à la frontière (ADR-0007).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from tests.conftest import ConnecterAdmin

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


@pytest.fixture
def app_competition(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _creer_categorie(client: TestClient, tournoi_id: int) -> int:
    """Crée une catégorie du tournoi et renvoie son identifiant (obligatoire depuis E02US002)."""
    reponse = client.post(
        f"/api/v1/tournois/{tournoi_id}/categories", json={"libelle": "Senior 1 H"}
    )
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def test_tranche_verticale_bout_en_bout(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Tournoi → archer → placement → scores → classement, avec diffusion temps réel."""
    with TestClient(app_competition) as client, client.websocket_connect("/ws") as ws:
        assert ws.receive_json()["type"] == "connected"
        connecter_admin(client)  # accès admin requis pour créer le tournoi (E10US002)

        tournoi = client.post(
            "/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14"}
        ).json()
        assert ws.receive_json()["type"] == "donnees_modifiees"

        categorie_id = _creer_categorie(client, tournoi["id"])
        assert ws.receive_json()["type"] == "donnees_modifiees"

        alice = client.post(
            f"/api/v1/tournois/{tournoi['id']}/archers",
            json={"nom": "Martin", "prenom": "Alice", "categorie_id": categorie_id},
        )
        assert alice.status_code == 201, alice.text
        alice_id = alice.json()["id"]
        assert alice.json()["cible"] is None
        # Le DTO restitue l'identité complète : sans cette assertion, un `de_agregat` qui
        # confondrait `prenom` et `nom` passerait la suite entière au vert (les tests de
        # repository couvrent l'ORM, pas la traduction en DTO).
        assert (alice.json()["prenom"], alice.json()["categorie_id"]) == ("Alice", categorie_id)
        assert alice.json()["club_id"] is None
        assert ws.receive_json()["type"] == "donnees_modifiees"

        bob_id = client.post(
            f"/api/v1/tournois/{tournoi['id']}/archers",
            json={"nom": "Durand", "prenom": "Bob", "categorie_id": categorie_id},
        ).json()["id"]
        assert ws.receive_json()["type"] == "donnees_modifiees"

        place = client.post(f"/api/v1/archers/{alice_id}/placement", json={"cible": 3})
        assert place.status_code == 200
        assert place.json()["cible"] == 3
        assert ws.receive_json()["type"] == "donnees_modifiees"

        # Scores : Alice 10 + 9 = 19, Bob 8 → Alice devant.
        for archer_id, points in [(alice_id, 10), (alice_id, 9), (bob_id, 8)]:
            reponse = client.post(f"/api/v1/archers/{archer_id}/scores", json={"points": points})
            assert reponse.status_code == 201
            assert ws.receive_json()["type"] == "donnees_modifiees"

        classement = client.get(f"/api/v1/tournois/{tournoi['id']}/classement")
        assert classement.status_code == 200
        corps = classement.json()
        assert corps["tournoi_id"] == tournoi["id"]
        assert [
            (ligne["nom"], ligne["rang"], ligne["total"], ligne["cible"])
            for ligne in corps["lignes"]
        ] == [
            ("Martin", 1, 19, 3),
            ("Durand", 2, 8, None),
        ]
        # Le classement porte le signal « club inconnu » (E02US002, ADR-0014) : c'est la seule
        # surface où un archer inscrit apparaît, donc le seul endroit où l'anomalie se voit.
        assert [(ligne["prenom"], ligne["club_id"]) for ligne in corps["lignes"]] == [
            ("Alice", None),
            ("Bob", None),
        ]


def test_ajouter_archer_tournoi_inconnu_404(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Inscrire dans un tournoi inexistant → 404 (code applicatif typé), une fois authentifié."""
    with TestClient(app_competition) as client:
        connecter_admin(client)
        reponse = client.post(
            "/api/v1/tournois/999/archers",
            json={"nom": "Robin", "prenom": "Jean", "categorie_id": 1},
        )
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"


def test_placer_archer_inconnu_404(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Placer un archer inexistant → 404 avec le code applicatif typé (une fois authentifié)."""
    with TestClient(app_competition) as client:
        connecter_admin(client)
        reponse = client.post("/api/v1/archers/999/placement", json={"cible": 1})
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "archer_introuvable"


def test_score_hors_plage_422(app_competition: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Un score hors de 0-10 → 422 avec le code métier (règle du domaine)."""
    with TestClient(app_competition) as client:
        connecter_admin(client)
        tournoi = client.post(
            "/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14"}
        ).json()
        categorie_id = _creer_categorie(client, tournoi["id"])
        archer = client.post(
            f"/api/v1/tournois/{tournoi['id']}/archers",
            json={"nom": "Robin", "prenom": "Jean", "categorie_id": categorie_id},
        ).json()
        reponse = client.post(f"/api/v1/archers/{archer['id']}/scores", json={"points": 11})
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "score_invalide"


def test_classement_tournoi_inconnu_404(app_competition: FastAPI) -> None:
    """Consulter le classement d'un tournoi inexistant → 404."""
    with TestClient(app_competition) as client:
        reponse = client.get("/api/v1/tournois/999/classement")
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"


def _tournoi_avec_categorie(client: TestClient, nom: str = "Salle 18m") -> tuple[int, int]:
    """Crée un tournoi et une catégorie ; renvoie leurs identifiants."""
    tournoi = client.post("/api/v1/tournois", json={"nom": nom, "date": "2026-03-14"}).json()
    return int(tournoi["id"]), _creer_categorie(client, tournoi["id"])


def test_inscrire_sans_prenom_rend_400(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le prénom est obligatoire au **contrat d'entrée** → 400 Pydantic, avant tout métier."""
    with TestClient(app_competition) as client:
        connecter_admin(client)
        tournoi_id, categorie_id = _tournoi_avec_categorie(client)

        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/archers",
            json={"nom": "Robin", "categorie_id": categorie_id},
        )

    assert reponse.status_code == 400
    assert reponse.json()["code"] == "requete_invalide"


def test_inscrire_avec_un_prenom_vide_rend_422(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un prénom **présent mais vide** passe Pydantic et tombe sur la règle du domaine → 422."""
    with TestClient(app_competition) as client:
        connecter_admin(client)
        tournoi_id, categorie_id = _tournoi_avec_categorie(client)

        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/archers",
            json={"nom": "Robin", "prenom": "   ", "categorie_id": categorie_id},
        )

    assert reponse.status_code == 422
    assert reponse.json()["code"] == "prenom_archer_invalide"


def test_inscrire_avec_une_categorie_d_un_autre_tournoi_rend_409(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Conflit inter-agrégats → 409 (`categorie_hors_tournoi`), comme `blason_hors_tournoi`."""
    with TestClient(app_competition) as client:
        connecter_admin(client)
        tournoi_id, _ = _tournoi_avec_categorie(client)
        _, categorie_etrangere = _tournoi_avec_categorie(client, "Trophée d'hiver")

        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/archers",
            json={"nom": "Robin", "prenom": "Jean", "categorie_id": categorie_etrangere},
        )

    assert reponse.status_code == 409
    assert reponse.json()["code"] == "categorie_hors_tournoi"


def test_inscrire_un_homonyme_rend_409_puis_passe_sur_confirmation(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le protocole en **deux temps** d'E02US002, bout en bout : signaler, puis laisser passer.

    Le 409 n'est pas un refus définitif — c'est la question posée à l'admin. Le second appel,
    porteur de la réponse, inscrit le père **et** le fils.
    """
    with TestClient(app_competition) as client:
        connecter_admin(client)
        tournoi_id, categorie_id = _tournoi_avec_categorie(client)
        corps = {"nom": "Dupont", "prenom": "Jean", "categorie_id": categorie_id}

        premier = client.post(f"/api/v1/tournois/{tournoi_id}/archers", json=corps)
        assert premier.status_code == 201, premier.text

        signale = client.post(f"/api/v1/tournois/{tournoi_id}/archers", json=corps)
        assert signale.status_code == 409
        assert signale.json()["code"] == "homonyme_archer"

        confirme = client.post(
            f"/api/v1/tournois/{tournoi_id}/archers", json={**corps, "autoriser_homonyme": True}
        )
        assert confirme.status_code == 201, confirme.text
        assert confirme.json()["id"] != premier.json()["id"]


def _inscrire(client: TestClient, tournoi_id: int, categorie_id: int, nom: str, prenom: str) -> int:
    """Inscrit un archer et renvoie son identifiant."""
    reponse = client.post(
        f"/api/v1/tournois/{tournoi_id}/archers",
        json={"nom": nom, "prenom": prenom, "categorie_id": categorie_id},
    )
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def test_lister_archers_trie_et_reste_ouvert_en_lecture(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La liste des inscrits est triée par nom puis prénom, et lisible sans session (E02US003)."""
    with TestClient(app_competition) as client:
        connecter_admin(client)
        tournoi_id, categorie_id = _tournoi_avec_categorie(client)
        _inscrire(client, tournoi_id, categorie_id, "Zola", "Émile")
        _inscrire(client, tournoi_id, categorie_id, "Élan", "Bruno")
        _inscrire(client, tournoi_id, categorie_id, "Dupont", "Paul")
        _inscrire(client, tournoi_id, categorie_id, "Dupont", "Anne")
        del client.headers["Authorization"]

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/archers")

    assert reponse.status_code == 200, reponse.text
    assert [(a["nom"], a["prenom"]) for a in reponse.json()] == [
        ("Dupont", "Anne"),
        ("Dupont", "Paul"),
        ("Élan", "Bruno"),
        ("Zola", "Émile"),
    ]


def test_lister_archers_tournoi_inconnu_404(app_competition: FastAPI) -> None:
    """Lister les archers d'un tournoi inexistant → 404, pas une liste vide."""
    with TestClient(app_competition) as client:
        reponse = client.get("/api/v1/tournois/999/archers")
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"


def test_modifier_archer_corrige_les_champs_et_diffuse(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """PUT remplace les quatre champs éditables et diffuse l'écriture aux abonnés (E02US003)."""
    with TestClient(app_competition) as client, client.websocket_connect("/ws") as ws:
        assert ws.receive_json()["type"] == "connected"
        connecter_admin(client)
        tournoi_id, categorie_id = _tournoi_avec_categorie(client)
        club = client.post("/api/v1/clubs", json={"nom": "Arc Club Rennes"}).json()
        archer_id = _inscrire(client, tournoi_id, categorie_id, "Robain", "Jean")
        # Quatre écritures ont précédé (tournoi, catégorie, club, inscription) : on consomme
        # leurs quatre événements **nommément**. Un drainage « jusqu'au premier » en laisserait
        # trois en file, et l'assertion d'après lirait l'événement du tournoi en croyant tenir
        # celui du PUT — elle passerait au vert sans rien prouver.
        for _ in range(4):
            assert ws.receive_json()["type"] == "donnees_modifiees"

        reponse = client.put(
            f"/api/v1/archers/{archer_id}",
            json={
                "nom": "Robin",
                "prenom": "Jeanne",
                "categorie_id": categorie_id,
                "club_id": club["id"],
            },
        )
        assert ws.receive_json()["type"] == "donnees_modifiees"

    assert reponse.status_code == 200, reponse.text
    assert (reponse.json()["nom"], reponse.json()["prenom"]) == ("Robin", "Jeanne")
    assert reponse.json()["club_id"] == club["id"]


def test_modifier_archer_inconnu_404(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Éditer un archer inexistant → 404 avec le code applicatif typé."""
    with TestClient(app_competition) as client:
        connecter_admin(client)
        tournoi_id, categorie_id = _tournoi_avec_categorie(client)
        reponse = client.put(
            "/api/v1/archers/999",
            json={"nom": "Robin", "prenom": "Jean", "categorie_id": categorie_id},
        )
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "archer_introuvable"


def test_modifier_archer_homonyme_409_puis_passe_sur_confirmation(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le protocole en deux temps d'ADR-0015 vaut aussi à l'édition (E02US003)."""
    with TestClient(app_competition) as client:
        connecter_admin(client)
        tournoi_id, categorie_id = _tournoi_avec_categorie(client)
        _inscrire(client, tournoi_id, categorie_id, "Dupont", "Jean")
        autre_id = _inscrire(client, tournoi_id, categorie_id, "Martin", "Alice")
        corps = {"nom": "Dupont", "prenom": "Jean", "categorie_id": categorie_id}

        signale = client.put(f"/api/v1/archers/{autre_id}", json=corps)
        assert signale.status_code == 409
        assert signale.json()["code"] == "homonyme_archer"

        confirme = client.put(
            f"/api/v1/archers/{autre_id}", json={**corps, "autoriser_homonyme": True}
        )

    assert confirme.status_code == 200, confirme.text
    assert confirme.json()["prenom"] == "Jean"


def test_modifier_categorie_d_un_archer_engage_409_puis_passe_sur_confirmation(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Changer la catégorie d'un archer qui a tiré est signalé, puis accepté (CA E02US003)."""
    with TestClient(app_competition) as client:
        connecter_admin(client)
        tournoi_id, categorie_id = _tournoi_avec_categorie(client)
        autre_categorie = client.post(
            f"/api/v1/tournois/{tournoi_id}/categories", json={"libelle": "Senior 2 H"}
        ).json()
        archer_id = _inscrire(client, tournoi_id, categorie_id, "Robin", "Jean")
        client.post(f"/api/v1/archers/{archer_id}/scores", json={"points": 9})
        corps = {"nom": "Robin", "prenom": "Jean", "categorie_id": autre_categorie["id"]}

        signale = client.put(f"/api/v1/archers/{archer_id}", json=corps)
        assert signale.status_code == 409
        assert signale.json()["code"] == "changement_categorie_archer_engage"

        confirme = client.put(
            f"/api/v1/archers/{archer_id}",
            json={**corps, "autoriser_changement_categorie": True},
        )

    assert confirme.status_code == 200, confirme.text
    assert confirme.json()["categorie_id"] == autre_categorie["id"]


def test_supprimer_archer_rend_204_et_le_retire_du_classement(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """DELETE désinscrit un archer ni placé ni engagé → 204, et il quitte le classement."""
    with TestClient(app_competition) as client:
        connecter_admin(client)
        tournoi_id, categorie_id = _tournoi_avec_categorie(client)
        archer_id = _inscrire(client, tournoi_id, categorie_id, "Robin", "Jean")

        reponse = client.delete(f"/api/v1/archers/{archer_id}")
        restants = client.get(f"/api/v1/tournois/{tournoi_id}/archers").json()

    assert reponse.status_code == 204, reponse.text
    assert restants == []


def test_supprimer_archer_place_rend_409(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Refus définitif tant que l'archer occupe une cible (CA E02US003)."""
    with TestClient(app_competition) as client:
        connecter_admin(client)
        tournoi_id, categorie_id = _tournoi_avec_categorie(client)
        archer_id = _inscrire(client, tournoi_id, categorie_id, "Robin", "Jean")
        client.post(f"/api/v1/archers/{archer_id}/placement", json={"cible": 3})

        reponse = client.delete(f"/api/v1/archers/{archer_id}")

    assert reponse.status_code == 409
    assert reponse.json()["code"] == "archer_engage"


def test_supprimer_archer_avec_scores_rend_409_pas_500(
    app_competition: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le service refuse **avant** la base : la FK sans cascade (DETTE-001) rendrait un 500.

    C'est l'intérêt du contrôle applicatif : sans lui, `session.delete` échouerait sur
    `score.archer_id` et le bénévole recevrait « erreur interne » au lieu d'une consigne.
    """
    with TestClient(app_competition) as client:
        connecter_admin(client)
        tournoi_id, categorie_id = _tournoi_avec_categorie(client)
        archer_id = _inscrire(client, tournoi_id, categorie_id, "Robin", "Jean")
        client.post(f"/api/v1/archers/{archer_id}/scores", json={"points": 9})

        reponse = client.delete(f"/api/v1/archers/{archer_id}")

    assert reponse.status_code == 409
    assert reponse.json()["code"] == "archer_engage"


@pytest.mark.parametrize(
    ("methode", "chemin", "corps"),
    [
        ("put", "/api/v1/archers/1", {"nom": "Robin", "prenom": "Jean", "categorie_id": 1}),
        ("delete", "/api/v1/archers/1", None),
    ],
)
def test_action_admin_sur_archer_refusee_sans_session(
    app_competition: FastAPI, methode: str, chemin: str, corps: dict[str, object] | None
) -> None:
    """Éditer et désinscrire sont des écritures : sans session admin → 401 (E10US001)."""
    with TestClient(app_competition) as client:
        reponse = client.request(methode.upper(), chemin, json=corps)
    assert reponse.status_code == 401
    assert reponse.json()["code"] == "non_authentifie"
