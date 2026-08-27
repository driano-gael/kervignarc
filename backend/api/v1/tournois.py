"""Tournois — CRUD et cycle de vie (brouillon, démarrer, pause, reprendre, terminer, archiver).

Patron de bout en bout : DTO distincts des agrégats, écritures par la **file** et sous session
admin, lectures hors boucle, erreurs typées traduites à la frontière.
"""

from __future__ import annotations

import asyncio
import datetime
from collections.abc import Callable

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.tournois import ExigenceEffectifTournoi, OrigineExigence, ServiceTournois
from domain.tournoi import StatutTournoi, Tournoi, TransitionTournoi, TypeTournoi
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1/tournois", tags=["tournois"])


class CreerTournoiRequete(BaseModel):
    """Corps de création d'un tournoi (nom et date requis ; lieu et type facultatifs).

    Le tarif ne se fixe plus ici : il vit sur chaque départ (créneau), configuré à part
    (E02US004, ADR-0017).
    """

    nom: str
    date: datetime.date
    lieu: str | None = None
    type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL


class ModifierTournoiRequete(BaseModel):
    """Corps d'édition des métadonnées d'un tournoi (le statut n'est pas modifiable ici)."""

    nom: str
    date: datetime.date
    lieu: str | None = None
    type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL


class TournoiReponse(BaseModel):
    """Représentation d'un tournoi renvoyée au client."""

    id: int
    nom: str
    date: datetime.date
    lieu: str | None
    type_tournoi: TypeTournoi
    statut: StatutTournoi

    @staticmethod
    def de_agregat(tournoi: Tournoi) -> TournoiReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert tournoi.id is not None, "Un tournoi persisté a toujours un identifiant."
        return TournoiReponse(
            id=tournoi.id,
            nom=tournoi.nom,
            date=tournoi.date,
            lieu=tournoi.lieu,
            type_tournoi=tournoi.type_tournoi,
            statut=tournoi.statut,
        )


class TransitionReponse(BaseModel):
    """Une transition de cycle de vie **offerte** depuis le statut courant (E14US001).

    `nom` est le suffixe d'endpoint à appeler (`POST /api/v1/tournois/{id}/{nom}`), `libelle` le
    texte du bouton, `vers` le statut cible. La *garde* reste au service : une transition listée
    peut échouer à l'exécution (ex. `vers-pret` sans départ → 409).
    """

    nom: str
    libelle: str
    vers: StatutTournoi

    @staticmethod
    def de_domaine(transition: TransitionTournoi) -> TransitionReponse:
        """Traduit une transition du domaine en DTO de réponse."""
        return TransitionReponse(
            nom=transition.nom,
            libelle=transition.libelle,
            vers=transition.vers,
        )


class ExigenceEffectifReponse(BaseModel):
    """Ce que le déroulé d'un tournoi exige d'inscrits, et ce qu'il en a (E05US021).

    Sert l'affichage **permanent** du CA (« 28 inscrits / 34 requis ») : l'écran s'en sert pour
    prévenir *avant* le clic « Démarrer », que le serveur refuserait. `minimum` vaut `0` quand aucun
    déroulé n'est composé — il n'y a alors rien à exiger.

    `ordre_phase`, `rang_debut` et `ordre_source` disent **pourquoi** — « la phase 3 prélève à
    partir du rang 5 **de la phase 2** » — et sont `None` quand le manque ne vient d'aucun
    prélèvement en particulier (rien de composé, ou exigence propre du club). `D-16` / `P-4` : une
    alerte qui ne chiffre pas son impact est un clic de plus, pas une protection.

    ⚠️ **`ordre_source` est indispensable depuis E05US024** : le plancher remonte la chaîne des
    sources, si bien que `rang_debut` se lit dans la phase **source** tandis que `minimum` compte
    des **inscrits** au tournoi. Sans nommer la source, les deux chiffres ne se déduisaient plus
    l'un de l'autre et l'alerte devenait indéchiffrable — corrigé côté 409 mais pas ici dans un
    premier jet, alors que c'est cet écran-là que l'organisateur voit **en premier**.
    """

    inscrits: int
    minimum: int
    suffisant: bool
    # E05US021 : d'où vient le chiffre — `deroule` (plancher déduit) ou `club` (règle saisie). Le
    # front en fait deux phrases distinctes ; le déduire de `ordre_phase is None` faisait annoncer
    # une règle de club là où il n'y en avait aucune.
    origine: OrigineExigence
    ordre_phase: int | None
    rang_debut: int | None
    ordre_source: int | None = None

    @staticmethod
    def de_agregat(exigence: ExigenceEffectifTournoi) -> ExigenceEffectifReponse:
        """Traduit la lecture applicative en DTO de réponse."""
        return ExigenceEffectifReponse(
            inscrits=exigence.inscrits,
            minimum=exigence.minimum,
            suffisant=exigence.suffisant,
            origine=exigence.origine,
            ordre_phase=exigence.ordre_phase,
            rang_debut=exigence.rang_debut,
            ordre_source=exigence.ordre_source,
        )


