"""Endpoints REST des gabarits de salle (`/api/v1`) — CRUD des gabarits réutilisables (E01US007).

Suit le patron de bout en bout (E00US009) :
- **DTO Pydantic** distincts des agrégats de domaine ;
- **écriture** routée par la **file d'écriture** (writer unique, ADR-0005), protégée par
  `exiger_admin` (E10US001/E10US002) ;
- **lecture** directe exécutée **hors boucle** (threadpool) ;
- **erreurs typées** traduites à la frontière (`api/erreurs.py`).

Deux familles de routes :
- **bibliothèque** de modèles réutilisables (E01US007), à plat sous `/gabarits` ;
- **plan de salle d'un tournoi** (E01US008), sous `/tournois/{tournoi_id}/gabarit` : appliquer un
  modèle (copie), lire et ajuster la copie (plafond cible par cible) sans altérer le modèle.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.gabarits import ServiceGabarits
from domain.gabarit_salle import CAPACITE_CIBLE_DEFAUT, GabaritSalle
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["gabarits"])


class CreerGabaritRequete(BaseModel):
    """Corps de création d'un gabarit (nom requis ; nb de cibles ; plafond par cible, défaut 4)."""

    nom: str
    nb_cibles: int
    capacite: int = CAPACITE_CIBLE_DEFAUT


class ModifierGabaritRequete(BaseModel):
    """Corps d'édition d'un gabarit (mêmes champs que la création)."""

    nom: str
    nb_cibles: int
    capacite: int = CAPACITE_CIBLE_DEFAUT


class AppliquerGabaritRequete(BaseModel):
    """Corps d'application d'un modèle à un tournoi (E01US008) : l'identifiant du modèle."""

    modele_id: int


class AjusterGabaritRequete(BaseModel):
    """Corps d'ajustement du gabarit d'un tournoi (E01US008) : nom + plafond **cible par cible**.

    `capacites` porte une valeur par cible ; son nombre fixe le nombre de cibles.
    """

    nom: str
    capacites: list[int]


class CibleReponse(BaseModel):
    """Une cible du gabarit : rang, plafond d'archers et positions déduites."""

    index: int
    capacite: int
    positions: list[str]


class GabaritReponse(BaseModel):
    """Représentation d'un gabarit de salle renvoyée au client.

    `tournoi_id` vaut `None` pour un **modèle** de bibliothèque, l'identifiant du tournoi pour
    une **instance** appliquée (E01US008).
    """

    id: int
    nom: str
    nb_cibles: int
    tournoi_id: int | None
    cibles: list[CibleReponse]

    @staticmethod
    def de_agregat(gabarit: GabaritSalle) -> GabaritReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert gabarit.id is not None, "Un gabarit persisté a toujours un identifiant."
        return GabaritReponse(
            id=gabarit.id,
            nom=gabarit.nom,
            nb_cibles=gabarit.nb_cibles,
            tournoi_id=gabarit.tournoi_id,
            cibles=[
                CibleReponse(
                    index=cible.index, capacite=cible.capacite, positions=list(cible.positions)
                )
                for cible in gabarit.cibles
            ],
        )


@router.get("/gabarits", response_model=list[GabaritReponse])
async def lister_gabarits(request: Request) -> list[GabaritReponse]:
    """Liste tous les gabarits de salle : lecture directe exécutée hors de la boucle."""
    service: ServiceGabarits = request.app.state.service_gabarits
    gabarits = await run_in_threadpool(service.lister)
    return [GabaritReponse.de_agregat(gabarit) for gabarit in gabarits]


