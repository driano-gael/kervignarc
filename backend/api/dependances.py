"""Dépendances FastAPI transverses (couche API).

`exiger_admin` protège les routes d'administration (E10US002) : elle exige un jeton de session
admin valide dans l'en-tête `Authorization: Bearer <jeton>`. À défaut, elle lève `NonAuthentifie`
(traduite en **401** à la frontière, ADR-0007). Les dépendances restent **cantonnées à l'API**
(guide §2.2) : elles n'atteignent pas le domaine.
"""

from __future__ import annotations

from fastapi import Request

from application.auth import ServiceAuth
from application.erreurs import NonAuthentifie

_PREFIXE_BEARER = "Bearer "


def extraire_jeton(request: Request) -> str | None:
    """Jeton de l'en-tête `Authorization: Bearer <jeton>`, ou `None` s'il est absent/mal formé."""
    entete = request.headers.get("Authorization")
    if entete is None or not entete.startswith(_PREFIXE_BEARER):
        return None
    return entete[len(_PREFIXE_BEARER) :].strip() or None


async def exiger_admin(request: Request) -> None:
    """Exige une session admin valide ; lève `NonAuthentifie` (→ 401) sinon."""
    service: ServiceAuth = request.app.state.service_auth
    if not service.session_valide(extraire_jeton(request)):
        raise NonAuthentifie("Authentification administrateur requise.")
