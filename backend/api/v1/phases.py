"""Endpoints REST de la séquence de phases (`/api/v1`) — composition d'un tournoi (E05US001).

Suit le patron de bout en bout (E00US009) : **DTO Pydantic** distincts des agrégats, **écritures**
routées par la file (writer unique, ADR-0005) et protégées par `exiger_admin`, **lectures** hors
boucle (threadpool), **erreurs typées** traduites à la frontière (`api/erreurs.py`).

Ressource rattachée au tournoi : `/tournois/{tournoi_id}/phases`. Lecture ouverte (comme les autres
consultations, E10US001) ; composition et cycle de vie réservés à l'admin. La **cohérence** de la
séquence (source vide / rangs inexistants / effectif incompatible) est une règle du domaine → elle
remonte en 422 ; les conflits d'état (transition illégale, suppression d'une source référencée) en
409 (ADR-0045).
"""

from __future__ import annotations

import asyncio
from enum import Enum

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.phases import ServicePhases
from domain.phase import Phase, SourcePhase, StatutPhase, TypePhase
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["phases"])


class SourceDTO(BaseModel):
    """Peuplement : rangs `[rang_debut..rang_fin]` de la phase d'ordre `ordre_source`."""

    ordre_source: int
    rang_debut: int
    rang_fin: int

    @staticmethod
    def de_agregat(source: SourcePhase) -> SourceDTO:
        return SourceDTO(
            ordre_source=source.ordre_source,
            rang_debut=source.rang_debut,
            rang_fin=source.rang_fin,
        )

    def vers_agregat(self) -> SourcePhase:
        return SourcePhase(
            ordre_source=self.ordre_source,
            rang_debut=self.rang_debut,
            rang_fin=self.rang_fin,
        )


class ConfigPhaseRequete(BaseModel):
    """Config de séquence d'une phase : son type, sa source (facultative) et son effectif attendu
    (facultatif). Sert à l'ajout comme à l'édition (totale)."""

    type: TypePhase
    source: SourceDTO | None = None
    effectif: int | None = None


class ReordonnerRequete(BaseModel):
    """Nouvel ordre de **l'ensemble** des phases : la liste complète de leurs identifiants."""

    phases: list[int]


class TransitionPhase(str, Enum):
    """Action de cycle de vie demandée sur une phase (ADR-0045 §1)."""

    DEMARRER = "demarrer"
    METTRE_EN_PAUSE = "mettre_en_pause"
    REPRENDRE = "reprendre"
    TERMINER = "terminer"


class TransitionRequete(BaseModel):
    """Transition de statut à appliquer à une phase."""

    transition: TransitionPhase


class PhaseReponse(BaseModel):
    """Représentation d'une phase renvoyée au client (config de séquence, sans les politiques de
    scoring — celles-ci ont leurs propres endpoints)."""

    id: int
    tournoi_id: int
    ordre: int
    type: TypePhase
    statut: StatutPhase
    source: SourceDTO | None
    effectif: int | None

    @staticmethod
    def de_agregat(phase: Phase) -> PhaseReponse:
        assert phase.id is not None, "Une phase renvoyée par le service est persistée."
        return PhaseReponse(
            id=phase.id,
            tournoi_id=phase.tournoi_id,
            ordre=phase.ordre,
            type=phase.type,
            statut=phase.statut,
            source=None if phase.source is None else SourceDTO.de_agregat(phase.source),
            effectif=phase.effectif,
        )


@router.get("/tournois/{tournoi_id}/phases", response_model=list[PhaseReponse])
async def lister_phases(tournoi_id: int, request: Request) -> list[PhaseReponse]:
    """Renvoie les phases du tournoi, ordonnées. Lève `TournoiIntrouvable` (404) si inconnu."""
    service: ServicePhases = request.app.state.service_phases
    phases = await run_in_threadpool(service.lister, tournoi_id)
    return [PhaseReponse.de_agregat(phase) for phase in phases]


