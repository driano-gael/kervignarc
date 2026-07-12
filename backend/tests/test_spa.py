"""Tests du service du build front en statique (E00US012).

Vérifie que FastAPI sert la SPA (`index.html` + assets) quand un build est présent, **sans
masquer** les routes API/santé, et qu'en l'absence de build rien n'est monté (l'API reste
servie seule). Un **faux** répertoire `dist/` est fabriqué à la volée : le test ne dépend
donc pas d'un vrai build (job CI backend, dépôt fraîchement cloné).
"""

from __future__ import annotations

from pathlib import Path

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


def test_repertoire_dist_par_defaut_pointe_vers_le_front() -> None:
    """Le répertoire par défaut est `frontend/dist` à la racine du dépôt."""
    chemin = frontend_dist_dir()
    assert chemin.name == "dist"
    assert chemin.parent.name == "frontend"
