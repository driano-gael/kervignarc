"""Service du build front en statique — adapter entrant (couche API ; E00US012).

En production (et via l'exécutable de dev), **FastAPI sert la SPA React** (le build
`frontend/dist/`) au **même origin** que l'API : plus besoin du proxy Vite, un seul
serveur pour tout (base d'EPIC-11, packaging PyInstaller).

Le montage est **conditionnel** : s'il n'y a pas de build (dépôt fraîchement cloné, job
CI backend qui ne construit pas le front, tests), on ne monte rien — l'API reste servie
seule. Le montage se fait **en dernier**, à la racine `/`, pour ne jamais masquer les
routes déjà déclarées (`/api/v1/…`, `/ws`, `/health`, `/docs`).
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

# Préfixes qui **ne se replient jamais** vers `index.html` (E14US003). Sous ces chemins, une URL
# inconnue est une **vraie erreur** du client : la lui renvoyer en 404 est la seule réponse honnête.
# Replier tout aveuglément aurait deux effets pervers :
#  - un appel d'API vers une route inexistante recevrait une **page HTML en 200**, donc un client
#    qui croit avoir réussi et un message d'erreur introuvable dans les logs ;
#  - un asset manquant (`/assets/app-abc123.js` après un build changé) répondrait du HTML avec un
#    type MIME faux, ce que le navigateur signale par une erreur obscure au lieu d'un 404 clair.
_PREFIXES_SANS_REPLI = ("api/", "ws", "health", "docs", "redoc", "openapi.json", "assets/")


def _sous_prefixe_serveur(path: str) -> bool:
    """Le chemin demandé tombe-t-il sous un préfixe qui ne se replie pas ?

    ⚠️ **Le séparateur doit être normalisé avant la comparaison.** `StaticFiles` construit son
    `path` avec `os.path.normpath`, qui rend `api\\v1\\x` **sur Windows** — là où les préfixes sont
    écrits en `/`. Comparer brut fait donc échouer le garde sur Windows *et nulle part ailleurs* :
    la CI (Linux) resterait verte pendant que le poste de la table d'organisation renverrait une
    page HTML en 200 sur un appel d'API inexistant. Trouvé par
    `test_le_repli_ne_masque_ni_l_api_ni_les_assets`.
    """
    return path.replace(os.sep, "/").replace("\\", "/").lstrip("/").startswith(_PREFIXES_SANS_REPLI)


class _StatiquesSpa(StaticFiles):
    """`StaticFiles` qui **replie les liens profonds** vers `index.html` (routage côté client).

    Nécessaire dès que la SPA a des routes (E14US003) : `F5` sur `/admin/pilotage/supervision`
    demande au serveur un fichier qui n'existe pas — sans repli, l'utilisateur reçoit un 404 au lieu
    de son écran. Le repli est **borné** par `_PREFIXES_SANS_REPLI`.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except ErreurHttpStarlette as erreur:
            if erreur.status_code != 404 or _sous_prefixe_serveur(path):
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
