"""Fabrique le binaire de release (E11US001) : build front → PyInstaller.

`npm run build` → `frontend/dist/` (sauf `--no-build`), puis PyInstaller sur `kervignarc.spec` →
`backend/dist/kervignarc[.exe]`, onefile auto-contenu. Usage depuis `backend/`, venv dev actif :
`python build_release.py [--no-build]`. La procédure de déploiement vit dans `docs/deploiement.md`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Réutilise le build front de l'entrée de dev — même commande `npm run build`, pas de doublon.
from run_dev import construire_front

_BACKEND_ROOT = Path(__file__).resolve().parent


def packager() -> None:
    """Lance PyInstaller sur la spec (onefile) depuis la racine backend."""
    print("-> Packaging PyInstaller (kervignarc.spec)...")
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "kervignarc.spec"],
        cwd=_BACKEND_ROOT,
        check=True,
    )


def main() -> None:
    """Build front (optionnel) → packaging PyInstaller."""
    if "--no-build" not in sys.argv:
        construire_front()
    packager()
    exe = "kervignarc.exe" if sys.platform == "win32" else "kervignarc"
    print(f"-> Binaire prêt : {_BACKEND_ROOT / 'dist' / exe}")


if __name__ == "__main__":
    main()
