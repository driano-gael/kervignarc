"""Adapters de diffusion temps réel (guide §7, ADR-0005 ; CDC technique §6.2).

Hub de diffusion WebSocket alimenté, après commit, par le writer unique (E00US007).
Le domaine ignore tout du temps réel : ces adapters vivent dans l'infrastructure.
"""

from infrastructure.realtime.broadcaster import Broadcaster, LiveEvent, Subscription

__all__ = [
    "Broadcaster",
    "LiveEvent",
    "Subscription",
]
