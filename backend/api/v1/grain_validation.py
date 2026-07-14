"""Endpoints REST du grain de validation (`/api/v1`) — quand le scoreur valide (E01US015, `D-11`).

Suit le patron de bout en bout (E00US009) :
- **DTO Pydantic** distincts des agrégats de domaine ;
- **écriture** routée par la **file d'écriture** (writer unique, ADR-0005), protégée par
  `exiger_admin` (E10US001/E10US002) ;
- **lecture** directe exécutée **hors boucle** (threadpool) ;
- **erreurs typées** traduites à la frontière (`api/erreurs.py`).

Ressource rattachée au tournoi : routes sous `/tournois/{tournoi_id}/grain-validation`, en miroir
du barème. Lecture publique (comme les autres consultations) ; définition réservée à l'admin. Le
grain est porté par la phase de qualification du tournoi (ADR-0011), transparent pour le client.
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
