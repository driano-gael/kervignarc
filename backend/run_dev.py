"""Exécutable de développement (E00US012) — lance **toute** l'app en une commande.

Enchaîne, dans l'ordre :
1. **build du front** (`npm run build` → `frontend/dist/`), sauf `--no-build` ;
2. **migrations** de la base (`alembic upgrade head`) — schéma prêt ;
3. **serveur unique** Uvicorn sur un **port fixe**, servant l'API, le WebSocket **et** la
   SPA au même origin (plus de proxy Vite).

But : un point d'entrée « double-clic » de dev, **base du packaging PyInstaller** (EPIC-11).
Usage : `python run_dev.py` (depuis `backend/`), ou `python run_dev.py --no-build` pour
réutiliser un build existant.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config

_BACKEND_ROOT = Path(__file__).resolve().parent
_FRONTEND_ROOT = _BACKEND_ROOT.parent / "frontend"

# Port **fixe** (le proxy Vite de dev et la SPA en production visent cet origin).
HOST = "127.0.0.1"
PORT = 8000


def construire_front() -> None:
    """Construit le build de production du front (`npm run build`)."""
    npm = shutil.which("npm")
    if npm is None:
        raise SystemExit(
            "npm introuvable : impossible de construire le front (installer Node >= 20), "
            "ou relancer avec --no-build pour reutiliser un build existant."
        )
    print("-> Build du front (npm run build)...")
    try:
        subprocess.run([npm, "run", "build"], cwd=_FRONTEND_ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(
            "Build du front en échec (voir la sortie npm ci-dessus). "
            "Corriger le front, ou relancer avec --no-build pour réutiliser un build existant."
        ) from exc


def migrer() -> None:
    """Applique les migrations jusqu'à la dernière révision (`alembic upgrade head`)."""
    print("-> Migrations de la base (alembic upgrade head)...")
    config = Config(str(_BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    command.upgrade(config, "head")


def main() -> None:
    """Build front (optionnel) → migrations → serveur unique sur le port fixe."""
    if "--no-build" not in sys.argv:
        construire_front()
    migrer()

    # Import tardif : l'app est câblée APRÈS le build, pour que le montage de la SPA
    # (composition root) trouve `frontend/dist/`.
    from bootstrap.composition import create_app

    print(f"-> Serveur unique sur http://{HOST}:{PORT}  (API + WebSocket + SPA)")
    uvicorn.run(create_app(), host=HOST, port=PORT)


if __name__ == "__main__":
    main()
