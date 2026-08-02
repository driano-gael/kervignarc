"""Endpoints REST du **barrage de places décisives** (E06US003, ADR-0066).

Expose `ServiceBarrage` à l'organisateur : **annoncer** un barrage sur une égalité que la politique
`tiebreak` signale, **saisir** (ou corriger) ses manches, le **clore**. Écritures routées par la
**file** du writer unique (règle 7), derrière `exiger_admin` — annoncer un barrage change le
classement publié, c'est un acte d'organisation, pas de saisie de cible.

Les **égalités à départager** ne sont pas exposées ici : elles voyagent avec le classement
(`GET /tournois/{id}/classement`), qui est la seule surface qui sache les calculer. Un second
endpoint qui les recalculerait produirait une réponse qui dériverait de celle affichée à l'écran.

⚠️ **La distance au centre est en dixièmes de millimètre**, et son absence n'est **pas** un zéro :
c'est une mesure non faite, sur laquelle le moteur refuse de départager (il fait retirer). C'est le
cas le plus fréquent du jour J — le juge mesure la flèche litigieuse, rarement les deux.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.barrages import ServiceBarrage
from domain.barrage import BarrageDePlaces
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["barrages"])


# --- DTO ---


class TirRequete(BaseModel):
    """Ce qu'un archer a réalisé au barrage.

    `score` **nul** signifie **absent au barrage annoncé** — issue réglementaire (B.6.5.2.4 :
    l'archer est déclaré perdant), et non « je ne l'ai pas encore saisi ». Une flèche pas encore
    notée ne s'envoie tout simplement pas.
    """

    archer_id: int
    score: int | None = Field(default=None, ge=0, le=10)
    distance_au_centre: int | None = Field(default=None, ge=0)


class MancheRequete(BaseModel):
    """Les tirs d'une manche. `manche` absent = la suivante ; fourni = la manche à **corriger**."""

    tirs: list[TirRequete] = Field(min_length=2, max_length=64)
    """Un barrage oppose **au moins deux** tireurs, et le groupe se retire **en entier**.

    `min_length=2` n'est pas décoratif : une liste vide effaçait la manche, et une liste d'un seul
    tir faisait « gagner » celui qui avait tiré, faute d'adversaire. Le plafond borne l'entrée
    cliente, comme `ConfigPhaseRequete.sources`.
    """

    manche: int | None = Field(default=None, ge=1)


class AnnonceRequete(BaseModel):
    """Le rang partagé sur lequel on fait tirer."""

    rang: int = Field(ge=1)


class TirReponse(BaseModel):
    archer_id: int
    score: int | None
    distance_au_centre: int | None


class BarrageReponse(BaseModel):
    """Un barrage et son état — y compris ce qu'il **reste** à faire tirer.

    `ordre` est le verdict quand le barrage a tout départagé, et **vide** sinon :
    `groupes_a_rejouer` nomme alors qui doit retirer, **par groupe**. Les deux sont exclusifs, et
    les groupes ne sont pas aplatis — un barrage à quatre dont deux à 10 et deux à 8 laisse *deux*
    égalités distinctes, qui se retirent séparément.
    """

    id: int | None
    tournoi_id: int
    portee: str
    rang_dispute: int | None
    participants: list[int]
    manches: list[list[TirReponse]]
    clos: bool
    est_resolu: bool
    ordre: list[int]
    groupes_a_rejouer: list[list[int]]

    @staticmethod
    def de_agregat(barrage: BarrageDePlaces) -> BarrageReponse:
        resultat = barrage.resultat()
        return BarrageReponse(
            id=barrage.id,
            tournoi_id=barrage.tournoi_id,
            portee=barrage.portee.value,
            rang_dispute=barrage.rang_dispute,
            participants=[p.ref_id for p in barrage.participants],
            manches=[
                [
                    TirReponse(
                        archer_id=tir.participant.ref_id,
                        score=tir.score,
                        distance_au_centre=tir.distance_au_centre,
                    )
                    for tir in manche
                ]
                for manche in barrage.manches
            ],
            clos=barrage.clos,
            est_resolu=resultat.est_resolu,
            ordre=[p.ref_id for p in resultat.ordre],
            groupes_a_rejouer=[[p.ref_id for p in groupe] for groupe in resultat.groupes_a_rejouer],
        )


# --- routes ---


@router.get("/tournois/{tournoi_id}/barrages", response_model=list[BarrageReponse])
async def lister_barrages(tournoi_id: int, request: Request) -> list[BarrageReponse]:
    """Les barrages d'un tournoi, **clos compris** — ce sont eux qui portent les verdicts acquis."""
    service: ServiceBarrage = request.app.state.service_barrage
    barrages = await run_in_threadpool(service.lister, tournoi_id)
    return [BarrageReponse.de_agregat(barrage) for barrage in barrages]


@router.post(
    "/tournois/{tournoi_id}/barrages",
    response_model=BarrageReponse,
    status_code=201,
    dependencies=[Depends(exiger_admin)],
)
async def annoncer_barrage(
    tournoi_id: int, requete: AnnonceRequete, request: Request
) -> BarrageReponse:
    """Annonce un barrage sur l'égalité signalée à ce rang (**idempotent** : rend celui en cours).

    409 `egalite_non_departageable` si plus rien n'est à départager à ce rang — le classement a pu
    bouger entre l'affichage et le clic.
    """
    service: ServiceBarrage = request.app.state.service_barrage
    write_queue: WriteQueue = request.app.state.write_queue
    barrage = await asyncio.wrap_future(
        write_queue.submit(lambda: service.annoncer(tournoi_id, requete.rang))
    )
    return BarrageReponse.de_agregat(barrage)


@router.put(
    "/tournois/{tournoi_id}/barrages/{barrage_id}/manche",
    response_model=BarrageReponse,
    dependencies=[Depends(exiger_admin)],
)
async def saisir_manche(
    tournoi_id: int, barrage_id: int, requete: MancheRequete, request: Request
) -> BarrageReponse:
    """Saisit la manche suivante, ou **réécrit** celle indiquée (correction d'une flèche mal notée).

    Le verdict n'étant jamais stocké mais recalculé depuis les tirs, corriger une flèche corrige le
    classement. 422 si la manche est incohérente (tireur déjà départagé, groupe retiré à moitié).
    """
    service: ServiceBarrage = request.app.state.service_barrage
    write_queue: WriteQueue = request.app.state.write_queue
    tirs = [
        ServiceBarrage.tir(tir.archer_id, tir.score, tir.distance_au_centre) for tir in requete.tirs
    ]
    barrage = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.saisir_manche(tournoi_id, barrage_id, tirs, requete.manche)
        )
    )
    return BarrageReponse.de_agregat(barrage)