@router.post(
    "",
    status_code=201,
    response_model=TournoiReponse,
    dependencies=[Depends(exiger_admin)],
)
async def creer_tournoi(requete: CreerTournoiRequete, request: Request) -> TournoiReponse:
    """Crée un tournoi (**action admin**, E10US002) : l'écriture passe par la file (ADR-0005)."""
    service: ServiceTournois = request.app.state.service_tournois
    write_queue: WriteQueue = request.app.state.write_queue
    tournoi = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.creer(
                requete.nom,
                requete.date,
                requete.lieu,
                requete.type_tournoi,
            )
        )
    )
    return TournoiReponse.de_agregat(tournoi)


@router.get("", response_model=list[TournoiReponse])
async def lister_tournois(request: Request) -> list[TournoiReponse]:
    """Liste tous les tournois : lecture directe exécutée hors de la boucle événementielle."""
    service: ServiceTournois = request.app.state.service_tournois
    tournois = await run_in_threadpool(service.lister)
    return [TournoiReponse.de_agregat(tournoi) for tournoi in tournois]


@router.get("/{tournoi_id}", response_model=TournoiReponse)
async def consulter_tournoi(tournoi_id: int, request: Request) -> TournoiReponse:
    """Relit un tournoi : lecture directe exécutée hors de la boucle événementielle."""
    service: ServiceTournois = request.app.state.service_tournois
    tournoi = await run_in_threadpool(service.consulter, tournoi_id)
    return TournoiReponse.de_agregat(tournoi)


@router.get("/{tournoi_id}/transitions", response_model=list[TransitionReponse])
async def transitions_tournoi(tournoi_id: int, request: Request) -> list[TransitionReponse]:
    """Transitions de cycle de vie offertes par le statut courant (E14US001, accueil admin).

    Lecture directe hors boucle événementielle. `TournoiIntrouvable` (→ 404) si l'identifiant est
    inconnu. La *garde* de chaque transition reste au service ; l'accueil s'en sert pour proposer
    les bons boutons.
    """
    service: ServiceTournois = request.app.state.service_tournois
    transitions = await run_in_threadpool(service.transitions_possibles, tournoi_id)
    return [TransitionReponse.de_domaine(transition) for transition in transitions]


@router.get("/{tournoi_id}/exigence-effectif", response_model=ExigenceEffectifReponse)
async def exigence_effectif_tournoi(tournoi_id: int, request: Request) -> ExigenceEffectifReponse:
    """Combien d'inscrits ce tournoi exige, et combien il en a (E05US021).

    Lecture directe hors boucle événementielle, **sans refus** : c'est un état à afficher en continu
    (« 28 inscrits / 34 requis »), pas un verdict à provoquer — le refus, lui, vient du `POST
    …/demarrer`. `TournoiIntrouvable` (→ 404) si l'identifiant est inconnu.
    """
    service: ServiceTournois = request.app.state.service_tournois
    exigence = await run_in_threadpool(service.exigence_effectif, tournoi_id)
    return ExigenceEffectifReponse.de_agregat(exigence)


@router.put(
    "/{tournoi_id}",
    response_model=TournoiReponse,
    dependencies=[Depends(exiger_admin)],
)
async def modifier_tournoi(
    tournoi_id: int, requete: ModifierTournoiRequete, request: Request
) -> TournoiReponse:
    """Édite les métadonnées d'un tournoi (**action admin**) : écriture via la file (ADR-0005)."""
    service: ServiceTournois = request.app.state.service_tournois
    write_queue: WriteQueue = request.app.state.write_queue
    tournoi = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.modifier(
                tournoi_id,
                requete.nom,
                requete.date,
                requete.lieu,
                requete.type_tournoi,
            )
        )
    )
    return TournoiReponse.de_agregat(tournoi)


