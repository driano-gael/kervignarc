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
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.categories import ServiceCategories
from domain.categorie import HAUTEUR_CENTRE_DEFAUT, Categorie, SexeCategorie, TrancheAge
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["categories"])


class CreerCategorieRequete(BaseModel):
    """Corps de création d'une catégorie (libellé requis ; arme/ages/sexe/blason facultatifs).

    `ages` accepte zéro, une ou plusieurs tranches (E01US013) ; chaque valeur doit appartenir aux
    huit tranches FFTA (`TrancheAge`), sans quoi la validation Pydantic rejette la requête en 400
    (`requete_invalide`) à la frontière — avant que le domaine ne la voie (règle 5).
    """

    libelle: str
    arme: str | None = None
    ages: list[TrancheAge] = Field(default_factory=list)
    sexe: SexeCategorie | None = None
    blason_id: int | None = None
    # Hauteur du centre de l'or, en cm (E03US001) — facultative : omise, vaut 130 (défaut FFTA).
    # Le pré-chargement FFTA fixe 110 pour les U11 côté service, pas via ce DTO.
    hauteur_cm: int = HAUTEUR_CENTRE_DEFAUT


class ModifierCategorieRequete(BaseModel):
    """Corps d'édition d'une catégorie (mêmes champs que la création).

    `hauteur_cm` est **obligatoire** : le PUT est **total** (ADR-0020). Le formulaire catégorie
    porte ce champ depuis E03US004 (UI de placement), ce qui résorbe DETTE-009 — l'entorse « champ
    partiel » qui l'avait rendu facultatif le temps que l'UI le porte a disparu.
    """

    libelle: str
    arme: str | None = None
    ages: list[TrancheAge] = Field(default_factory=list)
    sexe: SexeCategorie | None = None
    blason_id: int | None = None
    hauteur_cm: int


class CategorieReponse(BaseModel):
    """Représentation d'une catégorie renvoyée au client.

    `ages` est **toujours** une liste (éventuellement vide), sérialisée en codes de tranche
    (ex. `["U15", "U18"]`) — jamais un scalaire, contrairement à l'ancien `tranche_age`.
    """

    id: int
    tournoi_id: int
    libelle: str
    arme: str | None
    ages: list[TrancheAge]
    sexe: SexeCategorie | None
    blason_id: int | None
    hauteur_cm: int

    @staticmethod
    def de_agregat(categorie: Categorie) -> CategorieReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert categorie.id is not None, "Une catégorie persistée a toujours un identifiant."
        return CategorieReponse(
            id=categorie.id,
            tournoi_id=categorie.tournoi_id,
            libelle=categorie.libelle,
            arme=categorie.arme,
            ages=list(categorie.ages),
            sexe=categorie.sexe,
            blason_id=categorie.blason_id,
            hauteur_cm=categorie.hauteur_cm,
        )


@router.get("/tournois/{tournoi_id}/categories", response_model=list[CategorieReponse])
async def lister_categories(tournoi_id: int, request: Request) -> list[CategorieReponse]:
    """Liste les catégories d'un tournoi : lecture directe exécutée hors de la boucle."""
    service: ServiceCategories = request.app.state.service_categories
    categories = await run_in_threadpool(service.lister, tournoi_id)
    return [CategorieReponse.de_agregat(categorie) for categorie in categories]


@router.post(
    "/tournois/{tournoi_id}/categories/precharger-ffta",
    status_code=201,
    response_model=list[CategorieReponse],
    dependencies=[Depends(exiger_admin)],
)
async def precharger_categories_ffta(tournoi_id: int, request: Request) -> list[CategorieReponse]:
    """Pré-charge les catégories FFTA salle (18 m) dans un tournoi (**action admin**, E01US004).

    Une seule écriture via la file (ADR-0005) crée l'ensemble du jeu. Idempotent sur le libellé
    (les catégories déjà présentes sont ignorées). Renvoie les catégories **créées** (celles
    ignorées ne sont pas renvoyées) ; les catégories créées restent modifiables/supprimables.
    """
    service: ServiceCategories = request.app.state.service_categories
    write_queue: WriteQueue = request.app.state.write_queue
    creees = await asyncio.wrap_future(
        write_queue.submit(lambda: service.precharger_ffta(tournoi_id))
    )
    return [CategorieReponse.de_agregat(categorie) for categorie in creees]


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
                tournoi_id,
                requete.libelle,
                requete.arme,
                requete.ages,
                requete.sexe,
                requete.blason_id,
                requete.hauteur_cm,
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
                categorie_id,
                requete.libelle,
                requete.arme,
                requete.ages,
                requete.sexe,
                requete.blason_id,
                hauteur_cm=requete.hauteur_cm,
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
