"""Frontière API — plan de cibles d'un départ (E03US001 lecture ; E03US004 ajustement, ADR-0024).

La **lecture** (`GET`) renvoie le plan **persisté** (matérialisé E03US004) : cibles remplies +
réserve (dans `conflits`, avec sa raison). Directe hors boucle (`run_in_threadpool`, règle 7).
Les **écritures** — régénérer/annuler, déplacer/échanger/mettre en réserve, placer les restants —
passent par la **file** (writer unique, ADR-0005) et sont réservées à l'admin (`exiger_admin`) ;
leur commit déclenche la diffusion live (broadcaster post-commit → invalidation front). DTO
**distincts** des value objects du domaine (règle 6) : `PlanDeCibles` n'est jamais exposé tel quel.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.placement import ServicePlacement
from domain.impact import ImpactRegeneration, NiveauImpact
from domain.placement import CiblePlacee, Conflit, PlanDeCibles, RaisonConflit
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["placement"])


def _inscription(inscription_id: int | None) -> int:
    """Garantit l'inscription d'un placement/conflit **exposé** : le service la renseigne toujours.

    Le moteur pur laisse `inscription_id` à `None` (il ignore l'inscription) ; un plan atteint
    l'API **uniquement** via le service, qui la fixe (E03US004). L'assertion documente cet invariant
    et satisfait le typage strict."""
    assert inscription_id is not None, "Un placement exposé porte toujours son inscription."
    return inscription_id


class PlacementReponse(BaseModel):
    """Un archer posé sur une cible : position, blason, et son **inscription** (cible d'ajustement).

    `inscription_id` évite au client de reconstituer la correspondance archer → inscription : c'est
    lui qu'il renvoie au `PUT .../inscriptions/{id}` pour déplacer l'archer."""

    position: str
    archer_id: int
    blason_id: int
    inscription_id: int


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
                PlacementReponse(
                    position=p.position,
                    archer_id=p.archer_id,
                    blason_id=p.blason_id,
                    inscription_id=_inscription(p.inscription_id),
                )
                for p in cible.placements
            ],
        )


class ConflitReponse(BaseModel):
    """Un archer **en réserve** (non posé), et pourquoi : `non_place`/`sans_blason`/`en_reserve`.

    `inscription_id` : pour reposer l'archer depuis la réserve (drag) sans reconstituer la
    correspondance archer → inscription côté client."""

    archer_id: int
    raison: RaisonConflit
    inscription_id: int

    @staticmethod
    def de_conflit(conflit: Conflit) -> ConflitReponse:
        return ConflitReponse(
            archer_id=conflit.archer_id,
            raison=conflit.raison,
            inscription_id=_inscription(conflit.inscription_id),
        )


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


class ImpactRegenerationReponse(BaseModel):
    """Impact chiffré de régénérer le plan (E12US007, ADR-0040) : prévisualisation avant le geste.

    `niveau` (`aucun`/`confirmation`/`massif`) dicte l'UI : rien à afficher, confirmation simple, ou
    **taper `REPLACER`**. Les chiffres nourrissent l'alerte (« N archers replacés ; M cibles ont des
    scores, conservés »). DTO **distinct** du value object domaine (règle 6)."""

    niveau: NiveauImpact
    archers_deplaces: int
    cibles_avec_scores: int

    @staticmethod
    def de_impact(impact: ImpactRegeneration) -> ImpactRegenerationReponse:
        return ImpactRegenerationReponse(
            niveau=impact.niveau,
            archers_deplaces=impact.archers_deplaces,
            cibles_avec_scores=impact.cibles_avec_scores,
        )


class RegenererRequete(BaseModel):
    """Corps de la régénération : `confirme` autorise l'écrasement d'un plan **massif** (E12US007).

    Le serveur n'exige qu'un **booléen** (contrat `autoriser_*`) : le mot à taper (`REPLACER`) est
    une friction **front**, le serveur ignore la copie d'UI (ADR-0040 §4). `confirme=false` par
    défaut : régénérer sans prévisualiser reçoit le 409 chiffré si l'action est massive."""

    confirme: bool = False


class DeplacerRequete(BaseModel):
    """Destination d'un inscrit : `cible_index` + `position`, ou `cible_index` **null** = réserve.

    Un dépôt sur une case **libre** déplace ; sur une case **occupée**, échange atomique ; `null`
    met en réserve. Une position invalide/occupée-depuis-la-réserve/hauteur incompatible → 409
    `deplacement_invalide` (le service tranche, cf. `application/erreurs.py`)."""

    cible_index: int | None = None
    position: str | None = None


@router.get(
    "/tournois/{tournoi_id}/departs/{depart_id}/plan-de-cibles",
    response_model=PlanDeCiblesReponse,
)
async def plan_de_cibles(tournoi_id: int, depart_id: int, request: Request) -> PlanDeCiblesReponse:
    """Renvoie le plan **persisté** d'un départ (lecture ; ADR-0024, plus de recalcul à la demande).

    Cibles remplies + réserve (dans `conflits`, avec sa raison). 404 si le tournoi, le départ, ou le
    gabarit appliqué au tournoi n'existent pas : le service lève l'erreur applicative, traduite à la
    frontière."""
    service: ServicePlacement = request.app.state.service_placement
    plan = await run_in_threadpool(service.plan_de_cibles, tournoi_id, depart_id)
    return PlanDeCiblesReponse.de_plan(depart_id, plan)


@router.get(
    "/tournois/{tournoi_id}/departs/{depart_id}/plan-de-cibles/impact-regeneration",
    response_model=ImpactRegenerationReponse,
    dependencies=[Depends(exiger_admin)],
)
async def impact_regeneration(
    tournoi_id: int, depart_id: int, request: Request
) -> ImpactRegenerationReponse:
    """Prévisualise l'impact de régénérer le plan (**action admin**, E12US007, ADR-0040).

    Lecture pure (aucune écriture) → directe hors boucle (`run_in_threadpool`, règle 7). Le front
    l'interroge **avant** d'agir pour afficher l'alerte chiffrée ; l'action réelle (`regenerer`)
    recalcule l'impact au commit (jamais cru sur parole)."""
    service: ServicePlacement = request.app.state.service_placement
    impact = await run_in_threadpool(service.impact_regeneration, tournoi_id, depart_id)
    return ImpactRegenerationReponse.de_impact(impact)


@router.post(
    "/tournois/{tournoi_id}/departs/{depart_id}/plan-de-cibles/regenerer",
    response_model=PlanDeCiblesReponse,
    dependencies=[Depends(exiger_admin)],
)
async def regenerer_plan(
    tournoi_id: int, depart_id: int, request: Request, requete: RegenererRequete | None = None
) -> PlanDeCiblesReponse:
    """(Re)génère le plan auto d'un départ (**action admin**) — c'est aussi « annuler les
    modifications » (ADR-0024, auto déterministe). Écriture via la file.

    **409 `replacement_non_confirme`** (chiffré, dans `details`) si le plan est **massif** (des
    scores
    existent) et que `confirme` n'est pas vrai (E12US007, ADR-0040). Corps optionnel : une
    régénération non massive (première génération, plan sans score) n'a rien à confirmer."""
    service: ServicePlacement = request.app.state.service_placement
    write_queue: WriteQueue = request.app.state.write_queue
    confirme = requete.confirme if requete is not None else False
    plan = await asyncio.wrap_future(
        write_queue.submit(lambda: service.regenerer(tournoi_id, depart_id, confirme=confirme))
    )
    return PlanDeCiblesReponse.de_plan(depart_id, plan)


@router.put(
    "/tournois/{tournoi_id}/departs/{depart_id}/plan-de-cibles/inscriptions/{inscription_id}",
    response_model=PlanDeCiblesReponse,
    dependencies=[Depends(exiger_admin)],
)
async def deplacer_archer(
    tournoi_id: int,
    depart_id: int,
    inscription_id: int,
    requete: DeplacerRequete,
    request: Request,
) -> PlanDeCiblesReponse:
    """Déplace, échange ou met en réserve un inscrit (**action admin**) : écriture via la file.

    Renvoie le plan mis à jour, ou **409 `deplacement_invalide`** si le geste viole une contrainte
    (état inchangé). 404 si l'inscription n'appartient pas au départ."""
    service: ServicePlacement = request.app.state.service_placement
    write_queue: WriteQueue = request.app.state.write_queue
    plan = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.deplacer(
                tournoi_id, depart_id, inscription_id, requete.cible_index, requete.position
            )
        )
    )
    return PlanDeCiblesReponse.de_plan(depart_id, plan)


@router.post(
    "/tournois/{tournoi_id}/departs/{depart_id}/plan-de-cibles/placer-restants",
    response_model=PlanDeCiblesReponse,
    dependencies=[Depends(exiger_admin)],
)
async def placer_les_restants(
    tournoi_id: int, depart_id: int, request: Request
) -> PlanDeCiblesReponse:
    """Place automatiquement la réserve dans les trous du plan (**action admin**) : écriture via la
    file. Les archers qu'aucune cible ne peut prendre restent en réserve."""
    service: ServicePlacement = request.app.state.service_placement
    write_queue: WriteQueue = request.app.state.write_queue
    plan = await asyncio.wrap_future(
        write_queue.submit(lambda: service.placer_les_restants(tournoi_id, depart_id))
    )
    return PlanDeCiblesReponse.de_plan(depart_id, plan)