@router.delete(
    "/tournois/{tournoi_id}/barrages/{barrage_id}",
    status_code=204,
    dependencies=[Depends(exiger_admin)],
)
async def annuler_barrage(tournoi_id: int, barrage_id: int, request: Request) -> None:
    """Annule un barrage annoncé par erreur (mauvais rang, égalité disparue).

    Sans cette route, un barrage qu'on ne veut pas faire tirer était **définitif** : la clôture
    exige un barrage résolu, et son rang bloquait toute nouvelle annonce. 409 si le barrage est
    clos — son verdict est acquis, c'est une correction de manche qu'il faut alors, pas une
    suppression.
    """
    service: ServiceBarrage = request.app.state.service_barrage
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(write_queue.submit(lambda: service.annuler(tournoi_id, barrage_id)))


@router.post(
    "/tournois/{tournoi_id}/barrages/{barrage_id}/cloture",
    response_model=BarrageReponse,
    dependencies=[Depends(exiger_admin)],
)
async def clore_barrage(tournoi_id: int, barrage_id: int, request: Request) -> BarrageReponse:
    """Clôt un barrage **résolu**. 409 s'il reste un groupe à faire retirer."""
    service: ServiceBarrage = request.app.state.service_barrage
    write_queue: WriteQueue = request.app.state.write_queue
    barrage = await asyncio.wrap_future(
        write_queue.submit(lambda: service.clore(tournoi_id, barrage_id))
    )
    return BarrageReponse.de_agregat(barrage)
