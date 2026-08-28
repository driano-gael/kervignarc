"""Exécutable de développement (E00US012) — lance **toute** l'app en une commande.

Enchaîne le build du front (sauf `--no-build`), les migrations Alembic, puis un serveur Uvicorn
unique sur port fixe servant l'API, le WebSocket **et** la SPA au même origin. Base du packaging
PyInstaller (EPIC-11). ⚠️ **Écoute `0.0.0.0` par défaut** (E11US008) : le QR encode l'origine de la
requête (`DETTE-012`), donc ouvert par l'IP LAN il devient scannable. `--host 127.0.0.1` pour une
démo isolée ; procédure dans `docs/deploiement.md`.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import uvicorn

from infrastructure.db.migrate import appliquer_migrations

_BACKEND_ROOT = Path(__file__).resolve().parent
_FRONTEND_ROOT = _BACKEND_ROOT.parent / "frontend"

# Port **fixe** (le proxy Vite de dev et la SPA en production visent cet origin).
# Écoute par défaut sur **toutes les interfaces** (E11US008) pour joindre le serveur depuis les
# tablettes du réseau local ; `--host 127.0.0.1` restreint au loopback.
HOST_DEFAUT = "0.0.0.0"
PORT = 8000


def _hote(argv: list[str]) -> str:
    """Hôte d'écoute : la valeur de `--host <valeur>` si fournie, sinon `0.0.0.0` (écoute LAN)."""
    if "--host" in argv:
        rang = argv.index("--host")
        if rang + 1 >= len(argv):
            raise SystemExit("--host attend une valeur (ex. : --host 127.0.0.1).")
        return argv[rang + 1]
    return HOST_DEFAUT


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
    appliquer_migrations(
        _BACKEND_ROOT / "migrations",
        alembic_ini=_BACKEND_ROOT / "alembic.ini",
    )


def main() -> None:
    """Build front (optionnel) → migrations → serveur unique sur le port fixe."""
    if "--no-build" not in sys.argv:
        construire_front()
    migrer()

    # Import tardif : l'app est câblée APRÈS le build, pour que le montage de la SPA
    # (composition root) trouve `frontend/dist/`.
    from bootstrap.composition import create_app

    hote = _hote(sys.argv)
    print(f"-> Serveur unique sur http://{hote}:{PORT}  (API + WebSocket + SPA)")
    if hote == "0.0.0.0":
        # Écoute LAN : afficher l'IP réelle joignable par les tablettes (l'adresse `0.0.0.0`
        # n'est pas « ouvrable » telle quelle). Réutilise l'introspection réseau du binaire de
        # release (best-effort, aucun paquet émis) — ADR-0033 / E11US001.
        from release.reseau import adresse_lan

        print(f"   Depuis une tablette du réseau : http://{adresse_lan()}:{PORT}")
    uvicorn.run(create_app(), host=hote, port=PORT)


if __name__ == "__main__":
    main()
