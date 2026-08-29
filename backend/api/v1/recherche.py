"""Recherche transverse — « chercher partout », entité par entité (E16US010).

Une **seule** route paramétrée par l'entité, comme la famille des jalons : recopier trois routes
jumelles ferait diverger trois contrats pour une même question.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.recherche import ServiceRecherche
from domain.recherche import EntiteRecherchable, Recherche, ResultatRecherche

router = APIRouter(prefix="/api/v1/recherche", tags=["recherche"])


class ResultatRechercheReponse(BaseModel):
    """Une proposition de complétion : de quoi l'afficher, et de quoi ouvrir sa fiche.

    `entite` voyage dans **chaque** ligne bien que la requête la fixe : le front range les
    résultats dans un composant unique, et une ligne qui ne sait pas ce qu'elle désigne ne peut
    pas dire où elle mène.
    """

    entite: str
    id: int
    libelle: str
    precision: str | None
    tournoi_id: int | None


class RechercheReponse(BaseModel):
    """Les propositions **et** le total trouvé.

    ⚠️ `total` peut dépasser `len(resultats)` : la complétion est bornée. Le front doit le dire
    (« 8 sur 34 »), sans quoi la liste tronquée se lit « il n'y a que ça » et l'organisateur cesse
    de préciser sa saisie.
    """

    resultats: list[ResultatRechercheReponse]
    total: int

    @staticmethod
    def de_recherche(recherche: Recherche) -> RechercheReponse:
        """Traduit la recherche du domaine en DTO de réponse."""
        return RechercheReponse(
            resultats=[_de_resultat(resultat) for resultat in recherche.resultats],
            total=recherche.total,
        )


def _de_resultat(resultat: ResultatRecherche) -> ResultatRechercheReponse:
    return ResultatRechercheReponse(
        entite=resultat.entite.value,
        id=resultat.id,
        libelle=resultat.libelle,
        precision=resultat.precision,
        tournoi_id=resultat.tournoi_id,
    )


@router.get("", response_model=RechercheReponse, dependencies=[Depends(exiger_admin)])
async def chercher(
    request: Request,
    entite: EntiteRecherchable,
    q: str = Query(default="", max_length=100),
    tournoi_id: int | None = None,
) -> RechercheReponse:
    """Complétion sur une entité (**admin**), éventuellement scopée à un tournoi.

    `tournoi_id` réalise le CA « recherche d'archer en pilotage » ; il n'a de sens que sur les
    archers, clubs et tournois étant des référentiels globaux. `400` si `entite` n'en est pas une.
    ⚠️ Un `q` vide rend une liste vide, jamais le référentiel entier (`domain.recherche`).
    Lecture pure : hors file d'écriture, dans le threadpool.
    """
    service: ServiceRecherche = request.app.state.service_recherche
    recherche = await run_in_threadpool(lambda: service.chercher(entite, q, tournoi_id=tournoi_id))
    return RechercheReponse.de_recherche(recherche)
