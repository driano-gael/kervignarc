"""Endpoint REST des **jalons « prêt à… »** (E16US012).

`GET /api/v1/tournois/{tournoi_id}/jalons/{jalon}` (**admin**) : « puis-je passer à l'étape
suivante, et sinon qu'est-ce qui manque ? ». Une **route unique paramétrée par le membre**, image
directe de la forme unique décidée au domaine — quatre routes jumelles auraient rouvert côté API
la divergence que l'US ferme (ADR-0096).

Lecture ; le front la **poll** comme la complétude et la supervision. DTO Pydantic distincts des
value objects du domaine (règle 6). Erreurs typées traduites à la frontière (`api/erreurs.py`) :
tournoi inconnu **et** membre pas encore instruit → 404.

⚠️ `LigneCompletudeReponse` est **réutilisée** depuis `api.v1.completude` et non recopiée : c'est
littéralement la même ligne (`domain.completude.LigneCompletude`), et le jalon *terminer* rend
exactement les lignes que l'écran de complétude rendait déjà. Une 2ᵉ écriture du même DTO aurait
fait diverger deux contrats que le front consomme avec le **même** composant — c'est le motif de
`DETTE-065`, qu'on ne va pas alimenter en le sachant.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from api.v1.completude import LigneCompletudeReponse
from application.jalons import ServiceJalons
from domain.jalon import Jalon, PreparationJalon, question

router = APIRouter(prefix="/api/v1/tournois/{tournoi_id}", tags=["jalons"])


class PreparationJalonReponse(BaseModel):
    """La réponse d'un jalon : la question posée, ce qui manque, et si l'action passera.

    - `question` : « Prêt à démarrer ? » — **dérivée** du jalon, pour que le front n'ait pas à
      tenir sa propre table de libellés (elle divergerait au premier membre ajouté) ;
    - `lignes` : ce qui manque, en états (`D-17`) — jamais un pourcentage ;
    - `pret` : la réponse binaire ;
    - `bloquant` : à `false`, l'action passe **quand même** malgré `pret: false` (`D-15`).

    ⚠️ `bloquant` ne sert **pas** à désactiver un bouton : il choisit ce que l'écran annonce (un
    refus à venir, ou une simple gêne). E05US021 avait déjà tranché — le refus remonte du serveur,
    le front ne décide d'aucune garde.
    """

    jalon: str
    question: str
    lignes: list[LigneCompletudeReponse]
    pret: bool
    bloquant: bool

    @staticmethod
    def de_preparation(preparation: PreparationJalon) -> PreparationJalonReponse:
        """Traduit la préparation du domaine en DTO de réponse."""
        return PreparationJalonReponse(
            jalon=preparation.jalon.value,
            question=question(preparation.jalon),
            lignes=[LigneCompletudeReponse.de_ligne(ligne) for ligne in preparation.lignes],
            pret=preparation.pret,
            bloquant=preparation.bloquant,
        )


@router.get(
    "/jalons/{jalon}",
    response_model=PreparationJalonReponse,
    dependencies=[Depends(exiger_admin)],
)
async def preparation_jalon(
    tournoi_id: int, jalon: Jalon, request: Request
) -> PreparationJalonReponse:
    """Préparation d'un tournoi à un jalon (**admin**).

    `404` si le tournoi n'existe pas **ou** si le membre n'a pas encore d'écran (`archiver`,
    `exporter`). `400` si le segment n'est pas un membre de la famille : l'énumération du domaine
    sert de validation de chemin, et le projet remappe `RequestValidationError` en 400
    (`api/erreurs.py`).

    Lecture pure (départs, déroulé, séries, plan en base) : hors file d'écriture, dans le
    threadpool.
    """
    service: ServiceJalons = request.app.state.service_jalons
    preparation = await run_in_threadpool(service.preparation, tournoi_id, jalon)
    return PreparationJalonReponse.de_preparation(preparation)
