"""Frontière API — plan de duels d'une phase de tableau (E03US009, ADR-0048).

Le `GET` renvoie le plan **persisté** : cibles remplies, réserve (`conflits`) et signal côte à côte
(`adjacence_non_garantie` par cible, `duels_separes` pour la bannière). `PlacementReponse` et
`ConflitReponse` sont partagées avec le plan de cibles — même sens métier, pas une commodité.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from api.v1.placement import ConflitReponse, PlacementReponse, _inscription
from application.placement_duels import PlanDeDuels, ServicePlacementDuels
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["placement-duels"])


class CiblePlaceeDuelReponse(BaseModel):
    """Une cible du plan de duels : rang, plafond, duellistes posés, et le drapeau d'adjacence.

    `adjacence_non_garantie` (E03US009, ADR-0048) : `true` quand un duelliste posé n'a pas son
    adversaire côte à côte. Le front en fait un badge ambre ; dérivé, jamais persisté.
    `cloisonnement_non_respecte` (E03US007) : `true` quand la cible mêle ce que le réglage interdit
    — un plan **posé avant** l'activation du réglage. Même régime dérivé, et même signal que sur le
    plan de cibles : le cloisonnement vaut pour la salle, pas pour un écran.
    """

    index: int
    capacite: int
    placements: list[PlacementReponse]
    adjacence_non_garantie: bool
    cloisonnement_non_respecte: bool


class DuelSepareReponse(BaseModel):
    """Un duel non côte à côte : les `archer_id` des deux adversaires (bannière récapitulative)."""

    archer_a: int
    archer_b: int


class PlanDeDuelsReponse(BaseModel):
    """Le plan de duels d'un **tour** : cibles remplies + réserve + duels non côte à côte."""

    phase_id: int
    # Le tour que ce plan pose (ADR-0106 §2) : l'écran le nomme. `null` quand le tableau n'est
    # pas encore constitué — il n'y a alors aucun tour à nommer, et en inventer un ferait afficher
    # « Tour 1 » pendant que le tableau joue le tour N.
    tour: int | None
    cibles: list[CiblePlaceeDuelReponse]
    conflits: list[ConflitReponse]
    duels_separes: list[DuelSepareReponse]

    @staticmethod
    def de_plan(phase_id: int, plan: PlanDeDuels) -> PlanDeDuelsReponse:
        return PlanDeDuelsReponse(
            phase_id=phase_id,
            tour=plan.tour,
            cibles=[
                CiblePlaceeDuelReponse(
                    index=cible.index,
                    capacite=cible.capacite,
                    placements=[
                        PlacementReponse(
                            position=p.position,
                            archer_id=p.archer_id,
                            blason_id=p.blason_id,
                            inscription_id=_inscription(p.inscription_id),
                        )
                        for p in cible.placements
                    ],
                    adjacence_non_garantie=cible.index in plan.adjacence_non_garantie,
                    cloisonnement_non_respecte=cible.cloisonnement_non_respecte,
                )
                for cible in plan.cibles
            ],
            conflits=[ConflitReponse.de_conflit(conflit) for conflit in plan.conflits],
            duels_separes=[
                DuelSepareReponse(archer_a=a, archer_b=b) for a, b in plan.duels_separes
            ],
        )


class DeplacerRequete(BaseModel):
    """Destination d'un duelliste : `cible_index` + `position`, ou `cible_index` **null** = réserve.

    Case libre → déplacement ; case occupée → échange atomique ; `null` → réserve. Un geste invalide
    (position inexistante/occupée, hauteur incompatible) → 409 `deplacement_invalide`."""

    cible_index: int | None = None
    position: str | None = None


@router.get(
    "/tournois/{tournoi_id}/phases/{phase_id}/plan-de-duels",
    response_model=PlanDeDuelsReponse,
)
async def plan_de_duels(tournoi_id: int, phase_id: int, request: Request) -> PlanDeDuelsReponse:
    """Renvoie le plan de duels **persisté** d'une phase de tableau (lecture, ADR-0048).

    Cibles remplies + réserve + signal côte à côte. 404 si le tournoi, la phase ou le gabarit
    n'existent pas ; 409 `phase_pas_un_tableau` si la phase n'est pas une élimination directe."""
    service: ServicePlacementDuels = request.app.state.service_placement_duels
    plan = await run_in_threadpool(service.plan_de_duels, tournoi_id, phase_id)
    return PlanDeDuelsReponse.de_plan(phase_id, plan)


@router.post(
    "/tournois/{tournoi_id}/phases/{phase_id}/plan-de-duels/regenerer",
    response_model=PlanDeDuelsReponse,
    dependencies=[Depends(exiger_admin)],
)
async def regenerer_plan(tournoi_id: int, phase_id: int, request: Request) -> PlanDeDuelsReponse:
    """(Re)génère le plan de duels auto (**action admin**) — c'est aussi « annuler » (déterministe).

    Recalcule l'arbre du classement, place les duellistes côte à côte, écrase l'existant. Écriture
    via la file. Pas de confirmation d'impact parce qu'il n'y a rien à chiffrer : la route est
    **refusée** (409, `regeneration_sur_tour_en_tir`) dès qu'un duel du tour posé porte un tir.
    ⚠️ Le tour posé est celui **qui se joue** — ne pas lire « tour déjà tiré » comme « tour
    terminé »."""
    service: ServicePlacementDuels = request.app.state.service_placement_duels
    write_queue: WriteQueue = request.app.state.write_queue
    plan = await asyncio.wrap_future(
        write_queue.submit(lambda: service.regenerer(tournoi_id, phase_id))
    )
    return PlanDeDuelsReponse.de_plan(phase_id, plan)


@router.put(
    "/tournois/{tournoi_id}/phases/{phase_id}/plan-de-duels/inscriptions/{inscription_id}",
    response_model=PlanDeDuelsReponse,
    dependencies=[Depends(exiger_admin)],
)
async def deplacer_duelliste(
    tournoi_id: int,
    phase_id: int,
    inscription_id: int,
    requete: DeplacerRequete,
    request: Request,
) -> PlanDeDuelsReponse:
    """Déplace, échange ou met en réserve un duelliste (**action admin**) : écriture via la file.

    Renvoie le plan mis à jour, ou **409 `deplacement_invalide`** si le geste viole une contrainte
    (état inchangé). 404 si l'inscription ne dispute pas la phase."""
    service: ServicePlacementDuels = request.app.state.service_placement_duels
    write_queue: WriteQueue = request.app.state.write_queue
    plan = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.deplacer(
                tournoi_id, phase_id, inscription_id, requete.cible_index, requete.position
            )
        )
    )
    return PlanDeDuelsReponse.de_plan(phase_id, plan)


@router.post(
    "/tournois/{tournoi_id}/phases/{phase_id}/plan-de-duels/placer-restants",
    response_model=PlanDeDuelsReponse,
    dependencies=[Depends(exiger_admin)],
)
async def placer_les_restants(
    tournoi_id: int, phase_id: int, request: Request
) -> PlanDeDuelsReponse:
    """Place automatiquement la réserve dans les trous du plan (**action admin**) : écriture via la
    file. Ce qu'aucune cible ne peut prendre reste en réserve."""
    service: ServicePlacementDuels = request.app.state.service_placement_duels
    write_queue: WriteQueue = request.app.state.write_queue
    plan = await asyncio.wrap_future(
        write_queue.submit(lambda: service.placer_les_restants(tournoi_id, phase_id))
    )
    return PlanDeDuelsReponse.de_plan(phase_id, plan)
