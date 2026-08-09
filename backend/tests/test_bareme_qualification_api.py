"""Test bout-en-bout de l'API barème de qualification (E01US009).

Traverse toutes les couches — DTO Pydantic → file d'écriture → service → repository → DB, puis
relecture — et vérifie le **mapping des erreurs typées** à la frontière :
- absence de barème → `null` ; définition (PUT) puis relecture avec total et score max dérivés ;
- redéfinition (upsert) ; lecture publique ; définition réservée à l'admin (401) ;
- tournoi inconnu → 404 ; valeurs invalides → 422 ; corps invalide → 400.
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
def app_bareme(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _creer_tournoi(client: TestClient) -> int:
    """Crée un tournoi via l'API (admin déjà connecté) et renvoie son identifiant."""
    reponse = client.post("/api/v1/tournois", json={"nom": "Kervignarc", "date": "2026-03-14"})
    assert reponse.status_code == 201, reponse.text
    tournoi_id = int(reponse.json()["id"])
    # Un créneau est requis : le barème et le grain se règlent sur la qualification, qui vit sur un
    # départ (E01US025, ADR-0075). Sans lui, le service refuse en 409 (`tournoi_sans_depart`) —
    # il ne saurait ni sur quoi écrire, ni combien de fois.
    creneau = client.post(
        f"/api/v1/tournois/{tournoi_id}/departs",
        json={"horaire": "09:00", "tarif_centimes": 800},
    )
    assert creneau.status_code == 201, creneau.text
    return tournoi_id


def test_definir_puis_relire(app_bareme: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """PUT définit le barème (via la file) ; GET le relit avec total et score max dérivés."""
    with TestClient(app_bareme) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        assert client.get(f"/api/v1/tournois/{tournoi_id}/bareme-qualification").json() is None

        definition = client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 20, "nb_fleches_par_volee": 3},
        )
        assert definition.status_code == 200, definition.text
        assert definition.json() == {
            "nb_volees": 20,
            "nb_fleches_par_volee": 3,
            "nb_fleches_total": 60,
            "score_max": 600,
        }
        assert (
            client.get(f"/api/v1/tournois/{tournoi_id}/bareme-qualification").json()
            == definition.json()
        )


def test_redefinir_remplace_les_valeurs(
    app_bareme: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un second PUT met à jour le barème (upsert, une seule phase qualification)."""
    with TestClient(app_bareme) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 20, "nb_fleches_par_volee": 3},
        )
        maj = client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 10, "nb_fleches_par_volee": 6},
        )
        assert maj.status_code == 200
        corps = maj.json()
        assert corps["nb_volees"] == 10
        assert corps["nb_fleches_total"] == 60
        assert corps["score_max"] == 600


def test_lire_est_public(app_bareme: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Le barème d'un tournoi est lisible sans session (lecture publique)."""
    with TestClient(app_bareme) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 20, "nb_fleches_par_volee": 3},
        )
    with TestClient(app_bareme) as anonyme:
        reponse = anonyme.get(f"/api/v1/tournois/{tournoi_id}/bareme-qualification")
    assert reponse.status_code == 200
    assert reponse.json()["nb_volees"] == 20


