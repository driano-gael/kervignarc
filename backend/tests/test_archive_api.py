"""Test bout-en-bout de l'API d'archive de fin de tournoi (E11US003) — **câblage** de la route.

Traverse HTTP → `ServiceArchive` → `ConstructeurArchiveZip`, après avoir peuplé un tournoi via les
endpoints existants. Infra/câblage : tests **après** implémentation (règle 9 — pas d'oracle de CA).
On valide : réponse `application/zip` téléchargeable ; contenu du paquet (snapshot SQLite, dump
CSV, PDF régénérés, manifeste) ; respect de la **sélection** ; protection admin ; mapping 404.
"""

from __future__ import annotations

import io
import json
import zipfile
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
def app_archive(tmp_path: Path) -> Iterator[FastAPI]:
    """App câblée sur une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    app = create_app(url, admin_env_path=tmp_path / ".env")
    try:
        yield app
    finally:
        app.state.database.engine.dispose()


def _preparer_tournoi(client: TestClient) -> tuple[int, int]:
    """Crée un tournoi complet (gabarit, club, catégorie, départ, deux archers inscrits) et
    matérialise le plan. Renvoie `(tournoi_id, depart_id)`."""
    tournoi = client.post("/api/v1/tournois", json={"nom": "Trophée", "date": "2026-03-14"})
    assert tournoi.status_code == 201, tournoi.text
    tournoi_id = int(tournoi.json()["id"])

    modele = client.post("/api/v1/gabarits", json={"nom": "Salle", "nb_cibles": 2})
    assert modele.status_code == 201, modele.text
    applique = client.put(
        f"/api/v1/tournois/{tournoi_id}/gabarit", json={"modele_id": modele.json()["id"]}
    )
    assert applique.status_code == 200, applique.text

    club = client.post("/api/v1/clubs", json={"nom": "Arcs de Test"})
    assert club.status_code == 201, club.text
    club_id = int(club.json()["id"])

    blason = client.post(
        f"/api/v1/tournois/{tournoi_id}/blasons",
        json={"nom": "Blason 40", "taille": 0.5, "capacite": 1},
    )
    assert blason.status_code == 201, blason.text
    categorie = client.post(
        f"/api/v1/tournois/{tournoi_id}/categories",
        json={"libelle": "Senior", "blason_id": blason.json()["id"], "hauteur_cm": 130},
    )
    assert categorie.status_code == 201, categorie.text
    categorie_id = int(categorie.json()["id"])

    depart = client.post(
        f"/api/v1/tournois/{tournoi_id}/departs", json={"tarif_centimes": 800, "horaire": "09:00"}
    )
    assert depart.status_code == 201, depart.text
    depart_id = int(depart.json()["id"])

    for prenom, avec_club in (("Guillaume", True), ("Walter", False)):
        corps = {"nom": "Tell", "prenom": prenom, "categorie_id": categorie_id}
        if avec_club:
            corps["club_id"] = club_id
        archer = client.post(f"/api/v1/tournois/{tournoi_id}/archers", json=corps)
        assert archer.status_code == 201, archer.text
        inscription = client.post(
            f"/api/v1/archers/{archer.json()['id']}/inscriptions", json={"depart_id": depart_id}
        )
        assert inscription.status_code == 201, inscription.text

    plan = client.post(
        f"/api/v1/tournois/{tournoi_id}/departs/{depart_id}/plan-de-cibles/regenerer"
    )
    assert plan.status_code == 200, plan.text
    return tournoi_id, depart_id


def _ouvrir_zip(contenu: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(contenu))


def test_archive_telecharge_un_zip_complet(
    app_archive: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """L'archive complète renvoie un ZIP téléchargeable réunissant snapshot, CSV, PDF, manifeste."""
    with TestClient(app_archive) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer_tournoi(client)
        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/archive")

    assert reponse.status_code == 200, reponse.text
    assert reponse.headers["content-type"] == "application/zip"
    assert "attachment" in reponse.headers["content-disposition"]
    with _ouvrir_zip(reponse.content) as paquet:
        noms = set(paquet.namelist())
    assert "manifeste.json" in noms
    assert "kervignarc.db" in noms
    assert "donnees/tournoi.csv" in noms
    assert "donnees/archer.csv" in noms
    # Les PDF régénérés du tournoi (feuille de marque du départ + listes) sont présents.
    assert "documents/placement.pdf" in noms
    assert "documents/club-paiement.pdf" in noms
    assert any(n.startswith("documents/feuille-de-marque-depart-") for n in noms)


