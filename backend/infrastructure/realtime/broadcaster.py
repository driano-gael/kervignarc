"""Diffusion temps réel — hub d'abonnés WebSocket (guide §7, ADR-0005 ; CDC technique §6.2).

Adapter sortant de diffusion : après **commit** d'une écriture, le writer unique
(E00US007) pousse un `LiveEvent` que le `Broadcaster` **fan-out** vers tous les abonnés
connectés. Point clé : le writer tourne sur un **thread**, la diffusion WebSocket sur la
**boucle asyncio** ; `publish()` franchit ce pont via `loop.call_soon_threadsafe` —
thread-safe et non bloquant pour le writer.

Modèle minimal (walking skeleton) : **un canal unique**, diffusion à tous les abonnés.
L'abonnement par **sujet / tournoi** (CDC §6.2) viendra avec les US métier.
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LiveEvent:
    """Événement de diffusion temps réel — contrat de message minimal (évolutif)."""

    type: str
    data: dict[str, Any] = field(default_factory=dict)

    def as_message(self) -> dict[str, Any]:
        """Représentation JSON poussée aux clients WebSocket."""
        return {"type": self.type, "data": self.data}


class Subscription:
    """Abonnement d'un client : une file asyncio alimentée par le `Broadcaster`."""

    def __init__(self, broadcaster: Broadcaster, queue: asyncio.Queue[LiveEvent]) -> None:
        self._broadcaster = broadcaster
        self._queue = queue

    async def receive(self) -> LiveEvent:
        """Attend le prochain événement diffusé."""
        return await self._queue.get()

    def close(self) -> None:
        """Désabonne le client (idempotent)."""
        self._broadcaster.unsubscribe(self._queue)

    def __enter__(self) -> Subscription:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class Broadcaster:
    """Hub de diffusion : gère les abonnés et pousse les événements post-commit.

    `bind_loop()` mémorise la boucle asyncio au démarrage de l'app ; `publish()`, appelé
    depuis le thread du writer, y planifie le fan-out. Le fan-out et la gestion des abonnés
    sont protégés par un verrou (accès concurrents boucle/threads).
    """

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subscribers: set[asyncio.Queue[LiveEvent]] = set()
        self._lock = threading.Lock()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Mémorise la boucle asyncio cible (démarrage de l'app)."""
        self._loop = loop

    def unbind_loop(self) -> None:
        """Oublie la boucle (arrêt de l'app) : les publications suivantes sont ignorées."""
        self._loop = None

    def subscribe(self) -> Subscription:
        """Enregistre un abonné et renvoie son `Subscription`.

        À appeler **depuis la boucle asyncio** (handler WebSocket) : la file est liée à
        la boucle courante.
        """
        queue: asyncio.Queue[LiveEvent] = asyncio.Queue()
        with self._lock:
            self._subscribers.add(queue)
        return Subscription(self, queue)

    def unsubscribe(self, queue: asyncio.Queue[LiveEvent]) -> None:
        """Retire un abonné (idempotent)."""
        with self._lock:
            self._subscribers.discard(queue)

    def publish(self, event: LiveEvent) -> None:
        """Diffuse `event` à tous les abonnés. **Appelable depuis n'importe quel thread.**

        Planifie le fan-out sur la boucle asyncio (`call_soon_threadsafe`) : sûr depuis le
        thread du writer, sans le bloquer. Sans boucle liée (app arrêtée), l'événement est
        ignoré.
        """
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        loop.call_soon_threadsafe(self._fanout, event)

    def _fanout(self, event: LiveEvent) -> None:
        """Distribue l'événement aux files des abonnés (exécuté sur la boucle asyncio)."""
        with self._lock:
            subscribers = list(self._subscribers)
        for queue in subscribers:
            queue.put_nowait(event)

    def subscriber_count(self) -> int:
        """Nombre d'abonnés connectés (diagnostic / tests)."""
        with self._lock:
            return len(self._subscribers)
