"""Endpoints REST des inscriptions — liens archer ↔ départ (E02US009, ADR-0017).

Inscrire un archer sur des départs (créneaux) de son tournoi, marquer payé, désinscrire. Deux
racines, comme pour les archers (cf. `competition.py`) : la **création et la liste** sont imbriquées
sous l'archer (`/api/v1/archers/{archer_id}/inscriptions`), la **mutation d'une inscription** est à
plat sur sa ressource (`/api/v1/inscriptions/{inscription_id}`).

Suit le patron de bout en bout : DTO Pydantic distincts des agrégats ; écritures routées par la
**file d'écriture** (writer unique, ADR-0005) et réservées à l'admin (`exiger_admin`) ; lectures
**hors boucle** (threadpool) ; erreurs typées traduites à la frontière (`api/erreurs.py`).
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.inscriptions import InscriptionDetaillee, ServiceInscriptions
from application.paiements import ServicePaiements
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["inscriptions"])


class InscrireRequete(BaseModel):
    """Corps d'inscription : le départ (créneau) sur lequel inscrire l'archer."""

    depart_id: int


class MarquerPayeRequete(BaseModel):
    """Corps de mise à jour du statut de paiement d'une inscription."""

    paye: bool


class InscriptionReponse(BaseModel):
    """Représentation d'une inscription renvoyée au client.

    `montant_du_centimes` est **dérivé** du tarif du départ (ADR-0017), pas un champ stocké ; en
    **centimes entiers** (l'unité est dans le nom), c'est le client qui met en forme des euros.
    `numero_depart` et `horaire` évitent au client une seconde lecture pour afficher le créneau.
    """

    id: int
    archer_id: int
    depart_id: int
    numero_depart: int
    horaire: str | None
    paye: bool
    montant_du_centimes: int

    @staticmethod
    def de_detail(detail: InscriptionDetaillee) -> InscriptionReponse:
        """Traduit la vue applicative (inscription + départ) en DTO de réponse."""
        inscription = detail.inscription
        assert inscription.id is not None, "Une inscription persistée a toujours un identifiant."
        return InscriptionReponse(
            id=inscription.id,
            archer_id=inscription.archer_id,
            depart_id=inscription.depart_id,
            numero_depart=detail.depart.numero,
            horaire=detail.depart.horaire,
            paye=inscription.paye,
            montant_du_centimes=detail.montant_du_centimes,
        )


class MontantDuReponse(BaseModel):
    """Montant total dû par un archer, en **centimes entiers** (ADR-0012 ; le client met en euros).

    Somme **dérivée** des tarifs de ses créneaux (E08US001) — aucun champ stocké : le total change
    dès qu'une inscription ou un tarif change.
    """

    archer_id: int
    montant_du_centimes: int


@router.post(
    "/archers/{archer_id}/inscriptions",
    status_code=201,
    response_model=InscriptionReponse,
    dependencies=[Depends(exiger_admin)],
)
async def inscrire(
    archer_id: int, requete: InscrireRequete, request: Request
) -> InscriptionReponse:
    """Inscrit un archer sur un départ de son tournoi (**action admin**) : écriture via la file.

    Renvoie `404` si l'archer ou le départ n'existe pas (ou n'est pas du tournoi de l'archer),
    `409 deja_inscrit` si l'archer est déjà inscrit sur ce créneau, `409 depart_complet` si le
    créneau porte un quota déjà atteint (E02US006).
    """
    service: ServiceInscriptions = request.app.state.service_inscriptions
    write_queue: WriteQueue = request.app.state.write_queue
    detail = await asyncio.wrap_future(
        write_queue.submit(lambda: service.inscrire(archer_id, requete.depart_id))
    )
    return InscriptionReponse.de_detail(detail)


@router.get("/archers/{archer_id}/inscriptions", response_model=list[InscriptionReponse])
async def lister_inscriptions(archer_id: int, request: Request) -> list[InscriptionReponse]:
    """Liste les inscriptions d'un archer (avec montant dû dérivé) : lecture directe hors boucle."""
    service: ServiceInscriptions = request.app.state.service_inscriptions
    details = await run_in_threadpool(service.lister_par_archer, archer_id)
    return [InscriptionReponse.de_detail(detail) for detail in details]


@router.get("/archers/{archer_id}/montant-du", response_model=MontantDuReponse)
async def montant_du(archer_id: int, request: Request) -> MontantDuReponse:
    """Montant total dû par un archer (somme dérivée des tarifs) : lecture directe hors boucle.

    Renvoie `404 archer_introuvable` si l'archer n'existe pas — pas « 0 dû » pour un inconnu.
    """
    service: ServiceInscriptions = request.app.state.service_inscriptions
    montant = await run_in_threadpool(service.montant_du_par_archer, archer_id)
    return MontantDuReponse(archer_id=archer_id, montant_du_centimes=montant)


@router.put(
    "/inscriptions/{inscription_id}",
    response_model=InscriptionReponse,
    dependencies=[Depends(exiger_admin)],
)
async def marquer_paye(
    inscription_id: int, requete: MarquerPayeRequete, request: Request
) -> InscriptionReponse:
    """Marque une inscription payée / non payée (**action admin**) : écriture via la file.

    Le marquage a migré vers `ServicePaiements` (E08US002) — même voie que les règlements groupés,
    donc **audité** (trace `PAIEMENT`). L'endpoint reste sur la ressource inscription (le front de
    saisie l'appelle par inscription) ; seul le service change.
    """
    service: ServicePaiements = request.app.state.service_paiements
    write_queue: WriteQueue = request.app.state.write_queue
    detail = await asyncio.wrap_future(
        write_queue.submit(lambda: service.marquer_inscription(inscription_id, requete.paye))
    )
    return InscriptionReponse.de_detail(detail)


@router.delete(
    "/inscriptions/{inscription_id}",
    status_code=204,
    dependencies=[Depends(exiger_admin)],
)
async def desinscrire(inscription_id: int, request: Request) -> Response:
    """Désinscrit un archer d'un départ (**action admin**) : écriture via la file, 204 si succès."""
    service: ServiceInscriptions = request.app.state.service_inscriptions
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(write_queue.submit(lambda: service.desinscrire(inscription_id)))
    return Response(status_code=204)
