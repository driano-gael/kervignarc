"""Copie **cohérente** d'une base SQLite vive — API `sqlite3.backup` (E11US003).

Copier une base SQLite en mode WAL par un simple `shutil.copy` est **faux** : le fichier
`.db` seul ignore les pages encore dans le journal `-wal`, et une copie prise pendant une
écriture peut être tronquée. L'API en ligne `sqlite3.Connection.backup()` fait la copie
**page à page** au niveau moteur : elle inclut l'état WAL et redémarre proprement si la source
est modifiée pendant la copie. C'est le mécanisme prévu par SQLite pour sauvegarder une base
**ouverte et en service**.

Une sauvegarde est une **lecture** : elle ne passe donc **pas** par la file d'écriture
(règle 7 — seules les écritures y transitent ; les lectures sont concurrentes, WAL). Ce module
est appelé hors boucle événementielle (threadpool), aussi bien par la sauvegarde périodique
(`infrastructure/backup/`) que par la composition d'archive (`infrastructure/archive/`).
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
