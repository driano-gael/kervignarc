"""Endpoint REST de la **complétude du tournoi** (E12US005).

`GET /api/v1/tournois/{tournoi_id}/completude` (**admin**) : la réponse à « qu'est-ce qui manque
pour finir ? », sportif et hors sportif comptés séparément (`D-17`, CDC UX §8.3). Lecture ; le
front la **poll** (live) comme la supervision (E12US001). DTO Pydantic distincts des value objects
du domaine (règle 6). Erreurs typées traduites à la frontière (`api/erreurs.py`) : tournoi → 404.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.completude import ServiceCompletude
from domain.completude import Completude, LigneCompletude

router = APIRouter(prefix="/api/v1/tournois/{tournoi_id}", tags=["completude"])


class LigneCompletudeReponse(BaseModel):
    """Une ligne du tableau : `cle` stable, `libelle` lisible, `etat`, et décompte `fait/total`.

    `etat` ∈ `ok` · `alerte` · `en_attente` · `a_venir` (valeur de `EtatSection`). `fait`/`total`
    sont `null` pour les lignes sans décompte (phases à venir, classement) : l'info est dans `etat`.
    """

    cle: str
    libelle: str
    etat: str
    fait: int | None
    total: int | None

    @staticmethod
    def de_ligne(ligne: LigneCompletude) -> LigneCompletudeReponse:
        """Traduit une ligne du domaine en DTO de réponse."""
        return LigneCompletudeReponse(
            cle=ligne.cle,
            libelle=ligne.libelle,
            etat=ligne.etat.value,
            fait=ligne.fait,
            total=ligne.total,
        )


class CompletudeReponse(BaseModel):
    """Complétude complète : les deux sections séparées + le verrou du sportif.

    `sportif_complet` pilote l'avertissement avant *terminé* (la seule action irréversible) côté
    front : à `false`, l'écran chiffre ce qui reste avant de laisser confirmer.
    """

    sportif: list[LigneCompletudeReponse]
    hors_sportif: list[LigneCompletudeReponse]
    sportif_complet: bool

    @staticmethod
    def de_completude(completude: Completude) -> CompletudeReponse:
        """Traduit la complétude du domaine en DTO de réponse."""
        return CompletudeReponse(
            sportif=[LigneCompletudeReponse.de_ligne(ligne) for ligne in completude.sportif],
            hors_sportif=[
                LigneCompletudeReponse.de_ligne(ligne) for ligne in completude.hors_sportif
            ],
            sportif_complet=completude.sportif_complet,
        )


@router.get(
    "/completude",
    response_model=CompletudeReponse,
    dependencies=[Depends(exiger_admin)],
)
async def completude_tournoi(tournoi_id: int, request: Request) -> CompletudeReponse:
    """Complétude d'un tournoi (**admin**). `404` si le tournoi n'existe pas.

    Lecture pure (séries, plan, paiements en base) : hors file d'écriture, dans le threadpool.
    """
    service: ServiceCompletude = request.app.state.service_completude
    completude = await run_in_threadpool(service.pour_tournoi, tournoi_id)
    return CompletudeReponse.de_completude(completude)
