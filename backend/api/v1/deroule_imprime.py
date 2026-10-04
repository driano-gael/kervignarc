"""Endpoint du **déroulé horaire imprimable** (`/api/v1`, E09US007).

⚠️ **Public, sans authentification**, comme la lecture `GET /tournois/{id}/horaires-prevus`
qu'il imprime — arbitrage reversé dans `stories/E09-exports.md`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from fastapi.concurrency import run_in_threadpool

from api.documents import reponse_document, reponses_document
from application.deroule_imprime import ServiceDerouleImprime
from application.exports import FormatExport

router = APIRouter(prefix="/api/v1", tags=["deroule"])


@router.get(
    "/tournois/{tournoi_id}/deroule-horaire/document",
    response_class=Response,
    responses=reponses_document(FormatExport.PDF),
)
async def imprimer_deroule_horaire(
    tournoi_id: int,
    request: Request,
    depart_id: int | None = None,
    format_: Annotated[FormatExport, Query(alias="format")] = FormatExport.PDF,
) -> Response:
    """Rend le déroulé horaire — tous les créneaux, ou le seul `depart_id`.

    404 pour un tournoi inconnu ou un départ d'un autre tournoi ; 409 pour un tournoi sans créneau.
    """
    service: ServiceDerouleImprime = request.app.state.service_deroule_imprime
    document = await run_in_threadpool(service.imprimer, tournoi_id, depart_id, format_)
    return reponse_document(
        document, format_, f"deroule-horaire-{tournoi_id}", disposition="inline"
    )
