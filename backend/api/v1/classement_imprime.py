"""Endpoint du **classement de qualification imprimable** (`/api/v1`, E09US005).

⚠️ **Public, sans authentification**, comme le classement qu'il rend (`GET /departs/{id}/classement`)
et le document du palmarès — arbitrage reversé dans `stories/E09-exports.md`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from fastapi.concurrency import run_in_threadpool

from api.documents import reponse_document, reponses_document
from application.classement_imprime import ServiceClassementImprime
from application.exports import FormatExport

router = APIRouter(prefix="/api/v1", tags=["classement"])


@router.get(
    "/tournois/{tournoi_id}/classement-qualification/document",
    response_class=Response,
    responses=reponses_document(FormatExport.PDF, FormatExport.CSV, FormatExport.XLSX),
)
async def imprimer_classement_qualification(
    tournoi_id: int,
    request: Request,
    depart_id: int | None = None,
    format_: Annotated[FormatExport, Query(alias="format")] = FormatExport.PDF,
) -> Response:
    """Rend le classement de qualification — tous les créneaux, ou le seul `depart_id`.

    404 pour un tournoi inconnu ou un départ d'un autre tournoi ; 409 pour un tournoi sans créneau.
    """
    service: ServiceClassementImprime = request.app.state.service_classement_imprime
    document = await run_in_threadpool(service.imprimer, tournoi_id, depart_id, format_)
    # `inline` pour le PDF seul, comme le palmarès : on l'ouvre pour l'imprimer au mur.
    disposition = "inline" if format_ is FormatExport.PDF else "attachment"
    return reponse_document(
        document, format_, f"classement-qualification-{tournoi_id}", disposition=disposition
    )
