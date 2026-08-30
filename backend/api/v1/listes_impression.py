"""Frontière API — listes imprimables d'organisation (E09US003, formats E16US007).

Lecture seule, admin, document en pièce jointe ; `tri` (`cible` | `nom`) et `depart_id` restreignent
la liste de placement, `format` choisit le rendu parmi ceux du catalogue (`GET /api/v1/exports`).
Patron de bout en bout : E00US009.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from api.v1.exports import REPONSE_DOCUMENT, reponse_document
from application.exports import FormatExport
from application.listes_impression import ServiceListesImpression
from domain.listes_impression import TriPlacement

router = APIRouter(prefix="/api/v1", tags=["listes-impression"])


@router.get(
    "/tournois/{tournoi_id}/listes/placement",
    dependencies=[Depends(exiger_admin)],
    responses=REPONSE_DOCUMENT,
)
async def liste_placement(
    tournoi_id: int,
    request: Request,
    tri: TriPlacement = TriPlacement.CIBLE,
    depart_id: int | None = None,
    format: FormatExport = FormatExport.PDF,
) -> Response:
    """Renvoie la liste de placement (tout le tournoi, ou un seul départ si `depart_id`)."""
    service: ServiceListesImpression = request.app.state.service_listes_impression
    document = await run_in_threadpool(
        service.generer_placement, tournoi_id, depart_id, tri, format
    )
    suffixe = f"-depart-{depart_id}" if depart_id is not None else ""
    return reponse_document(document, format, f"placement-tournoi-{tournoi_id}{suffixe}")


@router.get(
    "/tournois/{tournoi_id}/listes/club-paiement",
    dependencies=[Depends(exiger_admin)],
    responses=REPONSE_DOCUMENT,
)
async def liste_club_paiement(
    tournoi_id: int, request: Request, format: FormatExport = FormatExport.PDF
) -> Response:
    """Renvoie la liste club & paiement (un bloc par club en PDF, une ligne par archer en CSV)."""
    service: ServiceListesImpression = request.app.state.service_listes_impression
    document = await run_in_threadpool(service.generer_club_paiement, tournoi_id, format)
    return reponse_document(document, format, f"club-paiement-tournoi-{tournoi_id}")
