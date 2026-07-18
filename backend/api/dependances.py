"""Dépendances FastAPI transverses (couche API).

`exiger_admin` protège les routes d'administration (E10US002) : elle exige un jeton de session
admin valide dans l'en-tête `Authorization: Bearer <jeton>`. `exiger_scoreur` protège les routes
réservées au scoreur (E10US003) : elle exige un jeton de session scoreur valide dans l'en-tête
**dédié** `X-Jeton-Scoreur`. À défaut, elles lèvent `NonAuthentifie` (traduite en **401** à la
frontière, ADR-0007). Les dépendances restent **cantonnées à l'API** (guide §2.2) : elles
n'atteignent pas le domaine.

Deux en-têtes **distincts** parce que les deux modes d'identité sont **orthogonaux** (`D-13`) :
l'admin (identité = un secret) et le scoreur (identité = la personne) peuvent cohabiter sur des
appareils différents sans se marcher dessus, et un futur endpoint de validation (E04US002) acceptera
l'un **ou** l'autre sans que l'un masque l'autre.
"""

from __future__ import annotations

from fastapi import Request

from application.auth import ServiceAuth
from application.erreurs import NonAuthentifie
from application.scoreurs import ServiceScoreurs

_PREFIXE_BEARER = "Bearer "
_ENTETE_JETON_SCOREUR = "X-Jeton-Scoreur"


def extraire_jeton(request: Request) -> str | None:
    """Jeton de l'en-tête `Authorization: Bearer <jeton>`, ou `None` s'il est absent/mal formé."""
    entete = request.headers.get("Authorization")
    if entete is None or not entete.startswith(_PREFIXE_BEARER):
        return None
    return entete[len(_PREFIXE_BEARER) :].strip() or None


def extraire_jeton_scoreur(request: Request) -> str | None:
    """Jeton de session scoreur, porté par l'en-tête dédié `X-Jeton-Scoreur`, ou `None`."""
    entete = request.headers.get(_ENTETE_JETON_SCOREUR)
    if entete is None:
        return None
    return entete.strip() or None


async def exiger_admin(request: Request) -> None:
    """Exige une session admin valide ; lève `NonAuthentifie` (→ 401) sinon."""
    service: ServiceAuth = request.app.state.service_auth
    if not service.session_valide(extraire_jeton(request)):
        raise NonAuthentifie("Authentification administrateur requise.")


async def exiger_scoreur(request: Request) -> None:
    """Exige une session scoreur valide ; lève `NonAuthentifie` (→ 401) sinon."""
    service: ServiceScoreurs = request.app.state.service_scoreurs
    if not service.session_valide(extraire_jeton_scoreur(request)):
        raise NonAuthentifie("Session scoreur requise.")
