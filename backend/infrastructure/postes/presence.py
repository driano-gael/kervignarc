"""Adapter : présence des postes par heartbeat, en mémoire (E12US001, ADR-0038).

Réalise le port `domain.ports.RegistrePresence`. Dictionnaire `poste_id → ActivitePoste` (instant du
dernier heartbeat + IP vue), protégé par un verrou (lectures/écritures peuvent venir des threads du
threadpool, comme le `PosteSessionStore`). **Sans persistance** : effacé au redémarrage serveur, au
même titre que le jeton de poste (ADR-0029) et le départ courant (ADR-0034). Aucune éviction : le
dictionnaire est borné par le nombre de postes d'un tournoi (~30) — un heartbeat écrase l'ancien.
"""

from __future__ import annotations

import datetime
import threading

from domain.poste import PosteId
from domain.supervision import ActivitePoste


class RegistrePresenceMemoire:
    """Présence des postes en mémoire : `poste_id` → dernière activité (heartbeat + IP)."""

    def __init__(self) -> None:
        self._activite: dict[PosteId, ActivitePoste] = {}
        self._verrou = threading.Lock()

    def enregistrer(self, poste_id: PosteId, instant: datetime.datetime, ip: str | None) -> None:
        """Mémorise le heartbeat d'un poste (dernière vue + IP), en écrasant le précédent."""
        with self._verrou:
            self._activite[poste_id] = ActivitePoste(instant=instant, ip=ip)

    def derniere_activite(self, poste_id: PosteId) -> ActivitePoste | None:
        """Dernière présence signalée par ce poste, ou `None` s'il n'a jamais pingé."""
        with self._verrou:
            return self._activite.get(poste_id)

    def oublier(self, poste_id: PosteId) -> None:
        """Oublie la présence d'un poste (à sa révocation) ; sans effet s'il est absent."""
        with self._verrou:
            self._activite.pop(poste_id, None)
