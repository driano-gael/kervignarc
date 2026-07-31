"""Test bout-en-bout de l'API de la séquence de phases (E05US001).

Traverse toutes les couches — DTO Pydantic → file d'écriture → service → repository → DB — et
vérifie le **mapping des erreurs typées** à la frontière : composition (ajout/liste/édition),
réordonnancement, suppression, cycle de vie, lecture publique / écritures admin (401), tournoi ou
phase inconnus (404), cohérence de séquence (422), conflits d'état (409), corps invalide (400).
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
def app_phases(tmp_path: Path) -> Iterator[FastAPI]:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _creer_tournoi(client: TestClient) -> int:
    reponse = client.post("/api/v1/tournois", json={"nom": "Kervignarc", "date": "2026-03-14"})
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def test_composer_editer_et_lister(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Ajout de deux phases, édition de la source de la seconde, relecture ordonnée."""
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"

        assert client.get(base).json() == []

        qualif = client.post(base, json={"type": "placement", "effectif": 40})
        assert qualif.status_code == 201, qualif.text
        assert qualif.json()["ordre"] == 1

        elim = client.post(base, json={"type": "elimination_directe"})
        assert elim.status_code == 201
        elim_id = elim.json()["id"]

        modifiee = client.put(
            f"{base}/{elim_id}",
            json={
                "type": "elimination_directe",
                "sources": [{"ordre_source": 1, "rang_debut": 1, "rang_fin": 16}],
                "effectif": 16,
            },
        )
        assert modifiee.status_code == 200, modifiee.text
        assert modifiee.json()["sources"] == [
            {
                "ordre_source": 1,
                "nature": "rangs",
                "rang_debut": 1,
                "rang_fin": 16,
                "tour": None,
                "issue": None,
            }
        ]

        phases = client.get(base).json()
        assert [p["ordre"] for p in phases] == [1, 2]
        assert [p["type"] for p in phases] == ["placement", "elimination_directe"]


