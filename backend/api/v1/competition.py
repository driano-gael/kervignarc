"""Endpoints REST de la tranche verticale (`/api/v1`) — archers, placement, scores, classement.

Les routes d'administration des archers (lister, éditer, désinscrire — E02US003) sont posées ici,
auprès des routes archer déjà existantes, plutôt que dans un `api/v1/archers.py` neuf : elles
partagent le même DTO de réponse et le même service. Un module dédié se justifiera quand la
tranche verticale du walking skeleton sera démantelée (placement en E03, saisie en E04).

Concrétise le fil rouge E00US011 : inscrire un archer → le placer sur une cible → saisir un
score → consulter le classement (qui se met à jour en direct côté client via WebSocket, la
diffusion post-commit étant câblée dans la composition root).

Suit le patron de bout en bout (E00US009) : DTO Pydantic distincts des agrégats ; **écritures**
routées par la file d'écriture (writer unique, ADR-0005) ; **lecture** du classement exécutée
hors boucle (threadpool) ; erreurs typées traduites à la frontière (`api/erreurs.py`).
"""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import autoriser_saisie, exiger_admin
from application.archers import ServiceArchers
from application.classements import ServiceClassement
from domain.archer import Archer
from domain.classement import Classement
from domain.poste import Poste
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


class ModifierArcherRequete(BaseModel):
    """Corps d'édition d'un archer inscrit (E02US003) — **remplacement total**.

    DTO distinct d'`AjouterArcherRequete` bien qu'il en reprenne les champs : les deux corps
    divergent déjà (`autoriser_changement_categorie` n'a pas de sens à l'inscription) et le
    patron du projet est un DTO par cas d'usage, même quand ils coïncident (E02US001).

    Les quatre champs éditables sont **tous** attendus : c'est un PUT, pas un patch. `club_id`
    absent ou `null` **détache** le club (retour à « club inconnu », ADR-0014), il ne signifie
    jamais « laisse en l'état ».

    Les deux drapeaux sont des **confirmations** de l'admin après un premier 409, chacun pour son
    propre signalement : `autoriser_homonyme` (l'édition fait entrer l'archer dans l'identité d'un
    autre inscrit) et `autoriser_changement_categorie` (elle change la catégorie d'un archer qui a
    déjà tiré). Ils sont indépendants : si les deux faits sont vrais, le client reçoit un 409 pour
    l'un, puis pour l'autre — deux confirmations distinctes, plutôt qu'un blanc-seing sur un motif
    que l'admin n'aurait pas lu.
    """

    nom: str
    prenom: str
    categorie_id: int
    club_id: int | None = None
    autoriser_homonyme: bool = False
    autoriser_changement_categorie: bool = False


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
    """Une ligne de classement renvoyée au client (E06US001).

    Deux rangs : `rang_scratch` (global, toutes catégories) et `rang_categorie` (au sein de la
    catégorie de l'archer). `nb_dix`/`nb_neuf` rendent le **départage traçable** (à total égal, plus
    de 10 puis de 9) : le client peut afficher *pourquoi* deux archers sont ainsi ordonnés.

    `club_id` à `null` = club encore **inconnu** : c'est le signal que l'écran affiche pour que
    l'anomalie soit résorbée (E02US002, ADR-0014). Le nom du club n'est pas résolu ici — le
    client dispose déjà du référentiel s'il veut l'afficher.
    """

    rang_scratch: int
    rang_categorie: int
    archer_id: int
    nom: str
    prenom: str
    categorie_id: int
    categorie_libelle: str
    cible: int | None
    club_id: int | None
    total: int
    nb_dix: int
    nb_neuf: int


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
                    rang_scratch=ligne.rang_scratch,
                    rang_categorie=ligne.rang_categorie,
                    archer_id=ligne.archer_id,
                    nom=ligne.nom,
                    prenom=ligne.prenom,
                    categorie_id=ligne.categorie_id,
                    categorie_libelle=ligne.categorie_libelle,
                    cible=ligne.cible,
                    club_id=ligne.club_id,
                    total=ligne.total,
                    nb_dix=ligne.nb_dix,
                    nb_neuf=ligne.nb_neuf,
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


@router.get("/tournois/{tournoi_id}/archers", response_model=list[ArcherReponse])
async def lister_archers(tournoi_id: int, request: Request) -> list[ArcherReponse]:
    """Renvoie les inscrits d'un tournoi, triés par nom puis prénom (lecture hors boucle).

    Alimente l'écran d'administration des archers (E02US003). Lecture **ouverte**, comme le
    classement : la liste des inscrits est affichée publiquement le jour J.
    """
    service: ServiceArchers = request.app.state.service_archers
    archers = await run_in_threadpool(service.lister, tournoi_id)
    return [ArcherReponse.de_agregat(archer) for archer in archers]


