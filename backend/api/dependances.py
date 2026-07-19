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
from application.postes import ServicePostes
from application.scoreurs import ServiceScoreurs
from domain.poste import Poste
from domain.scoreur import Scoreur

_PREFIXE_BEARER = "Bearer "
_ENTETE_JETON_SCOREUR = "X-Jeton-Scoreur"
_ENTETE_JETON_POSTE = "X-Jeton-Poste"


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


def extraire_jeton_poste(request: Request) -> str | None:
    """Jeton de session de poste, porté par l'en-tête dédié `X-Jeton-Poste`, ou `None`."""
    entete = request.headers.get(_ENTETE_JETON_POSTE)
    if entete is None:
        return None
    return entete.strip() or None


async def exiger_admin(request: Request) -> None:
    """Exige une session admin valide ; lève `NonAuthentifie` (→ 401) sinon."""
    service: ServiceAuth = request.app.state.service_auth
    if not service.session_valide(extraire_jeton(request)):
        raise NonAuthentifie("Authentification administrateur requise.")


def exiger_scoreur(request: Request) -> Scoreur:
    """Exige une session scoreur valide et **renvoie le scoreur** ; lève `NonAuthentifie` (→ 401).

    Rend le `Scoreur` (nom, tournoi) pour tracer « qui a validé » (E10US005, E04US002) et borner son
    action à **son** tournoi — au-delà du simple booléen. **Synchrone** (comme `exiger_poste`) : la
    résolution relit la base (`par_id`), FastAPI l'exécute dans le threadpool. Les gardes sans
    (`dependencies=[Depends(exiger_scoreur)]`, ex. déconnexion) ignorent le retour ; seul le 401
    importe pour elles.
    """
    service: ServiceScoreurs = request.app.state.service_scoreurs
    scoreur = service.resoudre_session(extraire_jeton_scoreur(request))
    if scoreur is None:
        raise NonAuthentifie("Session scoreur requise.")
    return scoreur


def exiger_poste(request: Request) -> Poste:
    """Exige une session de poste **encore valide** et renvoie sa cible ; lève `NonAuthentifie`
    (→ 401) sinon.

    **Synchrone** (à dessein) : la validité d'un poste dépend du **statut de son tournoi**
    (révocation « tournoi terminé », ADR-0029), donc `resoudre_session` relit la base — FastAPI
    exécute une dépendance synchrone dans le threadpool, sans bloquer la boucle événementielle
    (au contraire d'`exiger_admin`, purement en mémoire ; `exiger_scoreur` relit aussi la base
    depuis E04US002). Renvoie le `Poste` pour que l'appelant sache **quelle cible** est servie sans
    le redemander (E10US007, E04US002).
    """
    service: ServicePostes = request.app.state.service_postes
    poste = service.resoudre_session(extraire_jeton_poste(request))
    if poste is None:
        raise NonAuthentifie("Session de poste requise.")
    return poste


def autoriser_saisie(request: Request) -> Poste | None:
    """Autorise la **saisie** de score : admin **ou** poste de cible (E10US007).

    Élargit l'autorisation d'écriture au-delà de l'admin (E10US001) au **jeton de poste**
    (E04US001), sans jamais rouvrir la saisie au public. Renvoie :

    - `None` si une session **admin** valide est présente — l'admin saisit sans contrainte ;
    - le `Poste` si un **jeton de poste** valide est présent — l'appelant (le service) restreindra
      alors la saisie à **sa** cible (« un poste ne saisit que pour SA cible ») ;
    - sinon `NonAuthentifie` (→ 401), comme toute écriture sans session (garde-fou
      `test_acces_public`).

    L'admin est essayé **en premier** : c'est le mode le plus large, et purement en mémoire, alors
    que la résolution d'un poste relit la base (statut du tournoi, ADR-0029). **Synchrone** pour la
    même raison qu'`exiger_poste` — FastAPI exécute une dépendance synchrone dans le threadpool.
    """
    service_auth: ServiceAuth = request.app.state.service_auth
    if service_auth.session_valide(extraire_jeton(request)):
        return None
    service_postes: ServicePostes = request.app.state.service_postes
    poste = service_postes.resoudre_session(extraire_jeton_poste(request))
    if poste is None:
        raise NonAuthentifie("Session requise pour saisir un score (admin ou poste de cible).")
    return poste
