"""Adapter de diffusion **isolée** de la simulation (E15US003, ADR-0055 §5).

Réalise le port applicatif `DiffusionSimulation` (`signaler(session_id)`) au-dessus d'un
`Broadcaster` **dédié** — distinct de celui du temps réel réel. L'isolement est **structurel** :
deux hubs séparés (`/ws` réel, `/ws/simulation` simulé), aucune fuite possible de l'un vers l'autre.
On ne pousse **pas** l'état par le socket : on **signale** qu'une session a changé, le front re-lit
l'état par REST — comme le canal réel (événement générique + invalidation React Query).
"""

from __future__ import annotations

from infrastructure.realtime.broadcaster import Broadcaster, LiveEvent

# Type d'événement du canal simulé : un seul, générique (le front recharge l'état de la session).
_TYPE_EVENEMENT = "simulation_modifiee"


class DiffusionSimulationBroadcaster:
    """Publie « la session N a changé » sur le broadcaster de simulation (canal
    `/ws/simulation`)."""

    def __init__(self, broadcaster: Broadcaster) -> None:
        self._broadcaster = broadcaster

    def signaler(self, session_id: int) -> None:
        """Diffuse un signal de changement pour `session_id` (fan-out à tous les abonnés
        simulés)."""
        self._broadcaster.publish(LiveEvent(_TYPE_EVENEMENT, {"session_id": session_id}))
