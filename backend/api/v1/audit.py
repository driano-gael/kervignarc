"""Journal d'audit — consultation **admin** seulement : un journal de litiges ne s'ouvre pas au
public.

⚠️ **Aucun endpoint d'écriture, et c'est structurel** : les entrées naissent d'un **acte métier**,
écrites dans la commande du producteur. L'audit reflète des actes, il ne s'édite pas. ADR-0050
"""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from api.documents import reponse_document, reponses_document
from application.audit import ServiceAudit, ServiceExportAudit
from application.exports import FormatExport
from domain.entree_audit import EntreeAudit

router = APIRouter(prefix="/api/v1/tournois/{tournoi_id}/audit", tags=["audit"])


class EntreeAuditReponse(BaseModel):
    """Représentation d'une entrée d'audit renvoyée à l'admin (qui / quand / objet / avant-après).

    `action` est le **slug** de l'énumération (`validation`, `correction_score`, `forfait`) ;
    `horodatage` est sérialisé en ISO-8601 (UTC) ; `avant`/`apres` peuvent être `null` (une
    validation n'a pas d'état antérieur).
    """

    id: int
    tournoi_id: int
    action: str
    auteur: str
    horodatage: datetime.datetime
    objet: str
    avant: str | None
    apres: str | None

    @staticmethod
    def de_agregat(entree: EntreeAudit) -> EntreeAuditReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert entree.id is not None, "Une entrée d'audit persistée a toujours un identifiant."
        return EntreeAuditReponse(
            id=entree.id,
            tournoi_id=entree.tournoi_id,
            action=entree.action.value,
            auteur=entree.auteur,
            horodatage=entree.horodatage,
            objet=entree.objet,
            avant=entree.avant,
            apres=entree.apres,
        )


@router.get("", response_model=list[EntreeAuditReponse], dependencies=[Depends(exiger_admin)])
async def lister_audit(tournoi_id: int, request: Request) -> list[EntreeAuditReponse]:
    """Liste les entrées d'audit d'un tournoi (chronologique) — lecture **admin**.

    `DETTE-101` : aucun paramètre de filtre ni de pagination ; le tri se fait à l'écran.

    `404 tournoi_introuvable` si le tournoi n'existe pas (et non une liste vide trompeuse).
    """
    service: ServiceAudit = request.app.state.service_audit
    entrees = await run_in_threadpool(service.lister, tournoi_id)
    return [EntreeAuditReponse.de_agregat(entree) for entree in entrees]


@router.get(
    "/document",
    response_class=Response,
    dependencies=[Depends(exiger_admin)],
    responses=reponses_document(FormatExport.CSV, FormatExport.XLSX),
)
async def exporter_audit(
    tournoi_id: int,
    request: Request,
    format_: Annotated[FormatExport, Query(alias="format")] = FormatExport.CSV,
) -> Response:
    """Sort le journal d'audit en document téléchargeable (E16US016) — **admin**, comme la lecture.

    ⚠️ Le défaut est le **CSV** et non le PDF : ce document n'a pas de rendu PDF, un défaut aligné
    sur les autres exports répondrait 400 à qui ne passe aucun format.
    """
    service: ServiceExportAudit = request.app.state.service_export_audit
    document = await run_in_threadpool(service.exporter, tournoi_id, format_)
    return reponse_document(document, format_, f"audit-{tournoi_id}")
