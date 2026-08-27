"""Instantané cohérent d'une base **ouverte et en service** (API `backup` de SQLite, page à page).

⚠️ **Une sauvegarde est une LECTURE** : elle ne passe donc pas par la file d'écriture (règle 7).
Appelée hors boucle, par la sauvegarde périodique comme par la composition d'archive.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def copier_base_coherente(source: Path, cible: Path) -> None:
    """Copie la base `source` vers `cible` par l'API de sauvegarde en ligne de SQLite.

    `cible` est créée (ou écrasée) ; son dossier parent doit exister. La copie est un
    **instantané cohérent** de la source, sûre même si des lectures concurrentes ont lieu.
    """
    connexion_source = sqlite3.connect(str(source))
    try:
        # `source` est la base **vive** : sous contention rare (checkpoint WAL, opération
        # exclusive) un `database is locked` avorterait la copie. On laisse SQLite patienter
        # brièvement plutôt qu'échouer sec (busy_timeout) — la copie WAL reste cohérente.
        connexion_source.execute("PRAGMA busy_timeout = 5000")
        connexion_cible = sqlite3.connect(str(cible))
        try:
            connexion_source.backup(connexion_cible)
        finally:
            connexion_cible.close()
    finally:
        connexion_source.close()
