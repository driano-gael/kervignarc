"""Frontière API — archive de fin de tournoi en ZIP (E11US003, CA « export/archive »).

Endpoint de **lecture** : compose le paquet à la demande (instantané SQLite + CSV + PDF), aucune
écriture DB → exécuté hors boucle événementielle (`run_in_threadpool`, règle 7). Réservé à l'admin
(`exiger_admin`, E10US001). Renvoie un **binaire** `application/zip` avec `Content-Disposition:
attachment`.

Les parties à inclure sont des **paramètres de requête booléens** (cases à cocher côté UI), toutes
à `true` par défaut — l'archive complète est le cas nominal. La garde 404 (`TournoiIntrouvable`)
remonte du service et est traduite à la frontière (`api/erreurs.py`) — pas de gestion locale
(règle 5).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.archive import OptionsArchive, ServiceArchive

router = APIRouter(prefix="/api/v1", tags=["archive"])


@router.get(
    "/tournois/{tournoi_id}/archive",
    dependencies=[Depends(exiger_admin)],
    responses={200: {"content": {"application/zip": {}}, "description": "Paquet ZIP d'archive"}},
)
async def archive_tournoi(
    tournoi_id: int,
    request: Request,
    base: bool = True,
    donnees_csv: bool = True,
    feuilles_de_marque: bool = True,
    liste_placement: bool = True,
    liste_club_paiement: bool = True,
) -> Response:
    """Renvoie le ZIP d'archive du tournoi selon les parties sélectionnées."""
    service: ServiceArchive = request.app.state.service_archive
    options = OptionsArchive(
        base=base,
        donnees_csv=donnees_csv,
        feuilles_de_marque=feuilles_de_marque,
        liste_placement=liste_placement,
        liste_club_paiement=liste_club_paiement,
    )
    paquet = await run_in_threadpool(service.composer, tournoi_id, options)
    return Response(
        content=paquet.contenu,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{paquet.nom_fichier}"'},
    )
