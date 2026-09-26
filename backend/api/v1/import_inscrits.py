"""Import d'un fichier d'inscrits (E02US007, ADR-0115) : aperçu, puis confirmation.

Le **corps est le fichier** (patron du logo, E16US006 : pas de multipart, `python-multipart` n'est
pas au manifeste). La confirmation redépose le même fichier : rien n'est gardé côté serveur entre
les deux appels, et le plan est recalculé sur l'état du moment.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.corps import lire_le_corps_borne
from api.dependances import exiger_admin
from application.import_inscrits import ServiceImportInscrits
from domain.import_inscrits import LignePlan, PlanImport
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["import-inscrits"])

# Coupure de sécurité, pas une règle métier : l'export réel de 99 archers pèse 8 Ko (CSV) et
# 12 Ko (xls). Un gymnase entier tient cent fois dedans.
_PLAFOND_OCTETS = 2 * 1024 * 1024


class LigneRapportReponse(BaseModel):
    numero: int
    decision: str
    motif: str | None
    nom: str | None
    prenom: str | None
    licence: str | None
    depart_numero: int | None
    categorie_id: int | None
    club: str | None
    club_a_creer: bool
    homonyme_de: str | None
    fiche: str | None

    @staticmethod
    def de_ligne(ligne: LignePlan) -> LigneRapportReponse:
        return LigneRapportReponse(
            numero=ligne.ligne.numero,
            decision=ligne.decision.value,
            motif=ligne.motif,
            nom=ligne.ligne.nom,
            prenom=ligne.ligne.prenom,
            licence=ligne.licence or ligne.ligne.licence,
            fiche=ligne.fiche,
            depart_numero=ligne.ligne.depart_numero,
            categorie_id=ligne.categorie_id,
            club=ligne.ligne.club,
            club_a_creer=ligne.club_a_creer is not None,
            homonyme_de=ligne.homonyme_de,
        )


class RapportImportReponse(BaseModel):
    source: str
    importables: int
    rejetees: int
    homonymes: int
    colonnes_ignorees: list[str]
    lignes: list[LigneRapportReponse]

    @staticmethod
    def de_plan(plan: PlanImport) -> RapportImportReponse:
        return RapportImportReponse(
            source=plan.source.value,
            importables=len(plan.importables),
            rejetees=len(plan.rejetees),
            homonymes=len(plan.homonymes),
            colonnes_ignorees=list(plan.colonnes_ignorees),
            lignes=[LigneRapportReponse.de_ligne(ligne) for ligne in plan.lignes],
        )


@router.post(
    "/tournois/{tournoi_id}/import-inscrits/apercu",
    response_model=RapportImportReponse,
    dependencies=[Depends(exiger_admin)],
)
async def apercu_import(tournoi_id: int, request: Request) -> RapportImportReponse:
    """Rapport de ce que ferait l'import (**n'écrit rien** — lecture hors boucle, règle 7)."""
    contenu = await lire_le_corps_borne(request, _PLAFOND_OCTETS)
    service: ServiceImportInscrits = request.app.state.service_import_inscrits
    plan = await run_in_threadpool(service.apercu, tournoi_id, contenu)
    return RapportImportReponse.de_plan(plan)


@router.post(
    "/tournois/{tournoi_id}/import-inscrits",
    response_model=RapportImportReponse,
    dependencies=[Depends(exiger_admin)],
)
async def importer(
    tournoi_id: int,
    request: Request,
    homonymes: Annotated[list[int] | None, Query()] = None,
) -> RapportImportReponse:
    """Écrit toutes les lignes importables en **une** transaction ; `homonymes` : lignes cochées."""
    contenu = await lire_le_corps_borne(request, _PLAFOND_OCTETS)
    service: ServiceImportInscrits = request.app.state.service_import_inscrits
    write_queue: WriteQueue = request.app.state.write_queue
    # Décoder le fichier hors du writer unique : il ne dépend d'aucun état (règle 7).
    fichier = await run_in_threadpool(service.lire, contenu)
    cochees = frozenset(homonymes or ())
    plan = await asyncio.wrap_future(
        write_queue.submit(lambda: service.importer(tournoi_id, fichier, cochees))
    )
    return RapportImportReponse.de_plan(plan)
