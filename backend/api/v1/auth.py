"""Endpoints REST de l'accès administrateur (`/api/v1/auth`) — E10US002, E10US006.

⚠️ `POST /configurer` n'est ouvert qu'au **1ᵉʳ accès** : il pose login et mot de passe, puis ouvre
aussitôt une session. Écrire les identifiants touche le fichier `.env`, d'où le threadpool.
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


class ModificationIdentifiantsRequete(BaseModel):
    """Corps de modification : mot de passe actuel requis ; `None` = valeur inchangée."""

    mot_de_passe_actuel: str = Field(min_length=1)
    nouveau_login: str | None = None
    nouveau_mot_de_passe: str | None = None


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


@router.patch("/identifiants", status_code=204, dependencies=[Depends(exiger_admin)])
async def modifier_identifiants(requete: ModificationIdentifiantsRequete, request: Request) -> None:
    """Change login et/ou mot de passe (réécrit `.env`) ; seule la session courante survit."""
    service: ServiceAuth = request.app.state.service_auth
    await run_in_threadpool(
        service.modifier,
        extraire_jeton(request),
        requete.mot_de_passe_actuel,
        requete.nouveau_login,
        requete.nouveau_mot_de_passe,
    )
