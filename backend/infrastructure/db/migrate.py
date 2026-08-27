"""Migration au démarrage — `upgrade head`, y compris sur une base absente au 1er lancement.

⚠️ **Le `script_location` est INJECTÉ, jamais lu depuis `alembic.ini`** : sous PyInstaller, le
dossier des migrations est embarqué à un chemin sans rapport avec celui du fichier de config au
moment du build — seul l'appelant connaît le vrai chemin à l'exécution.
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

    `migrations_dir` : dossier contenant `env.py` et `versions/`. `alembic_ini` est optionnel — un
    `Config` sans fichier suffit, `env.py` résolvant l'URL via `infrastructure.db.config`. ⚠️ `url`
    est **réservé aux tests** : en production on passe par `KERVIGNARC_DATABASE_URL`, pour que la
    composition root vise la **même** base.
    """
    config = Config(str(alembic_ini)) if alembic_ini is not None else Config()
    config.set_main_option("script_location", str(migrations_dir))
    if url is not None:
        config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
