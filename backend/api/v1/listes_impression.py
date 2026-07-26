"""Frontière API — listes imprimables d'organisation en PDF (E09US003).

Deux endpoints de **lecture** (aucune écriture DB : ils composent à la demande à partir du plan et
des inscriptions) → exécutés hors boucle événementielle (`run_in_threadpool`, règle 7). Réservés à
l'admin (`exiger_admin`, E10US001). Renvoient un **binaire** `application/pdf` avec
`Content-Disposition: attachment` pour déclencher le téléchargement.

La liste de placement accepte deux paramètres de requête : `tri` (`cible` par défaut, ou `nom`) et
`depart_id` (optionnel, pour n'imprimer qu'un départ). Les gardes 404 (`TournoiIntrouvable`,
`DepartIntrouvable`) remontent du service et sont traduites à la frontière (`api/erreurs.py`) — pas
de gestion d'erreur locale (règle 5).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.listes_impression import ServiceListesImpression
from domain.listes_impression import TriPlacement

router = APIRouter(prefix="/api/v1", tags=["listes-impression"])

_PDF: dict[int | str, dict[str, Any]] = {
    200: {"content": {"application/pdf": {}}, "description": "Document PDF"}
}


@router.get(
    "/tournois/{tournoi_id}/listes/placement",
    dependencies=[Depends(exiger_admin)],
    responses=_PDF,
)
async def liste_placement(
    tournoi_id: int,
    request: Request,
    tri: TriPlacement = TriPlacement.CIBLE,
    depart_id: int | None = None,
) -> Response:
    """Renvoie le PDF de placement (tout le tournoi, ou un seul départ si `depart_id`)."""
    service: ServiceListesImpression = request.app.state.service_listes_impression
    pdf = await run_in_threadpool(service.generer_placement, tournoi_id, depart_id, tri)
    suffixe = f"-depart-{depart_id}" if depart_id is not None else ""
    nom_fichier = f"placement-tournoi-{tournoi_id}{suffixe}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nom_fichier}"'},
    )


@router.get(
    "/tournois/{tournoi_id}/listes/club-paiement",
    dependencies=[Depends(exiger_admin)],
    responses=_PDF,
)
async def liste_club_paiement(tournoi_id: int, request: Request) -> Response:
    """Renvoie le PDF de la liste club & paiement (un bloc par club, avec totaux)."""
    service: ServiceListesImpression = request.app.state.service_listes_impression
    pdf = await run_in_threadpool(service.generer_club_paiement, tournoi_id)
    nom_fichier = f"club-paiement-tournoi-{tournoi_id}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nom_fichier}"'},
    )
