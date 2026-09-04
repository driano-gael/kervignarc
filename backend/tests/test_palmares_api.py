"""Test bout-en-bout de l'API du palmarès (E06US004).

Traverse les couches — HTTP → `ServicePalmares` → classement + saisie de duels → repositories —
après avoir peuplé un tournoi (gabarit, catégorie, départ, 4 archers **classés**) et une phase
d'élimination directe. Vérifie le **câblage** : la route rend le classement final, le filtre par
catégorie passe, l'export PDF sort un vrai document, et les deux se lisent **sans
authentification** (contrat de lecture publique, E10US001).

La règle métier est couverte par `test_service_palmares` et `test_domain_palmares` — tests écrits,
eux, **depuis le CA** (règle 9) ; ceux-ci le sont après l'implémentation, il n'y a pas d'oracle en
jeu à cette couche.
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
from tests.test_placement_api import _appliquer_gabarit, _creer_tournoi
from tests.test_placement_duels_api import _phase_elimination, _quatre_archers_classes


@pytest.fixture
def app_palmares(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    preparer_base(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _preparer(app: FastAPI, client: TestClient) -> tuple[int, list[int]]:
    """Tournoi peuplé (gabarit, 4 archers classés, phase de tableau) avec le plan de duels posé."""
    tournoi_id = _creer_tournoi(client)
    _appliquer_gabarit(client, tournoi_id, nb_cibles=2)
    archers = _quatre_archers_classes(app, client, tournoi_id)
    phase_id = _phase_elimination(app, tournoi_id)
    regen = client.post(f"/api/v1/tournois/{tournoi_id}/phases/{phase_id}/plan-de-duels/regenerer")
    assert regen.status_code == 200, regen.text
    return tournoi_id, archers


def test_le_palmares_rend_une_ligne_par_archer_avec_ses_deux_rangs(
    app_palmares: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Câblage : une ligne par archer du tournoi, rangs scratch et catégorie, origine renseignée."""
    with TestClient(app_palmares) as client:
        connecter_admin(client)
        tournoi_id, archers = _preparer(app_palmares, client)

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/palmares")

    assert reponse.status_code == 200, reponse.text
    corps = reponse.json()
    assert corps["tournoi_id"] == tournoi_id
    assert {ligne["archer_id"] for ligne in corps["lignes"]} == set(archers)
    for ligne in corps["lignes"]:
        assert ligne["rang_min"] is not None and ligne["rang_max"] is not None
        assert ligne["rang_categorie_min"] is not None
        assert ligne["origine"] in {"duels", "qualification"}
        assert ligne["statut"] == "en_lice"
        assert ligne["nom"] != ""


