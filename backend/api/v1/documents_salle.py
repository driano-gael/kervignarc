"""Frontière API — documents de préparation de salle en PDF (E09US008).

Deux endpoints de **lecture** (aucune écriture DB : ils composent à la demande à partir des codes
déjà préparés) → exécutés hors boucle événementielle (`run_in_threadpool`, règle 7). Réservés à
l'admin (`exiger_admin`, E10US001) : les codes sont des secrets d'usage à imprimer, ils n'ont pas à
fuiter au public. Renvoient un **binaire** `application/pdf` avec `Content-Disposition: attachment`.

Les étiquettes de cible encodent une URL de rattachement : elle est bâtie sur l'**origine de la
requête** (`request.base_url`), passée au service — le seul endroit qui connaisse l'adresse par
laquelle l'admin (donc, le jour J, les tablettes) atteint le serveur. La garde 404
(`TournoiIntrouvable`) remonte du service et est traduite à la frontière (`api/erreurs.py`).
"""

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
