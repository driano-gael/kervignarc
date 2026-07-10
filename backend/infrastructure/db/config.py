"""Configuration de la source de données (URL SQLite).

Point unique d'où proviennent l'URL par défaut et sa surcharge par variable
d'environnement — consommé aussi bien par la composition root que par Alembic
(`migrations/env.py`), pour éviter toute duplication de la valeur.
"""

from __future__ import annotations

import os

# Base locale mono-club (fichier à côté de l'exécutable/CWD) — cf. ADR-0002/0005.
DEFAULT_DATABASE_URL = "sqlite:///kervignarc.db"

# Variable d'environnement de surcharge (tests, chemins de déploiement).
_ENV_VAR = "KERVIGNARC_DATABASE_URL"


def default_database_url() -> str:
    """URL de la base : variable d'environnement si définie, sinon défaut local."""
    return os.environ.get(_ENV_VAR, DEFAULT_DATABASE_URL)
