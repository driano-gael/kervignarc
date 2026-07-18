"""Frontière API — feuille de marque d'un départ en PDF (E09US001).

Endpoint de **lecture** : compose le document à la demande à partir du plan persisté (aucune
écriture DB) → exécuté hors boucle événementielle (`run_in_threadpool`, règle 7). Réservé à
l'admin (`exiger_admin`, E10US001). Premier endpoint du projet à renvoyer un **binaire** : la
réponse porte `application/pdf` et un `Content-Disposition: attachment` pour déclencher le
téléchargement. Les gardes 404 (`TournoiIntrouvable`, `DepartIntrouvable`) remontent du service et
sont traduites à la frontière (`api/erreurs.py`) — pas de gestion d'erreur locale (règle 5).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.feuille_de_marque import ServiceFeuilleDeMarque

router = APIRouter(prefix="/api/v1", tags=["feuille-de-marque"])


@router.get(
    "/tournois/{tournoi_id}/departs/{depart_id}/feuille-de-marque",
    dependencies=[Depends(exiger_admin)],
    responses={200: {"content": {"application/pdf": {}}, "description": "Document PDF"}},
)
async def feuille_de_marque(tournoi_id: int, depart_id: int, request: Request) -> Response:
    """Renvoie le PDF de feuille de marque du départ (une page par archer placé)."""
    service: ServiceFeuilleDeMarque = request.app.state.service_feuille_de_marque
    pdf = await run_in_threadpool(service.generer, tournoi_id, depart_id)
    nom_fichier = f"feuille-de-marque-tournoi-{tournoi_id}-depart-{depart_id}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nom_fichier}"'},
    )
