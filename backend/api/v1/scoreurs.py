"""Endpoints REST des scoreurs (E10US003) — **définition** (admin) et **session** (scoreur).

Deux routers, deux portées :

- **Définition**, imbriquée sous le tournoi (`/api/v1/tournois/{tournoi_id}/scoreurs`) : CRUD
  réservé à l'admin. La lecture y est **aussi** protégée (`exiger_admin`), à rebours des autres
  référentiels (clubs, départs, publics) : la réponse porte le **code** de chaque scoreur, un secret
  à distribuer, qui n'a pas à fuiter au public (E10US001 ouvre les *lectures*, pas les *secrets*).
- **Session**, à la racine (`/api/v1/scoreurs/session`) : `connexion` par code — **ouverte**, c'est
  l'acte d'authentification lui-même — et `deconnexion`, protégée par la session scoreur elle-même.
  Le code seul suffit (aucun tournoi à désigner) : il est unique dans toute la base.

Suit le patron de bout en bout : DTO Pydantic distincts des agrégats ; **écritures** (CRUD) routées
par la file (writer unique, ADR-0005) ; la connexion est une **lecture** (relecture par code +
session en mémoire), donc hors file (threadpool), comme la connexion admin. Erreurs typées traduites
à la frontière (`api/erreurs.py`).
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin, exiger_scoreur, extraire_jeton_scoreur
from application.scoreurs import ServiceScoreurs
from domain.scoreur import Scoreur
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1/tournois/{tournoi_id}/scoreurs", tags=["scoreurs"])
session_router = APIRouter(prefix="/api/v1/scoreurs/session", tags=["scoreurs"])


class CreerScoreurRequete(BaseModel):
    """Corps de création d'un scoreur : le **nom** seul — le code est généré par le serveur."""

    nom: str = Field(min_length=1)


class ModifierScoreurRequete(BaseModel):
    """Corps d'édition d'un scoreur : le **nom** (le code, imprimé et distribué, est figé)."""

    nom: str = Field(min_length=1)


class ScoreurReponse(BaseModel):
    """Représentation d'un scoreur renvoyée au client (admin) : porte le `code` à imprimer."""

    id: int
    tournoi_id: int
    nom: str
    code: str

    @staticmethod
    def de_agregat(scoreur: Scoreur) -> ScoreurReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert scoreur.id is not None, "Un scoreur persisté a toujours un identifiant."
        return ScoreurReponse(
            id=scoreur.id, tournoi_id=scoreur.tournoi_id, nom=scoreur.nom, code=scoreur.code
        )


class ConnexionScoreurRequete(BaseModel):
    """Corps de connexion d'un scoreur : son **code** individuel (normalisé côté service)."""

    code: str = Field(min_length=1)


