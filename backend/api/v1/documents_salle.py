"""Documents de salle — deux PDF à imprimer, plus les **QR à l'écran** (SVG) : cible, scoreur.

Le SVG est chargé par **blob authentifié** : le Bearer admin vit en JS, un `<img src>` direct
n'emporterait pas le jeton. ⚠️ **Réservé à l'admin** (`exiger_admin`, E10US001) : les QR encodent
des codes de rattachement, secrets d'usage qui n'ont pas à fuiter au public.
"""

# ⚠️ **Les QR encodent une URL bâtie sur l'ORIGINE DE LA REQUÊTE** — le seul endroit qui connaisse
# l'adresse par laquelle les tablettes atteindront le serveur le jour J (`DETTE-012`).

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.documents_salle import ServiceDocumentsSalle

router = APIRouter(prefix="/api/v1", tags=["documents-salle"])

_PDF: dict[int | str, dict[str, Any]] = {
    200: {"content": {"application/pdf": {}}, "description": "Document PDF"}
}

_SVG: dict[int | str, dict[str, Any]] = {
    200: {"content": {"image/svg+xml": {}}, "description": "Image SVG (QR de rattachement)"}
}


@router.get(
    "/tournois/{tournoi_id}/postes/etiquettes-qr",
    dependencies=[Depends(exiger_admin)],
    responses=_PDF,
)
async def etiquettes_qr(tournoi_id: int, request: Request) -> Response:
    """Renvoie le PDF des étiquettes de cible (une page par cible : QR de rattachement + code)."""
    service: ServiceDocumentsSalle = request.app.state.service_documents_salle
    pdf = await run_in_threadpool(service.etiquettes_cibles, tournoi_id, str(request.base_url))
    nom_fichier = f"etiquettes-qr-tournoi-{tournoi_id}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nom_fichier}"'},
    )


@router.get(
    "/tournois/{tournoi_id}/postes/{cible_index}/qr",
    dependencies=[Depends(exiger_admin)],
    responses=_SVG,
)
async def qr_cible(tournoi_id: int, cible_index: int, request: Request) -> Response:
    """Renvoie l'image **SVG** du QR de rattachement d'une cible (affiché à l'écran, E11US008)."""
    service: ServiceDocumentsSalle = request.app.state.service_documents_salle
    svg = await run_in_threadpool(
        service.qr_rattachement, tournoi_id, cible_index, str(request.base_url)
    )
    return Response(content=svg, media_type="image/svg+xml")


@router.get(
    "/tournois/{tournoi_id}/scoreurs/cartes-codes",
    dependencies=[Depends(exiger_admin)],
    responses=_PDF,
)
async def cartes_codes(tournoi_id: int, request: Request) -> Response:
    """Renvoie le PDF des cartes de scoreur (une page par scoreur : nom + code personnel)."""
    service: ServiceDocumentsSalle = request.app.state.service_documents_salle
    pdf = await run_in_threadpool(service.cartes_scoreurs, tournoi_id)
    nom_fichier = f"cartes-scoreurs-tournoi-{tournoi_id}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nom_fichier}"'},
    )


@router.get(
    "/tournois/{tournoi_id}/scoreurs/{scoreur_id}/qr",
    dependencies=[Depends(exiger_admin)],
    responses=_SVG,
)
async def qr_scoreur(tournoi_id: int, scoreur_id: int, request: Request) -> Response:
    """Renvoie l'image **SVG** du QR de rattachement d'un scoreur (affiché à l'écran, E16US015)."""
    service: ServiceDocumentsSalle = request.app.state.service_documents_salle
    svg = await run_in_threadpool(service.qr_scoreur, tournoi_id, scoreur_id, str(request.base_url))
    return Response(content=svg, media_type="image/svg+xml")
