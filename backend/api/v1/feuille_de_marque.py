"""Frontière API — feuille de marque d'un départ en PDF (E09US001).

Lecture seule, admin : le document se compose à la demande depuis le plan persisté, d'où le
`run_in_threadpool` (règle 7). Réponse binaire `application/pdf` en pièce jointe. Patron de bout en
bout : E00US009.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from api.documents import reponse_document, reponses_document
from application.exports import FormatExport
from application.feuille_de_marque import ServiceFeuilleDeMarque

router = APIRouter(prefix="/api/v1", tags=["feuille-de-marque"])


@router.get(
    "/tournois/{tournoi_id}/departs/{depart_id}/feuille-de-marque",
    dependencies=[Depends(exiger_admin)],
    responses=reponses_document(FormatExport.PDF),
)
async def feuille_de_marque(
    tournoi_id: int,
    depart_id: int,
    request: Request,
    format_: Annotated[FormatExport, Query(alias="format")] = FormatExport.PDF,
) -> Response:
    """Renvoie la feuille de marque du départ (une page par archer placé).

    ⚠️ `format` n'accepte que ce que le catalogue annonce pour ce document — **le PDF seul**.
    Le paramètre existe pour que le refus soit une 400 explicite plutôt qu'un format ignoré en
    silence, qui rendrait un PDF à qui a demandé du CSV.
    """
    service: ServiceFeuilleDeMarque = request.app.state.service_feuille_de_marque
    document = await run_in_threadpool(service.generer, tournoi_id, depart_id, format_)
    return reponse_document(
        document, format_, f"feuille-de-marque-tournoi-{tournoi_id}-depart-{depart_id}"
    )
