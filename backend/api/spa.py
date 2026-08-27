"""Service du build front en statique — adapter entrant (couche API ; E00US012).

FastAPI sert la SPA React au **même origin** que l'API : un seul serveur, pas de proxy Vite.

⚠️ Le montage est **conditionnel** (pas de build ⇒ on ne monte rien) et se fait **en dernier**, à la
racine `/`, pour ne jamais masquer `/api/v1/…`, `/ws`, `/health` ni `/docs`.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as ErreurHttpStarlette
from starlette.responses import Response
from starlette.types import Scope

_ENV_VAR = "KERVIGNARC_FRONTEND_DIST"

# Premiers segments qui **appartiennent au serveur** et ne se replient jamais vers `index.html`
# (E14US003). Sous ces chemins, une URL inconnue est une **vraie erreur** du client : lui renvoyer
# un 404 est la seule réponse honnête. Un appel d'API vers une route inexistante qui recevrait une
# page HTML en 200 donnerait un client persuadé d'avoir réussi, et une erreur introuvable en logs.
#
# Comparaison **par segment**, pas par préfixe de chaîne : `startswith("ws")` mordrait aussi sur une
# future adresse de SPA comme `/wsx` ou `/health-checklist`, qui recevrait alors un 404 au lieu de
# l'application — panne invisible en développement (Vite sert tout) et seulement derrière FastAPI.
_SEGMENTS_SERVEUR = frozenset({"api", "ws", "health", "docs", "redoc", "openapi.json"})


def _premier_segment(path: str) -> str:
    """Premier segment du chemin demandé, normalisé.

    Deux normalisations, chacune pour un piège vérifié :

    - **le séparateur** — `StaticFiles` construit son `path` avec `os.path.normpath`, qui rend le
      chemin avec des antislashs **sur Windows**, là où les segments sont écrits en `/`. Comparer
      brut fait échouer le garde sur Windows *et nulle part ailleurs* : la CI (Linux) resterait
      verte pendant que le poste de la table d'organisation renverrait une page HTML en 200 sur un
      appel d'API inexistant ;
    - **la casse** — le routage FastAPI y est sensible, donc `/API/v1/x` n'est **aucune** route :
      c'est un 404, pas une adresse de SPA. Sans repli de casse, elle recevait `index.html` en 200.
    """
    return path.replace(os.sep, "/").replace("\\", "/").lstrip("/").split("/", 1)[0].lower()


def _demande_une_page(scope: Scope) -> bool:
    """Le client demande-t-il une **page** (navigation) plutôt qu'une ressource ?

    C'est ce qui referme la classe entière au lieu d'allonger une liste à maintenir : un navigateur
    qui **navigue** envoie `Accept: text/html…`, alors qu'un appel d'API (`application/json`, `*/*`)
    ou une ressource (`image/svg+xml` pour un favicon) ne le fait pas.

    Sans ce filtre, tout fichier de `frontend/public/` — que Vite copie **à la racine de `dist/`,
    hors `assets/`** : `favicon.svg`, `icons.svg`, et demain un `robots.txt` ou une police —
    recevrait `index.html` en 200 avec un type MIME faux dès qu'il manquerait, ce que le navigateur
    signale par une erreur obscure. Une liste de préfixes ne peut pas suivre le contenu d'un
    répertoire.
    """
    entetes = dict(scope.get("headers") or [])
    return b"text/html" in entetes.get(b"accept", b"")


class _StatiquesSpa(StaticFiles):
    """`StaticFiles` qui **replie les liens profonds** vers `index.html` (routage côté client).

    Nécessaire dès que la SPA a des routes (E14US003) : `F5` sur `/admin/12/pilotage/supervision`
    demande au serveur un fichier qui n'existe pas — sans repli, l'utilisateur reçoit un 404 au lieu
    de son écran.

    Le repli est **doublement borné**, et les deux bornes attrapent des cas différents :
    `_SEGMENTS_SERVEUR` protège les routes du serveur (une 404 d'API doit rester une 404), et
    `_demande_une_page` protège **tout le reste** — aucune ressource manquante ne reçoit du HTML,
    quel que soit son emplacement dans `dist/`.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except ErreurHttpStarlette as erreur:
            sur_le_serveur = _premier_segment(path) in _SEGMENTS_SERVEUR
            if erreur.status_code != 404 or sur_le_serveur or not _demande_une_page(scope):
                raise
            return await super().get_response("index.html", scope)


def frontend_dist_dir() -> Path:
    """Répertoire du build front : surcharge d'environnement, sinon `frontend/dist/`.

    Par défaut, résolu relativement au dépôt (`backend/api/spa.py` → racine → `frontend/dist`).
    La surcharge `KERVIGNARC_FRONTEND_DIST` sert au packaging (chemin embarqué) et aux tests.
    """
    surcharge = os.environ.get(_ENV_VAR)
    if surcharge:
        return Path(surcharge)
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"


def monter_spa(app: FastAPI, dist_dir: Path) -> None:
    """Monte le build front à la racine `/` (index + assets), en servant `index.html`.

    `html=True` : `/` renvoie `index.html`. Le **repli des liens profonds** vers `index.html` est
    assuré par `_StatiquesSpa` — la SPA a désormais des routes (`/admin/…`, `/cible`, `/scoreur`,
    `/public`), donc un rechargement sur une URL profonde doit rendre l'application, pas un 404.
    """
    app.mount("/", _StatiquesSpa(directory=str(dist_dir), html=True), name="spa")