def test_definir_sans_jeton_401(app_bareme: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Définir le barème est une action admin : refusée sans session (401)."""
    with TestClient(app_bareme) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
    with TestClient(app_bareme) as anonyme:
        reponse = anonyme.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 20, "nb_fleches_par_volee": 3},
        )
    assert reponse.status_code == 401
    assert reponse.json()["code"] == "non_authentifie"


def test_definir_tournoi_inconnu_404(app_bareme: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Définir sur un tournoi inexistant → 404 `tournoi_introuvable`."""
    with TestClient(app_bareme) as client:
        connecter_admin(client)
        reponse = client.put(
            "/api/v1/tournois/999/bareme-qualification",
            json={"nb_volees": 20, "nb_fleches_par_volee": 3},
        )
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"


def test_lire_tournoi_inconnu_404(app_bareme: FastAPI) -> None:
    """Lire le barème d'un tournoi inexistant → 404 `tournoi_introuvable`."""
    with TestClient(app_bareme) as client:
        reponse = client.get("/api/v1/tournois/999/bareme-qualification")
    assert reponse.status_code == 404
    assert reponse.json()["code"] == "tournoi_introuvable"


def test_definir_valeur_invalide_422(app_bareme: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Un nombre de volées nul → 422 avec le code métier (règle du domaine)."""
    with TestClient(app_bareme) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 0, "nb_fleches_par_volee": 3},
        )
    assert reponse.status_code == 422
    assert reponse.json()["code"] == "nombre_volees_invalide"


def test_definir_corps_invalide_400(app_bareme: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    """Un corps invalide (nb_volees non entier) → 400 avec le détail."""
    with TestClient(app_bareme) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        reponse = client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": "beaucoup", "nb_fleches_par_volee": 3},
        )
    assert reponse.status_code == 400
    assert reponse.json()["code"] == "requete_invalide"


# --- E05US025 : plusieurs qualifications dans un même déroulé (ADR-0082) --------------------------


def _composer_seconde_qualification(client: TestClient, tournoi_id: int) -> int:
    """Ajoute une 2ᵉ qualification au déroulé (prélevée dans la 1ʳᵉ) et rend son `etape_id`.

    Passe par l'atelier (`POST .../phases`), c'est-à-dire le chemin réel de composition : un test
    qui écrirait l'étape par le repository n'éprouverait pas que la séquence l'accepte — or c'est
    précisément l'invariant qu'E05US025 lève.
    """
    reponse = client.post(
        f"/api/v1/tournois/{tournoi_id}/phases",
        json={
            "type": "qualification",
            "sources": [{"ordre_source": 1, "rang_debut": 1, "rang_fin": 8}],
            "effectif": 8,
        },
    )
    assert reponse.status_code == 201, reponse.text
    return int(reponse.json()["id"])


def test_lister_les_qualifications_d_un_deroule(
    app_bareme: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA « deux qualifications coexistent » : l'écran doit pouvoir les lister pour choisir.

    C'est ce que la route historique ne pouvait pas rendre — elle n'en connaissait qu'une.
    """
    with TestClient(app_bareme) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 20, "nb_fleches_par_volee": 3},
        )
        _composer_seconde_qualification(client, tournoi_id)

        qualifications = client.get(f"/api/v1/tournois/{tournoi_id}/qualifications")

        assert qualifications.status_code == 200, qualifications.text
        corps = qualifications.json()
        assert [q["libelle"] for q in corps] == ["Qualification 1", "Qualification 2"]
        assert corps[0]["bareme"]["nb_volees"] == 20
        # La seconde arrive avec le **preset FFTA 18 m** : l'invariant du domaine exige qu'une
        # qualification porte barème et grain, donc l'atelier ne peut pas la composer « vide ».
        # La valeur de départ est visible ici même — c'est ce qui la rend ajustable plutôt que
        # subie (arbitrage E05US025, cf. `ServicePhases.ajouter`).
        assert corps[1]["bareme"]["nb_volees"] == 20
        assert corps[1]["grain"] == "fin_de_serie"


