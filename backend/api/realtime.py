"""Canal WebSocket temps réel — adapter entrant (couche API ; CDC technique §6.2).

`/ws` : un client **s'abonne** au flux d'événements ; le serveur pousse chaque `LiveEvent`
diffusé après commit d'une écriture (E00US008). Un message `connected` est envoyé dès
l'abonnement (le client sait qu'il est en ligne et peut se resynchroniser).

Modèle minimal (walking skeleton) : **un canal unique**, sans sujets — et il l'est resté.

⚠️ **Ne pas lire cette ligne comme une étape à venir.** L'abonnement par sujet / tournoi
(CDC §6.2) était annoncé « avec les US métier » ; les US métier sont livrées et le hub est
toujours mono-canal, parce que le projet a **décidé autour** plutôt que de l'étendre :

- [ADR-0064](../../docs/adr/0064-ecran-de-salle-poste-type-et-pilotage-par-etat-lu.md) fait du
  pilotage d'un écran de salle un **état lu** et non un ordre poussé — précisément parce que le hub
  ne sait pas cibler un destinataire (et parce que la *fin* d'une prise de contrôle naît du temps
  qui passe, qu'aucun événement ne peut diffuser) ;
- [ADR-0055](../../docs/adr/0055-session-de-simulation-vivante-pilotee-par-pas.md) isole la
  simulation dans un **second hub** (`/ws/simulation`) plutôt que par un filtre de sujet : deux hubs
  rendent l'isolement **structurel**, un filtre le rendrait conditionnel à l'absence de bug.

Le mono-canal est donc aujourd'hui une **contrainte assumée sur laquelle deux décisions
s'appuient**, pas une dette en attente. L'introduire demanderait de rouvrir ces deux ADR.
*(Réévalué le 08/08/2026 : la formulation d'origine promettait une suite qui n'arrive plus.)*
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

    Deux tâches concurrentes : l'une **émet** les événements diffusés, l'autre **surveille**
    la fermeture du socket. Dès que l'une se termine, on annule l'autre et on l'attend en
    absorbant son exception (dont l'annulation) : aucune ne fuite au démontage.

    **Helper partagé** (public, sans underscore) : le canal réel (`/ws`) **et** le canal isolé de
    simulation (`/ws/simulation`, E15US003) réutilisent cette boucle plutôt que de dupliquer sa
    logique d'annulation non triviale (revue axe A/C2 — un import de `_pump` privé inter-module).
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
