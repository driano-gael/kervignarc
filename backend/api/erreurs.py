"""Traduction des erreurs typées en réponses HTTP normalisées (frontière API, ADR-0007).

Le mapping des familles d'exceptions (domaine / application / infrastructure) vers HTTP se
fait **uniquement ici**. Format de réponse uniforme : `{ code, message, details? }`. Les
messages techniques **ne fuient pas** : une panne d'infrastructure renvoie un message
générique, le détail étant journalisé côté serveur.

| Famille                | HTTP           |
|------------------------|----------------|
| `DomainError`          | 422            |
| `ApplicationError`     | 401 (auth) / 403 (interdit) / 404 / 409 |
| `InfrastructureError`  | 500 (générique)|
| `RequestValidationError` (entrée) | 400 |
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from application.erreurs import (
    ApplicationError,
    ArcherIntrouvable,
    BlasonIntrouvable,
    CategorieIntrouvable,
    ClubIntrouvable,
    CodePosteInconnu,
    CodeScoreurInconnu,
    DepartIntrouvable,
    GabaritDuTournoiAbsent,
    GabaritIntrouvable,
    IdentifiantsInvalides,
    InscriptionIntrouvable,
    NonAuthentifie,
    PhaseQualificationAbsente,
    PosteIntrouvable,
    SaisieHorsCible,
    ScoreurHorsTournoi,
    ScoreurIntrouvable,
    TournoiIntrouvable,
)
from domain.erreurs import DomainError
from infrastructure.erreurs import InfrastructureError

_logger = logging.getLogger(__name__)


def _reponse(status: int, code: str, message: str, details: Any = None) -> JSONResponse:
    corps: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        corps["details"] = details
    return JSONResponse(status_code=status, content=corps)


async def _sur_erreur_domaine(_: Request, exc: Exception) -> JSONResponse:
    """Règle métier violée → 422 avec le code métier."""
    return _reponse(422, getattr(exc, "code", DomainError.code), str(exc))


async def _sur_erreur_application(_: Request, exc: Exception) -> JSONResponse:
    """Cas d'usage impossible → 401 (auth), 403 (interdit), 404 (introuvable) ou 409 (conflit)."""
    if isinstance(
        exc, IdentifiantsInvalides | NonAuthentifie | CodeScoreurInconnu | CodePosteInconnu
    ):
        status = 401
    elif isinstance(exc, SaisieHorsCible | ScoreurHorsTournoi):
        # 403 : l'identité est établie (jeton de poste/scoreur valide) mais elle n'autorise pas
        # **cette** ressource — la cible (poste, E10US007) ou le tournoi (scoreur, E04US002). À
        # distinguer du 401 (aucune session) et du 409 (conflit d'état).
        status = 403
    elif isinstance(
        exc,
        TournoiIntrouvable
        | ArcherIntrouvable
        | CategorieIntrouvable
        | ClubIntrouvable
        | DepartIntrouvable
        | InscriptionIntrouvable
        | BlasonIntrouvable
        | GabaritIntrouvable
        | GabaritDuTournoiAbsent
        | PhaseQualificationAbsente
        | PosteIntrouvable
        | ScoreurIntrouvable,
    ):
        status = 404
    else:
        status = 409
    return _reponse(status, getattr(exc, "code", ApplicationError.code), str(exc))


async def _sur_erreur_infrastructure(_: Request, exc: Exception) -> JSONResponse:
    """Panne technique → 500, message générique (le détail reste au serveur)."""
    _logger.exception("Erreur d'infrastructure à la frontière API.", exc_info=exc)
    code = getattr(exc, "code", InfrastructureError.code)
    return _reponse(500, code, "Erreur interne du serveur.")


async def _sur_erreur_inattendue(_: Request, exc: Exception) -> JSONResponse:
    """Dernier filet : toute exception **non typée** → 500 au format uniforme `{code, message}`.

    Sans ce gestionnaire, une exception qui échappe aux familles typées (un `AssertionError` d'un
    invariant « un persisté a un id », un bug de programmation) retombe sur le 500 **texte brut** de
    Starlette : hors du contrat `{code, message}` (règle 5), et surtout **la trace complète fuirait
    au client** si l'app tournait un jour avec `debug=True`. On journalise le détail côté serveur
    (`_logger.exception`) et on ne rend qu'un message générique. Enregistré pour `Exception`, il
    n'attrape que le résidu des gestionnaires plus spécifiques (domaine / application / infra /
    validation) — Starlette route vers le handler le plus précis de la MRO.
    """
    _logger.exception("Exception non gérée à la frontière API.", exc_info=exc)
    return _reponse(500, "erreur_interne", "Erreur interne du serveur.")


async def _sur_erreur_validation(_: Request, exc: Exception) -> JSONResponse:
    """Entrée invalide (Pydantic) → 400 avec le détail des champs fautifs."""
    # DETTE-008 (docs/dette.md) : `exc.errors()` embarque le champ `input` — l'entrée du client,
    # verbatim — sans borne de taille ni plafond du nombre d'erreurs listées. Amplification
    # mesurée x42,9 (50 Ko envoyés -> 2,1 Mo reçus). **Ne pas retirer `details`** pour autant : le
    # format `{code, message, details?}` est la règle 5, et DETTE-007 prévoit de s'en servir. Le
    # correctif est de **borner**, en US dédiée.
    details = jsonable_encoder(exc.errors()) if isinstance(exc, RequestValidationError) else None
    return _reponse(400, "requete_invalide", "Requête invalide.", details)


def enregistrer_gestionnaires_erreurs(app: FastAPI) -> None:
    """Branche les gestionnaires d'exceptions typées sur l'app (composition root)."""
    app.add_exception_handler(DomainError, _sur_erreur_domaine)
    app.add_exception_handler(ApplicationError, _sur_erreur_application)
    app.add_exception_handler(InfrastructureError, _sur_erreur_infrastructure)
    app.add_exception_handler(RequestValidationError, _sur_erreur_validation)
    # Filet catch-all EN DERNIER (le plus général) : toute exception non typée qui a échappé aux
    # gestionnaires ci-dessus. Starlette route vers le handler le plus précis, celui-ci ne prend
    # donc que le résidu — mais garantit qu'aucune réponse ne sort hors du format `{code, message}`.
    app.add_exception_handler(Exception, _sur_erreur_inattendue)
