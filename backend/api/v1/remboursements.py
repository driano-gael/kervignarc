"""Endpoints REST du registre de remboursements (E08US005, ADR-0057).

Consulter les sommes encaissées à rendre d'un tournoi (à traiter d'abord, puis les plus récentes) et
**traiter** un poste — le marquer **remboursé** (l'argent a été rendu) ou **reporté** (réaffecté à
un
autre créneau). Les postes ne se **créent** pas ici : ils naissent à la suppression d'une
inscription
payée (désinscription, suppression de départ) — voir `inscriptions.py` / `departs.py`.

Suit le patron de bout en bout : DTO Pydantic distincts des agrégats ; **tout réservé à l'admin**
(`exiger_admin`) — un mouvement d'argent n'est pas public ; traitement routé par la **file
d'écriture** (writer unique, ADR-0005), lecture **hors boucle** (threadpool) ; erreurs typées
traduites à la frontière (`404 remboursement_introuvable`, `409 remboursement_deja_traite`).
"""

from __future__ import annotations

import asyncio
import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.remboursements import ServiceRemboursements
from domain.remboursement import Remboursement
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["remboursements"])


class TraiterRemboursementRequete(BaseModel):
    """Corps d'un traitement : l'issue visée — `rembourse` (rendu) ou `reporte` (réaffecté).

    `Literal` borne le champ aux deux issues **terminales** offertes par le CA (pas de retour à
    `a_rembourser` : le registre n'annule pas un traitement). Une valeur hors des deux est refusée
    à la frontière (400), avant le service.
    """

    statut: Literal["rembourse", "reporte"]


class RemboursementReponse(BaseModel):
    """Un poste du registre : l'archer, le créneau détruit, le montant à rendre, l'état.

    `archer_prenom`/`archer_nom`/`creneau` sont des **instantanés** figés à l'ouverture
    (l'inscription
    et souvent le départ ont disparu, ADR-0057) — pas des identifiants à re-résoudre côté client.
    `cree_le` date l'ouverture, `traite_le` le traitement (`null` tant qu'à traiter). Montant en
    **centimes entiers** (le client met en euros).
    """

    id: int
    archer_prenom: str
    archer_nom: str
    creneau: str
    montant_centimes: int
    motif: str
    statut: str
    cree_le: datetime.datetime
    traite_le: datetime.datetime | None

    @staticmethod
    def de(remboursement: Remboursement) -> RemboursementReponse:
        assert remboursement.id is not None, "Un remboursement relu est persisté."
        return RemboursementReponse(
            id=remboursement.id,
            archer_prenom=remboursement.archer_prenom,
            archer_nom=remboursement.archer_nom,
            creneau=remboursement.creneau,
            montant_centimes=remboursement.montant_centimes,
            motif=remboursement.motif.value,
            statut=remboursement.statut.value,
            cree_le=remboursement.cree_le,
            traite_le=remboursement.traite_le,
        )


@router.get(
    "/tournois/{tournoi_id}/remboursements",
    response_model=list[RemboursementReponse],
    dependencies=[Depends(exiger_admin)],
)
async def lister(tournoi_id: int, request: Request) -> list[RemboursementReponse]:
    """Liste des remboursements d'un tournoi (à traiter d'abord) : lecture directe hors boucle.

    Renvoie `404 tournoi_introuvable` si le tournoi n'existe pas.
    """
    service: ServiceRemboursements = request.app.state.service_remboursements
    remboursements = await run_in_threadpool(service.lister, tournoi_id)
    return [RemboursementReponse.de(remboursement) for remboursement in remboursements]


@router.put(
    "/tournois/{tournoi_id}/remboursements/{remboursement_id}",
    response_model=RemboursementReponse,
    dependencies=[Depends(exiger_admin)],
)
async def traiter(
    tournoi_id: int,
    remboursement_id: int,
    requete: TraiterRemboursementRequete,
    request: Request,
) -> RemboursementReponse:
    """Marque un remboursement **remboursé** ou **reporté** (audité) : écriture via la file.

    Renvoie `404 remboursement_introuvable` si l'`id` est inconnu, `409 remboursement_deja_traite`
    s'il est déjà traité. `tournoi_id` est le contexte de la ressource ; le service adresse le poste
    par son `id` (globalement unique).
    """
    service: ServiceRemboursements = request.app.state.service_remboursements
    write_queue: WriteQueue = request.app.state.write_queue
    action = service.marquer_rembourse if requete.statut == "rembourse" else service.marquer_reporte
    remboursement = await asyncio.wrap_future(write_queue.submit(lambda: action(remboursement_id)))
    return RemboursementReponse.de(remboursement)
