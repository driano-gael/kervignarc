"""Sauvegardes périodiques et rétention des N plus récentes.

⚠️ **Le tri par NOM suffit** : `kervignarc-AAAAMMJJ-HHMMSS.db` est croissant dans l'ordre
lexicographique. Pas besoin des `mtime`, peu fiables et non déterministes en test. L'instant vient
du port `Horloge`, jamais de `datetime.now()`.
"""

from __future__ import annotations

import logging
from pathlib import Path

from domain.ports import Horloge
from infrastructure.db.snapshot import copier_base_coherente

_logger = logging.getLogger(__name__)

_MOTIF = "kervignarc-*.db"


class SauvegardeSQLite:
    """Sauvegarde horodatée de la base avec rétention des N copies les plus récentes."""

    def __init__(self, source: Path, dossier: Path, retention: int, horloge: Horloge) -> None:
        self._source = source
        self._dossier = dossier
        self._retention = max(1, retention)
        self._horloge = horloge

    def sauvegarder(self) -> Path:
        """Dépose une copie horodatée, purge les plus anciennes, renvoie le chemin créé."""
        self._dossier.mkdir(parents=True, exist_ok=True)
        horodatage = self._horloge.maintenant().strftime("%Y%m%d-%H%M%S")
        cible = self._dossier / f"kervignarc-{horodatage}.db"
        copier_base_coherente(self._source, cible)
        self._appliquer_retention()
        _logger.info("Sauvegarde de la base : %s", cible.name)
        return cible

    def _appliquer_retention(self) -> None:
        """Supprime les sauvegardes au-delà des `retention` plus récentes (tri par nom)."""
        # `_retention >= 1` (clampé au constructeur), donc `[:-retention]` est toujours correct :
        # ≤ retention fichiers ⇒ tranche vide (on garde tout) ; au-delà ⇒ purge des plus anciens.
        sauvegardes = sorted(self._dossier.glob(_MOTIF))
        for ancienne in sauvegardes[: -self._retention]:
            ancienne.unlink(missing_ok=True)
