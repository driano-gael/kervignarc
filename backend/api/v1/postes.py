"""Endpoints REST des postes de cible (E04US001, ADR-0029) — **préparation** (admin) et
**session** (poste : rattacher une tablette à sa cible).

Deux routers, deux portées :

- **Préparation**, imbriquée sous le tournoi (`/api/v1/tournois/{tournoi_id}/postes`) : réservée à
  l'admin. `POST` garantit **un code par cible** du plan (idempotent) et renvoie la liste **avec les
  codes** — des secrets d'usage à imprimer (E09US008), qui n'ont pas à fuiter au public.
- **Session**, à la racine (`/api/v1/postes/session`) : `rattacher` par code — **ouverte**, c'est
  l'acte de rattachement lui-même — puis `GET` (retrouver sa cible à la réouverture) et
  `deconnexion`, protégés par la session de poste elle-même (`exiger_poste`).

Patron de bout en bout : DTO Pydantic distincts des agrégats ; **écriture** (préparation) routée par
la file (writer unique, ADR-0005) ; le rattachement et la relecture de session sont des **lectures**
(hors file, threadpool). Erreurs typées traduites à la frontière (`api/erreurs.py`).
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin, exiger_poste, extraire_jeton_poste
from application.postes import ServicePostes
from domain.poste import Poste
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1/tournois/{tournoi_id}/postes", tags=["postes"])
session_router = APIRouter(prefix="/api/v1/postes/session", tags=["postes"])


class PosteReponse(BaseModel):
    """Représentation d'un poste renvoyée à l'admin : porte le `code` de cible à imprimer."""

    id: int
    tournoi_id: int
    cible_index: int
    code: str

    @staticmethod
    def de_agregat(poste: Poste) -> PosteReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert poste.id is not None, "Un poste persisté a toujours un identifiant."
        return PosteReponse(
            id=poste.id,
            tournoi_id=poste.tournoi_id,
            cible_index=poste.cible_index,
            code=poste.code,
        )


class RattacherRequete(BaseModel):
    """Corps de rattachement : le **code** de la cible (scanné ou retapé ; normalisé au service)."""

    code: str = Field(min_length=1)


class PosteRattacheReponse(BaseModel):
    """Cible servie par le poste : de quoi savoir **quel tournoi** et **quelle cible**, **sans le
    code** (la session est un endpoint public ; le front n'a besoin que du couple tournoi/cible)."""

    tournoi_id: int
    cible_index: int

    @staticmethod
    def de_agregat(poste: Poste) -> PosteRattacheReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de session, **code omis**."""
        return PosteRattacheReponse(tournoi_id=poste.tournoi_id, cible_index=poste.cible_index)


class SessionPosteReponse(BaseModel):
    """Réponse de rattachement : le **jeton** de session et la cible rattachée.

    Le jeton est à joindre aux actions du poste via l'en-tête `X-Jeton-Poste` (persisté par le
    navigateur en `localStorage` pour survivre à la fermeture de l'onglet, à une veille, à un
    redémarrage de la tablette).
    """

    jeton: str
    poste: PosteRattacheReponse


# --- Préparation (admin), imbriquée sous le tournoi ---


@router.post("", response_model=list[PosteReponse], dependencies=[Depends(exiger_admin)])
async def preparer_postes(tournoi_id: int, request: Request) -> list[PosteReponse]:
    """Garantit un code par cible du plan et renvoie la liste (**action admin**, écriture via file).

    Idempotent : les codes déjà émis sont préservés (les QR sont imprimés). `404
    tournoi_introuvable` si le tournoi n'existe pas ; liste vide s'il n'a pas encore de plan.
    """
    service: ServicePostes = request.app.state.service_postes
    write_queue: WriteQueue = request.app.state.write_queue
    postes = await asyncio.wrap_future(
        write_queue.submit(lambda: service.assurer_codes(tournoi_id))
    )
    return [PosteReponse.de_agregat(poste) for poste in postes]


@router.get("", response_model=list[PosteReponse], dependencies=[Depends(exiger_admin)])
async def lister_postes(tournoi_id: int, request: Request) -> list[PosteReponse]:
    """Liste les postes déjà préparés (avec leurs codes) — lecture **admin**, sans rien créer.

    Sert à afficher/distribuer les codes ; liste vide tant que la préparation n'a pas été lancée.
    """
    service: ServicePostes = request.app.state.service_postes
    postes = await run_in_threadpool(service.lister, tournoi_id)
    return [PosteReponse.de_agregat(poste) for poste in postes]


# --- Session (poste), à la racine ---


@session_router.post("", response_model=SessionPosteReponse)
async def rattacher_poste(requete: RattacherRequete, request: Request) -> SessionPosteReponse:
    """Rattache une tablette à sa cible à partir du code (**ouvert** : c'est le rattachement).

    `401 code_poste_inconnu` si le code ne correspond à aucune cible ; `409
    rattachement_tournoi_termine` si le tournoi de la cible est terminé. Lecture (relecture par code
    + ouverture de session en mémoire), donc **hors file**.
    """
    service: ServicePostes = request.app.state.service_postes
    connexion = await run_in_threadpool(service.rattacher, requete.code)
    return SessionPosteReponse(
        jeton=connexion.jeton, poste=PosteRattacheReponse.de_agregat(connexion.poste)
    )


@session_router.get("", response_model=PosteRattacheReponse)
async def cible_du_poste(request: Request) -> PosteRattacheReponse:
    """Renvoie la cible du poste courant (réouverture : « retrouve sa cible sans rien demander »).

    `401` si le jeton est absent, inconnu, ou si son tournoi est terminé (révocation) → le front
    purge le jeton et redemande un rattachement. `exiger_poste` est appelée via le threadpool : elle
    relit la base (statut du tournoi), on ne bloque donc pas la boucle événementielle.
    """
    poste = await run_in_threadpool(exiger_poste, request)
    return PosteRattacheReponse.de_agregat(poste)


@session_router.post("/deconnexion", status_code=204, dependencies=[Depends(exiger_poste)])
async def deconnexion_poste(request: Request) -> None:
    """Ferme la session de poste courante (jeton de poste valide requis via `exiger_poste`)."""
    service: ServicePostes = request.app.state.service_postes
    jeton = extraire_jeton_poste(request)
    if jeton is not None:
        await run_in_threadpool(service.deconnexion, jeton)