@router.put(
    "/archers/{archer_id}",
    response_model=ArcherReponse,
    dependencies=[Depends(exiger_admin)],
)
async def modifier_archer(
    archer_id: int, requete: ModifierArcherRequete, request: Request
) -> ArcherReponse:
    """Corrige un archer inscrit (**écriture**, session requise — E10US001 ; E02US003).

    Renvoie `409 homonyme_archer` ou `409 changement_categorie_archer_engage` — des
    **signalements**, que le client lève en rejouant l'appel avec le drapeau correspondant.
    """
    service: ServiceArchers = request.app.state.service_archers
    write_queue: WriteQueue = request.app.state.write_queue
    archer = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.modifier(
                archer_id,
                requete.nom,
                requete.prenom,
                requete.categorie_id,
                requete.club_id,
                requete.autoriser_homonyme,
                requete.autoriser_changement_categorie,
            )
        )
    )
    return ArcherReponse.de_agregat(archer)


@router.delete(
    "/archers/{archer_id}",
    status_code=204,
    dependencies=[Depends(exiger_admin)],
)
async def supprimer_archer(
    archer_id: int, request: Request, autoriser_suppression_engage: bool = False
) -> Response:
    """Désinscrit un archer (**écriture**, session requise — E10US001 ; E02US003).

    Renvoie `409 archer_engage` si l'archer est placé ou a déjà tiré : un **signalement**, que le
    client lève en rejouant l'appel avec `autoriser_suppression_engage`. La suppression confirmée
    **efface ses scores et son placement**. Un archer qui abandonne relève du forfait (E04US015 en
    qualification, E12US004 en duels), pas d'ici — voir ADR-0016.

    Le drapeau est en **paramètre de requête** et non dans le corps, contrairement à la forme posée
    par ADR-0015 — qui prévoit ce cas (« soit justifier d'en diverger ») : un `DELETE` n'a pas de
    corps par convention HTTP, et certains intermédiaires le suppriment. La substance d'ADR-0015 est
    tenue : drapeau booléen explicite, à `False` par défaut, sur une route réservée à l'admin.
    **ADR-0016 sanctionne cette variante** — ADR-0015 est immuable, il ne pouvait pas l'accueillir.
    """
    service: ServiceArchers = request.app.state.service_archers
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(
        write_queue.submit(lambda: service.supprimer(archer_id, autoriser_suppression_engage))
    )
    return Response(status_code=204)


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
)
async def saisir_score(
    archer_id: int,
    requete: SaisirScoreRequete,
    request: Request,
    poste_autorise: Annotated[Poste | None, Depends(autoriser_saisie)],
) -> ScoreReponse:
    """Enregistre une flèche marquée par un archer (**écriture** — E10US001, E10US007).

    Autorisée à l'**admin** (sans contrainte) **ou** au **poste de cible** (E04US001), qui ne peut
    marquer que pour **sa** cible — `autoriser_saisie` renvoie le `Poste` correspondant, transmis au
    service qui fait respecter cet invariant (403 sinon). La **validation** d'une série reste
    réservée au scoreur (E04US002) : un poste saisit, il ne valide pas.

    `Annotated[..., Depends(...)]` plutôt qu'un défaut `= Depends(...)` : c'est le premier endpoint
    qui exploite la **valeur** rendue par sa dépendance (les autres passent par `dependencies=[...]`
    dans le décorateur), et cette forme évite le faux positif B008 sans `noqa`.
    """
    service: ServiceArchers = request.app.state.service_archers
    write_queue: WriteQueue = request.app.state.write_queue
    score = await asyncio.wrap_future(
        write_queue.submit(lambda: service.saisir_score(archer_id, requete.points, poste_autorise))
    )
    return ScoreReponse.de_agregat(score)


@router.get("/tournois/{tournoi_id}/classement", response_model=ClassementReponse)
async def consulter_classement(
    tournoi_id: int, request: Request, categorie_id: int | None = None
) -> ClassementReponse:
    """Renvoie le classement de qualification d'un tournoi (lecture directe hors boucle).

    `categorie_id` (optionnel) **filtre** l'affichage à une catégorie ; les rangs (scratch et
    catégorie) restent ceux du classement complet — filtrer une catégorie ne réordonne pas le reste.
    """
    service: ServiceClassement = request.app.state.service_classement
    classement = await run_in_threadpool(service.pour_tournoi, tournoi_id, categorie_id)
    return ClassementReponse.de_agregat(tournoi_id, classement)
