"""Endpoints REST des catégories (`/api/v1`) — CRUD des catégories d'un tournoi (E01US003).

Suit le patron de bout en bout (E00US009) :
- **DTO Pydantic** distincts des agrégats de domaine ;
- **écriture** routée par la **file d'écriture** (writer unique, ADR-0005), protégée par
  `exiger_admin` (E10US001/E10US002) ;
- **lecture** directe exécutée **hors boucle** (threadpool) ;
- **erreurs typées** traduites à la frontière (`api/erreurs.py`).

Routes imbriquées sous le tournoi pour la création/liste (une catégorie appartient à un
tournoi) ; l'édition et la suppression ciblent la catégorie par son identifiant.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.categories import ServiceCategories
from domain.categorie import Categorie, SexeCategorie
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["categories"])


class CreerCategorieRequete(BaseModel):
    """Corps de création d'une catégorie (libellé requis ; arme/âge/sexe facultatifs)."""

    libelle: str
    arme: str | None = None
    tranche_age: str | None = None
    sexe: SexeCategorie | None = None


class ModifierCategorieRequete(BaseModel):
    """Corps d'édition d'une catégorie (mêmes champs que la création)."""

    libelle: str
    arme: str | None = None
    tranche_age: str | None = None
    sexe: SexeCategorie | None = None


class CategorieReponse(BaseModel):
    """Représentation d'une catégorie renvoyée au client."""

    id: int
    tournoi_id: int
    libelle: str
    arme: str | None
    tranche_age: str | None
    sexe: SexeCategorie | None

    @staticmethod
    def de_agregat(categorie: Categorie) -> CategorieReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert categorie.id is not None, "Une catégorie persistée a toujours un identifiant."
        return CategorieReponse(
            id=categorie.id,
            tournoi_id=categorie.tournoi_id,
            libelle=categorie.libelle,
            arme=categorie.arme,
            tranche_age=categorie.tranche_age,
            sexe=categorie.sexe,
        )


@router.get("/tournois/{tournoi_id}/categories", response_model=list[CategorieReponse])
async def lister_categories(tournoi_id: int, request: Request) -> list[CategorieReponse]:
    """Liste les catégories d'un tournoi : lecture directe exécutée hors de la boucle."""
    service: ServiceCategories = request.app.state.service_categories
    categories = await run_in_threadpool(service.lister, tournoi_id)
    return [CategorieReponse.de_agregat(categorie) for categorie in categories]


@router.post(
    "/tournois/{tournoi_id}/categories",
    status_code=201,
    response_model=CategorieReponse,
    dependencies=[Depends(exiger_admin)],
)
async def creer_categorie(
    tournoi_id: int, requete: CreerCategorieRequete, request: Request
) -> CategorieReponse:
    """Crée une catégorie dans un tournoi (**action admin**) : écriture via la file (ADR-0005)."""
    service: ServiceCategories = request.app.state.service_categories
    write_queue: WriteQueue = request.app.state.write_queue
    categorie = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.creer(
                tournoi_id, requete.libelle, requete.arme, requete.tranche_age, requete.sexe
            )
        )
    )
    return CategorieReponse.de_agregat(categorie)


@router.put(
    "/categories/{categorie_id}",
    response_model=CategorieReponse,
    dependencies=[Depends(exiger_admin)],
)
async def modifier_categorie(
    categorie_id: int, requete: ModifierCategorieRequete, request: Request
) -> CategorieReponse:
    """Édite une catégorie (**action admin**) : écriture via la file (ADR-0005)."""
    service: ServiceCategories = request.app.state.service_categories
    write_queue: WriteQueue = request.app.state.write_queue
    categorie = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.modifier(
                categorie_id, requete.libelle, requete.arme, requete.tranche_age, requete.sexe
            )
        )
    )
    return CategorieReponse.de_agregat(categorie)


@router.delete(
    "/categories/{categorie_id}",
    status_code=204,
    dependencies=[Depends(exiger_admin)],
)
async def supprimer_categorie(categorie_id: int, request: Request) -> Response:
    """Supprime une catégorie (**action admin**) : écriture via la file ; renvoie 204."""
    service: ServiceCategories = request.app.state.service_categories
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(write_queue.submit(lambda: service.supprimer(categorie_id)))
    return Response(status_code=204)