def test_manifeste_decrit_le_tournoi_et_le_schema(
    app_archive: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """Le manifeste porte l'identité du tournoi, la version de schéma et le compte des tables."""
    with TestClient(app_archive) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer_tournoi(client)
        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/archive")

    with _ouvrir_zip(reponse.content) as paquet:
        manifeste = json.loads(paquet.read("manifeste.json"))
    assert manifeste["tournoi"]["nom"] == "Trophée"
    assert manifeste["tournoi"]["id"] == tournoi_id
    assert isinstance(manifeste["version_schema"], str) and manifeste["version_schema"]
    assert manifeste["tables"]["tournoi"] == 1
    assert manifeste["tables"]["archer"] == 2


def test_selection_ne_met_que_les_parties_cochees(
    app_archive: FastAPI, connecter_admin: ConnecterAdmin
) -> None:
    """En décochant tout, le paquet ne contient plus que le manifeste (toujours présent)."""
    with TestClient(app_archive) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer_tournoi(client)
        reponse = client.get(
            f"/api/v1/tournois/{tournoi_id}/archive",
            params={
                "base": "false",
                "donnees_csv": "false",
                "feuilles_de_marque": "false",
                "liste_placement": "false",
                "liste_club_paiement": "false",
            },
        )

    assert reponse.status_code == 200, reponse.text
    with _ouvrir_zip(reponse.content) as paquet:
        noms = set(paquet.namelist())
    assert noms == {"manifeste.json"}


def test_document_en_echec_est_omis_sans_casser_l_archive(
    app_archive: FastAPI, connecter_admin: ConnecterAdmin, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Best-effort (CA) : un PDF qui échoue est **omis** (et tracé au manifeste), l'archive tient.

    On force `service_feuille_de_marque.generer` à lever : la feuille de marque est absente du ZIP,
    listée dans `parties_incluses.documents_omis`, et le reste (base, CSV, autres PDF) est présent —
    la génération renvoie bien 200, pas une erreur.
    """

    def _echouer(*_args: object, **_kwargs: object) -> bytes:
        raise RuntimeError("échec simulé de la feuille de marque")

    with TestClient(app_archive) as client:
        connecter_admin(client)
        tournoi_id, _ = _preparer_tournoi(client)
        monkeypatch.setattr(app_archive.state.service_feuille_de_marque, "generer", _echouer)
        reponse = client.get(f"/api/v1/tournois/{tournoi_id}/archive")

    assert reponse.status_code == 200, reponse.text
    with _ouvrir_zip(reponse.content) as paquet:
        noms = set(paquet.namelist())
        manifeste = json.loads(paquet.read("manifeste.json"))
    # Aucune feuille de marque dans le ZIP…
    assert not any(n.startswith("documents/feuille-de-marque-depart-") for n in noms)
    # …mais l'omission est **découvrable** dans le manifeste, et le reste est bien là.
    omis = manifeste["parties_incluses"]["documents_omis"]
    assert any(n.startswith("feuille-de-marque-depart-") for n in omis)
    assert "documents/placement.pdf" in noms
    assert "kervignarc.db" in noms


def test_archive_sans_admin_refuse(app_archive: FastAPI) -> None:
    """Route réservée à l'admin (E10US001) : sans session, 401."""
    with TestClient(app_archive) as client:
        reponse = client.get("/api/v1/tournois/1/archive")
    assert reponse.status_code == 401, reponse.text


def test_archive_tournoi_inconnu_404(app_archive: FastAPI, connecter_admin: ConnecterAdmin) -> None:
    with TestClient(app_archive) as client:
        connecter_admin(client)
        reponse = client.get("/api/v1/tournois/9999/archive")
    assert reponse.status_code == 404, reponse.text
