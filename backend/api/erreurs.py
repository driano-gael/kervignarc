"""Traduction des erreurs typées en réponses HTTP normalisées (frontière API, ADR-0007).

Le mapping des familles d'exceptions (domaine / application / infrastructure) vers HTTP se
fait **uniquement ici**. Format de réponse uniforme : `{ code, message, details? }`. Les
messages techniques **ne fuient pas** : une panne d'infrastructure renvoie un message
générique, le détail étant journalisé côté serveur.

| Famille                | HTTP           |
|------------------------|----------------|
| `DomainError`          | 422            |
| `ApplicationError`     | 404 / 409      |
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

from application.erreurs import ApplicationError, TournoiIntrouvable
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
    """Cas d'usage impossible → 404 (introuvable) sinon 409 (conflit)."""
    status = 404 if isinstance(exc, TournoiIntrouvable) else 409
    return _reponse(status, getattr(exc, "code", ApplicationError.code), str(exc))


async def _sur_erreur_infrastructure(_: Request, exc: Exception) -> JSONResponse:
    """Panne technique → 500, message générique (le détail reste au serveur)."""
    _logger.exception("Erreur d'infrastructure à la frontière API.", exc_info=exc)
    code = getattr(exc, "code", InfrastructureError.code)
    return _reponse(500, code, "Erreur interne du serveur.")


async def _sur_erreur_validation(_: Request, exc: Exception) -> JSONResponse:
    """Entrée invalide (Pydantic) → 400 avec le détail des champs fautifs."""
    details = jsonable_encoder(exc.errors()) if isinstance(exc, RequestValidationError) else None
    return _reponse(400, "requete_invalide", "Requête invalide.", details)


def enregistrer_gestionnaires_erreurs(app: FastAPI) -> None:
    """Branche les gestionnaires d'exceptions typées sur l'app (composition root)."""
    app.add_exception_handler(DomainError, _sur_erreur_domaine)
    app.add_exception_handler(ApplicationError, _sur_erreur_application)
    app.add_exception_handler(InfrastructureError, _sur_erreur_infrastructure)
    app.add_exception_handler(RequestValidationError, _sur_erreur_validation)
