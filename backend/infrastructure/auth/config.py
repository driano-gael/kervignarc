"""Emplacement du fichier `.env` des identifiants admin (E10US002).

Point unique d'où provient le chemin par défaut et sa surcharge par variable d'environnement
(tests, chemins de déploiement) — miroir de `infrastructure/db/config.py`.
"""

from __future__ import annotations

import os
from pathlib import Path

# Fichier local à côté de l'exécutable/CWD (comme la base SQLite) — cf. ADR-0002/0005.
DEFAULT_ENV_FILE = ".env"

# Variable d'environnement de surcharge du chemin (tests, déploiement).
_ENV_VAR = "KERVIGNARC_ENV_FILE"


def default_env_path() -> Path:
    """Chemin du fichier `.env` : variable d'environnement si définie, sinon défaut local."""
    return Path(os.environ.get(_ENV_VAR, DEFAULT_ENV_FILE))
