"""Frontière API — plan de cibles d'un départ (E03US001).

Un seul endpoint, en **lecture** : le plan est recalculé à la demande par `ServicePlacement`
(pas de persistance en E03US001). Lecture directe hors de la boucle événementielle
(`run_in_threadpool`, règle 7) ; pas d'écriture, donc pas de file. DTO **distincts** des value
objects du domaine (règle 6) : `PlanDeCibles` n'est jamais exposé tel quel.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from application.placement import ServicePlacement
from domain.placement import CiblePlacee, Conflit, PlanDeCibles, RaisonConflit

router = APIRouter(prefix="/api/v1", tags=["placement"])


class PlacementReponse(BaseModel):
    """Un archer posé sur une cible : sa position (lettre) et le blason sur lequel il tire."""

    position: str
    archer_id: int
    blason_id: int


class CiblePlaceeReponse(BaseModel):
    """Une cible du plan : rang, plafond d'archers, et les archers posés (vide si cible libre)."""

    index: int
    capacite: int
    placements: list[PlacementReponse]

    @staticmethod
    def de_cible(cible: CiblePlacee) -> CiblePlaceeReponse:
        return CiblePlaceeReponse(
            index=cible.index,
            capacite=cible.capacite,
            placements=[
                PlacementReponse(position=p.position, archer_id=p.archer_id, blason_id=p.blason_id)
                for p in cible.placements
            ],
        )


class ConflitReponse(BaseModel):
    """Un archer que le placement n'a pas pu poser, et pourquoi (`non_place` / `sans_blason`)."""

    archer_id: int
    raison: RaisonConflit

    @staticmethod
    def de_conflit(conflit: Conflit) -> ConflitReponse:
        return ConflitReponse(archer_id=conflit.archer_id, raison=conflit.raison)


class PlanDeCiblesReponse(BaseModel):
    """Le plan de cibles d'un départ : cibles remplies + rapport de conflits."""

    depart_id: int
    cibles: list[CiblePlaceeReponse]
    conflits: list[ConflitReponse]

    @staticmethod
    def de_plan(depart_id: int, plan: PlanDeCibles) -> PlanDeCiblesReponse:
        return PlanDeCiblesReponse(
            depart_id=depart_id,
            cibles=[CiblePlaceeReponse.de_cible(cible) for cible in plan.cibles],
            conflits=[ConflitReponse.de_conflit(conflit) for conflit in plan.conflits],
        )


@router.get(
    "/tournois/{tournoi_id}/departs/{depart_id}/plan-de-cibles",
    response_model=PlanDeCiblesReponse,
)
async def plan_de_cibles(tournoi_id: int, depart_id: int, request: Request) -> PlanDeCiblesReponse:
    """Renvoie le plan de cibles calculé pour un départ (lecture, recalcul à la demande).

    404 si le tournoi, le départ, ou le gabarit appliqué au tournoi n'existent pas : le service
    lève l'erreur applicative correspondante, traduite à la frontière."""
    service: ServicePlacement = request.app.state.service_placement
    plan = await run_in_threadpool(service.plan_de_cibles, tournoi_id, depart_id)
    return PlanDeCiblesReponse.de_plan(depart_id, plan)
