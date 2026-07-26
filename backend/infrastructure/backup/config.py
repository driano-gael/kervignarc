"""Paramètres de la sauvegarde périodique — variables d'environnement (E11US003).

Miroir de `infrastructure/db/config.py` et `infrastructure/auth/config.py` : le projet n'a pas
de `BaseSettings`, la configuration se lit dans `os.environ` avec un défaut et une variable de
surcharge (règle 12 — simplicité hors domaine). `run.py` peut publier ces variables ; à défaut,
les valeurs par défaut conviennent au déploiement standard (dossier `backups/` à côté de l'exe).

- **intervalle** (`KERVIGNARC_BACKUP_INTERVAL_SECONDS`) : période entre deux sauvegardes. 900 s
  (15 min) par défaut — assez fréquent pour un tournoi d'une journée, assez espacé pour rester
  invisible. `0` (ou négatif) **désactive** la sauvegarde périodique.
- **rétention** (`KERVIGNARC_BACKUP_RETENTION`) : nombre de sauvegardes conservées (les plus
  récentes) ; les plus anciennes sont purgées. 48 par défaut (≈ 12 h à 15 min).
- **dossier** (`KERVIGNARC_BACKUP_DIR`) : où déposer les copies. Par défaut `backups/` dans le
  dossier de données (à côté de l'exécutable en release, cf. `release/chemins.py`).
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
