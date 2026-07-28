"""Canal WebSocket **isolé** de la simulation — `/ws/simulation` (E15US003, ADR-0055 §5).

Jumeau de `/ws` (temps réel réel), mais servi par un `Broadcaster` **dédié**
(`app.state.broadcaster_simulation`) : le simulé et le réel ne partagent aucun hub. Un client
s'abonne, reçoit `connected`, puis chaque signal `simulation_modifiee` (« la session N a changé ») ;
il recharge alors l'état de la session par REST. Aucune écriture simulée ne passe par la file
d'écriture, donc le canal réel reste muet pendant une simulation (ADR-0054 §6), et réciproquement.
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket

from api.realtime import pump
from infrastructure.realtime import Broadcaster, LiveEvent

router = APIRouter(tags=["realtime"])


@router.websocket("/ws/simulation")
async def live_simulation(websocket: WebSocket) -> None:
    """Abonne le client au canal **simulé** et lui pousse les signaux jusqu'à sa déconnexion."""
    broadcaster: Broadcaster = websocket.app.state.broadcaster_simulation
    await websocket.accept()
    with broadcaster.subscribe() as subscription:
        await websocket.send_json(LiveEvent("connected").as_message())
        await pump(websocket, subscription)
