"""Résolution des chemins du binaire de release (E11US001).

Un exécutable PyInstaller vit dans **deux mondes** :

- **Ressources embarquées** (lecture seule) : le front `frontend/dist/` et les migrations
  `migrations/` sont dépaquetés au lancement dans un dossier temporaire exposé par
  `sys._MEIPASS`. On lit là.
- **Données mutables et persistantes** : la base SQLite doit **survivre** entre deux
  lancements et être inscriptible ; on ne l'écrit donc **pas** dans `_MEIPASS` (effacé à la
  sortie du programme) mais **à côté de l'exécutable**. Le répertoire courant ne convient
  pas : un `.exe` double-cliqué peut hériter d'un CWD arbitraire (p. ex. `C:\\Windows\\System32`).

Hors gel (dev, tests), tout retombe sur l'arborescence du dépôt — ces fonctions sont donc
utilisables partout, `run_dev.py` restant l'entrée de développement.
"""

from __future__ import annotations

import sys
from pathlib import Path

# `release/` est sous `backend/` : la racine backend est le parent du dossier de ce module.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def est_gele() -> bool:
    """Vrai si le code s'exécute dans un binaire PyInstaller (attribut `sys.frozen`)."""
    return bool(getattr(sys, "frozen", False))


def dossier_ressources() -> Path:
    """Racine des ressources en lecture seule (dossier `_MEIPASS` si gelé, dépôt sinon)."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass is not None:
        return Path(str(meipass))
    return _BACKEND_ROOT


def dossier_donnees() -> Path:
    """Dossier inscriptible et persistant de la base (à côté de l'exécutable si gelé)."""
    if est_gele():
        return Path(sys.executable).resolve().parent
    return _BACKEND_ROOT


def dossier_migrations() -> Path:
    """Dossier `migrations/` (env.py + versions/), embarqué en ressource si gelé."""
    return dossier_ressources() / "migrations"


def dossier_front() -> Path:
    """Build front `frontend/dist/` à servir en statique.

    Gelé : embarqué sous `_MEIPASS/frontend/dist`. Dépôt : `../frontend/dist` (hors backend).
    """
    if est_gele():
        return dossier_ressources() / "frontend" / "dist"
    return _BACKEND_ROOT.parent / "frontend" / "dist"


def url_base_donnees() -> str:
    """URL SQLite de la base persistante : fichier `kervignarc.db` du dossier données.

    Chemin **absolu** (au format POSIX, accepté par SQLAlchemy y compris sous Windows) pour
    que la base soit toujours celle d'à côté de l'exe, indépendamment du CWD au lancement.
    """
    fichier = dossier_donnees() / "kervignarc.db"
    return f"sqlite:///{fichier.as_posix()}"
