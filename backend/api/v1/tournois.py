"""Endpoints REST des tournois (`/api/v1/tournois`).

- créer, consulter, lister (E01US001) ;
- éditer, démarrer, terminer, supprimer (E01US002).

Suit le patron de bout en bout (E00US009) :
- **DTO Pydantic** distincts des agrégats de domaine (aucune entité domaine exposée) ;
- **écriture** routée par la **file d'écriture** (writer unique, ADR-0005), attendue via
  `asyncio.wrap_future` sans bloquer la boucle ; toute écriture exige une session admin
  (`exiger_admin`, E10US001/E10US002) ;
- **lecture** directe exécutée **hors boucle** (threadpool) ;
- **erreurs typées** traduites à la frontière (`api/erreurs.py`).
"""

from __future__ import annotations

import asyncio
import datetime

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.tournois import ServiceTournois
from domain.tournoi import StatutTournoi, Tournoi, TypeTournoi
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1/tournois", tags=["tournois"])


class CreerTournoiRequete(BaseModel):
    """Corps de création d'un tournoi (nom et date requis ; lieu, type et tarif facultatifs)."""

    nom: str
    date: datetime.date
    lieu: str | None = None
    type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL
    tarif_depart_centimes: int | None = None


class ModifierTournoiRequete(BaseModel):
    """Corps d'édition des métadonnées d'un tournoi (le statut n'est pas modifiable ici).

    `tarif_depart_centimes` est **remplacé**, pas fusionné : l'omettre (ou l'envoyer à `null`) remet
    le tarif à « non défini ». Le client réémet la valeur qu'il a lue.
    """

    nom: str
    date: datetime.date
    lieu: str | None = None
    type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL
    tarif_depart_centimes: int | None = None


class TournoiReponse(BaseModel):
    """Représentation d'un tournoi renvoyée au client.

    `tarif_depart_centimes` est en **centimes entiers** (l'unité est dans le nom) : c'est le client
    qui met en forme des euros. `null` = tarif **non défini**, `0` = **gratuit** — deux états
    distincts, à ne pas confondre à l'affichage.
    """

    id: int
    nom: str
    date: datetime.date
    lieu: str | None
    type_tournoi: TypeTournoi
    statut: StatutTournoi
    tarif_depart_centimes: int | None

    @staticmethod
    def de_agregat(tournoi: Tournoi) -> TournoiReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert tournoi.id is not None, "Un tournoi persisté a toujours un identifiant."
        return TournoiReponse(
            id=tournoi.id,
            nom=tournoi.nom,
            date=tournoi.date,
            lieu=tournoi.lieu,
            type_tournoi=tournoi.type_tournoi,
            statut=tournoi.statut,
            tarif_depart_centimes=tournoi.tarif_depart_centimes,
        )


@router.post(
    "",
    status_code=201,
    response_model=TournoiReponse,
    dependencies=[Depends(exiger_admin)],
)
async def creer_tournoi(requete: CreerTournoiRequete, request: Request) -> TournoiReponse:
    """Crée un tournoi (**action admin**, E10US002) : l'écriture passe par la file (ADR-0005)."""
    service: ServiceTournois = request.app.state.service_tournois
    write_queue: WriteQueue = request.app.state.write_queue
    tournoi = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.creer(
                requete.nom,
                requete.date,
                requete.lieu,
                requete.type_tournoi,
                requete.tarif_depart_centimes,
            )
        )
    )
    return TournoiReponse.de_agregat(tournoi)


@router.get("", response_model=list[TournoiReponse])
async def lister_tournois(request: Request) -> list[TournoiReponse]:
    """Liste tous les tournois : lecture directe exécutée hors de la boucle événementielle."""
    service: ServiceTournois = request.app.state.service_tournois
    tournois = await run_in_threadpool(service.lister)
    return [TournoiReponse.de_agregat(tournoi) for tournoi in tournois]


@router.get("/{tournoi_id}", response_model=TournoiReponse)
async def consulter_tournoi(tournoi_id: int, request: Request) -> TournoiReponse:
    """Relit un tournoi : lecture directe exécutée hors de la boucle événementielle."""
    service: ServiceTournois = request.app.state.service_tournois
    tournoi = await run_in_threadpool(service.consulter, tournoi_id)
    return TournoiReponse.de_agregat(tournoi)


@router.put(
    "/{tournoi_id}",
    response_model=TournoiReponse,
    dependencies=[Depends(exiger_admin)],
)
async def modifier_tournoi(
    tournoi_id: int, requete: ModifierTournoiRequete, request: Request
) -> TournoiReponse:
    """Édite les métadonnées d'un tournoi (**action admin**) : écriture via la file (ADR-0005)."""
    service: ServiceTournois = request.app.state.service_tournois
    write_queue: WriteQueue = request.app.state.write_queue
    tournoi = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.modifier(
                tournoi_id,
                requete.nom,
                requete.date,
                requete.lieu,
                requete.type_tournoi,
                requete.tarif_depart_centimes,
            )
        )
    )
    return TournoiReponse.de_agregat(tournoi)


@router.post(
    "/{tournoi_id}/demarrer",
    response_model=TournoiReponse,
    dependencies=[Depends(exiger_admin)],
)
async def demarrer_tournoi(tournoi_id: int, request: Request) -> TournoiReponse:
    """Démarre un tournoi (`brouillon` → `en_cours`, **action admin**) : écriture via la file."""
    service: ServiceTournois = request.app.state.service_tournois
    write_queue: WriteQueue = request.app.state.write_queue
    tournoi = await asyncio.wrap_future(write_queue.submit(lambda: service.demarrer(tournoi_id)))
    return TournoiReponse.de_agregat(tournoi)


@router.post(
    "/{tournoi_id}/terminer",
    response_model=TournoiReponse,
    dependencies=[Depends(exiger_admin)],
)
async def terminer_tournoi(tournoi_id: int, request: Request) -> TournoiReponse:
    """Termine un tournoi (`en_cours` → `termine`, **action admin**) : écriture via la file."""
    service: ServiceTournois = request.app.state.service_tournois
    write_queue: WriteQueue = request.app.state.write_queue
    tournoi = await asyncio.wrap_future(write_queue.submit(lambda: service.terminer(tournoi_id)))
    return TournoiReponse.de_agregat(tournoi)


@router.delete(
    "/{tournoi_id}",
    status_code=204,
    dependencies=[Depends(exiger_admin)],
)
async def supprimer_tournoi(tournoi_id: int, request: Request) -> Response:
    """Supprime un tournoi (**action admin**) : refusé (409) s'il est en cours.

    L'écriture passe par la file (ADR-0005) ; renvoie 204 sans contenu en cas de succès.
    """
    service: ServiceTournois = request.app.state.service_tournois
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(write_queue.submit(lambda: service.supprimer(tournoi_id)))
    return Response(status_code=204)
