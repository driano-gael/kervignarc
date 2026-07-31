"""Prépare une base de test au schéma courant — **en migrant une fois, puis en copiant**.

Chaque fixture de test créait sa base par un `alembic upgrade head` complet. Mesuré sur le poste de
développement au 31/07/2026 : **3,74 s** pour rejouer les 36 migrations, contre **2,2 ms** pour
copier le fichier de 156 Ko qui en résulte — un rapport de **1664**. Multiplié par le millier de
tests qui montent une application, c'est l'essentiel du temps de la suite.

**Ce que ce module ne sacrifie pas.** Les migrations sont toujours **réellement rejouées**, depuis
une base vide, par le même `upgrade head` qu'exécute le produit à son premier lancement
(`infrastructure/db/migrate.py`) : le garde-fou « la chaîne de migrations produit bien le schéma
que `models.py` décrit » reste entier. Il ne s'exerce plus qu'**une fois par session** au lieu d'une
fois par test — ce qu'il faut, puisque c'est une propriété de la chaîne, pas de chaque test.

**Ce module n'est pas dans `conftest.py`, et c'est délibéré** : ce dernier doit rester importable
avec `pytest` pour seule dépendance (hook pre-commit `domain-isolation`), or Alembic n'en fait pas
partie. Seuls les modules de test qui montent une base l'importent — ils dépendent déjà d'Alembic.

⚠️ **Les tests de migration ne passent pas par ici.** Ceux qui visent une révision *intermédiaire*
(`test_migration_0036` s'arrête à `0035` pour y insérer des lignes à l'ancienne forme avant
d'appliquer la migration) doivent continuer à piloter Alembic eux-mêmes : c'est le chemin qu'ils
testent.
"""

from __future__ import annotations

import atexit
import shutil
import sqlite3
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config

_BACKEND_ROOT = Path(__file__).resolve().parents[1]

_template: Path | None = None
"""La base migrée de référence, construite au premier appel et réutilisée ensuite."""


def _config(url: str) -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _construire_template() -> Path:
    """Migre une base neuve jusqu'à `head` et rend son chemin (une seule fois par session)."""
    dossier = Path(tempfile.mkdtemp(prefix="kervignarc-schema-"))
    atexit.register(shutil.rmtree, dossier, True)
    chemin = dossier / "schema.db"
    command.upgrade(_config(f"sqlite:///{chemin.as_posix()}"), "head")
    # Repli du journal dans le fichier principal : sans cela, un `-wal` resté à côté rendrait la
    # copie incomplète (le schéma vivrait pour partie dans un fichier qu'on ne copie pas).
    with sqlite3.connect(chemin) as connexion:
        connexion.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    return chemin


def preparer_base(url: str) -> None:
    """Crée, à l'emplacement désigné par `url`, une base au schéma courant.

    `url` est une URL SQLAlchemy de fichier SQLite (`sqlite:///chemin/vers/base.db`) — la forme que
    les fixtures construisent depuis `tmp_path`.
    """
    global _template
    if _template is None:
        _template = _construire_template()
    destination = Path(url.removeprefix("sqlite:///"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(_template, destination)
