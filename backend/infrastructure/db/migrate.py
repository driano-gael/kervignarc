"""Application programmatique des migrations Alembic (E00US006, E11US001).

Point unique d'où l'on déclenche `alembic upgrade head` **depuis du code Python** (par
opposition à la CLI `alembic`). Réutilisé par l'exécutable de dev (`run_dev.py`) et par le
point d'entrée de release (`run.py`) : tous deux doivent, au démarrage, garantir que le
schéma est à jour. Au **1er lancement**, `upgrade head` sur un fichier SQLite absent le
crée et applique la suite complète des révisions — c'est le CA « base au 1er lancement ».

Le `script_location` est **injecté** plutôt que lu depuis `alembic.ini` : sous PyInstaller,
le dossier `migrations/` est embarqué à un chemin (`sys._MEIPASS`) sans rapport avec
l'emplacement d'`alembic.ini` au moment du build — seul l'appelant connaît le vrai chemin
à l'exécution.
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config


def appliquer_migrations(
    migrations_dir: Path,
    *,
    alembic_ini: Path | None = None,
    url: str | None = None,
) -> None:
    """Applique toutes les migrations jusqu'à `head` (crée la base si absente).

    - `migrations_dir` : dossier `migrations/` (contenant `env.py` et `versions/`).
    - `alembic_ini` : `alembic.ini` (logging, options) — optionnel ; un `Config` sans
      fichier suffit, `env.py` résout l'URL via `infrastructure.db.config`.
    - `url` : surcharge explicite de l'URL SQLite ; sinon `env.py` prend le défaut
      applicatif (variable d'env `KERVIGNARC_DATABASE_URL` ou défaut local). Réservé aux
      tests — en production, on passe par la variable d'environnement pour que la
      composition root vise la **même** base.
    """
    config = Config(str(alembic_ini)) if alembic_ini is not None else Config()
    config.set_main_option("script_location", str(migrations_dir))
    if url is not None:
        config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
