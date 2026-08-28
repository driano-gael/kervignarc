"""Réglages de sauvegarde périodique, par variables d'environnement (règle 12).

Intervalle 900 s par défaut — `0` **désactive**. Rétention 48 copies (~12 h). Dossier `backups/`
à côté de l'exécutable.
"""

from __future__ import annotations

import os
from pathlib import Path

from release import chemins

_VAR_INTERVALLE = "KERVIGNARC_BACKUP_INTERVAL_SECONDS"
_VAR_RETENTION = "KERVIGNARC_BACKUP_RETENTION"
_VAR_DOSSIER = "KERVIGNARC_BACKUP_DIR"

INTERVALLE_DEFAUT_SECONDES = 900
RETENTION_DEFAUT = 48


def intervalle_secondes() -> int:
    """Période entre deux sauvegardes (secondes) ; `0` ou moins désactive la sauvegarde."""
    brut = os.environ.get(_VAR_INTERVALLE)
    if brut is None:
        return INTERVALLE_DEFAUT_SECONDES
    try:
        return int(brut)
    except ValueError:
        return INTERVALLE_DEFAUT_SECONDES


def retention() -> int:
    """Nombre de sauvegardes conservées (au moins 1)."""
    brut = os.environ.get(_VAR_RETENTION)
    if brut is None:
        return RETENTION_DEFAUT
    try:
        return max(1, int(brut))
    except ValueError:
        return RETENTION_DEFAUT


def dossier_sauvegardes() -> Path:
    """Dossier des sauvegardes : variable d'environnement si définie, sinon `backups/` local."""
    brut = os.environ.get(_VAR_DOSSIER)
    if brut is not None:
        return Path(brut)
    return chemins.dossier_donnees() / "backups"