def test_le_bareme_se_regle_par_qualification(
    app_bareme: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA « le barème se règle par qualification » : 3x20 en tête, 3x15 ensuite.

    L'exemple du commanditaire tient dans ce test : les deux tours ne tirent pas le même nombre de
    flèches, et régler l'un ne doit pas toucher l'autre.
    """
    with TestClient(app_bareme) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 20, "nb_fleches_par_volee": 3},
        )
        seconde = _composer_seconde_qualification(client, tournoi_id)

        reglee = client.put(
            f"/api/v1/tournois/{tournoi_id}/qualifications/{seconde}/bareme",
            json={"nb_volees": 15, "nb_fleches_par_volee": 3},
        )

        assert reglee.status_code == 200, reglee.text
        assert reglee.json()["nb_volees"] == 15
        corps = client.get(f"/api/v1/tournois/{tournoi_id}/qualifications").json()
        assert [q["bareme"]["nb_volees"] for q in corps] == [20, 15]


def test_regler_le_bareme_d_une_phase_qui_n_est_pas_une_qualification_409(
    app_bareme: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Un tableau n'a pas de barème de série : conflit d'état, pas 404 — l'étape existe bien."""
    with TestClient(app_bareme) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 20, "nb_fleches_par_volee": 3},
        )
        tableau = client.post(
            f"/api/v1/tournois/{tournoi_id}/phases",
            json={
                "type": "elimination_directe",
                "sources": [{"ordre_source": 1, "rang_debut": 1, "rang_fin": 8}],
                "effectif": 8,
            },
        )
        assert tableau.status_code == 201, tableau.text

        refus = client.put(
            f"/api/v1/tournois/{tournoi_id}/qualifications/{tableau.json()['id']}/bareme",
            json={"nb_volees": 15, "nb_fleches_par_volee": 3},
        )

        assert refus.status_code == 409, refus.text
        assert refus.json()["code"] == "phase_pas_une_qualification"


def test_regler_le_bareme_d_une_etape_inconnue_404(
    app_bareme: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Une étape d'un autre tournoi (ou inexistante) est introuvable **dans celui-ci**."""
    with TestClient(app_bareme) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)

        refus = client.put(
            f"/api/v1/tournois/{tournoi_id}/qualifications/9999/bareme",
            json={"nb_volees": 15, "nb_fleches_par_volee": 3},
        )

        assert refus.status_code == 404, refus.text


def test_le_grain_se_regle_aussi_par_qualification(
    app_bareme: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """CA « chacune avec ses propres réglages » : le grain suit le barème, par étape."""
    with TestClient(app_bareme) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 20, "nb_fleches_par_volee": 3},
        )
        seconde = _composer_seconde_qualification(client, tournoi_id)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/qualifications/{seconde}/bareme",
            json={"nb_volees": 15, "nb_fleches_par_volee": 3},
        )

        reglage = client.put(
            f"/api/v1/tournois/{tournoi_id}/qualifications/{seconde}/grain-validation",
            json={"grain": "toutes_les_n_volees", "n_volees": 5},
        )

        assert reglage.status_code == 200, reglage.text
        corps = client.get(f"/api/v1/tournois/{tournoi_id}/qualifications").json()
        assert corps[0]["grain"] == "fin_de_serie"
        assert (corps[1]["grain"], corps[1]["grain_n_volees"]) == ("toutes_les_n_volees", 5)


def test_les_reglages_par_qualification_sans_jeton_401(
    app_bareme: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Les deux routes par étape sont des **écritures admin** : refusées sans session (401).

    Ce fichier a pour convention un test 401 par route d'écriture ; les deux routes neuves ne
    l'avaient pas (relevé de revue). Sans lui, un retrait futur d'`exiger_admin` passerait la suite
    au vert — et une écriture ouverte est un bloquant, pas un détail.
    """
    with TestClient(app_bareme) as client:
        connecter_admin(client)
        tournoi_id = _creer_tournoi(client)
        client.put(
            f"/api/v1/tournois/{tournoi_id}/bareme-qualification",
            json={"nb_volees": 20, "nb_fleches_par_volee": 3},
        )
        seconde = _composer_seconde_qualification(client, tournoi_id)

    with TestClient(app_bareme) as anonyme:
        bareme = anonyme.put(
            f"/api/v1/tournois/{tournoi_id}/qualifications/{seconde}/bareme",
            json={"nb_volees": 15, "nb_fleches_par_volee": 3},
        )
        grain = anonyme.put(
            f"/api/v1/tournois/{tournoi_id}/qualifications/{seconde}/grain-validation",
            json={"grain": "fin_de_serie"},
        )

    assert (bareme.status_code, bareme.json()["code"]) == (401, "non_authentifie")
    assert (grain.status_code, grain.json()["code"]) == (401, "non_authentifie")
