"""Mapping HTTP des erreurs typées — `DomainError` 422, `ApplicationError` 400/401/403/404/409,
`InfrastructureError` 500 générique, `RequestValidationError` 400.

⚠️ **Les messages techniques ne fuient JAMAIS** : une panne d'infrastructure rend un message
générique, le détail restant journalisé côté serveur. ADR-0007
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
    ArcherHorsBigShootOff,
    ArcherIntrouvable,
    ArretIntrouvable,
    BarrageIntrouvable,
    BlasonIntrouvable,
    CategorieIntrouvable,
    ClubIntrouvable,
    CodePosteInconnu,
    CodeScoreurInconnu,
    CorpsHorsDeProportion,
    DepartIntrouvable,
    EffectifSimulationInvalide,
    ForfaitIntrouvable,
    FormatIntrouvable,
    FormatNonSimulable,
    GabaritDuTournoiAbsent,
    GabaritIntrouvable,
    IdentifiantsInvalides,
    InscriptionIntrouvable,
    JalonNonInstruit,
    LogoIntrouvable,
    MancheIntrouvable,
    NonAuthentifie,
    PhaseIntrouvable,
    PhaseQualificationAbsente,
    PosteIntrouvable,
    RemboursementIntrouvable,
    RencontreIntrouvable,
    SaisieHorsCible,
    ScenarioInconnu,
    ScoreurHorsTournoi,
    ScoreurIntrouvable,
    SessionSimulationIntrouvable,
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
    elif isinstance(exc, EffectifSimulationInvalide | FormatNonSimulable):
        # 400 : la requête est impossible **en soi** (borne de service), pas en conflit avec un
        # état. Le 409 par défaut promettrait qu'un changement d'état la rendrait acceptable, ce qui
        # serait faux — 300 archers ne deviendront jamais simulables, et un format sans
        # qualification ne le devient pas davantage en changeant d'état (E01US024).
        status = 400
    elif isinstance(exc, CorpsHorsDeProportion):
        # 413 : le serveur refuse d'ingérer le corps, indépendamment de ce qu'il contient. Un 422
        # dirait « votre fichier est invalide », ce qui serait faux — il n'a pas été regardé.
        status = 413
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
        | FormatIntrouvable
        | GabaritDuTournoiAbsent
        | PhaseQualificationAbsente
        | PhaseIntrouvable
        | PosteIntrouvable
        | ScoreurIntrouvable
        | ForfaitIntrouvable
        | BarrageIntrouvable
        | RemboursementIntrouvable
        | RencontreIntrouvable
        # ⚠️ Ajoutées à la revue d'E05US028. `MancheIntrouvable` se documentait « → 404 » et se
        # réclamait de `RencontreIntrouvable` juste au-dessus, mais n'était **pas** dans cette
        # chaîne : elle retombait sur le `else: 409`. Le mapping est une liste écrite à la main —
        # rien ne relie une docstring à ce `isinstance`, et aucun test d'API n'exerçait le cas.
        | MancheIntrouvable
        | ArcherHorsBigShootOff
        | ScenarioInconnu
        | SessionSimulationIntrouvable
        # E05US033. `ArretIntrouvable` couvre l'identifiant inconnu, l'arrêt d'un autre créneau,
        # l'arrêt encore armé et l'arrêt déjà levé : quatre situations, un seul geste utile côté
        # client — recharger l'écran. Le 404 est donc exact, et il évite d'exposer *lequel* des
        # quatre, ce qui ne changerait rien pour l'organisateur.
        | ArretIntrouvable
        # E16US012. Un jalon sans écran est « introuvable » du point de vue du client, exactement
        # comme un identifiant inconnu : le geste utile est le même. Inscrit **ici et pas seulement
        # en docstring** — c'est le défaut relevé sur `MancheIntrouvable` ci-dessus, ce mapping
        # étant une liste écrite à la main que rien ne relie aux docstrings.
        | JalonNonInstruit
        # E16US006. Emplacement de logo vide. Inscrite **ici** et non seulement en docstring — cf.
        # les deux commentaires ci-dessus, ce mapping étant une liste écrite à la main.
        | LogoIntrouvable,
    ):
        status = 404
    else:
        status = 409
    # `details` optionnel : une erreur applicative peut porter un impact chiffré (E12US007,
    # `ReplacementNonConfirme`) — première utilisation du canal `details` du format `{code, message,
    # details?}` (règle 5, longtemps « jamais peuplé », cf. DETTE-007). Absent → réponse à deux
    # clés.
    details = getattr(exc, "details", None)
    return _reponse(status, getattr(exc, "code", ApplicationError.code), str(exc), details)


async def _sur_erreur_infrastructure(_: Request, exc: Exception) -> JSONResponse:
    """Panne technique → 500, message générique (le détail reste au serveur)."""
    _logger.exception("Erreur d'infrastructure à la frontière API.", exc_info=exc)
    code = getattr(exc, "code", InfrastructureError.code)
    return _reponse(500, code, "Erreur interne du serveur.")


async def _sur_erreur_inattendue(_: Request, exc: Exception) -> JSONResponse:
    """Dernier filet : toute exception **non typée** → 500 au format uniforme `{code, message}`.

    Sans lui, une exception échappant aux familles typées retombe sur le 500 **texte brut** de
    Starlette : hors du contrat `{code, message}` (règle 5), et ⚠️ **la trace complète fuirait au
    client** si l'app tournait un jour avec `debug=True`. On journalise côté serveur et on ne rend
    qu'un message générique. Enregistré pour `Exception`, il n'attrape que le résidu — Starlette
    route vers le handler le plus précis de la MRO.
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
