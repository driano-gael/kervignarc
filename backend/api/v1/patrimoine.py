"""Endpoints REST du patrimoine du club (`/api/v1`) — bibliothèque, assemblage, promotion.

E01US023 / ADR-0060. Suit le patron de bout en bout (E00US009) : DTO Pydantic distincts des
agrégats, écriture routée par la **file** (writer unique, ADR-0005) et protégée par `exiger_admin`,
lecture directe **hors boucle** (threadpool), erreurs typées traduites à la frontière.

**Trois familles de routes**, qui sont les trois temps de la vie d'une brique :

- **bibliothèque**, à plat sous `/categories` et `/blasons` — le pendant de `/gabarits` (E01US007).
  Seules la **lecture** et la **création** sont ici : l'édition (`PUT /categories/{id}`) et la
  suppression (`DELETE /categories/{id}`) sont **déjà** à plat depuis E01US003 et fonctionnent
  telles quelles sur un modèle, sans qu'il faille les redéclarer. Les redoubler aurait créé deux
  chemins pour un même geste ;
- **assemblage** d'un tournoi, sous `/tournois/{id}/assemblage` — copie de la bibliothèque ;
- **promotion**, sous `/categories/{id}/promotion` et `/blasons/{id}/promotion` — le retour.

Les routes de bibliothèque **ne portent pas de `tournoi_id`** : c'est tout l'objet de l'US, et ce
qui permet enfin à l'axe atelier de tenir sa promesse « fabriquer, hors tournoi » (DETTE-023).
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from api.v1.blasons import BlasonReponse
from api.v1.categories import CategorieReponse
from application.patrimoine import RapportAssemblage, ServicePatrimoine
from domain.blason import ZoneScore
from domain.categorie import HAUTEUR_CENTRE_DEFAUT, SexeCategorie, TrancheAge
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["patrimoine"])


class CreerCategorieBibliothequeRequete(BaseModel):
    """Corps de création d'une catégorie **de bibliothèque** — sans `tournoi_id`, par construction.

    Mêmes champs que la création dans un tournoi (E01US003), à l'exception notable du tournoi : un
    modèle n'en a pas. `blason_id`, s'il est fourni, doit désigner un blason **de la bibliothèque**
    (le service refuse un blason de tournoi en 409).
    """

    libelle: str
    arme: str | None = None
    ages: list[TrancheAge] = Field(default_factory=list)
    sexe: SexeCategorie | None = None
    blason_id: int | None = None
    hauteur_cm: int = HAUTEUR_CENTRE_DEFAUT


class CreerBlasonBibliothequeRequete(BaseModel):
    """Corps de création d'un blason **de bibliothèque** (zones omises → défaut du domaine)."""

    nom: str
    taille: float
    capacite: int
    zones: list[ZoneScore] | None = None


class RapportAssemblageReponse(BaseModel):
    """Compte-rendu d'un assemblage ou d'un pré-chargement.

    Les « ignorés » ne sont pas une anomalie : l'opération est **rejouable**, et c'est ce compte
    qui permet à l'écran de dire « rien de neuf » plutôt que de laisser croire à un échec.
    """

    blasons_copies: int
    blasons_ignores: int
    categories_copiees: int
    categories_ignorees: int

    @staticmethod
    def de_rapport(rapport: RapportAssemblage) -> RapportAssemblageReponse:
        return RapportAssemblageReponse(
            blasons_copies=rapport.blasons_copies,
            blasons_ignores=rapport.blasons_ignores,
            categories_copiees=rapport.categories_copiees,
            categories_ignorees=rapport.categories_ignorees,
        )


# --- Bibliothèque (hors tournoi) ----------------------------------------------------------------


@router.get("/categories", response_model=list[CategorieReponse])
async def lister_categories_bibliotheque(request: Request) -> list[CategorieReponse]:
    """Liste les catégories **modèles** du club : lecture directe exécutée hors de la boucle."""
    service: ServicePatrimoine = request.app.state.service_patrimoine
    categories = await run_in_threadpool(service.lister_categories)
    return [CategorieReponse.de_agregat(categorie) for categorie in categories]


@router.get("/blasons", response_model=list[BlasonReponse])
async def lister_blasons_bibliotheque(request: Request) -> list[BlasonReponse]:
    """Liste les blasons **modèles** du club : lecture directe exécutée hors de la boucle."""
    service: ServicePatrimoine = request.app.state.service_patrimoine
    blasons = await run_in_threadpool(service.lister_blasons)
    return [BlasonReponse.de_agregat(blason) for blason in blasons]


@router.post(
    "/categories",
    status_code=201,
    response_model=CategorieReponse,
    dependencies=[Depends(exiger_admin)],
)
async def creer_categorie_bibliotheque(
    requete: CreerCategorieBibliothequeRequete, request: Request
) -> CategorieReponse:
    """Crée une catégorie de bibliothèque (**action admin**) : écriture via la file (ADR-0005)."""
    service: ServicePatrimoine = request.app.state.service_patrimoine
    write_queue: WriteQueue = request.app.state.write_queue
    categorie = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.creer_categorie(
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


@router.post(
    "/blasons",
    status_code=201,
    response_model=BlasonReponse,
    dependencies=[Depends(exiger_admin)],
)
async def creer_blason_bibliotheque(
    requete: CreerBlasonBibliothequeRequete, request: Request
) -> BlasonReponse:
    """Crée un blason de bibliothèque (**action admin**) : écriture via la file (ADR-0005)."""
    service: ServicePatrimoine = request.app.state.service_patrimoine
    write_queue: WriteQueue = request.app.state.write_queue
    blason = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.creer_blason(
                requete.nom, requete.taille, requete.capacite, requete.zones
            )
        )
    )
    return BlasonReponse.de_agregat(blason)