@router.post(
    "/gabarits",
    status_code=201,
    response_model=GabaritReponse,
    dependencies=[Depends(exiger_admin)],
)
async def creer_gabarit(requete: CreerGabaritRequete, request: Request) -> GabaritReponse:
    """Crée un gabarit de salle (**action admin**) : écriture via la file (ADR-0005)."""
    service: ServiceGabarits = request.app.state.service_gabarits
    write_queue: WriteQueue = request.app.state.write_queue
    gabarit = await asyncio.wrap_future(
        write_queue.submit(lambda: service.creer(requete.nom, requete.nb_cibles, requete.capacite))
    )
    return GabaritReponse.de_agregat(gabarit)


@router.put(
    "/gabarits/{gabarit_id}",
    response_model=GabaritReponse,
    dependencies=[Depends(exiger_admin)],
)
async def modifier_gabarit(
    gabarit_id: int, requete: ModifierGabaritRequete, request: Request
) -> GabaritReponse:
    """Édite un gabarit (**action admin**) : écriture via la file (ADR-0005)."""
    service: ServiceGabarits = request.app.state.service_gabarits
    write_queue: WriteQueue = request.app.state.write_queue
    gabarit = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.modifier(gabarit_id, requete.nom, requete.nb_cibles, requete.capacite)
        )
    )
    return GabaritReponse.de_agregat(gabarit)


@router.delete(
    "/gabarits/{gabarit_id}",
    status_code=204,
    dependencies=[Depends(exiger_admin)],
)
async def supprimer_gabarit(gabarit_id: int, request: Request) -> Response:
    """Supprime un gabarit (**action admin**) : écriture via la file ; renvoie 204."""
    service: ServiceGabarits = request.app.state.service_gabarits
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(write_queue.submit(lambda: service.supprimer(gabarit_id)))
    return Response(status_code=204)


# --- Plan de salle d'un tournoi (E01US008) : appliquer / lire / ajuster la copie du tournoi. ---


@router.get("/tournois/{tournoi_id}/gabarit", response_model=GabaritReponse | None)
async def gabarit_du_tournoi(tournoi_id: int, request: Request) -> GabaritReponse | None:
    """Renvoie le gabarit appliqué au tournoi, ou `null` s'il n'y en a pas (lecture publique).

    Lève `TournoiIntrouvable` (404) si le tournoi n'existe pas.
    """
    service: ServiceGabarits = request.app.state.service_gabarits
    gabarit = await run_in_threadpool(service.gabarit_du_tournoi, tournoi_id)
    return None if gabarit is None else GabaritReponse.de_agregat(gabarit)


@router.put(
    "/tournois/{tournoi_id}/gabarit",
    response_model=GabaritReponse,
    dependencies=[Depends(exiger_admin)],
)
async def appliquer_gabarit(
    tournoi_id: int, requete: AppliquerGabaritRequete, request: Request
) -> GabaritReponse:
    """Applique un modèle au tournoi (**action admin**) : copie via la file (ADR-0005).

    Remplace le gabarit courant du tournoi le cas échéant ; le modèle d'origine reste intact.
    """
    service: ServiceGabarits = request.app.state.service_gabarits
    write_queue: WriteQueue = request.app.state.write_queue
    gabarit = await asyncio.wrap_future(
        write_queue.submit(lambda: service.appliquer(tournoi_id, requete.modele_id))
    )
    return GabaritReponse.de_agregat(gabarit)


@router.patch(
    "/tournois/{tournoi_id}/gabarit",
    response_model=GabaritReponse,
    dependencies=[Depends(exiger_admin)],
)
async def ajuster_gabarit(
    tournoi_id: int, requete: AjusterGabaritRequete, request: Request
) -> GabaritReponse:
    """Ajuste le gabarit du tournoi (**action admin**) : plafond cible par cible, via la file.

    N'affecte que la copie du tournoi (le modèle reste intact).
    """
    service: ServiceGabarits = request.app.state.service_gabarits
    write_queue: WriteQueue = request.app.state.write_queue
    gabarit = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.ajuster(tournoi_id, requete.nom, tuple(requete.capacites))
        )
    )
    return GabaritReponse.de_agregat(gabarit)
