"""Tests du service du build front en statique (E00US012).

Vérifie que FastAPI sert la SPA (`index.html` + assets) quand un build est présent, **sans
masquer** les routes API/santé, et qu'en l'absence de build rien n'est monté (l'API reste
servie seule). Un **faux** répertoire `dist/` est fabriqué à la volée : le test ne dépend
donc pas d'un vrai build (job CI backend, dépôt fraîchement cloné).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.spa import frontend_dist_dir
from bootstrap.composition import create_app


def _faux_build(dist: Path) -> Path:
    """Fabrique un build front minimal (index + un asset) et renvoie son répertoire."""
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "index.html").write_text("<!doctype html><title>Kervignarc</title>", encoding="utf-8")
    (dist / "assets").mkdir(exist_ok=True)
    (dist / "assets" / "app.js").write_text("console.log('kervignarc')", encoding="utf-8")
    return dist


def test_sert_le_build_front_sans_masquer_l_api(tmp_path: Path) -> None:
    """Avec un build présent : `/` → index, assets servis, et `/health` reste routé."""
    dist = _faux_build(tmp_path / "dist")
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    app = create_app(url, frontend_dist=dist)
    try:
        with TestClient(app) as client:
            racine = client.get("/")
            assert racine.status_code == 200
            assert "Kervignarc" in racine.text

            asset = client.get("/assets/app.js")
            assert asset.status_code == 200
            assert "kervignarc" in asset.text

            # La SPA (montée à `/`) ne masque pas les routes API déclarées avant.
            sante = client.get("/health")
            assert sante.status_code == 200
    finally:
        app.state.database.engine.dispose()


def test_pas_de_build_rien_n_est_monte(tmp_path: Path) -> None:
    """Sans build (répertoire absent) : `/` → 404, l'API est servie seule."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    app = create_app(url, frontend_dist=tmp_path / "dist_absent")
    try:
        with TestClient(app) as client:
            assert client.get("/").status_code == 404
            assert client.get("/health").status_code == 200
    finally:
        app.state.database.engine.dispose()


def test_lien_profond_replie_sur_index(tmp_path: Path) -> None:
    """`F5` sur une route de la SPA rend l'application, pas un 404 (E14US003).

    C'est la raison d'être du repli : ces chemins n'existent pas sur le disque, ils n'ont de sens
    que pour le routeur côté client.
    """
    dist = _faux_build(tmp_path / "dist")
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    app = create_app(url, frontend_dist=dist)
    try:
        with TestClient(app) as client:
            for profond in (
                "/admin",
                "/admin/pilotage/supervision",
                "/cible",
                "/scoreur",
                "/public",
            ):
                reponse = client.get(profond)
                assert reponse.status_code == 200, profond
                assert "Kervignarc" in reponse.text, profond
    finally:
        app.state.database.engine.dispose()


def test_le_repli_ne_masque_ni_l_api_ni_les_assets(tmp_path: Path) -> None:
    """Le repli est **borné** : sous les préfixes serveur et `assets/`, un 404 reste un 404.

    Les deux pièges qu'un repli aveugle introduirait : une route d'API inexistante répondrait une
    page HTML en 200 (le client croit avoir réussi), et un asset manquant répondrait du HTML avec un
    type MIME faux (le navigateur signale une erreur obscure au lieu d'un 404 clair).
    """
    dist = _faux_build(tmp_path / "dist")
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    app = create_app(url, frontend_dist=dist)
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/route-inexistante").status_code == 404
            assert client.get("/assets/absent.js").status_code == 404
            # Les routes serveur réelles répondent toujours, elles ne sont pas avalées par le mount.
            assert client.get("/health").status_code == 200
            assert client.get("/assets/app.js").status_code == 200
    finally:
        app.state.database.engine.dispose()


def test_repertoire_dist_par_defaut_pointe_vers_le_front(monkeypatch: pytest.MonkeyPatch) -> None:
    """Le répertoire par défaut (sans surcharge d'env) est `frontend/dist` à la racine."""
    monkeypatch.delenv("KERVIGNARC_FRONTEND_DIST", raising=False)
    chemin = frontend_dist_dir()
    assert chemin.name == "dist"
    assert chemin.parent.name == "frontend"
