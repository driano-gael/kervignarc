"""Adapters d'accès administrateur (E10US002) : identifiants `.env` + sessions en mémoire.

Implémentent les ports définis côté application (`application.auth`) : store d'identifiants
(persistance `.env`) et store de sessions (jetons opaques). Câblés dans la composition root.
"""

from infrastructure.auth.config import DEFAULT_ENV_FILE, default_env_path
from infrastructure.auth.identifiants import (
    CLE_LOGIN,
    CLE_MOT_DE_PASSE,
    AdminCredentialsStore,
)
from infrastructure.auth.sessions import SessionStore

__all__ = [
    "CLE_LOGIN",
    "CLE_MOT_DE_PASSE",
    "DEFAULT_ENV_FILE",
    "AdminCredentialsStore",
    "SessionStore",
    "default_env_path",
]
