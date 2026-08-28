"""Hub temps réel — **un canal unique, sans sujets**, et c'est resté un choix.

⚠️ **Ne pas lire le mono-canal comme une dette en attente** : deux décisions s'appuient dessus.
ADR-0064 fait du pilotage d'un écran un **état lu** parce que le hub ne sait pas cibler ; ADR-0055
isole la simulation dans un **second hub** plutôt que par un filtre de sujet — deux hubs rendent
l'isolement structurel, un filtre le rendrait conditionnel à l'absence de bug. L'introduire
demanderait de rouvrir ces deux ADR.
"""

from __future__ import annotations

import asyncio
import contextlib

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from infrastructure.realtime import Broadcaster, LiveEvent, Subscription

router = APIRouter(tags=["realtime"])


@router.websocket("/ws")
async def live(websocket: WebSocket) -> None:
    """Abonne le client et lui pousse les événements diffusés jusqu'à sa déconnexion."""
    broadcaster: Broadcaster = websocket.app.state.broadcaster
    await websocket.accept()
    with broadcaster.subscribe() as subscription:
        await websocket.send_json(LiveEvent("connected").as_message())
        await pump(websocket, subscription)


async def pump(websocket: WebSocket, subscription: Subscription) -> None:
    """Pousse les événements vers le client ; s'arrête proprement à la déconnexion.

    Deux tâches concurrentes : l'une **émet** les événements diffusés, l'autre **surveille** la
    fermeture du socket. Dès que l'une se termine, on annule l'autre et on l'attend en absorbant
    son exception (dont l'annulation) : aucune ne fuite au démontage. **Helper partagé** (public) :
    le canal réel et celui de simulation (E15US003) le réutilisent plutôt que de dupliquer une
    logique d'annulation non triviale.
    """
    emettre = asyncio.create_task(_emettre(websocket, subscription))
    surveiller = asyncio.create_task(_surveiller_deconnexion(websocket))
    taches = (emettre, surveiller)
    try:
        await asyncio.wait(taches, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for tache in taches:
            tache.cancel()
        for tache in taches:
            with contextlib.suppress(BaseException):
                await tache


async def _emettre(websocket: WebSocket, subscription: Subscription) -> None:
    """Émet vers le client chaque événement diffusé (boucle jusqu'à annulation)."""
    while True:
        event = await subscription.receive()
        await websocket.send_json(event.as_message())


async def _surveiller_deconnexion(websocket: WebSocket) -> None:
    """Draine les messages entrants pour détecter la fermeture du socket."""
    with contextlib.suppress(WebSocketDisconnect):
        while True:
            await websocket.receive_text()
