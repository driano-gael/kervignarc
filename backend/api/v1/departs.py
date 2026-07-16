"""Endpoints REST des départs — créneaux d'un tournoi (`/api/v1/tournois/{tournoi_id}/departs`).

Configurer les départs d'un tournoi (E02US004, ADR-0017) : créer, lister, éditer (tarif/horaire),
supprimer. Les routes sont **imbriquées sous le tournoi** — un départ n'existe pas hors de lui.

Suit le patron de bout en bout (E00US009) : DTO Pydantic distincts des agrégats ; écritures routées
par la **file d'écriture** (writer unique, ADR-0005) et réservées à l'admin (`exiger_admin`) ;
lectures **hors boucle** (threadpool) ; erreurs typées traduites à la frontière (`api/erreurs.py`).
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.departs import ServiceDeparts
from domain.depart import Depart
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1/tournois/{tournoi_id}/departs", tags=["departs"])


class CreerDepartRequete(BaseModel):
    """Corps de création d'un départ : tarif requis (centimes), horaire facultatif.

    Le **numéro** n'est pas dans le corps : il est attribué par le serveur (le plus grand + 1).
    """

    tarif_centimes: int
    horaire: str | None = None


class ModifierDepartRequete(BaseModel):
    """Corps d'édition d'un départ : tarif (centimes) et horaire ; le numéro est fixe."""

    tarif_centimes: int
    horaire: str | None = None


class DepartReponse(BaseModel):
    """Représentation d'un départ renvoyée au client.

    `tarif_centimes` est en **centimes entiers** (l'unité est dans le nom) : c'est le client qui met
    en forme des euros. `0` = gratuit.
    """

    id: int
    tournoi_id: int
    numero: int
    horaire: str | None
    tarif_centimes: int

    @staticmethod
    def de_agregat(depart: Depart) -> DepartReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert depart.id is not None, "Un départ persisté a toujours un identifiant."
        return DepartReponse(
            id=depart.id,
            tournoi_id=depart.tournoi_id,
            numero=depart.numero,
            horaire=depart.horaire,
            tarif_centimes=depart.tarif_centimes,
        )


@router.post(
    "",
    status_code=201,
    response_model=DepartReponse,
    dependencies=[Depends(exiger_admin)],
)
async def creer_depart(
    tournoi_id: int, requete: CreerDepartRequete, request: Request
) -> DepartReponse:
    """Crée un départ dans un tournoi (**action admin**) : écriture via la file (ADR-0005)."""
    service: ServiceDeparts = request.app.state.service_departs
    write_queue: WriteQueue = request.app.state.write_queue
    depart = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.creer(tournoi_id, requete.tarif_centimes, requete.horaire)
        )
    )
    return DepartReponse.de_agregat(depart)


@router.get("", response_model=list[DepartReponse])
async def lister_departs(tournoi_id: int, request: Request) -> list[DepartReponse]:
    """Liste les départs d'un tournoi (triés par numéro) : lecture directe hors boucle."""
    service: ServiceDeparts = request.app.state.service_departs
    departs = await run_in_threadpool(service.lister, tournoi_id)
    return [DepartReponse.de_agregat(depart) for depart in departs]


@router.put(
    "/{depart_id}",
    response_model=DepartReponse,
    dependencies=[Depends(exiger_admin)],
)
async def modifier_depart(
    tournoi_id: int, depart_id: int, requete: ModifierDepartRequete, request: Request
) -> DepartReponse:
    """Édite le tarif et l'horaire d'un départ (**action admin**) : écriture via la file."""
    service: ServiceDeparts = request.app.state.service_departs
    write_queue: WriteQueue = request.app.state.write_queue
    depart = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.modifier(tournoi_id, depart_id, requete.tarif_centimes, requete.horaire)
        )
    )
    return DepartReponse.de_agregat(depart)


@router.delete(
    "/{depart_id}",
    status_code=204,
    dependencies=[Depends(exiger_admin)],
)
async def supprimer_depart(
    tournoi_id: int,
    depart_id: int,
    request: Request,
    autoriser_suppression_inscrits: bool = False,
) -> Response:
    """Supprime un départ d'un tournoi (**action admin**) : écriture via la file, 204 si succès.

    Renvoie `409 depart_avec_inscriptions` si le créneau porte des inscriptions : un **signalement**
    ([ADR-0018](../../../docs/adr/0018-supprimer-un-depart-a-inscriptions-confirmable.md)), que le
    client lève en rejouant l'appel avec `autoriser_suppression_inscrits`. La suppression confirmée
    **efface les inscriptions** du créneau (les payées seront à rembourser — E08US005).

    Le drapeau est en **paramètre de requête**, comme `autoriser_suppression_engage` de la
    suppression d'archer : un `DELETE` n'a pas de corps par convention HTTP (même divergence assumée
    qu'en E02US003, sanctionnée par ADR-0016).
    """
    service: ServiceDeparts = request.app.state.service_departs
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.supprimer(tournoi_id, depart_id, autoriser_suppression_inscrits)
        )
    )
    return Response(status_code=204)