def test_reordonner(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        p1 = client.post(base, json={"type": "elimination_directe"}).json()
        p2 = client.post(base, json={"type": "placement"}).json()

        reponse = client.post(f"{base}/reordonner", json={"phases": [p2["id"], p1["id"]]})
        assert reponse.status_code == 200, reponse.text
        ordres = {p["id"]: p["ordre"] for p in reponse.json()}
        assert ordres == {p2["id"]: 1, p1["id"]: 2}


def test_supprimer(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        p1 = client.post(base, json={"type": "elimination_directe"}).json()
        client.post(base, json={"type": "placement"})

        assert client.delete(f"{base}/{p1['id']}").status_code == 204

        restantes = client.get(base).json()
        assert [p["type"] for p in restantes] == ["placement"]
        assert restantes[0]["ordre"] == 1  # recompacté


def test_cycle_de_vie(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        phase = client.post(base, json={"type": "elimination_directe"}).json()
        statut_url = f"{base}/{phase['id']}/statut"

        assert (
            client.post(statut_url, json={"transition": "demarrer"}).json()["statut"] == "en_cours"
        )
        assert (
            client.post(statut_url, json={"transition": "mettre_en_pause"}).json()["statut"]
            == "en_pause"
        )
        assert (
            client.post(statut_url, json={"transition": "reprendre"}).json()["statut"] == "en_cours"
        )
        assert (
            client.post(statut_url, json={"transition": "terminer"}).json()["statut"] == "terminee"
        )


def test_transition_illegale_409(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        phase = client.post(base, json={"type": "elimination_directe"}).json()

        reponse = client.post(
            f"{base}/{phase['id']}/statut", json={"transition": "mettre_en_pause"}
        )
        assert reponse.status_code == 409
        assert reponse.json()["code"] == "transition_statut_invalide"


def test_source_incoherente_422(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Une source qui prélève au-delà de l'effectif de sa source → 422 (règle du domaine)."""
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        client.post(base, json={"type": "placement", "effectif": 32})

        reponse = client.post(
            base,
            json={
                "type": "elimination_directe",
                "sources": [{"ordre_source": 1, "rang_debut": 1, "rang_fin": 40}],
            },
        )
        assert reponse.status_code == 422
        assert reponse.json()["code"] == "rangs_source_inexistants"


def test_supprimer_source_referencee_409(
    app_phases: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        source = client.post(base, json={"type": "placement", "effectif": 40}).json()
        conso = client.post(base, json={"type": "elimination_directe"}).json()
        client.put(
            f"{base}/{conso['id']}",
            json={
                "type": "elimination_directe",
                "sources": [{"ordre_source": 1, "rang_debut": 1, "rang_fin": 16}],
                "effectif": 16,
            },
        )

        reponse = client.delete(f"{base}/{source['id']}")
        assert reponse.status_code == 409
        assert reponse.json()["code"] == "phase_source_referencee"


def test_lecture_publique(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        client.post(f"/api/v1/tournois/{tournoi_id}/phases", json={"type": "elimination_directe"})
    with TestClient(app_phases) as anonyme:
        reponse = anonyme.get(f"/api/v1/tournois/{tournoi_id}/phases")
    assert reponse.status_code == 200
    assert len(reponse.json()) == 1


def test_ajouter_sans_jeton_401(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
    with TestClient(app_phases) as anonyme:
        reponse = anonyme.post(
            f"/api/v1/tournois/{tournoi_id}/phases", json={"type": "elimination_directe"}
        )
    assert reponse.status_code == 401
    assert reponse.json()["code"] == "non_authentifie"


def test_ajouter_tournoi_inconnu_404(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_phases) as client:
        connecter_admin(client)
        reponse = client.post("/api/v1/tournois/999/phases", json={"type": "elimination_directe"})
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"


def test_modifier_phase_inconnue_404(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/phases/999",
            json={"type": "placement", "sources": [], "effectif": None},
        )
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "phase_introuvable"


def test_definir_bareme_apres_ajout_place_la_qualification_en_tete(
    app_phases: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Régression bout-en-bout (revue axe D) : ajouter une phase **avant** de définir le barème ne
    crée pas deux « ordre 1 » — la qualification s'insère en tête, l'élimination descend en 2, et la
    composition se poursuit sans blocage 422."""
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        elim = client.post(base, json={"type": "elimination_directe"})
        assert elim.status_code == 201 and elim.json()["ordre"] == 1

        # Définir le barème crée la phase de qualification (via l'écran « Barème & validation »).
        definir = client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 20, "nb_fleches_par_volee": 3},
        )
        assert definir.status_code == 200, definir.text

        phases = client.get(base).json()
        assert [(p["ordre"], p["type"]) for p in phases] == [
            (1, "qualification"),
            (2, "elimination_directe"),
        ]
        # La composition n'est pas bloquée : on peut ajouter une phase de plus.
        suite = client.post(base, json={"type": "placement"})
        assert suite.status_code == 201 and suite.json()["ordre"] == 3


def test_supprimer_la_qualification_409(
    app_phases: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La qualification se gère via le barème : la supprimer par l'API des phases → 409."""
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 20, "nb_fleches_par_volee": 3},
        )
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        qualif = next(p for p in client.get(base).json() if p["type"] == "qualification")

        reponse = client.delete(f"{base}/{qualif['id']}")
        assert reponse.status_code == 409
        assert reponse.json()["code"] == "phase_qualification_non_supprimable"


def test_type_inconnu_400(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Un type hors énumération est rejeté par Pydantic → 400 (corps invalide)."""
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.post(
            f"/api/v1/tournois/{tournoi_id}/phases", json={"type": "poules_magiques"}
        )
    assert reponse.status_code == 400
    assert reponse.json()["code"] == "requete_invalide"


# --- contrat multi-sources à la frontière (E05US010) ---------------------------------------------
# Tests écrits **après** l'implémentation (règle 9 : pas d'oracle en jeu à la frontière), et
# **ajoutés à la revue** : le contrat a changé de forme *et* de vocabulaire sans qu'aucun test ne le
# traverse de bout en bout. Ils figent en particulier les `code` d'erreur que le front lira.


def test_une_phase_se_compose_de_plusieurs_sources_de_natures_differentes(
    app_phases: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le CA cardinal de l'US vu du client : deux prélèvements, deux natures, aller-retour."""
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        client.post(base, json={"type": "elimination_directe", "effectif": 8})

        reponse = client.post(
            base,
            json={
                "type": "placement",
                "sources": [
                    {"ordre_source": 1, "nature": "issue_de_tour", "tour": 2, "issue": "perdants"},
                    {"ordre_source": 1, "nature": "reste"},
                ],
            },
        )
        assert reponse.status_code == 201, reponse.text

        relue = next(p for p in client.get(base).json() if p["ordre"] == 2)
        assert [s["nature"] for s in relue["sources"]] == ["issue_de_tour", "reste"]
        assert (relue["sources"][0]["tour"], relue["sources"][0]["issue"]) == (2, "perdants")
        # Les champs étrangers à la nature ne sont pas inventés à la relecture.
        assert relue["sources"][1]["rang_fin"] is None


def test_une_plage_a_fin_ouverte_fait_l_aller_retour(
    app_phases: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`rang_fin: null` est une **valeur**, pas un champ manquant : il doit revenir tel quel."""
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        client.post(base, json={"type": "elimination_directe", "effectif": 120})

        reponse = client.post(
            base,
            json={
                "type": "placement",
                "sources": [{"ordre_source": 1, "rang_debut": 33, "rang_fin": None}],
            },
        )
        assert reponse.status_code == 201, reponse.text
        assert reponse.json()["sources"][0]["rang_fin"] is None


def test_une_source_mal_formee_rend_422_avec_son_code(
    app_phases: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un champ étranger à la nature est **refusé**, jamais avalé (ADR-0061 §4)."""
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        client.post(base, json={"type": "elimination_directe", "effectif": 8})

        reponse = client.post(
            base,
            json={
                "type": "placement",
                "sources": [
                    {
                        "ordre_source": 1,
                        "nature": "issue_de_tour",
                        "tour": 2,
                        "issue": "gagnants",
                        "rang_fin": 50,
                    }
                ],
            },
        )
        assert reponse.status_code == 422
        assert reponse.json()["code"] == "source_malformee"


def test_deux_sources_qui_se_recoupent_rendent_422_avec_leur_code(
    app_phases: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        client.post(base, json={"type": "elimination_directe", "effectif": 64})

        reponse = client.post(
            base,
            json={
                "type": "placement",
                "sources": [
                    {"ordre_source": 1, "rang_debut": 1, "rang_fin": 32},
                    {"ordre_source": 1, "rang_debut": 16, "rang_fin": 48},
                ],
            },
        )
        assert reponse.status_code == 422
        assert reponse.json()["code"] == "sources_qui_se_recoupent"


def test_l_ancienne_forme_source_est_refusee_et_n_efface_rien(
    app_phases: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """⚠️ Le test le plus important de ce bloc : `PUT` est une **édition totale**.

    Un client resté sur l'ancien contrat (`source`, au singulier) verrait, sans `extra="forbid"`,
    sa clé ignorée par Pydantic — et la phase réécrite **sans aucune source**, en 200. Il ne
    perdrait pas sa saisie : il **écraserait** la composition existante. On exige donc un 422, et
    on vérifie que la composition d'origine est intacte après le refus.
    """
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        client.post(base, json={"type": "elimination_directe", "effectif": 64})
        creee = client.post(
            base,
            json={
                "type": "placement",
                "sources": [{"ordre_source": 1, "rang_debut": 1, "rang_fin": 16}],
                "effectif": 16,
            },
        )
        phase_id = creee.json()["id"]

        refus = client.put(
            f"{base}/{phase_id}",
            json={
                "type": "placement",
                "source": {"ordre_source": 1, "rang_debut": 1, "rang_fin": 16},
                "effectif": 16,
            },
        )
        assert refus.status_code == 400, refus.text  # champ inconnu → requête invalide

        inchangee = next(p for p in client.get(base).json() if p["id"] == phase_id)
        assert len(inchangee["sources"]) == 1
        assert inchangee["sources"][0]["rang_fin"] == 16


def test_trop_de_sources_est_refuse(app_phases: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """La borne `max_length=16` protège la frontière d'une liste non bornée."""
    with TestClient(app_phases) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        base = f"/api/v1/tournois/{tournoi_id}/phases"
        client.post(base, json={"type": "elimination_directe", "effectif": 64})

        reponse = client.post(
            base,
            json={
                "type": "placement",
                "sources": [
                    {"ordre_source": 1, "rang_debut": r, "rang_fin": r} for r in range(1, 20)
                ],
            },
        )
        assert reponse.status_code == 400
