"""Endpoints REST des clubs (`/api/v1`) — CRUD du référentiel des clubs (E02US001).

Suit le patron de bout en bout (E00US009) :
- **DTO Pydantic** distincts des agrégats de domaine ;
- **écriture** routée par la **file d'écriture** (writer unique, ADR-0005), protégée par
  `exiger_admin` (E10US001/E10US002) ;
- **lecture** directe exécutée **hors boucle** (threadpool) ;
- **erreurs typées** traduites à la frontière (`api/erreurs.py`).

Routes **à la racine** (`/api/v1/clubs`), et non imbriquées sous un tournoi comme les blasons ou
les catégories : le référentiel est global et réutilisé d'une compétition à l'autre (E02US001).
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.clubs import ServiceClubs
from domain.club import Club
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["clubs"])


class CreerClubRequete(BaseModel):
    """Corps de création d'un club (nom non vide, unique à la casse près)."""

    nom: str


class ModifierClubRequete(BaseModel):
    """Corps de renommage d'un club (mêmes règles que la création)."""

    nom: str


class ClubReponse(BaseModel):
    """Représentation d'un club renvoyée au client."""

    id: int
    nom: str

    @staticmethod
    def de_agregat(club: Club) -> ClubReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert club.id is not None, "Un club persisté a toujours un identifiant."
        return ClubReponse(id=club.id, nom=club.nom)


@router.get("/clubs", response_model=list[ClubReponse])
async def lister_clubs(request: Request) -> list[ClubReponse]:
    """Liste le référentiel des clubs : lecture directe exécutée hors de la boucle."""
    service: ServiceClubs = request.app.state.service_clubs
    clubs = await run_in_threadpool(service.lister)
    return [ClubReponse.de_agregat(club) for club in clubs]


@router.post(
    "/clubs",
    status_code=201,
    response_model=ClubReponse,
    dependencies=[Depends(exiger_admin)],
)
async def creer_club(requete: CreerClubRequete, request: Request) -> ClubReponse:
    """Ajoute un club au référentiel (**action admin**) : écriture via la file (ADR-0005)."""
    service: ServiceClubs = request.app.state.service_clubs
    write_queue: WriteQueue = request.app.state.write_queue
    club = await asyncio.wrap_future(write_queue.submit(lambda: service.creer(requete.nom)))
    return ClubReponse.de_agregat(club)


@router.put(
    "/clubs/{club_id}",
    response_model=ClubReponse,
    dependencies=[Depends(exiger_admin)],
)
async def modifier_club(
    club_id: int, requete: ModifierClubRequete, request: Request
) -> ClubReponse:
    """Renomme un club (**action admin**) : écriture via la file (ADR-0005)."""
    service: ServiceClubs = request.app.state.service_clubs
    write_queue: WriteQueue = request.app.state.write_queue
    club = await asyncio.wrap_future(
        write_queue.submit(lambda: service.modifier(club_id, requete.nom))
    )
    return ClubReponse.de_agregat(club)


@router.delete(
    "/clubs/{club_id}",
    status_code=204,
    dependencies=[Depends(exiger_admin)],
)
async def supprimer_club(club_id: int, request: Request) -> Response:
    """Retire un club du référentiel (**action admin**) : écriture via la file ; renvoie 204."""
    service: ServiceClubs = request.app.state.service_clubs
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(write_queue.submit(lambda: service.supprimer(club_id)))
    return Response(status_code=204)
