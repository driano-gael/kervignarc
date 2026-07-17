"""Endpoints REST des blasons (`/api/v1`) — CRUD des blasons d'un tournoi (E01US005).

Suit le patron de bout en bout (E00US009) :
- **DTO Pydantic** distincts des agrégats de domaine ;
- **écriture** routée par la **file d'écriture** (writer unique, ADR-0005), protégée par
  `exiger_admin` (E10US001/E10US002) ;
- **lecture** directe exécutée **hors boucle** (threadpool) ;
- **erreurs typées** traduites à la frontière (`api/erreurs.py`).

Routes imbriquées sous le tournoi pour la création/liste (un blason appartient à un tournoi) ;
l'édition et la suppression ciblent le blason par son identifiant.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.blasons import ServiceBlasons
from domain.blason import Blason
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["blasons"])


class CreerBlasonRequete(BaseModel):
    """Corps de création d'un blason (nom, taille dans `]0, 1]`, capacité `>= 1`).

    `zones` (E01US014) est **facultatif** : omis, le domaine applique son défaut (le jeu complet
    d'un blason simple). La validation des valeurs appartient au domaine, pas au DTO.
    """

    nom: str
    taille: float
    capacite: int
    zones: list[str] | None = None


class ModifierBlasonRequete(BaseModel):
    """Corps d'édition d'un blason (mêmes champs que la création).

    `zones` omis laisse les zones du blason **inchangées** (édition partielle du champ).
    """

    nom: str
    taille: float
    capacite: int
    zones: list[str] | None = None


class BlasonReponse(BaseModel):
    """Représentation d'un blason renvoyée au client."""

    id: int
    tournoi_id: int
    nom: str
    taille: float
    capacite: int
    zones: list[str]

    @staticmethod
    def de_agregat(blason: Blason) -> BlasonReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert blason.id is not None, "Un blason persisté a toujours un identifiant."
        return BlasonReponse(
            id=blason.id,
            tournoi_id=blason.tournoi_id,
            nom=blason.nom,
            taille=blason.taille,
            capacite=blason.capacite,
            zones=list(blason.zones),
        )


@router.get("/tournois/{tournoi_id}/blasons", response_model=list[BlasonReponse])
async def lister_blasons(tournoi_id: int, request: Request) -> list[BlasonReponse]:
    """Liste les blasons d'un tournoi : lecture directe exécutée hors de la boucle."""
    service: ServiceBlasons = request.app.state.service_blasons
    blasons = await run_in_threadpool(service.lister, tournoi_id)
    return [BlasonReponse.de_agregat(blason) for blason in blasons]


@router.post(
    "/tournois/{tournoi_id}/blasons",
    status_code=201,
    response_model=BlasonReponse,
    dependencies=[Depends(exiger_admin)],
)
async def creer_blason(
    tournoi_id: int, requete: CreerBlasonRequete, request: Request
) -> BlasonReponse:
    """Crée un blason dans un tournoi (**action admin**) : écriture via la file (ADR-0005)."""
    service: ServiceBlasons = request.app.state.service_blasons
    write_queue: WriteQueue = request.app.state.write_queue
    blason = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.creer(
                tournoi_id, requete.nom, requete.taille, requete.capacite, requete.zones
            )
        )
    )
    return BlasonReponse.de_agregat(blason)


@router.put(
    "/blasons/{blason_id}",
    response_model=BlasonReponse,
    dependencies=[Depends(exiger_admin)],
)
async def modifier_blason(
    blason_id: int, requete: ModifierBlasonRequete, request: Request
) -> BlasonReponse:
    """Édite un blason (**action admin**) : écriture via la file (ADR-0005)."""
    service: ServiceBlasons = request.app.state.service_blasons
    write_queue: WriteQueue = request.app.state.write_queue
    blason = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.modifier(
                blason_id, requete.nom, requete.taille, requete.capacite, requete.zones
            )
        )
    )
    return BlasonReponse.de_agregat(blason)


@router.delete(
    "/blasons/{blason_id}",
    status_code=204,
    dependencies=[Depends(exiger_admin)],
)
async def supprimer_blason(blason_id: int, request: Request) -> Response:
    """Supprime un blason (**action admin**) : écriture via la file ; renvoie 204."""
    service: ServiceBlasons = request.app.state.service_blasons
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(write_queue.submit(lambda: service.supprimer(blason_id)))
    return Response(status_code=204)
