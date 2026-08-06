"""Tests bout-en-bout de l'API patrimoine et formats (E01US023 / ADR-0060).

Traversent toutes les couches — DTO Pydantic → file d'écriture → service → repository → DB, puis
relecture — et vérifient le **mapping des erreurs typées** à la frontière. Écrits **après**
l'implémentation : il n'y a pas d'oracle métier en jeu à ce niveau (règle 9), la règle a déjà été
éprouvée par `test_service_patrimoine` et `test_service_formats`. Ce qui se joue ici est le
**câblage** : routes, codes HTTP, sérialisation JSON de la séquence d'étapes, aller-retour en base.
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

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _migrer(url: str) -> None:
    preparer_base(url)


@pytest.fixture
def app_patrimoine(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _creer_tournoi(client: TestClient, nom: str = "Trophée") -> int:
    """Crée un tournoi **et son créneau** : un format s'applique à des départs (ADR-0075)."""
    reponse = client.post("/api/v1/tournois", json={"nom": nom, "date": "2026-03-14"})
    assert reponse.status_code == 201, reponse.text
    tournoi_id = int(reponse.json()["id"])
    creneau = client.post(
        f"/api/v1/tournois/{tournoi_id}/departs",
        json={"horaire": "09:00", "tarif_centimes": 800},
    )
    assert creneau.status_code == 201, creneau.text
    return tournoi_id


_QUALIFICATION: dict[str, Any] = {
    "ordre": 1,
    "type": "qualification",
    "bareme": {"nb_volees": 20, "nb_fleches_par_volee": 3},
    "validation": {"type": "fin_de_serie"},
}


# --- Bibliothèque : les routes ne portent pas de tournoi ----------------------------------------


def test_creer_puis_lister_une_brique_de_bibliotheque(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """La promesse de l'atelier, vue de l'API : **aucun `tournoi_id` dans l'URL**."""
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)

        creation = client.post(
            "/api/v1/blasons", json={"nom": "Blason 40 cm", "taille": 0.25, "capacite": 1}
        )

        assert creation.status_code == 201, creation.text
        cree = creation.json()
        assert cree["tournoi_id"] is None
        assert cree["origine"] == "utilisateur"
        liste = client.get("/api/v1/blasons")
        assert liste.status_code == 200
        assert liste.json() == [cree]


