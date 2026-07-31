"""Test bout-en-bout de l'API départs (E02US004, ADR-0017).

Traverse toutes les couches — DTO Pydantic → file d'écriture → service → repository → DB — sur les
routes imbriquées `/api/v1/tournois/{id}/departs`, et vérifie le mapping des erreurs typées :
- création (numéro attribué par le serveur) puis listing trié ;
- édition (PUT) du tarif et de l'horaire ; suppression (204) ;
- tarif hors plage → 422 (`DomainError`) ; tarif non entier → 400 (validation) ;
- horaire `HH:MM` (E02US010) : format libre → 422 (`horaire_depart_invalide`) ; champ **manquant**
  → 400 (validation du DTO — l'horaire est obligatoire) ;
- dernier départ d'un tournoi non-brouillon → 409 (`dernier_depart_non_supprimable`, E02US010) ;
- tournoi inconnu → 404 ; départ d'un autre tournoi → 404 ;
- garde admin : écriture sans session → 401 ;
- cycle de vie (E12US008) : le DTO expose `etat`, `ouvert` sur un créneau sans score, et les
  paramètres `confirme_cycle` sont acceptés (non-régression sur un créneau ouvert).

Le garde-fou de cycle **lancé/clos** (409 `depart_en_cours_non_confirme` + `details`) est couvert au
niveau **service** (`test_service_departs.py`, faux lecteur d'avancement) : l'exercer ici imposerait
d'amorcer un tir réel (gabarit + barème + placement + saisie + validation de toutes les volées), un
montage disproportionné pour ce que le service teste déjà — le mapping générique
`ApplicationError → 409 + details` est, lui, prouvé par `ReplacementNonConfirme` (E12US007).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bootstrap.composition import create_app
from tests.base_migree import preparer_base
from tests.conftest import ConnecterAdmin

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _migrer(url: str) -> None:
    preparer_base(url)


@pytest.fixture
def app_departs(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _creer_tournoi(client: TestClient) -> int:
    """Crée un tournoi et renvoie son identifiant (l'appelant est déjà connecté admin)."""
    reponse = client.post("/api/v1/tournois", json={"nom": "Salle 18m", "date": "2026-03-14"})
    assert reponse.status_code == 201
    tournoi_id = reponse.json()["id"]
    assert isinstance(tournoi_id, int)
    return tournoi_id


def test_creer_puis_lister_les_departs(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """POST crée les créneaux (numéros 1 puis 2, attribués par le serveur) ; GET les liste triés."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)

        premier = client.post(
            f"/api/v1/tournois/{tid}/departs",
            json={"tarif_centimes": 810, "horaire": "09:00"},
        )
        assert premier.status_code == 201
        corps = premier.json()
        assert corps["numero"] == 1
        assert corps["tarif_centimes"] == 810
        assert corps["horaire"] == "09:00"
        assert corps["tournoi_id"] == tid
        assert isinstance(corps["id"], int)

        second = client.post(
            f"/api/v1/tournois/{tid}/departs",
            json={"tarif_centimes": 1000, "horaire": "10:00"},
        )
        assert second.json()["numero"] == 2
        assert second.json()["horaire"] == "10:00"

        liste = client.get(f"/api/v1/tournois/{tid}/departs").json()
        assert [d["numero"] for d in liste] == [1, 2]


def test_creer_avec_quota_puis_le_restituer(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le quota fourni traverse toutes les couches et revient dans la réponse ; absent = `null`."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)

        avec = client.post(
            f"/api/v1/tournois/{tid}/departs",
            json={"tarif_centimes": 810, "horaire": "09:00", "quota": 20},
        )
        assert avec.status_code == 201
        assert avec.json()["quota"] == 20

        sans = client.post(
            f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": 810, "horaire": "09:00"}
        )
        assert sans.json()["quota"] is None


def test_creer_quota_nul_erreur_domaine(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un quota ≤ 0 est une valeur invalide → 422 métier (validé au domaine, comme le tarif)."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)
        reponse = client.post(
            f"/api/v1/tournois/{tid}/departs",
            json={"tarif_centimes": 810, "horaire": "09:00", "quota": 0},
        )
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "quota_depart_invalide"


def test_creer_quota_non_entier_erreur_400(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un quota décimal est rejeté par le DTO (le type) avant le domaine → 400."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)
        reponse = client.post(
            f"/api/v1/tournois/{tid}/departs",
            json={"tarif_centimes": 810, "horaire": "09:00", "quota": 2.5},
        )
    assert reponse.status_code == 400
    assert reponse.json()["code"] == "requete_invalide"


def test_modifier_remplace_le_quota_et_l_omission_le_retire(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """PUT remplace le quota ; un corps qui l'omet le **retire** (remplacement complet, CA)."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)
        cree = client.post(
            f"/api/v1/tournois/{tid}/departs",
            json={"tarif_centimes": 810, "horaire": "09:00", "quota": 20},
        ).json()

        pose = client.put(
            f"/api/v1/tournois/{tid}/departs/{cree['id']}",
            json={"tarif_centimes": 810, "horaire": "09:00", "quota": 30},
        )
        assert pose.json()["quota"] == 30

        # Corps sans `quota` : remplacement complet → le plafond est retiré (revient à null).
        retire = client.put(
            f"/api/v1/tournois/{tid}/departs/{cree['id']}",
            json={"tarif_centimes": 810, "horaire": "09:00"},
        )
        assert retire.json()["quota"] is None


def test_le_depart_expose_son_etat_ouvert(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un créneau sans aucun score est **ouvert** (E12US008) — à la création comme à la liste.

    L'état est dérivé (jamais stocké) : un créneau qui vient de naître, sans placement ni série, est
    ouvert par construction ; il le reste dans la liste tant que personne n'a tiré.
    """
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)

        cree = client.post(
            f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": 810, "horaire": "09:00"}
        )
        assert cree.json()["etat"] == "ouvert"

        liste = client.get(f"/api/v1/tournois/{tid}/departs").json()
        assert [d["etat"] for d in liste] == ["ouvert"]


def test_editer_et_supprimer_un_creneau_ouvert_ignorent_confirme_cycle(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Sur un créneau **ouvert** (aucun tir), `confirme_cycle` est sans objet : PUT/DELETE passent.

    Non-régression : le garde-fou de cycle ne se déclenche que sur un créneau lancé/clos. Le
    paramètre est accepté (câblé) mais inopérant ici — l'édition et la suppression restent libres.
    """
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)
        depart_id = client.post(
            f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": 810, "horaire": "09:00"}
        ).json()["id"]

        modif = client.put(
            f"/api/v1/tournois/{tid}/departs/{depart_id}",
            json={"tarif_centimes": 1250, "horaire": "09:00"},
        )
        assert modif.status_code == 200
        assert modif.json()["etat"] == "ouvert"

        suppr = client.delete(
            f"/api/v1/tournois/{tid}/departs/{depart_id}",
            params={"confirme_cycle": True},
        )
        assert suppr.status_code == 204


def test_creer_tarif_negatif_erreur_domaine(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un tarif négatif → 422 avec le code métier."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)
        reponse = client.post(
            f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": -1, "horaire": "09:00"}
        )
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "tarif_depart_invalide"


def test_creer_tarif_non_entier_erreur_400(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un tarif en euros décimaux (8.10) est rejeté par le DTO : l'API compte en centimes."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)
        reponse = client.post(
            f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": 8.10, "horaire": "09:00"}
        )
    assert reponse.status_code == 400
    assert reponse.json()["code"] == "requete_invalide"


def test_creer_horaire_libre_erreur_domaine(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un horaire non `HH:MM` (« 9h00 ») traverse le DTO (c'est bien un `str`) et est refusé **au
    domaine** → 422 `horaire_depart_invalide` (E02US010)."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)
        reponse = client.post(
            f"/api/v1/tournois/{tid}/departs",
            json={"tarif_centimes": 810, "horaire": "9h00"},
        )
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "horaire_depart_invalide"


def test_creer_horaire_manquant_erreur_400(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """L'horaire est **obligatoire** : un corps qui l'omet est malformé à la frontière → 400.

    Distinct du 422 ci-dessus : le champ absent est refusé par le **DTO** (validation Pydantic)
    avant que le domaine ne juge le format — c'est le versant « 400 si malformée » du CA E02US010.
    """
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)
        reponse = client.post(f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": 810})
    assert reponse.status_code == 400
    assert reponse.json()["code"] == "requete_invalide"


def test_creer_sur_tournoi_inconnu_404(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Créer un départ sur un tournoi inexistant → 404 typé."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        reponse = client.post(
            "/api/v1/tournois/999/departs", json={"tarif_centimes": 810, "horaire": "09:00"}
        )
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"


def test_modifier_un_depart(app_departs: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """PUT met à jour tarif et horaire ; le numéro ne bouge pas."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)
        cree = client.post(
            f"/api/v1/tournois/{tid}/departs",
            json={"tarif_centimes": 810, "horaire": "09:00"},
        ).json()

        modif = client.put(
            f"/api/v1/tournois/{tid}/departs/{cree['id']}",
            json={"tarif_centimes": 1250, "horaire": "14:00"},
        )
        assert modif.status_code == 200
        corps = modif.json()
        assert corps["numero"] == 1
        assert corps["tarif_centimes"] == 1250
        assert corps["horaire"] == "14:00"


def test_modifier_depart_d_un_autre_tournoi_404(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Éditer un départ via un autre tournoi → 404 `depart_introuvable` (pas de fuite du voisin)."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid_a = _creer_tournoi(client)
        autre = client.post("/api/v1/tournois", json={"nom": "Autre", "date": "2026-03-15"}).json()
        cree = client.post(
            f"/api/v1/tournois/{tid_a}/departs", json={"tarif_centimes": 810, "horaire": "09:00"}
        ).json()

        reponse = client.put(
            f"/api/v1/tournois/{autre['id']}/departs/{cree['id']}",
            json={"tarif_centimes": 900, "horaire": "09:00"},
        )
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "depart_introuvable"


def test_supprimer_un_depart(app_departs: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """DELETE → 204 ; le créneau disparaît de la liste."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)
        cree = client.post(
            f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": 810, "horaire": "09:00"}
        ).json()

        assert client.delete(f"/api/v1/tournois/{tid}/departs/{cree['id']}").status_code == 204
        assert client.get(f"/api/v1/tournois/{tid}/departs").json() == []


def test_supprimer_le_dernier_depart_d_un_tournoi_engage_409(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le dernier créneau d'un tournoi passé `prêt` ne se supprime pas → 409 (E02US010).

    Bout-en-bout du couple de gardes : le tournoi passe `prêt` (ce qui exige ≥ 1 départ), puis
    retirer son unique créneau est refusé — l'invariant « ≥ 1 départ dès qu'on quitte le brouillon »
    tient jusqu'à la suppression.
    """
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)
        depart_id = client.post(
            f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": 810, "horaire": "09:00"}
        ).json()["id"]

        pret = client.post(f"/api/v1/tournois/{tid}/vers-pret")
        assert pret.status_code == 200

        rejet = client.delete(f"/api/v1/tournois/{tid}/departs/{depart_id}")
        assert rejet.status_code == 409
        assert rejet.json()["code"] == "dernier_depart_non_supprimable"
        # Le créneau survit : sans lui le tournoi prêt n'aurait plus rien à jouer.
        assert [d["id"] for d in client.get(f"/api/v1/tournois/{tid}/departs").json()] == [
            depart_id
        ]


def test_ecriture_sans_session_admin_401(app_departs: FastAPI) -> None:
    """Créer un départ sans être connecté admin → 401 (route protégée)."""
    with TestClient(app_departs) as client:
        reponse = client.post(
            "/api/v1/tournois/1/departs", json={"tarif_centimes": 810, "horaire": "09:00"}
        )
    assert reponse.status_code == 401


def _inscrire_un_archer_sur(client: TestClient, tid: int, depart_id: int) -> int:
    """Monte une catégorie + un archer et l'inscrit sur `depart_id` ; renvoie l'id d'inscription."""
    categorie_id = client.post(
        f"/api/v1/tournois/{tid}/categories", json={"libelle": "Senior 1 H"}
    ).json()["id"]
    archer_id = client.post(
        f"/api/v1/tournois/{tid}/archers",
        json={"nom": "Martin", "prenom": "Alice", "categorie_id": categorie_id},
    ).json()["id"]
    return int(
        client.post(
            f"/api/v1/archers/{archer_id}/inscriptions", json={"depart_id": depart_id}
        ).json()["id"]
    )


def test_supprimer_depart_avec_inscriptions_409(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Supprimer un créneau à inscriptions → 409 `depart_avec_inscriptions` (garde-fou E02US009)."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)
        depart_id = client.post(
            f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": 810, "horaire": "09:00"}
        ).json()["id"]
        _inscrire_un_archer_sur(client, tid, depart_id)

        rejet = client.delete(f"/api/v1/tournois/{tid}/departs/{depart_id}")
        assert rejet.status_code == 409
        assert rejet.json()["code"] == "depart_avec_inscriptions"
        # Rien détruit : le créneau survit tant que l'admin n'a pas confirmé.
        assert [d["id"] for d in client.get(f"/api/v1/tournois/{tid}/departs").json()] == [
            depart_id
        ]


def test_supprimer_depart_avec_inscriptions_confirme_204(
    app_departs: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Avec `autoriser_suppression_inscrits=true`, l'admin confirme : 204, le créneau part."""
    with TestClient(app_departs) as client:
        connecter_admin(client)
        tid = _creer_tournoi(client)
        depart_id = client.post(
            f"/api/v1/tournois/{tid}/departs", json={"tarif_centimes": 810, "horaire": "09:00"}
        ).json()["id"]
        _inscrire_un_archer_sur(client, tid, depart_id)

        confirme = client.delete(
            f"/api/v1/tournois/{tid}/departs/{depart_id}",
            params={"autoriser_suppression_inscrits": True},
        )
        assert confirme.status_code == 204
        assert client.get(f"/api/v1/tournois/{tid}/departs").json() == []
