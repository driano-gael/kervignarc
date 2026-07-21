"""Endpoints REST du suivi des paiements (E08US002).

Consulter les paiements **par archer** (dû / payé / reste) et **par club** (mêmes totaux agrégés,
détail des archers), et **marquer** un règlement groupé (tout un archer, tout un club). Le marquage
d'**une** inscription reste sur sa ressource (`PUT /api/v1/inscriptions/{id}`, cf.
`inscriptions.py`)
— toutes ces écritures partagent la même voie de service (`ServicePaiements`), donc la même trace
d'audit `PAIEMENT`.

Suit le patron de bout en bout : DTO Pydantic distincts des vues applicatives ; **tout réservé à
l'admin** (`exiger_admin`) — les montants ne sont pas des données publiques (au contraire des
classements, E07US001) ; écritures routées par la **file d'écriture** (writer unique, ADR-0005),
lectures **hors boucle** (threadpool) ; erreurs typées traduites à la frontière.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.paiements import LignePaiementArcher, RecapClub, ServicePaiements
from domain.paiement import RecapPaiement
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["paiements"])


class MarquerPayeRequete(BaseModel):
    """Corps d'un marquage groupé : le statut visé pour toutes les inscriptions concernées."""

    paye: bool


class RecapPaiementReponse(BaseModel):
    """Récapitulatif dû / payé / reste, en **centimes entiers** (le client met en euros).

    `reste_centimes` est **explicité** dans la réponse (bien que dérivable de dû - payé) pour éviter
    au client de recalculer la règle métier : c'est le serveur autoritaire qui la porte.
    """

    du_centimes: int
    paye_centimes: int
    reste_centimes: int

    @staticmethod
    def de(recap: RecapPaiement) -> RecapPaiementReponse:
        return RecapPaiementReponse(
            du_centimes=recap.du_centimes,
            paye_centimes=recap.paye_centimes,
            reste_centimes=recap.reste_centimes,
        )


class LignePaiementArcherReponse(BaseModel):
    """Une ligne de la vue par archer : l'archer, son club éventuel et son récapitulatif."""

    archer_id: int
    nom: str
    prenom: str
    club_id: int | None
    recap: RecapPaiementReponse

    @staticmethod
    def de(ligne: LignePaiementArcher) -> LignePaiementArcherReponse:
        return LignePaiementArcherReponse(
            archer_id=ligne.archer_id,
            nom=ligne.nom,
            prenom=ligne.prenom,
            club_id=ligne.club_id,
            recap=RecapPaiementReponse.de(ligne.recap),
        )


class RecapClubReponse(BaseModel):
    """Un groupe de la vue par club : le club (ou le bucket « sans club »), son total, ses archers.

    `club_id is null` désigne le regroupement **virtuel** des archers sans club (ADR-0014) : il n'a
    pas d'identifiant réel et ne peut pas être marqué en lot (`PUT .../clubs/{id}` exige un club).
    """

    club_id: int | None
    nom: str
    recap: RecapPaiementReponse
    archers: list[LignePaiementArcherReponse]

    @staticmethod
    def de(recap_club: RecapClub) -> RecapClubReponse:
        return RecapClubReponse(
            club_id=recap_club.club_id,
            nom=recap_club.nom,
            recap=RecapPaiementReponse.de(recap_club.recap),
            archers=[LignePaiementArcherReponse.de(ligne) for ligne in recap_club.archers],
        )


@router.get(
    "/tournois/{tournoi_id}/paiements/archers",
    response_model=list[LignePaiementArcherReponse],
    dependencies=[Depends(exiger_admin)],
)
async def lister_par_archer(tournoi_id: int, request: Request) -> list[LignePaiementArcherReponse]:
    """Vue paiement **par archer** (dû / payé / reste) : lecture directe hors boucle.

    Renvoie `404 tournoi_introuvable` si le tournoi n'existe pas.
    """
    service: ServicePaiements = request.app.state.service_paiements
    lignes = await run_in_threadpool(service.lister_par_archer, tournoi_id)
    return [LignePaiementArcherReponse.de(ligne) for ligne in lignes]


@router.get(
    "/tournois/{tournoi_id}/paiements/clubs",
    response_model=list[RecapClubReponse],
    dependencies=[Depends(exiger_admin)],
)
async def recap_par_club(tournoi_id: int, request: Request) -> list[RecapClubReponse]:
    """Vue paiement **par club** (totaux + détail des archers) : lecture directe hors boucle.

    Renvoie `404 tournoi_introuvable` si le tournoi n'existe pas.
    """
    service: ServicePaiements = request.app.state.service_paiements
    recaps = await run_in_threadpool(service.recap_par_club, tournoi_id)
    return [RecapClubReponse.de(recap) for recap in recaps]


@router.put(
    "/tournois/{tournoi_id}/paiements/archers/{archer_id}",
    response_model=LignePaiementArcherReponse,
    dependencies=[Depends(exiger_admin)],
)
async def marquer_archer(
    tournoi_id: int, archer_id: int, requete: MarquerPayeRequete, request: Request
) -> LignePaiementArcherReponse:
    """Marque **toutes** les inscriptions d'un archer (règlement groupé) : écriture via la file.

    Renvoie `404 archer_introuvable` si l'archer n'existe pas ou n'est pas du tournoi.
    """
    service: ServicePaiements = request.app.state.service_paiements
    write_queue: WriteQueue = request.app.state.write_queue
    ligne = await asyncio.wrap_future(
        write_queue.submit(lambda: service.marquer_archer(tournoi_id, archer_id, requete.paye))
    )
    return LignePaiementArcherReponse.de(ligne)


@router.put(
    "/tournois/{tournoi_id}/paiements/clubs/{club_id}",
    response_model=RecapClubReponse,
    dependencies=[Depends(exiger_admin)],
)
async def marquer_club(
    tournoi_id: int, club_id: int, requete: MarquerPayeRequete, request: Request
) -> RecapClubReponse:
    """Marque toutes les inscriptions des archers d'un club (de ce tournoi) : écriture via la file.

    Renvoie `404 club_introuvable` si le club n'existe pas.
    """
    service: ServicePaiements = request.app.state.service_paiements
    write_queue: WriteQueue = request.app.state.write_queue
    recap = await asyncio.wrap_future(
        write_queue.submit(lambda: service.marquer_club(tournoi_id, club_id, requete.paye))
    )
    return RecapClubReponse.de(recap)
