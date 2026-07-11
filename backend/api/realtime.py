"""Canal WebSocket temps réel — adapter entrant (couche API ; CDC technique §6.2).

`/ws` : un client **s'abonne** au flux d'événements ; le serveur pousse chaque `LiveEvent`
diffusé après commit d'une écriture (E00US008). Un message `connected` est envoyé dès
l'abonnement (le client sait qu'il est en ligne et peut se resynchroniser).

Modèle minimal (walking skeleton) : **un canal unique**, sans sujets. L'abonnement par
sujet / tournoi (CDC §6.2) viendra avec les US métier.
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
        await _pump(websocket, subscription)


async def _pump(websocket: WebSocket, subscription: Subscription) -> None:
    """Pousse les événements vers le client ; s'arrête proprement à la déconnexion.

    Deux tâches concurrentes : l'une **émet** les événements diffusés, l'autre **surveille**
    la fermeture du socket. Dès que l'une se termine, on annule l'autre et on l'attend en
    absorbant son exception (dont l'annulation) : aucune ne fuite au démontage.
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
