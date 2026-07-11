"""Endpoints REST des tournois (`/api/v1/tournois`) — gabarit de bout en bout (E00US009).

Illustre le patron des US métier :
- **DTO Pydantic** distincts des agrégats de domaine (aucune entité domaine exposée) ;
- **écriture** routée par la **file d'écriture** (writer unique, ADR-0005), attendue via
  `asyncio.wrap_future` sans bloquer la boucle ;
- **lecture** directe exécutée **hors boucle** (threadpool) ;
- **erreurs typées** traduites à la frontière (`api/erreurs.py`).
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from application.tournois import ServiceTournois
from domain.tournoi import Tournoi
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1/tournois", tags=["tournois"])


class CreerTournoiRequete(BaseModel):
    """Corps de création d'un tournoi."""

    nom: str


class TournoiReponse(BaseModel):
    """Représentation d'un tournoi renvoyée au client."""

    id: int
    nom: str

    @staticmethod
    def de_agregat(tournoi: Tournoi) -> TournoiReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert tournoi.id is not None, "Un tournoi persisté a toujours un identifiant."
        return TournoiReponse(id=tournoi.id, nom=tournoi.nom)


@router.post("", status_code=201, response_model=TournoiReponse)
async def creer_tournoi(requete: CreerTournoiRequete, request: Request) -> TournoiReponse:
    """Crée un tournoi : l'écriture passe par la file (writer unique, ADR-0005)."""
    service: ServiceTournois = request.app.state.service_tournois
    write_queue: WriteQueue = request.app.state.write_queue
    tournoi = await asyncio.wrap_future(write_queue.submit(lambda: service.creer(requete.nom)))
    return TournoiReponse.de_agregat(tournoi)


@router.get("/{tournoi_id}", response_model=TournoiReponse)
async def consulter_tournoi(tournoi_id: int, request: Request) -> TournoiReponse:
    """Relit un tournoi : lecture directe exécutée hors de la boucle événementielle."""
    service: ServiceTournois = request.app.state.service_tournois
    tournoi = await run_in_threadpool(service.consulter, tournoi_id)
    return TournoiReponse.de_agregat(tournoi)
