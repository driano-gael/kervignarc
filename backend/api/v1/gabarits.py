"""Endpoints REST des gabarits de salle (`/api/v1`) — CRUD des gabarits réutilisables (E01US007).

Suit le patron de bout en bout (E00US009) :
- **DTO Pydantic** distincts des agrégats de domaine ;
- **écriture** routée par la **file d'écriture** (writer unique, ADR-0005), protégée par
  `exiger_admin` (E10US001/E10US002) ;
- **lecture** directe exécutée **hors boucle** (threadpool) ;
- **erreurs typées** traduites à la frontière (`api/erreurs.py`).

Ressource **autonome** (un gabarit n'appartient pas à un tournoi) : routes à plat sous
`/gabarits` ; le rattachement d'un gabarit à un tournoi viendra en E01US008.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.gabarits import ServiceGabarits
from domain.gabarit_salle import CAPACITE_CIBLE_DEFAUT, GabaritSalle
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["gabarits"])


class CreerGabaritRequete(BaseModel):
    """Corps de création d'un gabarit (nom requis ; nb de cibles ; plafond par cible, défaut 4)."""

    nom: str
    nb_cibles: int
    capacite: int = CAPACITE_CIBLE_DEFAUT


class ModifierGabaritRequete(BaseModel):
    """Corps d'édition d'un gabarit (mêmes champs que la création)."""

    nom: str
    nb_cibles: int
    capacite: int = CAPACITE_CIBLE_DEFAUT


class CibleReponse(BaseModel):
    """Une cible du gabarit : rang, plafond d'archers et positions déduites."""

    index: int
    capacite: int
    positions: list[str]


class GabaritReponse(BaseModel):
    """Représentation d'un gabarit de salle renvoyée au client."""

    id: int
    nom: str
    nb_cibles: int
    cibles: list[CibleReponse]

    @staticmethod
    def de_agregat(gabarit: GabaritSalle) -> GabaritReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert gabarit.id is not None, "Un gabarit persisté a toujours un identifiant."
        return GabaritReponse(
            id=gabarit.id,
            nom=gabarit.nom,
            nb_cibles=gabarit.nb_cibles,
            cibles=[
                CibleReponse(
                    index=cible.index, capacite=cible.capacite, positions=list(cible.positions)
                )
                for cible in gabarit.cibles
            ],
        )


@router.get("/gabarits", response_model=list[GabaritReponse])
async def lister_gabarits(request: Request) -> list[GabaritReponse]:
    """Liste tous les gabarits de salle : lecture directe exécutée hors de la boucle."""
    service: ServiceGabarits = request.app.state.service_gabarits
    gabarits = await run_in_threadpool(service.lister)
    return [GabaritReponse.de_agregat(gabarit) for gabarit in gabarits]


@router.post(
    "/gabarits",
    status_code=201,
    response_model=GabaritReponse,
    dependencies=[Depends(exiger_admin)],
)
async def creer_gabarit(requete: CreerGabaritRequete, request: Request) -> GabaritReponse:
    """Crée un gabarit de salle (**action admin**) : écriture via la file (ADR-0005)."""
    service: ServiceGabarits = request.app.state.service_gabarits
    write_queue: WriteQueue = request.app.state.write_queue
    gabarit = await asyncio.wrap_future(
        write_queue.submit(lambda: service.creer(requete.nom, requete.nb_cibles, requete.capacite))
    )
    return GabaritReponse.de_agregat(gabarit)


@router.put(
    "/gabarits/{gabarit_id}",
    response_model=GabaritReponse,
    dependencies=[Depends(exiger_admin)],
)
async def modifier_gabarit(
    gabarit_id: int, requete: ModifierGabaritRequete, request: Request
) -> GabaritReponse:
    """Édite un gabarit (**action admin**) : écriture via la file (ADR-0005)."""
    service: ServiceGabarits = request.app.state.service_gabarits
    write_queue: WriteQueue = request.app.state.write_queue
    gabarit = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.modifier(gabarit_id, requete.nom, requete.nb_cibles, requete.capacite)
        )
    )
    return GabaritReponse.de_agregat(gabarit)


@router.delete(
    "/gabarits/{gabarit_id}",
    status_code=204,
    dependencies=[Depends(exiger_admin)],
)
async def supprimer_gabarit(gabarit_id: int, request: Request) -> Response:
    """Supprime un gabarit (**action admin**) : écriture via la file ; renvoie 204."""
    service: ServiceGabarits = request.app.state.service_gabarits
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(write_queue.submit(lambda: service.supprimer(gabarit_id)))
    return Response(status_code=204)
