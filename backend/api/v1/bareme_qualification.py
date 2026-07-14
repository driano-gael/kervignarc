"""Endpoints REST du barème de qualification (`/api/v1`) — barème d'un tournoi (E01US009).

Suit le patron de bout en bout (E00US009) :
- **DTO Pydantic** distincts des agrégats de domaine ;
- **écriture** routée par la **file d'écriture** (writer unique, ADR-0005), protégée par
  `exiger_admin` (E10US001/E10US002) ;
- **lecture** directe exécutée **hors boucle** (threadpool) ;
- **erreurs typées** traduites à la frontière (`api/erreurs.py`).

Ressource rattachée au tournoi : routes sous `/tournois/{tournoi_id}/bareme-qualification`.
Lecture publique (comme les autres consultations) ; définition réservée à l'admin. Le barème est
porté par la phase de qualification du tournoi (ADR-0011), transparent pour le client.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.bareme_qualification import ServiceBaremeQualification
from domain.bareme import BaremeQualification
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["bareme-qualification"])


class DefinirBaremeRequete(BaseModel):
    """Corps de définition du barème : nombre de volées et nombre de flèches par volée."""

    nb_volees: int
    nb_fleches_par_volee: int


class BaremeReponse(BaseModel):
    """Représentation du barème de qualification renvoyée au client (total et max dérivés)."""

    nb_volees: int
    nb_fleches_par_volee: int
    nb_fleches_total: int
    score_max: int

    @staticmethod
    def de_agregat(bareme: BaremeQualification) -> BaremeReponse:
        """Traduit le value object de domaine en DTO de réponse."""
        return BaremeReponse(
            nb_volees=bareme.nb_volees,
            nb_fleches_par_volee=bareme.nb_fleches_par_volee,
            nb_fleches_total=bareme.nb_fleches_total,
            score_max=bareme.score_max,
        )


@router.get(
    "/tournois/{tournoi_id}/bareme-qualification",
    response_model=BaremeReponse | None,
)
async def bareme_du_tournoi(tournoi_id: int, request: Request) -> BaremeReponse | None:
    """Renvoie le barème de qualification du tournoi, ou `null` s'il n'est pas encore défini.

    Lève `TournoiIntrouvable` (404) si le tournoi n'existe pas.
    """
    service: ServiceBaremeQualification = request.app.state.service_bareme_qualification
    bareme = await run_in_threadpool(service.bareme_du_tournoi, tournoi_id)
    return None if bareme is None else BaremeReponse.de_agregat(bareme)


@router.put(
    "/tournois/{tournoi_id}/bareme-qualification",
    response_model=BaremeReponse,
    dependencies=[Depends(exiger_admin)],
)
async def definir_bareme(
    tournoi_id: int, requete: DefinirBaremeRequete, request: Request
) -> BaremeReponse:
    """Définit le barème de qualification (**action admin**) : écriture via la file (ADR-0005).

    Upsert : crée le barème s'il n'existe pas, sinon met à jour ses valeurs. Le preset FFTA 18 m
    (20 volées de 3) est fourni par le client, qui reste libre de saisir d'autres valeurs.
    """
    service: ServiceBaremeQualification = request.app.state.service_bareme_qualification
    write_queue: WriteQueue = request.app.state.write_queue
    bareme = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.definir(tournoi_id, requete.nb_volees, requete.nb_fleches_par_volee)
        )
    )
    return BaremeReponse.de_agregat(bareme)
