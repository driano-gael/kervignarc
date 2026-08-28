"""Jalons « prêt à… » — lecture pollée, comme la complétude et la supervision.

⚠️ **`LigneCompletudeReponse` est RÉUTILISÉE, jamais recopiée** : c'est littéralement la même ligne
de domaine, et le front la consomme avec le **même** composant. Une 2ᵉ écriture du DTO ferait
diverger deux contrats — le motif de `DETTE-065`, qu'on n'alimente pas en le sachant. ADR-0096
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

    `question` est **dérivée** du jalon (pas de table de libellés côté front). ⚠️ Chez *démarrer*,
    une liste `lignes` **vide** veut dire « plus rien à préparer », pas « rien ne manque » ; chez
    *terminer* elle **est l'état sportif** et est rendue à tout statut. ⚠️ **`question_posee` est
    le seul champ disant si la question a encore un objet** — ne le déduisez pas de `lignes` ;
    `moment` ne se lit jamais seul. ⚠️ `bloquant` ne désactive **aucun** bouton (E05US021).
    """

    jalon: str
    question: str
    lignes: list[LigneCompletudeReponse]
    pret: bool
    bloquant: bool
    question_posee: bool
    detail: str | None
    moment: str | None

    @staticmethod
    def de_preparation(preparation: PreparationJalon) -> PreparationJalonReponse:
        """Traduit la préparation du domaine en DTO de réponse."""
        return PreparationJalonReponse(
            jalon=preparation.jalon.value,
            question=question(preparation.jalon),
            lignes=[LigneCompletudeReponse.de_ligne(ligne) for ligne in preparation.lignes],
            pret=preparation.pret,
            bloquant=preparation.bloquant,
            question_posee=preparation.question_posee,
            detail=preparation.detail,
            moment=preparation.moment,
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

    `404` si le tournoi n'existe pas **ou** si le membre n'a pas encore d'écran ; `400` si le
    segment n'est pas un membre de la famille. ⚠️ **`Jalon` (domaine) sert de type de chemin,
    délibérément** — la règle 6 vise les **DTO de corps**, et recopier ici la liste des membres
    rouvrirait la divergence que l'US ferme. Le risque inverse est couvert : les tests d'API
    demandent les segments **littéraux**. Lecture pure : hors file d'écriture, dans le threadpool.
    """
    service: ServiceJalons = request.app.state.service_jalons
    preparation = await run_in_threadpool(service.preparation, tournoi_id, jalon)
    return PreparationJalonReponse.de_preparation(preparation)
