"""Endpoints REST des tournois (`/api/v1/tournois`) — créer, consulter, lister (E01US001).

Suit le patron de bout en bout (E00US009) :
- **DTO Pydantic** distincts des agrégats de domaine (aucune entité domaine exposée) ;
- **écriture** routée par la **file d'écriture** (writer unique, ADR-0005), attendue via
  `asyncio.wrap_future` sans bloquer la boucle ;
- **lecture** directe exécutée **hors boucle** (threadpool) ;
- **erreurs typées** traduites à la frontière (`api/erreurs.py`).
"""

from __future__ import annotations

import asyncio
import datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.tournois import ServiceTournois
from domain.tournoi import Tournoi, TypeTournoi
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1/tournois", tags=["tournois"])


class CreerTournoiRequete(BaseModel):
    """Corps de création d'un tournoi (nom et date requis ; lieu et type facultatifs)."""

    nom: str
    date: datetime.date
    lieu: str | None = None
    type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL


class TournoiReponse(BaseModel):
    """Représentation d'un tournoi renvoyée au client."""

    id: int
    nom: str
    date: datetime.date
    lieu: str | None
    type_tournoi: TypeTournoi

    @staticmethod
    def de_agregat(tournoi: Tournoi) -> TournoiReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert tournoi.id is not None, "Un tournoi persisté a toujours un identifiant."
        return TournoiReponse(
            id=tournoi.id,
            nom=tournoi.nom,
            date=tournoi.date,
            lieu=tournoi.lieu,
            type_tournoi=tournoi.type_tournoi,
        )


@router.post(
    "",
    status_code=201,
    response_model=TournoiReponse,
    dependencies=[Depends(exiger_admin)],
)
async def creer_tournoi(requete: CreerTournoiRequete, request: Request) -> TournoiReponse:
    """Crée un tournoi (**action admin**, E10US002) : l'écriture passe par la file (ADR-0005)."""
    service: ServiceTournois = request.app.state.service_tournois
    write_queue: WriteQueue = request.app.state.write_queue
    tournoi = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.creer(requete.nom, requete.date, requete.lieu, requete.type_tournoi)
        )
    )
    return TournoiReponse.de_agregat(tournoi)


@router.get("", response_model=list[TournoiReponse])
async def lister_tournois(request: Request) -> list[TournoiReponse]:
    """Liste tous les tournois : lecture directe exécutée hors de la boucle événementielle."""
    service: ServiceTournois = request.app.state.service_tournois
    tournois = await run_in_threadpool(service.lister)
    return [TournoiReponse.de_agregat(tournoi) for tournoi in tournois]


@router.get("/{tournoi_id}", response_model=TournoiReponse)
async def consulter_tournoi(tournoi_id: int, request: Request) -> TournoiReponse:
    """Relit un tournoi : lecture directe exécutée hors de la boucle événementielle."""
    service: ServiceTournois = request.app.state.service_tournois
    tournoi = await run_in_threadpool(service.consulter, tournoi_id)
    return TournoiReponse.de_agregat(tournoi)
