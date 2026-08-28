"""Endpoints REST des clubs (`/api/v1`) — CRUD du référentiel des clubs (E02US001).

⚠️ Routes **à la racine** et non imbriquées sous un tournoi comme les blasons ou les catégories :
le référentiel des clubs est global et se réutilise d'une compétition à l'autre.

Patron de bout en bout : E00US009.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.clubs import RapportImportClubs, ServiceClubs
from domain.club import Club
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["clubs"])


class CreerClubRequete(BaseModel):
    """Corps de création d'un club (nom non vide, unique au sens de `domain.club.cle_nom`)."""

    nom: str


class ModifierClubRequete(BaseModel):
    """Corps de renommage d'un club (mêmes règles que la création)."""

    nom: str


class ClubReponse(BaseModel):
    """Représentation d'un club renvoyée au client."""

    id: int
    nom: str

    @staticmethod
    def de_agregat(club: Club) -> ClubReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert club.id is not None, "Un club persisté a toujours un identifiant."
        return ClubReponse(id=club.id, nom=club.nom)


@router.get("/clubs", response_model=list[ClubReponse])
async def lister_clubs(request: Request) -> list[ClubReponse]:
    """Liste le référentiel des clubs : lecture directe exécutée hors de la boucle."""
    service: ServiceClubs = request.app.state.service_clubs
    clubs = await run_in_threadpool(service.lister)
    return [ClubReponse.de_agregat(club) for club in clubs]


@router.post(
    "/clubs",
    status_code=201,
    response_model=ClubReponse,
    dependencies=[Depends(exiger_admin)],
)
async def creer_club(requete: CreerClubRequete, request: Request) -> ClubReponse:
    """Ajoute un club au référentiel (**action admin**) : écriture via la file (ADR-0005)."""
    service: ServiceClubs = request.app.state.service_clubs
    write_queue: WriteQueue = request.app.state.write_queue
    club = await asyncio.wrap_future(write_queue.submit(lambda: service.creer(requete.nom)))
    return ClubReponse.de_agregat(club)


@router.put(
    "/clubs/{club_id}",
    response_model=ClubReponse,
    dependencies=[Depends(exiger_admin)],
)
async def modifier_club(
    club_id: int, requete: ModifierClubRequete, request: Request
) -> ClubReponse:
    """Renomme un club (**action admin**) : écriture via la file (ADR-0005)."""
    service: ServiceClubs = request.app.state.service_clubs
    write_queue: WriteQueue = request.app.state.write_queue
    club = await asyncio.wrap_future(
        write_queue.submit(lambda: service.modifier(club_id, requete.nom))
    )
    return ClubReponse.de_agregat(club)


@router.delete(
    "/clubs/{club_id}",
    status_code=204,
    dependencies=[Depends(exiger_admin)],
)
async def supprimer_club(club_id: int, request: Request) -> Response:
    """Retire un club du référentiel (**action admin**) : écriture via la file ; renvoie 204."""
    service: ServiceClubs = request.app.state.service_clubs
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(write_queue.submit(lambda: service.supprimer(club_id)))
    return Response(status_code=204)


class ImporterClubsRequete(BaseModel):
    """Corps d'un import en masse (E01US023) : le texte collé, **une ligne = un club**.

    Un champ texte libre plutôt qu'un `list[str]` : ce que l'organisateur a sous la main, c'est un
    copier-coller depuis un tableur ou un courriel. Lui demander de le transformer en tableau JSON
    serait déplacer sur lui le travail que cet import existe pour supprimer — et le front n'aurait
    qu'à faire un `split` que le service fait déjà, mieux (lignes vides, espaces de bord).
    """

    # Borné : l'import est **une seule** soumission à la file du writer unique (cf. l'endpoint), et
    # une tâche de durée non bornée y monopoliserait toutes les écritures — le jour J, cela gèlerait
    # la saisie des scores. 200 000 caractères laissent largement la place à un collage réaliste
    # (~5 000 clubs) et transforment l'accident en 400 avant toute écriture (règle 7).
    lignes: str = Field(max_length=200_000)


class RapportImportClubsReponse(BaseModel):
    """Compte-rendu d'un import : **aucun import partiel silencieux** (E01US023).

    Les trois issues restent distinctes à l'écran : un total unique laisserait l'organisateur
    croire à un échec là où il n'y a que du déjà-connu.
    """

    crees: list[str]
    doublons: list[str]
    lignes_ignorees: int

    @staticmethod
    def de_rapport(rapport: RapportImportClubs) -> RapportImportClubsReponse:
        return RapportImportClubsReponse(
            crees=list(rapport.crees),
            doublons=list(rapport.doublons),
            lignes_ignorees=rapport.lignes_ignorees,
        )


@router.post(
    "/clubs/import",
    status_code=201,
    response_model=RapportImportClubsReponse,
    dependencies=[Depends(exiger_admin)],
)
async def importer_clubs(
    requete: ImporterClubsRequete, request: Request
) -> RapportImportClubsReponse:
    """Alimente le référentiel **en masse** (**action admin**, E01US023) : écriture via la file.

    ⚠️ Une **seule** soumission à la file pour tout le lot : découper en une écriture par ligne
    ferait passer un collage de 200 clubs pour 200 transactions, là où c'est un geste unique
    (transactions courtes, règle 7). Ne lève pas sur une ligne vide — elle est comptée. À ne pas
    confondre avec l'import des **inscrits** depuis un fichier fédéral (E02US007).
    """
    service: ServiceClubs = request.app.state.service_clubs
    write_queue: WriteQueue = request.app.state.write_queue
    rapport = await asyncio.wrap_future(
        write_queue.submit(lambda: service.importer(requete.lignes))
    )
    return RapportImportClubsReponse.de_rapport(rapport)
