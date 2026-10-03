"""Frontière API — sauvegardes : lister, vérifier, restaurer à chaud (E11US006, ADR-0119).

Routes **à la racine**, hors tournoi : une restauration remplace la base entière, tous tournois
confondus. Toutes réservées à l'admin, lecture de la liste comprise (les noms datent l'activité).
"""

from __future__ import annotations

import asyncio
import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.sauvegardes import (
    RestaurationEffectuee,
    SauvegardeDisponible,
    ServiceSauvegardes,
    VerificationSauvegarde,
)
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["sauvegardes"], dependencies=[Depends(exiger_admin)])


class SauvegardeReponse(BaseModel):
    nom: str
    nature: Literal["periodique", "avant_restauration"]
    prise_le: datetime.datetime
    taille_octets: int

    @staticmethod
    def de(sauvegarde: SauvegardeDisponible) -> SauvegardeReponse:
        return SauvegardeReponse(
            nom=sauvegarde.nom,
            nature=sauvegarde.nature.value,
            prise_le=sauvegarde.prise_le,
            taille_octets=sauvegarde.taille_octets,
        )


class VerificationReponse(BaseModel):
    nom: str
    verdict: Literal["restaurable", "corrompue", "version_differente"]

    @staticmethod
    def de(verification: VerificationSauvegarde) -> VerificationReponse:
        return VerificationReponse(nom=verification.nom, verdict=verification.verdict.value)


class RestaurationReponse(BaseModel):
    restauree: str
    copie_de_securite: str

    @staticmethod
    def de(restauration: RestaurationEffectuee) -> RestaurationReponse:
        return RestaurationReponse(
            restauree=restauration.restauree, copie_de_securite=restauration.copie_de_securite
        )


@router.get("/sauvegardes", response_model=list[SauvegardeReponse])
async def lister_sauvegardes(request: Request) -> list[SauvegardeReponse]:
    service: ServiceSauvegardes = request.app.state.service_sauvegardes
    return [SauvegardeReponse.de(s) for s in await run_in_threadpool(service.lister)]


@router.post("/sauvegardes/{nom}/verification", response_model=VerificationReponse)
async def verifier_sauvegarde(nom: str, request: Request) -> VerificationReponse:
    """Lecture seule, hors file (ADR-0044)."""
    service: ServiceSauvegardes = request.app.state.service_sauvegardes
    return VerificationReponse.de(await run_in_threadpool(service.verifier, nom))


@router.post("/sauvegardes/{nom}/restauration", response_model=RestaurationReponse)
async def restaurer_sauvegarde(nom: str, request: Request) -> RestaurationReponse:
    """Dans la file : vérification, copie de sécurité et restauration sans écriture intercalée."""
    service: ServiceSauvegardes = request.app.state.service_sauvegardes
    write_queue: WriteQueue = request.app.state.write_queue
    restauration = await asyncio.wrap_future(write_queue.submit(lambda: service.restaurer(nom)))
    return RestaurationReponse.de(restauration)