@router.post(
    "/tournois/{tournoi_id}/phases",
    response_model=PhaseReponse,
    status_code=201,
    dependencies=[Depends(exiger_admin)],
)
async def ajouter_phase(
    tournoi_id: int, requete: ConfigPhaseRequete, request: Request
) -> PhaseReponse:
    """Ajoute une phase en fin de séquence (**action admin**), écriture via la file (ADR-0005)."""
    service: ServicePhases = request.app.state.service_phases
    write_queue: WriteQueue = request.app.state.write_queue
    source = None if requete.source is None else requete.source.vers_agregat()
    phase = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.ajouter(tournoi_id, requete.type, source, requete.effectif)
        )
    )
    return PhaseReponse.de_agregat(phase)


@router.put(
    "/tournois/{tournoi_id}/phases/{phase_id}",
    response_model=PhaseReponse,
    dependencies=[Depends(exiger_admin)],
)
async def modifier_phase(
    tournoi_id: int, phase_id: int, requete: ConfigPhaseRequete, request: Request
) -> PhaseReponse:
    """Édite (totalement) la config de séquence d'une phase (**action admin**)."""
    service: ServicePhases = request.app.state.service_phases
    write_queue: WriteQueue = request.app.state.write_queue
    source = None if requete.source is None else requete.source.vers_agregat()
    phase = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.modifier(tournoi_id, phase_id, requete.type, source, requete.effectif)
        )
    )
    return PhaseReponse.de_agregat(phase)


@router.post(
    "/tournois/{tournoi_id}/phases/reordonner",
    response_model=list[PhaseReponse],
    dependencies=[Depends(exiger_admin)],
)
async def reordonner_phases(
    tournoi_id: int, requete: ReordonnerRequete, request: Request
) -> list[PhaseReponse]:
    """Réordonne l'ensemble des phases du tournoi (**action admin**)."""
    service: ServicePhases = request.app.state.service_phases
    write_queue: WriteQueue = request.app.state.write_queue
    phases = await asyncio.wrap_future(
        write_queue.submit(lambda: service.reordonner(tournoi_id, requete.phases))
    )
    return [PhaseReponse.de_agregat(phase) for phase in phases]


@router.delete(
    "/tournois/{tournoi_id}/phases/{phase_id}",
    status_code=204,
    dependencies=[Depends(exiger_admin)],
)
async def supprimer_phase(tournoi_id: int, phase_id: int, request: Request) -> None:
    """Retire une phase de la séquence (**action admin**). Refuse (409) si elle en alimente une
    autre (`PhaseSourceReferencee`)."""
    service: ServicePhases = request.app.state.service_phases
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(write_queue.submit(lambda: service.supprimer(tournoi_id, phase_id)))


@router.post(
    "/tournois/{tournoi_id}/phases/{phase_id}/statut",
    response_model=PhaseReponse,
    dependencies=[Depends(exiger_admin)],
)
async def changer_statut(
    tournoi_id: int, phase_id: int, requete: TransitionRequete, request: Request
) -> PhaseReponse:
    """Applique une transition de cycle de vie à une phase (**action admin**).

    Une transition illégale depuis l'état courant remonte en `TransitionStatutInvalide` (409).
    """
    service: ServicePhases = request.app.state.service_phases
    write_queue: WriteQueue = request.app.state.write_queue
    transitions = {
        TransitionPhase.DEMARRER: service.demarrer,
        TransitionPhase.METTRE_EN_PAUSE: service.mettre_en_pause,
        TransitionPhase.REPRENDRE: service.reprendre,
        TransitionPhase.TERMINER: service.terminer,
    }
    action = transitions[requete.transition]
    phase = await asyncio.wrap_future(write_queue.submit(lambda: action(tournoi_id, phase_id)))
    return PhaseReponse.de_agregat(phase)