async def _transition_tournoi(
    request: Request,
    appliquer: Callable[[ServiceTournois, int], Tournoi],
    tournoi_id: int,
) -> TournoiReponse:
    """Applique une transition de cycle de vie (E01US017) : écriture via la file (writer unique).

    `appliquer` est la méthode de service non liée (`ServiceTournois.demarrer`, …) ; la garde de
    légalité et les conflits (`TransitionStatutInvalide` → 409) vivent dans le service — l'API ne
    fait que router l'écriture et traduire l'erreur (`api/erreurs.py`).
    """
    service: ServiceTournois = request.app.state.service_tournois
    write_queue: WriteQueue = request.app.state.write_queue
    tournoi = await asyncio.wrap_future(write_queue.submit(lambda: appliquer(service, tournoi_id)))
    return TournoiReponse.de_agregat(tournoi)


@router.post(
    "/{tournoi_id}/vers-pret",
    response_model=TournoiReponse,
    dependencies=[Depends(exiger_admin)],
)
async def passer_pret_tournoi(tournoi_id: int, request: Request) -> TournoiReponse:
    """Passe un tournoi `brouillon` à `prêt` — feu vert au démarrage (**action admin**)."""
    return await _transition_tournoi(request, ServiceTournois.vers_pret, tournoi_id)


@router.post(
    "/{tournoi_id}/revenir-brouillon",
    response_model=TournoiReponse,
    dependencies=[Depends(exiger_admin)],
)
async def revenir_brouillon_tournoi(tournoi_id: int, request: Request) -> TournoiReponse:
    """Repasse un tournoi `prêt` en `brouillon` pour rééditer (**action admin**)."""
    return await _transition_tournoi(request, ServiceTournois.revenir_brouillon, tournoi_id)


@router.post(
    "/{tournoi_id}/demarrer",
    response_model=TournoiReponse,
    dependencies=[Depends(exiger_admin)],
)
async def demarrer_tournoi(tournoi_id: int, request: Request) -> TournoiReponse:
    """Démarre un tournoi (`prêt` → `en_cours`, **action admin**) : écriture via la file."""
    return await _transition_tournoi(request, ServiceTournois.demarrer, tournoi_id)


@router.post(
    "/{tournoi_id}/mettre-en-pause",
    response_model=TournoiReponse,
    dependencies=[Depends(exiger_admin)],
)
async def mettre_en_pause_tournoi(tournoi_id: int, request: Request) -> TournoiReponse:
    """Gèle un tournoi `en_cours` en `en_pause` (**action admin**)."""
    return await _transition_tournoi(request, ServiceTournois.mettre_en_pause, tournoi_id)


@router.post(
    "/{tournoi_id}/reprendre",
    response_model=TournoiReponse,
    dependencies=[Depends(exiger_admin)],
)
async def reprendre_tournoi(tournoi_id: int, request: Request) -> TournoiReponse:
    """Reprend un tournoi `en_pause` en `en_cours` (**action admin**)."""
    return await _transition_tournoi(request, ServiceTournois.reprendre, tournoi_id)


@router.post(
    "/{tournoi_id}/terminer",
    response_model=TournoiReponse,
    dependencies=[Depends(exiger_admin)],
)
async def terminer_tournoi(tournoi_id: int, request: Request) -> TournoiReponse:
    """Termine un tournoi (`en_cours` → `termine`, **action admin**) : écriture via la file."""
    return await _transition_tournoi(request, ServiceTournois.terminer, tournoi_id)


@router.post(
    "/{tournoi_id}/archiver",
    response_model=TournoiReponse,
    dependencies=[Depends(exiger_admin)],
)
async def archiver_tournoi(tournoi_id: int, request: Request) -> TournoiReponse:
    """Archive un tournoi `terminé` — verrou total, lecture seule (**action admin**)."""
    return await _transition_tournoi(request, ServiceTournois.archiver, tournoi_id)


@router.post(
    "/{tournoi_id}/annuler",
    response_model=TournoiReponse,
    dependencies=[Depends(exiger_admin)],
)
async def annuler_tournoi(tournoi_id: int, request: Request) -> TournoiReponse:
    """Annule un tournoi abandonné — terminal, conserve la trace (**action admin**)."""
    return await _transition_tournoi(request, ServiceTournois.annuler, tournoi_id)


@router.delete(
    "/{tournoi_id}",
    status_code=204,
    dependencies=[Depends(exiger_admin)],
)
async def supprimer_tournoi(tournoi_id: int, request: Request) -> Response:
    """Supprime un tournoi (**action admin**) : refusé (409) s'il est en cours.

    L'écriture passe par la file (ADR-0005) ; renvoie 204 sans contenu en cas de succès.
    """
    service: ServiceTournois = request.app.state.service_tournois
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(write_queue.submit(lambda: service.supprimer(tournoi_id)))
    return Response(status_code=204)