def test_la_liste_de_bibliotheque_exclut_les_copies_des_tournois(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        client.post(
            f"/api/v1/tournois/{tournoi_id}/blasons",
            json={"nom": "Copie du tournoi", "taille": 1.0, "capacite": 1},
        )
        client.post("/api/v1/blasons", json={"nom": "Modèle", "taille": 1.0, "capacite": 1})

        liste = client.get("/api/v1/blasons").json()

        assert [b["nom"] for b in liste] == ["Modèle"]


def test_precharger_ffta_alimente_la_bibliotheque(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Une fois pour toutes, plus à chaque tournoi — la correction de fond de DETTE-023."""
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)

        rapport = client.post("/api/v1/patrimoine/precharger-ffta")

        assert rapport.status_code == 201, rapport.text
        assert rapport.json()["blasons_copies"] == 4
        assert rapport.json()["categories_copiees"] > 0
        categories = client.get("/api/v1/categories").json()
        assert all(c["tournoi_id"] is None for c in categories)
        assert all(c["origine"] == "ffta" for c in categories)


def test_precharger_ffta_est_rejouable(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        client.post("/api/v1/patrimoine/precharger-ffta")

        rapport = client.post("/api/v1/patrimoine/precharger-ffta").json()

        assert rapport["blasons_copies"] == 0
        assert rapport["blasons_ignores"] == 4
        assert rapport["categories_copiees"] == 0


def test_une_brique_de_bibliotheque_s_edite_par_la_route_existante(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`PUT /categories/{id}` est à plat depuis E01US003 : elle marche telle quelle sur un modèle.

    C'est ce qui justifie de **ne pas** avoir redoublé l'édition dans le routeur patrimoine — deux
    chemins pour un même geste auraient divergé.

    ⚠️ La fixture porte **tous** les champs (`ages`, `sexe`, `blason_id`), pas le seul libellé :
    la première version de ce test créait une catégorie nue, et ne pouvait donc pas voir que le PUT
    — **total** (ADR-0020) — effaçait ce qu'on ne lui renvoyait pas. Un test dont la fixture
    évite le champ fautif est vert quoi qu'il arrive (relevé en revue, E01US023).
    """
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        blason = client.post(
            "/api/v1/blasons", json={"nom": "Blason 60 cm", "taille": 0.5, "capacite": 1}
        ).json()
        complet = {
            "libelle": "Maison",
            "arme": "Arc Classique",
            "ages": ["U15", "U18"],
            "sexe": "F",
            "blason_id": blason["id"],
            "hauteur_cm": 125,
        }
        cree = client.post("/api/v1/categories", json=complet).json()

        edition = client.put(
            f"/api/v1/categories/{cree['id']}",
            json={**complet, "libelle": "Maison renommée"},
        )

        assert edition.status_code == 200, edition.text
        modifiee = edition.json()
        assert modifiee["tournoi_id"] is None
        assert modifiee["libelle"] == "Maison renommée"
        # Le reste de l'entité doit avoir survécu au PUT total.
        assert modifiee["ages"] == ["U15", "U18"]
        assert modifiee["sexe"] == "F"
        assert modifiee["blason_id"] == blason["id"]
        assert modifiee["hauteur_cm"] == 125


def test_editer_un_modele_refuse_un_blason_de_tournoi(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Miroir du refus à la **création** : la garde ne doit pas céder à l'**édition**.

    C'était le trou : `ServiceCategories.modifier` sautait la vérification pour un modèle au lieu de
    la remplacer, et cette route héritée devenait le seul chemin par lequel une brique du patrimoine
    pouvait acquérir une FK vers l'édition d'un tournoi.
    """
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        blason_du_tournoi = client.post(
            f"/api/v1/tournois/{tournoi_id}/blasons",
            json={"nom": "Du tournoi", "taille": 1.0, "capacite": 1},
        ).json()
        modele = client.post("/api/v1/categories", json={"libelle": "Maison"}).json()

        refus = client.put(
            f"/api/v1/categories/{modele['id']}",
            json={
                "libelle": "Maison",
                "blason_id": blason_du_tournoi["id"],
                "hauteur_cm": 130,
            },
        )

        assert refus.status_code == 409
        assert refus.json()["code"] == "brique_hors_bibliotheque"


def test_editer_un_modele_refuse_un_blason_inexistant(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Sans garde, la FK partait en base et rendait un 500 sur une saisie utilisateur."""
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        modele = client.post("/api/v1/categories", json={"libelle": "Maison"}).json()

        refus = client.put(
            f"/api/v1/categories/{modele['id']}",
            json={"libelle": "Maison", "blason_id": 999_999, "hauteur_cm": 130},
        )

        assert refus.status_code == 404
        assert refus.json()["code"] == "blason_introuvable"


def test_dupliquer_une_brique_officielle_garde_les_deux_modeles(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA « modifier un officiel » : la seconde issue, jusqu'ici livrée pour les seuls formats."""
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        client.post("/api/v1/patrimoine/precharger-ffta")
        officielle = client.get("/api/v1/categories").json()[0]

        copie = client.post(
            f"/api/v1/categories/{officielle['id']}/duplication",
            json={"nom": "Ma variante"},
        )

        assert copie.status_code == 201, copie.text
        assert copie.json()["origine"] == "utilisateur"
        assert copie.json()["id"] != officielle["id"]
        assert copie.json()["blason_id"] == officielle["blason_id"]
        # L'original est intact — c'est tout l'objet de « garder les deux modèles ».
        relues = {c["id"]: c for c in client.get("/api/v1/categories").json()}
        assert relues[officielle["id"]]["origine"] == "ffta"


def test_deux_briques_de_bibliotheque_ne_peuvent_pas_etre_homonymes(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """L'assemblage et la promotion dédoublonnent **par le nom** : deux homonymes les rendraient
    non déterministes (un seul serait copié, la promotion mettrait à jour l'un au hasard)."""
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        client.post("/api/v1/blasons", json={"nom": "Blason 40 cm", "taille": 0.25, "capacite": 1})

        refus = client.post(
            "/api/v1/blasons", json={"nom": "blason 40 CM", "taille": 1.0, "capacite": 2}
        )

        assert refus.status_code == 409
        assert refus.json()["code"] == "nom_brique_deja_pris"


def test_une_categorie_de_bibliotheque_refuse_un_blason_de_tournoi(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        blason = client.post(
            f"/api/v1/tournois/{tournoi_id}/blasons",
            json={"nom": "Du tournoi", "taille": 1.0, "capacite": 1},
        ).json()

        refus = client.post(
            "/api/v1/categories", json={"libelle": "Bancale", "blason_id": blason["id"]}
        )

        assert refus.status_code == 409
        assert refus.json()["code"] == "brique_hors_bibliotheque"


# --- Assemblage ---------------------------------------------------------------------------------


def test_assembler_copie_la_bibliotheque_et_rattache_les_blasons(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        client.post("/api/v1/patrimoine/precharger-ffta")

        rapport = client.post(f"/api/v1/tournois/{tournoi_id}/assemblage")

        assert rapport.status_code == 201, rapport.text
        copies = client.get(f"/api/v1/tournois/{tournoi_id}/categories").json()
        blasons_du_tournoi = {
            b["id"] for b in client.get(f"/api/v1/tournois/{tournoi_id}/blasons").json()
        }
        assert copies
        assert all(c["tournoi_id"] == tournoi_id for c in copies)
        # Le lien `blason_id` doit viser une copie **du tournoi**, jamais la bibliothèque.
        assert all(c["blason_id"] in blasons_du_tournoi for c in copies)


def test_assembler_un_tournoi_inconnu_renvoie_404(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)

        refus = client.post("/api/v1/tournois/404/assemblage")

        assert refus.status_code == 404
        assert refus.json()["code"] == "tournoi_introuvable"


def test_appliquer_une_brique_qui_est_une_copie_renvoie_409(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        autre = _creer_tournoi(client, "Autre")
        copie = client.post(
            f"/api/v1/tournois/{autre}/blasons",
            json={"nom": "Pas un modèle", "taille": 1.0, "capacite": 1},
        ).json()

        refus = client.post(f"/api/v1/tournois/{tournoi_id}/assemblage/blasons/{copie['id']}")

        assert refus.status_code == 409
        assert refus.json()["code"] == "brique_hors_bibliotheque"


def test_promouvoir_une_copie_la_fait_remonter(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        copie = client.post(
            f"/api/v1/tournois/{tournoi_id}/blasons",
            json={"nom": "Blason maison", "taille": 0.5, "capacite": 2},
        ).json()

        promotion = client.post(f"/api/v1/blasons/{copie['id']}/promotion")

        assert promotion.status_code == 201, promotion.text
        assert promotion.json()["tournoi_id"] is None
        assert [b["nom"] for b in client.get("/api/v1/blasons").json()] == ["Blason maison"]


def test_promouvoir_un_modele_renvoie_409(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        modele = client.post(
            "/api/v1/blasons", json={"nom": "Déjà modèle", "taille": 1.0, "capacite": 1}
        ).json()

        refus = client.post(f"/api/v1/blasons/{modele['id']}/promotion")

        assert refus.status_code == 409
        assert refus.json()["code"] == "brique_deja_en_bibliotheque"


def test_les_ecritures_du_patrimoine_exigent_l_admin(app_patrimoine: FastAPI) -> None:
    """Toutes les écritures restent derrière `exiger_admin` (E10US001) — la lecture, non."""
    with TestClient(app_patrimoine) as client:
        assert client.get("/api/v1/blasons").status_code == 200
        assert (
            client.post(
                "/api/v1/blasons", json={"nom": "X", "taille": 1.0, "capacite": 1}
            ).status_code
            == 401
        )
        assert client.post("/api/v1/patrimoine/precharger-ffta").status_code == 401
        assert client.post("/api/v1/tournois/1/assemblage").status_code == 401


# --- Formats ------------------------------------------------------------------------------------


def test_creer_puis_relire_un_format(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """L'aller-retour complet de la séquence d'étapes en JSON (`format_tournoi.config`)."""
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)

        creation = client.post(
            "/api/v1/formats",
            json={
                "nom": "Mon format",
                "etapes": [
                    {**_QUALIFICATION, "effectif": 16},
                    {
                        "ordre": 2,
                        "type": "elimination_directe",
                        "sources": [{"ordre_source": 1, "rang_debut": 1, "rang_fin": 8}],
                        "effectif": 8,
                    },
                ],
            },
        )

        assert creation.status_code == 201, creation.text
        relu = client.get("/api/v1/formats").json()
        assert relu == [creation.json()]
        assert [e["ordre"] for e in relu[0]["etapes"]] == [1, 2]
        assert relu[0]["etapes"][0]["bareme"] == {"nb_volees": 20, "nb_fleches_par_volee": 3}
        assert relu[0]["etapes"][1]["sources"] == [
            {
                "ordre_source": 1,
                "nature": "rangs",
                "rang_debut": 1,
                "rang_fin": 8,
                "tour": None,
                "issue": None,
            }
        ]


def test_un_format_sans_etape_s_enregistre_en_201_et_se_diagnostique(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """⚠️ **Test inversé en E01US024** — le refus n'a pas disparu, il s'est déplacé.

    Il vérifiait le 422 à la création ; il vérifie désormais que le brouillon s'enregistre (201) et
    que le diagnostic le **nomme** avec le **même code**. Le 422 est repris par le test suivant, à
    l'application — la seule porte qui protège un vrai tournoi (ADR-0063).
    """
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)

        cree = client.post("/api/v1/formats", json={"nom": "Vide", "etapes": []})
        assert cree.status_code == 201

        diagnostic = client.get(f"/api/v1/formats/{cree.json()['id']}/diagnostic")

        assert diagnostic.status_code == 200
        corps = diagnostic.json()
        assert corps["applicable"] is False
        assert "format_sans_etape" in {a["code"] for a in corps["anomalies"]}


def test_un_format_sans_etape_est_refuse_a_l_application_en_422(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """L'invariant tenu à l'**usage** : la même erreur, le même code, le même 422 qu'avant l'US."""
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        format_id = client.post("/api/v1/formats", json={"nom": "Vide", "etapes": []}).json()["id"]

        refus = client.put(f"/api/v1/tournois/{tournoi_id}/format", json={"format_id": format_id})

        assert refus.status_code == 422
        assert refus.json()["code"] == "format_sans_etape"


def test_un_nom_de_format_deja_pris_est_refuse_en_409(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        client.post("/api/v1/formats", json={"nom": "Mon format", "etapes": [_QUALIFICATION]})

        refus = client.post(
            "/api/v1/formats", json={"nom": "Mon format", "etapes": [_QUALIFICATION]}
        )

        assert refus.status_code == 409
        assert refus.json()["code"] == "nom_format_deja_pris"


def test_precharger_les_presets_puis_dupliquer_un_officiel(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        presets = client.post("/api/v1/formats/precharger-presets")
        assert presets.status_code == 201, presets.text
        officiel = next(f for f in presets.json() if f["origine"] == "ffta")

        copie = client.post(
            f"/api/v1/formats/{officiel['id']}/duplication", json={"nom": "Ma variante"}
        )

        assert copie.status_code == 201, copie.text
        assert copie.json()["origine"] == "utilisateur"
        assert copie.json()["id"] != officiel["id"]
        # L'original est intact — l'issue « garder les deux modèles » du CA.
        assert any(f["id"] == officiel["id"] for f in client.get("/api/v1/formats").json())


def test_appliquer_un_format_cree_les_phases_du_tournoi(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        format_tournoi = client.post(
            "/api/v1/formats", json={"nom": "Officiel", "etapes": [_QUALIFICATION]}
        ).json()

        application = client.put(
            f"/api/v1/tournois/{tournoi_id}/format", json={"format_id": format_tournoi["id"]}
        )

        assert application.status_code == 200, application.text
        # Les phases se lisent **par créneau** (ADR-0075) : appliquer un format en pose une
        # séquence sur chacun. Ici le tournoi n'a qu'un départ, donc une seule séquence.
        departs = client.get(f"/api/v1/tournois/{tournoi_id}/departs").json()
        depart_id = departs[0]["id"]
        phases = client.get(f"/api/v1/departs/{depart_id}/phases").json()
        assert [p["ordre"] for p in phases] == [1]
        assert phases[0]["statut"] == "a_venir"
        assert phases[0]["depart_id"] == depart_id


def test_appliquer_un_format_inconnu_renvoie_404(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        refus = client.put(f"/api/v1/tournois/{tournoi_id}/format", json={"format_id": 404})

        assert refus.status_code == 404
        assert refus.json()["code"] == "format_introuvable"


def test_promouvoir_le_deroule_d_un_tournoi(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        # Le barème crée la phase de qualification du tournoi (E01US009).
        client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 12, "nb_fleches_par_volee": 3},
        )

        promotion = client.post(
            f"/api/v1/tournois/{tournoi_id}/format/promotion", json={"nom": "Le format 2026"}
        )

        assert promotion.status_code == 201, promotion.text
        assert promotion.json()["etapes"][0]["bareme"] == {
            "nb_volees": 12,
            "nb_fleches_par_volee": 3,
        }


def test_appliquer_un_format_sans_qualification_est_refuse(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Route parallèle fermée : `ServicePhases.supprimer` refuse de retirer la qualification, mais
    `appliquer` passait par le repository et la supprimait — emportant le barème avec elle."""
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 20, "nb_fleches_par_volee": 3},
        )
        sans_qualif = client.post(
            "/api/v1/formats",
            json={
                "nom": "Tableau seul",
                "etapes": [{"ordre": 1, "type": "elimination_directe", "effectif": 16}],
            },
        ).json()

        refus = client.put(
            f"/api/v1/tournois/{tournoi_id}/format", json={"format_id": sans_qualif["id"]}
        )

        assert refus.status_code == 409
        assert refus.json()["code"] == "phases_engagees"
        # Le barème du tournoi est intact.
        bareme = client.get(f"/api/v1/tournois/{tournoi_id}/bareme-qualification").json()
        assert bareme["nb_volees"] == 20


def test_promouvoir_un_tournoi_sans_phase_renvoie_409(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        refus = client.post(f"/api/v1/tournois/{tournoi_id}/format/promotion", json={"nom": "Vide"})

        assert refus.status_code == 409
        assert refus.json()["code"] == "tournoi_sans_phase"


def test_supprimer_un_format_laisse_les_phases(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Les phases portent leur copie du déroulé : elles ne référencent aucun format."""
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        format_tournoi = client.post(
            "/api/v1/formats", json={"nom": "Officiel", "etapes": [_QUALIFICATION]}
        ).json()
        client.put(
            f"/api/v1/tournois/{tournoi_id}/format", json={"format_id": format_tournoi["id"]}
        )

        suppression = client.delete(f"/api/v1/formats/{format_tournoi['id']}")

        assert suppression.status_code == 204
        assert len(client.get(f"/api/v1/tournois/{tournoi_id}/phases").json()) == 1


# --- Import du référentiel des clubs ------------------------------------------------------------


def test_importer_des_clubs_rend_un_compte_rendu(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        client.post("/api/v1/clubs", json={"nom": "Arc Club de Lorient"})

        rapport = client.post(
            "/api/v1/clubs/import",
            json={"lignes": "Arc Club de Lorient\n\nLes Archers de Kervignac\nelan de fougeres"},
        )

        assert rapport.status_code == 201, rapport.text
        corps = rapport.json()
        assert corps["crees"] == ["Les Archers de Kervignac", "elan de fougeres"]
        assert corps["doublons"] == ["Arc Club de Lorient"]
        assert corps["lignes_ignorees"] == 1
        assert len(client.get("/api/v1/clubs").json()) == 3


def test_importer_des_clubs_exige_l_admin(app_patrimoine: FastAPI) -> None:
    with TestClient(app_patrimoine) as client:
        assert client.post("/api/v1/clubs/import", json={"lignes": "X"}).status_code == 401


def test_le_grain_d_une_etape_non_qualification_survit_a_l_aller_retour(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`_politiques_json` écrit le grain pour **tout** type d'étape ; la relecture ne le lisait que
    pour la qualification — on écrivait donc ce qu'on ne relisait pas, et le grain d'une élimination
    disparaissait en silence à la première relecture.

    Le test va jusqu'à l'**application** : le trou existait des deux côtés (format *et* phase), et
    la première correction n'avait fermé que le premier — il avait changé de table, pas disparu.
    """
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        creation = client.post(
            "/api/v1/formats",
            json={
                "nom": "Avec élimination",
                "etapes": [
                    {**_QUALIFICATION, "effectif": 16},
                    {
                        "ordre": 2,
                        "type": "elimination_directe",
                        "validation": {"type": "fin_de_duel"},
                        "sources": [{"ordre_source": 1, "rang_debut": 1, "rang_fin": 8}],
                        "effectif": 8,
                    },
                ],
            },
        )
        assert creation.status_code == 201, creation.text

        relu = client.get("/api/v1/formats").json()[0]
        assert relu["etapes"][1]["validation"] == {"type": "fin_de_duel", "n_volees": None}

        client.put(f"/api/v1/tournois/{tournoi_id}/format", json={"format_id": relu["id"]})
        promu = client.post(
            f"/api/v1/tournois/{tournoi_id}/format/promotion", json={"nom": "Repromu"}
        )

        assert promu.status_code == 201, promu.text
        assert promu.json()["etapes"][1]["validation"] == {
            "type": "fin_de_duel",
            "n_volees": None,
        }


def test_renommer_un_modele_vers_un_libelle_deja_pris_est_refuse(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """L'unicité était posée à la **création** et contournable par le bouton « Renommer » — la
    route héritée, une fois de plus. Deux modèles homonymes rendent l'assemblage non déterministe :
    un seul est copié, l'autre est compté « déjà présent » et n'atteint jamais aucun tournoi."""
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        client.post("/api/v1/categories", json={"libelle": "Senior 1 Homme"})
        autre = client.post("/api/v1/categories", json={"libelle": "Ma variante"}).json()

        refus = client.put(
            f"/api/v1/categories/{autre['id']}",
            json={"libelle": "senior 1 HOMME", "hauteur_cm": 130},
        )

        assert refus.status_code == 409
        assert refus.json()["code"] == "nom_brique_deja_pris"


def test_renommer_un_modele_en_lui_meme_reste_possible(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le pendant de la garde : sans l'exclusion « sauf soi-même », changer la hauteur d'une
    catégorie sans toucher au libellé deviendrait impossible."""
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        cree = client.post("/api/v1/categories", json={"libelle": "Senior 1 Homme"}).json()

        edition = client.put(
            f"/api/v1/categories/{cree['id']}",
            json={"libelle": "Senior 1 Homme", "hauteur_cm": 110},
        )

        assert edition.status_code == 200, edition.text
        assert edition.json()["hauteur_cm"] == 110


# --- Diagnostic & simulation d'un format (E01US024) ---------------------------------------------


def _format_qualif_puis_tableau(client: TestClient, nom: str = "Déroulé") -> int:
    """Un format à deux étapes : la qualification FFTA, puis un tableau des 8 premiers rangs."""
    reponse = client.post(
        "/api/v1/formats",
        json={
            "nom": nom,
            "etapes": [
                _QUALIFICATION,
                {
                    "ordre": 2,
                    "type": "elimination_directe",
                    "sources": [
                        {"ordre_source": 1, "nature": "rangs", "rang_debut": 1, "rang_fin": 8}
                    ],
                },
            ],
        },
    )
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def test_le_diagnostic_rend_le_schema_a_braquets(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Les quatre questions du CA, servies au front : qui, quoi, où, combien de tours."""
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        format_id = _format_qualif_puis_tableau(client)

        reponse = client.get(f"/api/v1/formats/{format_id}/diagnostic", params={"effectif": 24})

        assert reponse.status_code == 200, reponse.text
        corps = reponse.json()
        assert corps["applicable"] is True
        qualif, tableau = corps["blocs"]
        assert qualif["effectif"] == 24
        assert qualif["nb_volees"] == 20
        assert qualif["sans_suite"] == 16
        assert len(qualif["sorties"]) == 1
        assert tableau["tranche"] == [1, 8]
        assert [tour["plage_perdants"] for tour in tableau["tours"]] == [[5, 8], [3, 4], [2, 2]]


def test_le_diagnostic_sans_effectif_reste_abstrait(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        format_id = _format_qualif_puis_tableau(client)

        corps = client.get(f"/api/v1/formats/{format_id}/diagnostic").json()

        assert corps["effectif"] is None
        assert corps["blocs"][0]["effectif"] is None


def test_le_diagnostic_avertit_sans_bloquer_a_effectif_reduit(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un format composé pour 8 qualifiés reste applicable à 5 inscrits — il avertit, il ne bloque
    pas (ADR-0063 §3)."""
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        format_id = _format_qualif_puis_tableau(client)

        corps = client.get(f"/api/v1/formats/{format_id}/diagnostic", params={"effectif": 5}).json()

        assert corps["applicable"] is True
        anomalies = {a["code"]: a for a in corps["anomalies"]}
        assert "rangs_source_inexistants" in anomalies
        assert anomalies["rangs_source_inexistants"]["gravite"] == "avertissement"
        assert anomalies["rangs_source_inexistants"]["ordre"] == 2


def test_le_diagnostic_d_un_format_inconnu_est_404(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)

        assert client.get("/api/v1/formats/999/diagnostic").status_code == 404


def test_simuler_un_format_rend_le_classement_et_la_charge(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le CA « simuler le format » de bout en bout, par l'API."""
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        reponse_creation = client.post(
            "/api/v1/formats",
            json={
                "nom": "Court",
                "etapes": [
                    {
                        "ordre": 1,
                        "type": "qualification",
                        "bareme": {"nb_volees": 2, "nb_fleches_par_volee": 3},
                        "validation": {"type": "fin_de_serie"},
                    },
                    {
                        "ordre": 2,
                        "type": "elimination_directe",
                        # ⚠️ Un prélèvement **explicite**, et non `sources: []`. La première
                        # version de ce test décrivait un tableau que **personne n'atteint** — un
                        # bloc orphelin, que la revue a fait remonter en anomalie bloquante
                        # (`phase_sans_source`). Le test de la simulation était donc écrit sur le
                        # format qui exhibait le trou, et passait au vert parce que le moteur
                        # ignore les sources (DETTE-028).
                        "sources": [
                            {"ordre_source": 1, "nature": "rangs", "rang_debut": 1, "rang_fin": 8}
                        ],
                    },
                ],
            },
        )
        format_id = reponse_creation.json()["id"]

        reponse = client.post(
            f"/api/v1/formats/{format_id}/simulation", json={"effectif": 8, "graine": 7}
        )

        assert reponse.status_code == 200, reponse.text
        corps = reponse.json()
        assert len(corps["classement"]) == 8
        assert [ligne["rang"] for ligne in corps["classement"]] == list(range(1, 9))
        assert corps["duels_total"] == 8  # 7 duels d'arbre + la petite finale
        assert corps["diagnostic"]["effectif"] == 8


def test_simuler_un_effectif_hors_bornes_est_400(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Borne de **service** (E01US024) : ni 404 ni 409 — la requête est impossible en soi."""
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        format_id = _format_qualif_puis_tableau(client)

        refus = client.post(f"/api/v1/formats/{format_id}/simulation", json={"effectif": 500})

        assert refus.status_code == 400
        assert refus.json()["code"] == "effectif_simulation_invalide"


def test_un_brouillon_de_qualification_incomplete_fait_l_aller_retour(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """⚠️ **Régression fermée en revue — le scénario phare du CA était impersistable.**

    `_politiques_json` n'écrivait `policies.scoring` que si le barème existait, et
    `_vers_modele_phase` le relisait inconditionnellement pour une qualification : `KeyError` →
    `InfrastructureError` → **500**, levée *après* le `commit`. La ligne restait en base, et comme
    `lister()` mappe **toutes** les lignes, un seul brouillon incomplet mettait la bibliothèque
    entière en 500 — sans qu'aucune route ne permette de le supprimer, puisqu'elles relisent toutes.

    Ce test couvre ce que les tests inversés du domaine ne pouvaient pas voir : ils s'arrêtent à
    l'agrégat, le trou était dans l'**adapter**.
    """
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)

        cree = client.post(
            "/api/v1/formats",
            json={"nom": "Qualif à finir", "etapes": [{"ordre": 1, "type": "qualification"}]},
        )
        assert cree.status_code == 201, cree.text

        # 1. La bibliothèque reste lisible — c'était le point grave.
        liste = client.get("/api/v1/formats")
        assert liste.status_code == 200, liste.text

        # 2. L'aller-retour est fidèle : ni barème ni grain ne sont inventés à la relecture.
        relu = next(f for f in liste.json() if f["id"] == cree.json()["id"])
        assert relu["etapes"][0]["bareme"] is None
        assert relu["etapes"][0]["validation"] is None

        # 3. Le diagnostic nomme le défaut, et l'application le refuse.
        diagnostic = client.get(f"/api/v1/formats/{relu['id']}/diagnostic").json()
        assert diagnostic["applicable"] is False
        assert "phase_qualification_incomplete" in {a["code"] for a in diagnostic["anomalies"]}

        # 4. Et la ligne reste supprimable : aucun cul-de-sac.
        assert client.delete(f"/api/v1/formats/{relu['id']}").status_code == 204


def test_le_diagnostic_refuse_un_effectif_hors_bornes(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Même borne que la simulation : la route est **publique en lecture**, et son entrée est
    amplificatrice (la réponse grossit avec la taille des entiers de plage)."""
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        format_id = _format_qualif_puis_tableau(client)

        assert (
            client.get(
                f"/api/v1/formats/{format_id}/diagnostic", params={"effectif": 0}
            ).status_code
            == 400
        )
        assert (
            client.get(
                f"/api/v1/formats/{format_id}/diagnostic", params={"effectif": 10**60}
            ).status_code
            == 400
        )


def test_simuler_un_format_sans_qualification_est_refuse_en_400(
    app_patrimoine: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le format est **applicable** mais pas **simulable** : le bot n'a aucun barème.

    Avant correction, `applicable: true` activait le bouton « Simuler » et la requête revenait en
    **404** avec un message parlant d'un tournoi que l'organisateur ne voit nulle part.
    """
    with TestClient(app_patrimoine) as client:
        connecter_admin(client)
        cree = client.post(
            "/api/v1/formats",
            json={
                "nom": "Duels seuls",
                "etapes": [{"ordre": 1, "type": "elimination_directe"}],
            },
        )
        assert cree.status_code == 201, cree.text

        refus = client.post(f"/api/v1/formats/{cree.json()['id']}/simulation", json={"effectif": 8})

        assert refus.status_code == 400
        assert refus.json()["code"] == "format_non_simulable"
