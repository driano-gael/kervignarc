"""Grain de validation — ressource rattachée au tournoi, en miroir du barème.

Lecture publique, définition réservée à l'admin ; le grain est porté par la phase de qualification,
de façon transparente pour le client.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.grain_validation import ServiceGrainValidation
from domain.grain_validation import GrainValidation, TypeGrain
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["grain-validation"])


class DefinirGrainRequete(BaseModel):
    """Corps de définition du grain : son type et, pour « toutes les N volées », sa cadence.

    `n_volees` est **requis** pour `toutes_les_n_volees` et **ignoré** pour les grains de fin ; la
    règle est portée par le domaine (`GrainValidation.creer`), pas par le DTO.
    """

    grain: TypeGrain
    n_volees: int | None = None


class GrainReponse(BaseModel):
    """Représentation du grain de validation renvoyée au client."""

    grain: TypeGrain
    n_volees: int | None

    @staticmethod
    def de_agregat(validation: GrainValidation) -> GrainReponse:
        """Traduit le value object de domaine en DTO de réponse."""
        return GrainReponse(grain=validation.type, n_volees=validation.n_volees)


@router.get(
    "/tournois/{tournoi_id}/grain-validation",
    response_model=GrainReponse | None,
)
async def grain_du_tournoi(tournoi_id: int, request: Request) -> GrainReponse | None:
    """Renvoie le grain de validation de la qualification, ou `null` si le barème du tournoi n'est
    pas encore défini (la phase n'existe alors pas).

    Lève `TournoiIntrouvable` (404) si le tournoi n'existe pas.
    """
    service: ServiceGrainValidation = request.app.state.service_grain_validation
    grain = await run_in_threadpool(service.grain_du_tournoi, tournoi_id)
    return None if grain is None else GrainReponse.de_agregat(grain)


@router.put(
    "/tournois/{tournoi_id}/grain-validation",
    response_model=GrainReponse,
    dependencies=[Depends(exiger_admin)],
)
async def definir_grain(
    tournoi_id: int, requete: DefinirGrainRequete, request: Request
) -> GrainReponse:
    """Définit le grain de validation de la qualification (**action admin**) : écriture via la file
    (ADR-0005).

    Lève `PhaseQualificationAbsente` (404) si le barème du tournoi n'est pas encore défini.
    """
    service: ServiceGrainValidation = request.app.state.service_grain_validation
    write_queue: WriteQueue = request.app.state.write_queue
    grain = await asyncio.wrap_future(
        write_queue.submit(lambda: service.definir(tournoi_id, requete.grain, requete.n_volees))
    )
    return GrainReponse.de_agregat(grain)


@router.put(
    "/tournois/{tournoi_id}/qualifications/{etape_id}/grain-validation",
    response_model=GrainReponse,
    dependencies=[Depends(exiger_admin)],
)
async def definir_grain_d_etape(
    tournoi_id: int, etape_id: int, requete: DefinirGrainRequete, request: Request
) -> GrainReponse:
    """Règle le grain d'une qualification **désignée** (**action admin**, E05US025).

    Pendant de la route de barème par étape. `PhaseIntrouvable` (404) si l'étape n'appartient pas
    à ce tournoi, `PhasePasUneQualification` (409) si elle n'en est pas une.
    """
    service: ServiceGrainValidation = request.app.state.service_grain_validation
    write_queue: WriteQueue = request.app.state.write_queue
    grain = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.definir_pour_etape(
                tournoi_id, etape_id, requete.grain, requete.n_volees
            )
        )
    )
    return GrainReponse.de_agregat(grain)
