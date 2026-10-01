"""Test bout-en-bout de l'API des équipes (E13US002) : DTO → file → service → repository → base.

Couvre le contrat consommé par l'écran « Équipes », le mapping des erreurs à la frontière, et les
chemins qui suppriment ou fusionnent un archer membre (CA 6) sur une vraie base.
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


@pytest.fixture
def app_equipes(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    preparer_base(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


@pytest.fixture
def client(app_equipes: FastAPI, connecter_admin: ConnecterAdmin) -> Iterator[TestClient]:
    with TestClient(app_equipes) as client:
        connecter_admin(client)
        yield client


def _ok(reponse: Any, statut: int = 200) -> Any:
    assert reponse.status_code == statut, reponse.text
    return reponse.json() if statut != 204 else None


def _tournoi(client: TestClient) -> int:
    corps = {"nom": "Salle 18m", "date": "2026-11-14"}
    return int(_ok(client.post("/api/v1/tournois", json=corps), 201)["id"])


def _categorie(client: TestClient, tournoi_id: int, libelle: str, arme: str, sexe: str) -> int:
    corps = {"libelle": libelle, "arme": arme, "sexe": sexe, "hauteur_cm": 130}
    reponse = client.post(f"/api/v1/tournois/{tournoi_id}/categories", json=corps)
    return int(_ok(reponse, 201)["id"])


def _archer(client: TestClient, tournoi_id: int, prenom: str, categorie_id: int) -> int:
    corps = {"nom": "Tell", "prenom": prenom, "categorie_id": categorie_id}
    reponse = client.post(f"/api/v1/tournois/{tournoi_id}/archers", json=corps)
    return int(_ok(reponse, 201)["id"])


def _equipe(
    client: TestClient,
    tournoi_id: int,
    nom: str,
    type: str = "standard",
    effectif: int | None = None,
) -> dict[str, Any]:
    corps = {"nom": nom, "type": type, "effectif_attendu": effectif}
    resultat: dict[str, Any] = _ok(
        client.post(f"/api/v1/tournois/{tournoi_id}/equipes", json=corps), 201
    )
    return resultat


def _ajouter(client: TestClient, tournoi_id: int, equipe_id: int, archer_id: int) -> Any:
    return client.post(
        f"/api/v1/tournois/{tournoi_id}/equipes/{equipe_id}/membres", json={"archer_id": archer_id}
    )


def test_creer_rend_le_contrat_complet(client: TestClient) -> None:
    tournoi_id = _tournoi(client)
    equipe = _equipe(client, tournoi_id, "  Les Archers ")
    assert equipe == {
        "id": equipe["id"],
        "tournoi_id": tournoi_id,
        "nom": "Les Archers",
        "type": "standard",
        "effectif_attendu": 3,
        "membres": [],
        "conforme": False,
        "ecarts": ["effectif_insuffisant"],
    }


def test_composer_une_equipe_mixte_conforme_puis_la_lister(client: TestClient) -> None:
    tournoi_id = _tournoi(client)
    clh = _categorie(client, tournoi_id, "S1 H CL", "CL", "H")
    clf = _categorie(client, tournoi_id, "S1 F CL", "CL", "F")
    guillaume = _archer(client, tournoi_id, "Guillaume", clh)
    lucie = _archer(client, tournoi_id, "Lucie", clf)
    equipe = _equipe(client, tournoi_id, "Le Duo", "mixte")
    _ok(_ajouter(client, tournoi_id, equipe["id"], guillaume))
    apres = _ok(_ajouter(client, tournoi_id, equipe["id"], lucie))
    assert apres["membres"] == [
        {"archer_id": guillaume, "nom": "Tell", "prenom": "Guillaume", "categorie": "S1 H CL"},
        {"archer_id": lucie, "nom": "Tell", "prenom": "Lucie", "categorie": "S1 F CL"},
    ]
    assert (apres["conforme"], apres["ecarts"]) == (True, [])
    _equipe(client, tournoi_id, "Azur")
    liste = _ok(client.get(f"/api/v1/tournois/{tournoi_id}/equipes"))
    assert [e["nom"] for e in liste] == ["Azur", "Le Duo"]


def test_modifier_retirer_et_supprimer(client: TestClient) -> None:
    tournoi_id = _tournoi(client)
    clh = _categorie(client, tournoi_id, "S1 H CL", "CL", "H")
    guillaume = _archer(client, tournoi_id, "Guillaume", clh)
    equipe = _equipe(client, tournoi_id, "Les Archers")
    base = f"/api/v1/tournois/{tournoi_id}/equipes/{equipe['id']}"
    _ok(_ajouter(client, tournoi_id, equipe["id"], guillaume))
    modifiee = _ok(
        client.put(base, json={"nom": "Les Flèches", "type": "standard", "effectif_attendu": 1})
    )
    assert (modifiee["nom"], modifiee["effectif_attendu"], modifiee["conforme"]) == (
        "Les Flèches",
        1,
        True,
    )
    retiree = _ok(client.delete(f"{base}/membres/{guillaume}"))
    assert retiree["membres"] == []
    _ok(client.delete(base), 204)
    assert _ok(client.get(f"/api/v1/tournois/{tournoi_id}/equipes")) == []
    archers = _ok(client.get(f"/api/v1/tournois/{tournoi_id}/archers"))
    assert [a["id"] for a in archers] == [guillaume]


def test_les_refus_au_format_d_erreur(client: TestClient) -> None:
    tournoi_id = _tournoi(client)
    voisin = _tournoi(client)
    clh = _categorie(client, tournoi_id, "S1 H CL", "CL", "H")
    guillaume = _archer(client, tournoi_id, "Guillaume", clh)
    premiere = _equipe(client, tournoi_id, "Les Archers")
    seconde = _equipe(client, tournoi_id, "Les Flèches")
    _ok(_ajouter(client, tournoi_id, premiere["id"], guillaume))

    doublon = client.post(
        f"/api/v1/tournois/{tournoi_id}/equipes", json={"nom": "les archers", "type": "mixte"}
    )
    assert (doublon.status_code, doublon.json()["code"]) == (409, "nom_equipe_deja_pris")
    conflit = _ajouter(client, tournoi_id, seconde["id"], guillaume)
    assert (conflit.status_code, conflit.json()["code"]) == (409, "archer_deja_en_equipe")
    assert "Les Archers" in conflit.json()["message"]
    etranger = _ajouter(client, voisin, _equipe(client, voisin, "V")["id"], guillaume)
    assert (etranger.status_code, etranger.json()["code"]) == (409, "archer_hors_tournoi")
    ailleurs = client.delete(f"/api/v1/tournois/{voisin}/equipes/{premiere['id']}")
    assert (ailleurs.status_code, ailleurs.json()["code"]) == (404, "equipe_introuvable")
    inconnu = client.get("/api/v1/tournois/999/equipes")
    assert (inconnu.status_code, inconnu.json()["code"]) == (404, "tournoi_introuvable")
    vide = client.post(f"/api/v1/tournois/{tournoi_id}/equipes", json={"nom": " ", "type": "mixte"})
    assert (vide.status_code, vide.json()["code"]) == (422, "nom_equipe_invalide")
    nul = client.post(
        f"/api/v1/tournois/{tournoi_id}/equipes",
        json={"nom": "Zéro", "type": "mixte", "effectif_attendu": 0},
    )
    assert (nul.status_code, nul.json()["code"]) == (422, "effectif_equipe_invalide")
    deja = _ajouter(client, tournoi_id, premiere["id"], guillaume)
    assert (deja.status_code, deja.json()["code"]) == (422, "archer_deja_membre")
    type_inconnu = client.post(
        f"/api/v1/tournois/{tournoi_id}/equipes", json={"nom": "X", "type": "relais"}
    )
    assert type_inconnu.status_code == 400


def test_l_api_exige_une_session_admin(app_equipes: FastAPI) -> None:
    with TestClient(app_equipes) as anonyme:
        assert anonyme.get("/api/v1/tournois/1/equipes").status_code == 401


def test_supprimer_un_archer_membre_le_signale_puis_le_retire_de_l_equipe(
    client: TestClient,
) -> None:
    """CA 6 de bout en bout : signalement nommant l'équipe, puis retrait — l'équipe subsiste."""
    tournoi_id = _tournoi(client)
    clh = _categorie(client, tournoi_id, "S1 H CL", "CL", "H")
    guillaume = _archer(client, tournoi_id, "Guillaume", clh)
    walter = _archer(client, tournoi_id, "Walter", clh)
    equipe = _equipe(client, tournoi_id, "Les Archers")
    _ok(_ajouter(client, tournoi_id, equipe["id"], guillaume))
    _ok(_ajouter(client, tournoi_id, equipe["id"], walter))
    signale = client.delete(f"/api/v1/archers/{guillaume}")
    assert (signale.status_code, signale.json()["code"]) == (409, "archer_engage")
    assert "« Les Archers »" in signale.json()["message"]
    _ok(client.delete(f"/api/v1/archers/{guillaume}?autoriser_suppression_engage=true"), 204)
    (restante,) = _ok(client.get(f"/api/v1/tournois/{tournoi_id}/equipes"))
    assert [m["archer_id"] for m in restante["membres"]] == [walter]


def test_fusionner_transfere_l_appartenance_ou_refuse_deux_equipes_du_meme_type(
    client: TestClient,
) -> None:
    tournoi_id = _tournoi(client)
    clh = _categorie(client, tournoi_id, "S1 H CL", "CL", "H")
    gagnant = _archer(client, tournoi_id, "Guillaume", clh)
    perdant = _archer(client, tournoi_id, "Guilaume", clh)
    autre = _archer(client, tournoi_id, "Walter", clh)
    standard = _equipe(client, tournoi_id, "Les Archers")
    rivale = _equipe(client, tournoi_id, "Les Flèches")
    mixte = _equipe(client, tournoi_id, "Le Duo", "mixte")
    _ok(_ajouter(client, tournoi_id, standard["id"], gagnant))
    _ok(_ajouter(client, tournoi_id, rivale["id"], perdant))
    refus = client.post(f"/api/v1/archers/{gagnant}/fusionner", json={"perdant_id": perdant})
    assert (refus.status_code, refus.json()["code"]) == (409, "fusion_archers_en_equipes")
    assert "Les Archers" in refus.json()["message"] and "Les Flèches" in refus.json()["message"]

    base = f"/api/v1/tournois/{tournoi_id}/equipes"
    _ok(client.delete(f"{base}/{rivale['id']}/membres/{perdant}"))
    _ok(_ajouter(client, tournoi_id, standard["id"], perdant))
    _ok(_ajouter(client, tournoi_id, mixte["id"], perdant))
    _ok(_ajouter(client, tournoi_id, mixte["id"], autre))
    _ok(client.post(f"/api/v1/archers/{gagnant}/fusionner", json={"perdant_id": perdant}))
    par_nom = {e["nom"]: [m["archer_id"] for m in e["membres"]] for e in _ok(client.get(base))}
    assert par_nom["Les Archers"] == [gagnant]
    assert par_nom["Le Duo"] == [gagnant, autre]
