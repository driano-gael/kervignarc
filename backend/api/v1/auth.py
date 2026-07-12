"""Endpoints REST de l'accès administrateur (`/api/v1/auth`) — E10US002.

- `GET /etat` : l'accès admin est-il déjà défini ? (oriente le front : définir ou se connecter) ;
- `POST /configurer` : **1ᵉʳ accès** — définit login + mot de passe et ouvre aussitôt une session ;
- `POST /connexion` : vérifie les identifiants et ouvre une session (jeton) ;
- `POST /deconnexion` : ferme la session courante (jeton requis).

Les DTO Pydantic sont **distincts** de la couche application. Les opérations touchant le fichier
`.env` (lecture d'état, écriture des identifiants) s'exécutent **hors boucle** (threadpool).
Les erreurs typées sont traduites à la frontière (`api/erreurs.py`) : 401 (identifiants),
409 (déjà/pas configuré), 400 (entrée invalide).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin, extraire_jeton
from application.auth import ServiceAuth

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class EtatAuthReponse(BaseModel):
    """État de l'accès admin : `configure=False` → 1ᵉʳ accès (définir) ; `True` → se connecter."""

    configure: bool


class IdentifiantsRequete(BaseModel):
    """Corps de définition/connexion : login et mot de passe non vides."""

    login: str = Field(min_length=1)
    mot_de_passe: str = Field(min_length=1)


class JetonReponse(BaseModel):
    """Jeton de session admin à joindre aux actions admin (`Authorization: Bearer <jeton>`)."""

    jeton: str


@router.get("/etat", response_model=EtatAuthReponse)
async def etat(request: Request) -> EtatAuthReponse:
    """Indique si un accès administrateur a déjà été défini (lecture du fichier `.env`)."""
    service: ServiceAuth = request.app.state.service_auth
    configure = await run_in_threadpool(service.est_configure)
    return EtatAuthReponse(configure=configure)


@router.post("/configurer", status_code=201, response_model=JetonReponse)
async def configurer(requete: IdentifiantsRequete, request: Request) -> JetonReponse:
    """Définit l'accès admin au 1ᵉʳ usage (écrit `.env`) et ouvre une session."""
    service: ServiceAuth = request.app.state.service_auth
    jeton = await run_in_threadpool(service.configurer, requete.login, requete.mot_de_passe)
    return JetonReponse(jeton=jeton)


@router.post("/connexion", response_model=JetonReponse)
async def connexion(requete: IdentifiantsRequete, request: Request) -> JetonReponse:
    """Vérifie les identifiants et ouvre une session (jeton)."""
    service: ServiceAuth = request.app.state.service_auth
    jeton = await run_in_threadpool(service.connexion, requete.login, requete.mot_de_passe)
    return JetonReponse(jeton=jeton)


@router.post("/deconnexion", status_code=204, dependencies=[Depends(exiger_admin)])
async def deconnexion(request: Request) -> None:
    """Ferme la session courante (jeton valide requis via `exiger_admin`)."""
    service: ServiceAuth = request.app.state.service_auth
    jeton = extraire_jeton(request)
    if jeton is not None:
        await run_in_threadpool(service.deconnexion, jeton)
