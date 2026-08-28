"""Pilotage du lancement d'un tour — feu vert, chiffrage, puis le geste.

`lancer` passe par la **file** et renvoie un `LiveEvent` typé que le listener post-commit diffuse
aux abonnés. L'acte trace `LANCEMENT`.

⚠️ **`impact-lancement` est le MIROIR de ce que `lancer` fera** : les deux doivent donner le même
compte, sinon le bouton annonce autre chose que ce qu'il produit. ADR-0056
"""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from api.v1.saisie_duels import DuellisteReponse
from application.pilotage_tour import DuelAVenir, FeuVert, ResumeLancement, ServicePilotageTour
from infrastructure.db import WriteQueue
from infrastructure.realtime import LiveEvent

router = APIRouter(prefix="/api/v1/pilotage", tags=["pilotage"])


# --- DTO ---


class DuelAVenirReponse(BaseModel):
    """L'état d'un duel à venir : occupants, les trois questions du CA, et le blocage nommé."""

    numero: int
    tour: int
    haut: DuellisteReponse | None
    bas: DuellisteReponse | None
    participants_connus: bool
    cible_haut: int | None
    cible_bas: int | None
    cible_attribuee: bool
    sources_en_attente: list[int]
    pret_a_lancer: bool
    blocage: str | None

    @staticmethod
    def de_duel(duel: DuelAVenir) -> DuelAVenirReponse:
        return DuelAVenirReponse(
            numero=duel.numero,
            tour=duel.tour,
            haut=DuellisteReponse.de_duelliste(duel.haut),
            bas=DuellisteReponse.de_duelliste(duel.bas),
            participants_connus=duel.participants_connus,
            cible_haut=duel.cible_haut,
            cible_bas=duel.cible_bas,
            cible_attribuee=duel.cible_attribuee,
            sources_en_attente=list(duel.sources_en_attente),
            pret_a_lancer=duel.pret_a_lancer,
            blocage=duel.blocage,
        )


class FeuVertReponse(BaseModel):
    """Le feu vert : les duels à venir avec leur état, et combien sont prêts à partir."""

    phase_id: int
    est_termine: bool
    duels: list[DuelAVenirReponse]
    nb_prets: int

    @staticmethod
    def de_feu_vert(feu: FeuVert) -> FeuVertReponse:
        return FeuVertReponse(
            phase_id=feu.phase_id,
            est_termine=feu.est_termine,
            duels=[DuelAVenirReponse.de_duel(duel) for duel in feu.duels],
            nb_prets=feu.nb_prets,
        )


class ResumeLancementReponse(BaseModel):
    """Ce que le bouton chiffre (et ce que le lancement a émis) : duels, cibles, archers."""

    phase_id: int
    numeros: list[int]
    cibles: list[int]
    nb_duels: int
    nb_archers: int

    @staticmethod
    def de_resume(resume: ResumeLancement) -> ResumeLancementReponse:
        return ResumeLancementReponse(
            phase_id=resume.phase_id,
            numeros=list(resume.numeros),
            cibles=list(resume.cibles),
            nb_duels=resume.nb_duels,
            nb_archers=resume.nb_archers,
        )


class LancerRequete(BaseModel):
    """Corps du lancement : la phase, et éventuellement un **sous-ensemble** de duels à lancer.

    `numeros=None` = **lancement global** (tous les prêts) ; sinon, l'unité lançable est le duel
    (`D-23`). Le serveur recalcule le feu vert et n'émet que les duels **réellement** prêts.
    """

    tournoi_id: int
    phase_id: int
    numeros: list[int] | None = None


# --- Lecture ---


@router.get("/feu-vert/{tournoi_id}/{phase_id}", response_model=FeuVertReponse)
async def lire_feu_vert(
    tournoi_id: int,
    phase_id: int,
    request: Request,
    _admin: Annotated[None, Depends(exiger_admin)],
) -> FeuVertReponse:
    """L'état de préparation du prochain tour, duel par duel (admin ; lecture pure)."""
    service: ServicePilotageTour = request.app.state.service_pilotage_tour
    feu = await run_in_threadpool(service.feu_vert, tournoi_id, phase_id)
    return FeuVertReponse.de_feu_vert(feu)


@router.get("/impact-lancement/{tournoi_id}/{phase_id}", response_model=ResumeLancementReponse)
async def lire_impact_lancement(
    tournoi_id: int,
    phase_id: int,
    request: Request,
    _admin: Annotated[None, Depends(exiger_admin)],
) -> ResumeLancementReponse:
    """Le chiffrage du lancement global (ce que le bouton affiche), sans rien émettre (admin)."""
    service: ServicePilotageTour = request.app.state.service_pilotage_tour
    resume = await run_in_threadpool(service.impact_lancement, tournoi_id, phase_id)
    return ResumeLancementReponse.de_resume(resume)


# --- Écriture (via la file) ---


@router.post("/lancer", response_model=ResumeLancementReponse)
async def lancer(
    requete: LancerRequete,
    request: Request,
    _admin: Annotated[None, Depends(exiger_admin)],
) -> ResumeLancementReponse:
    """Fait **partir** les duels prêts et diffuse le signal `tour_lance` (admin ; via la **file**).

    La commande renvoie un `LiveEvent` typé : le listener post-commit le diffuse aux abonnés
    (E00US008) — c'est le point de branchement des 4 canaux (`D-09`). Le résumé chiffré, capté dans
    la commande, est renvoyé au client. `AucunDuelALancer` (aucun duel prêt) → **409** (frontière).
    """
    service: ServicePilotageTour = request.app.state.service_pilotage_tour
    write_queue: WriteQueue = request.app.state.write_queue
    numeros = tuple(requete.numeros) if requete.numeros is not None else None
    capture: list[ResumeLancement] = []

    def ecrire() -> LiveEvent:
        resume = service.lancer(requete.tournoi_id, requete.phase_id, numeros)
        capture.append(resume)
        return LiveEvent(
            "tour_lance",
            {
                "phase_id": resume.phase_id,
                "numeros": list(resume.numeros),
                "cibles": list(resume.cibles),
                "nb_duels": resume.nb_duels,
                "nb_archers": resume.nb_archers,
            },
        )

    await asyncio.wrap_future(write_queue.submit(ecrire))
    return ResumeLancementReponse.de_resume(capture[0])