def test_les_podiums_sortent_par_categorie(
    app_palmares: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le DTO porte un podium **par catégorie** : c'est là que se remettent les médailles.

    Aucun duel n'étant tranché, les quatre archers sont encore en lice et **aucun** rang n'est
    décerné : le podium est vide, mais la catégorie est bien listée. C'est la lecture au fil de
    l'eau — l'écran affiche la catégorie et dira « en cours », pas « catégorie absente ».
    """
    with TestClient(app_palmares) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer(app_palmares, client)

        corps = client.get(f"/api/v1/tournois/{tournoi_id}/palmares").json()

    assert len(corps["podiums"]) == 1
    assert corps["podiums"][0]["portee"] == "categorie"
    assert corps["podiums"][0]["libelle"] != ""
    assert corps["podiums"][0]["places"] == []


def test_le_filtre_par_categorie_est_transmis(
    app_palmares: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """`categorie_id` traverse jusqu'au service : une catégorie inconnue rend un palmarès vide."""
    with TestClient(app_palmares) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer(app_palmares, client)

        reponse = client.get(
            f"/api/v1/tournois/{tournoi_id}/palmares", params={"categorie_id": 9999}
        )

    assert reponse.status_code == 200, reponse.text
    assert reponse.json()["lignes"] == []


def test_tournoi_inconnu_rend_404(app_palmares: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """`TournoiIntrouvable` est traduit à la frontière, comme pour le classement."""
    with TestClient(app_palmares) as client:
        connecter_admin(client)
        _preparer(app_palmares, client)

        reponse = client.get("/api/v1/tournois/9999/palmares")

    assert reponse.status_code == 404, reponse.text


def test_l_export_pdf_rend_un_document(
    app_palmares: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA « exportable » : un vrai PDF, servi `inline` pour être ouvert puis imprimé."""
    with TestClient(app_palmares) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer(app_palmares, client)

        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/palmares.pdf")

    assert reponse.status_code == 200, reponse.text
    assert reponse.headers["content-type"] == "application/pdf"
    assert "inline" in reponse.headers["content-disposition"]
    assert reponse.content.startswith(b"%PDF")


def test_lecture_publique_sans_authentification(
    app_palmares: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Contrat E10US001 : le palmarès se lit **sans jeton** — il finit sur l'écran de salle et sur
    le téléphone du public, qui n'ont pas de session."""
    with TestClient(app_palmares) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer(app_palmares, client)
        client.cookies.clear()

        json = client.get(f"/api/v1/tournois/{tournoi_id}/palmares")
        pdf = client.get(f"/api/v1/tournois/{tournoi_id}/palmares.pdf")

    assert json.status_code == 200, json.text
    assert pdf.status_code == 200, pdf.text


# --- réglage des podiums (E16US014) --------------------------------------------------------------


def test_le_reglage_par_defaut_est_celui_d_e06us004(
    app_palmares: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Câblage du défaut serveur (migration 0052) jusqu'au DTO : catégorie seule, quatre places."""
    with TestClient(app_palmares) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer(app_palmares, client)

        corps = client.get(f"/api/v1/tournois/{tournoi_id}/reglage-podiums").json()

    assert corps == {"portees": ["categorie"], "profondeur": 4}


def test_le_reglage_se_pose_et_se_relit(
    app_palmares: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le PUT traverse la file d'écriture, et le GET suivant rend ce qui a été posé.

    Les portées ressortent dans l'ordre d'affichage, pas dans celui de la requête : c'est la
    propriété qui garantit qu'un même réglage rend le même écran d'une écriture à l'autre.
    """
    with TestClient(app_palmares) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer(app_palmares, client)

        pose = client.put(
            f"/api/v1/tournois/{tournoi_id}/reglage-podiums",
            json={"portees": ["club", "scratch"], "profondeur": 2},
        )
        relu = client.get(f"/api/v1/tournois/{tournoi_id}/reglage-podiums").json()

    assert pose.status_code == 200, pose.text
    assert pose.json() == {"portees": ["scratch", "club"], "profondeur": 2}
    assert relu == {"portees": ["scratch", "club"], "profondeur": 2}


def test_le_reglage_commande_les_blocs_rendus_par_le_palmares(
    app_palmares: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Bout en bout : ce qui est réglé décide des blocs du palmarès, y compris « rien du tout »."""
    with TestClient(app_palmares) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer(app_palmares, client)

        client.put(
            f"/api/v1/tournois/{tournoi_id}/reglage-podiums",
            json={"portees": ["scratch"], "profondeur": 4},
        )
        scratch = client.get(f"/api/v1/tournois/{tournoi_id}/palmares").json()
        client.put(
            f"/api/v1/tournois/{tournoi_id}/reglage-podiums",
            json={"portees": [], "profondeur": 4},
        )
        aucun = client.get(f"/api/v1/tournois/{tournoi_id}/palmares").json()

    assert [bloc["portee"] for bloc in scratch["podiums"]] == ["scratch"]
    assert scratch["podiums"][0]["cle"] is None
    assert aucun["podiums"] == []


def test_une_portee_inconnue_est_refusee_a_la_frontiere(
    app_palmares: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Refus typé plutôt qu'une valeur silencieusement ignorée — une portée qu'on croit réglée
    et qui ne rend rien est le pire des deux mondes. Idem pour une profondeur nulle.

    ⚠️ **Deux codes, et la différence est voulue** (corrigée en revue) : une portée inconnue est un
    refus de **forme**, tranché par l'énumération Pydantic → `RequestValidationError` → **400**
    générique (`api/erreurs.py`). Une profondeur hors bornes est un refus **métier**, tranché par
    `ReglagePodiums` → `DomainError` → **422** portant `profondeur_podium_invalide`. Répéter la
    borne à la frontière aurait dégradé le second en 400, comme `ReglagePages` l'a déjà écrit.
    """
    with TestClient(app_palmares) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer(app_palmares, client)

        portee = client.put(
            f"/api/v1/tournois/{tournoi_id}/reglage-podiums",
            json={"portees": ["equipe"], "profondeur": 4},
        )
        profondeur = client.put(
            f"/api/v1/tournois/{tournoi_id}/reglage-podiums",
            json={"portees": ["categorie"], "profondeur": 0},
        )
        plafond = client.put(
            f"/api/v1/tournois/{tournoi_id}/reglage-podiums",
            json={"portees": ["categorie"], "profondeur": 65},
        )

    assert portee.status_code == 400, portee.text
    assert profondeur.status_code == 422, profondeur.text
    assert profondeur.json()["code"] == "profondeur_podium_invalide"
    assert plafond.status_code == 422, plafond.text
    assert plafond.json()["code"] == "profondeur_podium_invalide"


def test_regler_les_podiums_exige_l_admin(app_palmares: FastAPI) -> None:
    """Poser le réglage est une **action admin** ; le lire reste ouvert, comme le palmarès."""
    with TestClient(app_palmares) as client:
        refus = client.put(
            "/api/v1/tournois/1/reglage-podiums",
            json={"portees": ["scratch"], "profondeur": 4},
        )

    assert refus.status_code in (401, 403), refus.text


def test_un_filtre_par_categorie_ne_rogne_pas_les_podiums(
    app_palmares: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le cas adverse du bloquant de revue : **un podium est celui du tournoi**, pas de la vue.

    Composer les blocs sur le palmarès filtré rendait un « Toutes catégories » réduit aux archers
    d'une seule catégorie — voire vide, avec « Podium en cours » sur un tournoi terminé — et le même
    document partait au mur en PDF. Le filtre ne doit toucher **que** le classement.
    """
    with TestClient(app_palmares) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer(app_palmares, client)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/reglage-podiums",
            json={"portees": ["scratch"], "profondeur": 4},
        )

        entier = client.get(f"/api/v1/tournois/{tournoi_id}/palmares").json()
        # Une catégorie qui n'existe pas : le filtre le plus dur qui soit, aucune ligne ne survit.
        filtre = client.get(f"/api/v1/tournois/{tournoi_id}/palmares?categorie_id=9999").json()

    # ⚠️ Ce test vérifie le **câblage** de la route (les blocs ne suivent pas le filtre) ; le décor
    # d'API ne joue aucun duel, donc aucune place n'y est décernée. La preuve que les blocs restent
    # **peuplés** sous filtre est au service, sur un tableau réellement joué :
    # `test_un_filtre_par_categorie_ne_rogne_pas_les_podiums` de `test_service_palmares.py`.
    assert entier["podiums"] == filtre["podiums"], "les podiums ne dépendent pas du filtre"
    # Ancré sur le contenu, pas sur une égalité de listes vides : le bloc doit exister et se
    # nommer. ⚠️ Son `effectif` vaut 0 ici, et c'est juste — le décor d'API ne joue aucun duel,
    # donc personne n'est récompensable. La valeur est ancrée au service, qui les joue.
    assert entier["podiums"][0]["libelle"] == "Toutes catégories"
    assert filtre["lignes"] == [], "le filtre, lui, restreint bien le classement"


def test_le_reglage_se_lit_sans_authentification(app_palmares: FastAPI) -> None:
    """CA « se règle en admin, **se lit en public** » — la moitié que le PUT ne prouve pas.

    Sans ce test, un `Depends(exiger_admin)` ajouté par erreur sur le GET ne ferait rougir personne.
    """
    with TestClient(app_palmares) as client:
        lecture = client.get("/api/v1/tournois/1/reglage-podiums")

    assert lecture.status_code != 401, lecture.text
    assert lecture.status_code != 403, lecture.text


def test_classement_vide_dit_le_tournoi_pas_la_selection(
    app_palmares: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le fait porté par le serveur, ancré **côté serveur** — sans quoi rien ne le protège.

    ⚠️ Les tests front mockent la réponse HTTP : ils ne peuvent structurellement pas voir un champ
    mal rempli ici. Remplacer `not rendu.complet.lignes` par `rendu.affiche.lignes` rétablirait à
    l'identique le bloquant de la 3ᵉ passe **et passerait toute la porte** (relevé en revue).
    """
    with TestClient(app_palmares) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer(app_palmares, client)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/reglage-podiums",
            json={"portees": [], "profondeur": 4},
        )

        entier = client.get(f"/api/v1/tournois/{tournoi_id}/palmares").json()
        filtre = client.get(f"/api/v1/tournois/{tournoi_id}/palmares?categorie_id=9999").json()

    assert entier["classement_vide"] is False, "le tournoi est classé"
    assert filtre["classement_vide"] is False, "il l'est toujours, filtre ou pas"
    assert filtre["lignes"] == [] and filtre["podiums"] == [], "le décor du 4ᵉ déplacement"


def test_le_classement_des_clubs_est_servi_avec_le_palmares(
    app_palmares: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """E16US017 : le DTO porte le classement des clubs et **sur quoi il repose**.

    ⚠️ Le décor d'API ne tranche aucun duel : aucune médaille n'est décernée, donc les clubs sont
    tous à zéro. Ce qui est ancré ici est le **câblage** — la preuve du décompte est au domaine
    (`test_domain_classement_clubs.py`), celle du nommage au service.
    """
    with TestClient(app_palmares) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer(app_palmares, client)

        corps = client.get(f"/api/v1/tournois/{tournoi_id}/palmares").json()

    assert corps["classement_clubs"]["portees_comptees"] == ["categorie"], "le défaut d'ADR-0103"
    assert corps["classement_clubs"]["provisoire"] is True, "aucun duel n'est tranché"


def test_la_portee_club_seule_ne_donne_aucune_base_au_classement_des_clubs(
    app_palmares: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Arbitrage du 04/09/2026, servi jusqu'au client : la portée *club* décerne un or **dans**
    chaque club, elle ne compare rien entre eux.

    L'écran a besoin de la distinction pour dire « aucune base de comparaison » plutôt que
    d'afficher un tableau vide que l'organisateur prendrait pour une panne.
    """
    with TestClient(app_palmares) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer(app_palmares, client)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/reglage-podiums",
            json={"portees": ["club"], "profondeur": 4},
        )

        corps = client.get(f"/api/v1/tournois/{tournoi_id}/palmares").json()

    assert corps["classement_clubs"]["portees_comptees"] == []
    assert corps["classement_clubs"]["lignes"] == []


def test_un_filtre_par_categorie_ne_rogne_pas_le_classement_des_clubs(
    app_palmares: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Même parti que les podiums (ADR-0103 §7) : le trophée du club est celui du **tournoi**.

    Composé sur la vue filtrée, il n'aurait compté que les médailles d'une catégorie — un
    classement faux, et faux différemment selon ce que l'organisateur regarde.
    """
    with TestClient(app_palmares) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer(app_palmares, client)

        entier = client.get(f"/api/v1/tournois/{tournoi_id}/palmares").json()
        filtre = client.get(f"/api/v1/tournois/{tournoi_id}/palmares?categorie_id=9999").json()

    assert entier["classement_clubs"] == filtre["classement_clubs"]
