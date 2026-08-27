"""Journal d'audit — consultation **admin** seulement : un journal de litiges ne s'ouvre pas au
public.

⚠️ **Aucun endpoint d'écriture, et c'est structurel** : les entrées naissent d'un **acte métier**,
écrites dans la commande du producteur. L'audit reflète des actes, il ne s'édite pas.
"""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.audit import ServiceAudit
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

    `404 tournoi_introuvable` si le tournoi n'existe pas (et non une liste vide trompeuse).
    """
    service: ServiceAudit = request.app.state.service_audit
    entrees = await run_in_threadpool(service.lister, tournoi_id)
    return [EntreeAuditReponse.de_agregat(entree) for entree in entrees]