class ScoreurConnecteReponse(BaseModel):
    """Identité renvoyée à la connexion : de quoi saluer le scoreur et savoir de quel tournoi.

    **Sans le `code`**, à la différence de `ScoreurReponse` (réservé à l'admin) : la connexion est
    un endpoint **public** ; ré-émettre le code — même celui que l'appelant vient de fournir —
    l'exposerait sans raison. Le front n'en a pas besoin (il ne lit que nom/tournoi).
    """

    id: int
    tournoi_id: int
    nom: str

    @staticmethod
    def de_agregat(scoreur: Scoreur) -> ScoreurConnecteReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de session, **code omis**."""
        assert scoreur.id is not None, "Un scoreur persisté a toujours un identifiant."
        return ScoreurConnecteReponse(id=scoreur.id, tournoi_id=scoreur.tournoi_id, nom=scoreur.nom)


class SessionScoreurReponse(BaseModel):
    """Réponse de connexion : le **jeton** de session et le scoreur identifié (nom, tournoi).

    Le jeton est à joindre aux actions du scoreur via l'en-tête `X-Jeton-Scoreur` (persisté par le
    navigateur pour survivre à la fermeture de l'onglet).
    """

    jeton: str
    scoreur: ScoreurConnecteReponse


# --- Définition (admin), imbriquée sous le tournoi ---


@router.post(
    "", status_code=201, response_model=ScoreurReponse, dependencies=[Depends(exiger_admin)]
)
async def creer_scoreur(
    tournoi_id: int, requete: CreerScoreurRequete, request: Request
) -> ScoreurReponse:
    """Déclare un scoreur (**action admin**) : écriture via la file (code généré côté serveur)."""
    service: ServiceScoreurs = request.app.state.service_scoreurs
    write_queue: WriteQueue = request.app.state.write_queue
    scoreur = await asyncio.wrap_future(
        write_queue.submit(lambda: service.creer(tournoi_id, requete.nom))
    )
    return ScoreurReponse.de_agregat(scoreur)


@router.get("", response_model=list[ScoreurReponse], dependencies=[Depends(exiger_admin)])
async def lister_scoreurs(tournoi_id: int, request: Request) -> list[ScoreurReponse]:
    """Liste les scoreurs (triés par nom) — lecture **admin**, la réponse porte les codes."""
    service: ServiceScoreurs = request.app.state.service_scoreurs
    scoreurs = await run_in_threadpool(service.lister, tournoi_id)
    return [ScoreurReponse.de_agregat(scoreur) for scoreur in scoreurs]


@router.put("/{scoreur_id}", response_model=ScoreurReponse, dependencies=[Depends(exiger_admin)])
async def modifier_scoreur(
    tournoi_id: int, scoreur_id: int, requete: ModifierScoreurRequete, request: Request
) -> ScoreurReponse:
    """Renomme un scoreur (**action admin**) : écriture via la file (le code reste figé)."""
    service: ServiceScoreurs = request.app.state.service_scoreurs
    write_queue: WriteQueue = request.app.state.write_queue
    scoreur = await asyncio.wrap_future(
        write_queue.submit(lambda: service.modifier(tournoi_id, scoreur_id, requete.nom))
    )
    return ScoreurReponse.de_agregat(scoreur)


@router.delete("/{scoreur_id}", status_code=204, dependencies=[Depends(exiger_admin)])
async def supprimer_scoreur(tournoi_id: int, scoreur_id: int, request: Request) -> Response:
    """Supprime un scoreur (**action admin**) : écriture via la file ; **invalide sa session**."""
    service: ServiceScoreurs = request.app.state.service_scoreurs
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(write_queue.submit(lambda: service.supprimer(tournoi_id, scoreur_id)))
    return Response(status_code=204)


# --- Session (scoreur), à la racine ---


@session_router.post("", response_model=SessionScoreurReponse)
async def connexion_scoreur(
    requete: ConnexionScoreurRequete, request: Request
) -> SessionScoreurReponse:
    """Ouvre une session scoreur à partir de son code (**ouvert** : c'est l'authentification).

    `401 code_scoreur_inconnu` si le code ne correspond à aucun scoreur. Lecture (relecture par code
    + ouverture de session en mémoire), donc **hors file**, comme la connexion admin.
    """
    service: ServiceScoreurs = request.app.state.service_scoreurs
    connexion = await run_in_threadpool(service.connexion, requete.code)
    return SessionScoreurReponse(
        jeton=connexion.jeton, scoreur=ScoreurConnecteReponse.de_agregat(connexion.scoreur)
    )


@session_router.post("/deconnexion", status_code=204, dependencies=[Depends(exiger_scoreur)])
async def deconnexion_scoreur(request: Request) -> None:
    """Ferme la session courante (jeton scoreur valide requis via `exiger_scoreur`)."""
    service: ServiceScoreurs = request.app.state.service_scoreurs
    jeton = extraire_jeton_scoreur(request)
    if jeton is not None:
        await run_in_threadpool(service.deconnexion, jeton)