@router.post(
    "/patrimoine/precharger-ffta",
    status_code=201,
    response_model=RapportAssemblageReponse,
    dependencies=[Depends(exiger_admin)],
)
async def precharger_ffta_bibliotheque(request: Request) -> RapportAssemblageReponse:
    """Pré-charge le référentiel FFTA **dans la bibliothèque** (**action admin**, E01US023).

    Une fois pour toutes, et non à chaque tournoi : c'est la correction de fond de DETTE-023.
    Rejouable sans doublonner — le rapport dit ce qui a été créé et ce qui était déjà là.
    """
    service: ServicePatrimoine = request.app.state.service_patrimoine
    write_queue: WriteQueue = request.app.state.write_queue
    rapport = await asyncio.wrap_future(write_queue.submit(service.precharger_ffta))
    return RapportAssemblageReponse.de_rapport(rapport)


# --- Assemblage d'un tournoi --------------------------------------------------------------------


@router.post(
    "/tournois/{tournoi_id}/assemblage",
    status_code=201,
    response_model=RapportAssemblageReponse,
    dependencies=[Depends(exiger_admin)],
)
async def assembler_tournoi(tournoi_id: int, request: Request) -> RapportAssemblageReponse:
    """Copie **toute la bibliothèque** dans un tournoi (**action admin**) : écriture via la file.

    Rejouable : une brique dont le nom est déjà pris dans le tournoi est ignorée, jamais écrasée
    — l'organisateur a pu ajuster sa copie, et l'assemblage ne défait pas son travail.
    """
    service: ServicePatrimoine = request.app.state.service_patrimoine
    write_queue: WriteQueue = request.app.state.write_queue
    rapport = await asyncio.wrap_future(write_queue.submit(lambda: service.assembler(tournoi_id)))
    return RapportAssemblageReponse.de_rapport(rapport)


@router.post(
    "/tournois/{tournoi_id}/assemblage/blasons/{blason_id}",
    status_code=201,
    response_model=BlasonReponse,
    dependencies=[Depends(exiger_admin)],
)
async def appliquer_blason(tournoi_id: int, blason_id: int, request: Request) -> BlasonReponse:
    """Copie **un** blason de bibliothèque dans un tournoi (**action admin**).

    Idempotent par nom : si le tournoi porte déjà un blason de ce nom, celui-ci est renvoyé tel
    quel. Renvoie 409 (`brique_hors_bibliotheque`) si l'identifiant vise la copie d'un tournoi.
    """
    service: ServicePatrimoine = request.app.state.service_patrimoine
    write_queue: WriteQueue = request.app.state.write_queue
    blason = await asyncio.wrap_future(
        write_queue.submit(lambda: service.appliquer_blason(tournoi_id, blason_id))
    )
    return BlasonReponse.de_agregat(blason)


@router.post(
    "/tournois/{tournoi_id}/assemblage/categories/{categorie_id}",
    status_code=201,
    response_model=CategorieReponse,
    dependencies=[Depends(exiger_admin)],
)
async def appliquer_categorie(
    tournoi_id: int, categorie_id: int, request: Request
) -> CategorieReponse:
    """Copie **une** catégorie de bibliothèque dans un tournoi (**action admin**).

    **Entraîne son blason** par défaut : `blason_id` vise un blason du tournoi (E01US006), donc le
    blason du modèle est copié d'abord s'il manque.
    """
    service: ServicePatrimoine = request.app.state.service_patrimoine
    write_queue: WriteQueue = request.app.state.write_queue
    categorie = await asyncio.wrap_future(
        write_queue.submit(lambda: service.appliquer_categorie(tournoi_id, categorie_id))
    )
    return CategorieReponse.de_agregat(categorie)


# --- Promotion ----------------------------------------------------------------------------------


@router.post(
    "/blasons/{blason_id}/promotion",
    status_code=201,
    response_model=BlasonReponse,
    dependencies=[Depends(exiger_admin)],
)
async def promouvoir_blason(blason_id: int, request: Request) -> BlasonReponse:
    """Fait remonter la copie d'un tournoi dans la bibliothèque (**action admin**, « permanent »).

    Ne rétroagit sur aucune édition déjà assemblée. Renvoie 409 (`brique_deja_en_bibliotheque`) si
    la brique visée est elle-même un modèle.
    """
    service: ServicePatrimoine = request.app.state.service_patrimoine
    write_queue: WriteQueue = request.app.state.write_queue
    blason = await asyncio.wrap_future(
        write_queue.submit(lambda: service.promouvoir_blason(blason_id))
    )
    return BlasonReponse.de_agregat(blason)


@router.post(
    "/categories/{categorie_id}/promotion",
    status_code=201,
    response_model=CategorieReponse,
    dependencies=[Depends(exiger_admin)],
)
async def promouvoir_categorie(categorie_id: int, request: Request) -> CategorieReponse:
    """Fait remonter la copie d'un tournoi dans la bibliothèque (**action admin**, « permanent »).

    Le blason par défaut est **retraduit** vers le blason de bibliothèque de même nom.
    """
    service: ServicePatrimoine = request.app.state.service_patrimoine
    write_queue: WriteQueue = request.app.state.write_queue
    categorie = await asyncio.wrap_future(
        write_queue.submit(lambda: service.promouvoir_categorie(categorie_id))
    )
    return CategorieReponse.de_agregat(categorie)
