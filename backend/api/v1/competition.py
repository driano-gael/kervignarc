"""Endpoints REST de la tranche verticale (`/api/v1`) — archers, placement, scores, classement.

Concrétise le fil rouge E00US011 : inscrire un archer → le placer sur une cible → saisir un
score → consulter le classement (qui se met à jour en direct côté client via WebSocket, la
diffusion post-commit étant câblée dans la composition root).

Suit le patron de bout en bout (E00US009) : DTO Pydantic distincts des agrégats ; **écritures**
routées par la file d'écriture (writer unique, ADR-0005) ; **lecture** du classement exécutée
hors boucle (threadpool) ; erreurs typées traduites à la frontière (`api/erreurs.py`).
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.archers import ServiceArchers
from application.classements import ServiceClassement
from domain.archer import Archer
from domain.classement import Classement
from domain.score import Score
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["competition"])


class AjouterArcherRequete(BaseModel):
    """Corps d'inscription d'un archer à un tournoi (E02US002).

    `categorie_id` est **obligatoire** et doit désigner une catégorie du tournoi visé. `club_id`
    reste **facultatif** : absent, il vaut « club encore inconnu » — jamais « aucun club »
    (ADR-0014). `autoriser_homonyme` est la **confirmation** de l'admin après un premier refus
    `homonyme_archer` (409) : il déclare que ce nouvel archer, malgré des nom, prénom et club
    identiques à un inscrit, est bien une autre personne (un père et son fils, typiquement).
    """

    nom: str
    prenom: str
    categorie_id: int
    club_id: int | None = None
    autoriser_homonyme: bool = False


class PlacerArcherRequete(BaseModel):
    """Corps de placement d'un archer sur une cible."""

    cible: int


class SaisirScoreRequete(BaseModel):
    """Corps de saisie d'une flèche marquée."""

    points: int


class ArcherReponse(BaseModel):
    """Représentation d'un archer renvoyée au client."""

    id: int
    tournoi_id: int
    nom: str
    prenom: str
    categorie_id: int
    cible: int | None
    club_id: int | None

    @staticmethod
    def de_agregat(archer: Archer) -> ArcherReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert archer.id is not None, "Un archer persisté a toujours un identifiant."
        return ArcherReponse(
            id=archer.id,
            tournoi_id=archer.tournoi_id,
            nom=archer.nom,
            prenom=archer.prenom,
            categorie_id=archer.categorie_id,
            cible=archer.cible,
            club_id=archer.club_id,
        )


class ScoreReponse(BaseModel):
    """Représentation d'un score renvoyée au client."""

    id: int
    archer_id: int
    points: int

    @staticmethod
    def de_agregat(score: Score) -> ScoreReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert score.id is not None, "Un score persisté a toujours un identifiant."
        return ScoreReponse(id=score.id, archer_id=score.archer_id, points=score.points)


class LigneClassementReponse(BaseModel):
    """Une ligne de classement renvoyée au client."""

    rang: int
    archer_id: int
    nom: str
    cible: int | None
    total: int


class ClassementReponse(BaseModel):
    """Classement d'un tournoi renvoyé au client."""

    tournoi_id: int
    lignes: list[LigneClassementReponse]

    @staticmethod
    def de_agregat(tournoi_id: int, classement: Classement) -> ClassementReponse:
        """Traduit le classement de domaine en DTO de réponse."""
        return ClassementReponse(
            tournoi_id=tournoi_id,
            lignes=[
                LigneClassementReponse(
                    rang=ligne.rang,
                    archer_id=ligne.archer_id,
                    nom=ligne.nom,
                    cible=ligne.cible,
                    total=ligne.total,
                )
                for ligne in classement.lignes
            ],
        )


@router.post(
    "/tournois/{tournoi_id}/archers",
    status_code=201,
    response_model=ArcherReponse,
    dependencies=[Depends(exiger_admin)],
)
async def ajouter_archer(
    tournoi_id: int, requete: AjouterArcherRequete, request: Request
) -> ArcherReponse:
    """Inscrit un archer à un tournoi (**écriture**, session requise — E10US001 ; ADR-0005).

    Renvoie `409 homonyme_archer` si un archer de mêmes nom, prénom et club est déjà inscrit :
    c'est un **signalement**, que le client lève en rejouant l'appel avec `autoriser_homonyme`
    (E02US002).
    """
    service: ServiceArchers = request.app.state.service_archers
    write_queue: WriteQueue = request.app.state.write_queue
    archer = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.ajouter(
                tournoi_id,
                requete.nom,
                requete.prenom,
                requete.categorie_id,
                requete.club_id,
                requete.autoriser_homonyme,
            )
        )
    )
    return ArcherReponse.de_agregat(archer)


@router.post(
    "/archers/{archer_id}/placement",
    response_model=ArcherReponse,
    dependencies=[Depends(exiger_admin)],
)
async def placer_archer(
    archer_id: int, requete: PlacerArcherRequete, request: Request
) -> ArcherReponse:
    """Place un archer sur une cible (**écriture**, session requise — E10US001)."""
    service: ServiceArchers = request.app.state.service_archers
    write_queue: WriteQueue = request.app.state.write_queue
    archer = await asyncio.wrap_future(
        write_queue.submit(lambda: service.placer(archer_id, requete.cible))
    )
    return ArcherReponse.de_agregat(archer)


@router.post(
    "/archers/{archer_id}/scores",
    status_code=201,
    response_model=ScoreReponse,
    dependencies=[Depends(exiger_admin)],
)
async def saisir_score(
    archer_id: int, requete: SaisirScoreRequete, request: Request
) -> ScoreReponse:
    """Enregistre une flèche marquée par un archer (**écriture**, session requise — E10US001).

    Ouverte à l'admin en intérim ; le rôle scoreur (E10US003) / archer (E10US007) élargiront
    cette autorisation. La **validation** d'une série restera réservée au scoreur (E04US007).
    """
    service: ServiceArchers = request.app.state.service_archers
    write_queue: WriteQueue = request.app.state.write_queue
    score = await asyncio.wrap_future(
        write_queue.submit(lambda: service.saisir_score(archer_id, requete.points))
    )
    return ScoreReponse.de_agregat(score)


@router.get("/tournois/{tournoi_id}/classement", response_model=ClassementReponse)
async def consulter_classement(tournoi_id: int, request: Request) -> ClassementReponse:
    """Renvoie le classement courant d'un tournoi (lecture directe hors boucle)."""
    service: ServiceClassement = request.app.state.service_classement
    classement = await run_in_threadpool(service.pour_tournoi, tournoi_id)
    return ClassementReponse.de_agregat(tournoi_id, classement)
