"""Arrêt propre à la **fermeture de la console** Windows (E11US006, CA 7, ADR-0119).

Python ne traduit pas `CTRL_CLOSE_EVENT` en signal : sans ce gestionnaire, la croix de la fenêtre
tue le processus sans passer par le `lifespan`, donc sans drainer la file d'écriture.
⚠️ Windows tue le processus dès que le gestionnaire rend la main, et au plus tard ~5 s après
l'événement : le gestionnaire **attend** la fin de l'arrêt, dans ce délai.
"""

from __future__ import annotations

import logging
import sys
import threading
from collections.abc import Callable

_logger = logging.getLogger(__name__)

# Valeurs de l'API Windows `SetConsoleCtrlHandler` (wincon.h).
_CTRL_CLOSE_EVENT = 2
_CTRL_LOGOFF_EVENT = 5
_CTRL_SHUTDOWN_EVENT = 6
_FERMETURES = frozenset({_CTRL_CLOSE_EVENT, _CTRL_LOGOFF_EVENT, _CTRL_SHUTDOWN_EVENT})

DELAI_ARRET_S = 4.5
"""Sous les ~5 s que Windows accorde avant de tuer le processus."""

ATTENTE_CONNEXIONS_S = 2
"""`timeout_graceful_shutdown` d'uvicorn : ⚠️ doit laisser au drain le reste de `DELAI_ARRET_S`."""


def traiter_evenement(
    evenement: int, demander_arret: Callable[[], None], arrete: threading.Event, delai: float
) -> bool:
    """Vrai si l'événement est une fermeture, prise en charge ; faux pour Ctrl+C / Ctrl+Break.

    Ctrl+C et Ctrl+Break restent aux signaux, qu'uvicorn traite déjà en arrêt propre.
    """
    if evenement not in _FERMETURES:
        return False
    demander_arret()
    arrete.wait(delai)
    return True


def installer(demander_arret: Callable[[], None], arrete: threading.Event) -> object | None:
    """Installe le gestionnaire ; renvoie le rappel, **à garder vivant** tant que le serveur tourne.

    Sans référence, le ramasse-miettes libère le rappel ctypes et Windows appelle une adresse morte.
    """
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    # `HandlerRoutine` rend un BOOL Windows (entier 32 bits), pas un `_Bool` : avec `c_bool`, les
    # bits hauts du registre de retour sont indéterminés.
    prototype = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.DWORD)

    def _gestionnaire(evenement: int) -> bool:
        return traiter_evenement(evenement, demander_arret, arrete, DELAI_ARRET_S)

    rappel = prototype(_gestionnaire)
    if not ctypes.windll.kernel32.SetConsoleCtrlHandler(rappel, True):
        _logger.warning("Gestionnaire de console non installé : la croix arrêtera sans drainer.")
        return None
    return rappel
