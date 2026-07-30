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
    # L'en-tête qu'envoie un navigateur qui **navigue** — c'est lui qui distingue une page d'une
    # ressource, et donc ce qui déclenche le repli (cf. `_demande_une_page`).
    navigateur = {"accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
    try:
        with TestClient(app) as client:
            for profond in (
                "/admin",
                "/admin/12/pilotage/supervision",
                "/cible",
                "/scoreur",
                "/public",
            ):
                reponse = client.get(profond, headers=navigateur)
                assert reponse.status_code == 200, profond
                assert "Kervignarc" in reponse.text, profond
    finally:
        app.state.database.engine.dispose()


def test_le_repli_ne_masque_pas_les_routes_du_serveur(tmp_path: Path) -> None:
    """Sous un segment du serveur, un 404 reste un 404 — quelle que soit la casse.

    Le piège qu'un repli aveugle introduirait : une route d'API inexistante répondrait une page HTML
    en 200, donc un client persuadé d'avoir réussi et une erreur introuvable dans les logs.

    La **casse** est testée parce que le routage FastAPI y est sensible : `/API/v1/x` n'est aucune
    route, c'est un 404 — et une comparaison brute la laissait passer en 200 HTML.
    """
    dist = _faux_build(tmp_path / "dist")
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    app = create_app(url, frontend_dist=dist)
    navigateur = {"accept": "text/html,application/xhtml+xml"}
    try:
        with TestClient(app) as client:
            for serveur in ("/api/v1/inexistante", "/API/v1/inexistante", "/ws/x", "/docs/x"):
                assert client.get(serveur, headers=navigateur).status_code == 404, serveur
            # Les routes serveur réelles répondent toujours : le mount ne les avale pas.
            assert client.get("/health").status_code == 200
    finally:
        app.state.database.engine.dispose()


def test_le_repli_ne_sert_du_html_qu_a_une_navigation(tmp_path: Path) -> None:
    """Une **ressource** manquante reste un 404, où qu'elle vive dans le build.

    Borner par une liste de préfixes ne suffisait pas : Vite copie `frontend/public/` **à la racine
    de `dist/`, hors `assets/`** (`favicon.svg`, `icons.svg`, demain un `robots.txt`). Ces
    fichiers-là recevaient `index.html` en 200 avec un type MIME faux — l'erreur obscure côté
    navigateur que le repli prétend éviter. Le discriminant est donc l'intention du client :
    navigue-t-il, ou demande-t-il une ressource ?
    """
    dist = _faux_build(tmp_path / "dist")
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    app = create_app(url, frontend_dist=dist)
    try:
        with TestClient(app) as client:
            # Ressources absentes, demandées comme des ressources → 404, jamais du HTML.
            assert client.get("/assets/absent.js", headers={"accept": "*/*"}).status_code == 404
            assert (
                client.get("/favicon.svg", headers={"accept": "image/svg+xml,*/*"}).status_code
                == 404
            )
            assert (
                client.get("/api/v1/x", headers={"accept": "application/json"}).status_code == 404
            )
            # La ressource qui existe est servie normalement.
            assert client.get("/assets/app.js").status_code == 200
    finally:
        app.state.database.engine.dispose()


def test_repertoire_dist_par_defaut_pointe_vers_le_front(monkeypatch: pytest.MonkeyPatch) -> None:
    """Le répertoire par défaut (sans surcharge d'env) est `frontend/dist` à la racine."""
    monkeypatch.delenv("KERVIGNARC_FRONTEND_DIST", raising=False)
    chemin = frontend_dist_dir()
    assert chemin.name == "dist"
    assert chemin.parent.name == "frontend"
