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

_ENV_VAR = "KERVIGNARC_FRONTEND_DIST"


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

    `html=True` : `/` renvoie `index.html`. Le repli des liens profonds vers `index.html`
    (routage côté client) sera ajouté quand la SPA aura des routes ; ici, une seule page.
    """
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="spa")
