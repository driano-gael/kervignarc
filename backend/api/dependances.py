"""Dépendances d'authentification — **cantonnées à l'API**, elles n'atteignent pas le domaine.

⚠️ **Deux en-têtes DISTINCTS, parce que les deux identités sont orthogonales** (`D-13`) : l'admin
(un secret) et le scoreur (une personne) cohabitent sur des appareils différents, et un endpoint
peut accepter l'un **ou** l'autre sans que l'un masque l'autre.
"""

from __future__ import annotations

from fastapi import Request

from application.auth import ServiceAuth
from application.erreurs import NonAuthentifie, SaisieHorsCible
from application.postes import ServicePostes
from application.scoreurs import ServiceScoreurs
from domain.poste import Poste, TypePoste
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
    """Exige une session de poste **encore valide** et renvoie sa cible ; `NonAuthentifie` (401).

    **Synchrone** à dessein : la validité d'un poste dépend du **statut de son tournoi**
    (ADR-0029), donc `resoudre_session` relit la base — FastAPI exécute une dépendance synchrone
    dans le threadpool, sans bloquer la boucle (au contraire d'`exiger_admin`, en mémoire). Renvoie
    le `Poste` pour que l'appelant sache **quelle cible** est servie sans la redemander.
    """
    service: ServicePostes = request.app.state.service_postes
    poste = service.resoudre_session(extraire_jeton_poste(request))
    if poste is None:
        raise NonAuthentifie("Session de poste requise.")
    return poste


def exiger_poste_de_cible(request: Request) -> Poste:
    """Comme `exiger_poste`, mais **refuse un écran de salle** (E07US004, correctif de revue).

    La portée « poste » couvre **deux natures** : la tablette d'une cible et l'écran de salle, qui
    partagent en-tête, store et endpoint de rattachement (CA « même mécanisme »). ⚠️ Un écran est
    du **matériel public**, code affiché dans le gymnase : aucune surface de saisie. La garde vit à
    la **dépendance** — question de portée d'identité, pas de métier —, d'où `SaisieHorsCible`
    (403) et non un `DomainError` (422) que le front confondrait avec une erreur de saisie.
    """
    poste = exiger_poste(request)
    return _refuser_ecran(poste)


def _refuser_ecran(poste: Poste) -> Poste:
    """Refuse un poste de type écran sur une surface de saisie (E07US004)."""
    if poste.type is not TypePoste.CIBLE:
        raise SaisieHorsCible("Un écran de salle ne saisit pas de score.")
    return poste


def autoriser_saisie(request: Request) -> Poste | None:
    """Autorise la **saisie** de score : admin **ou** poste de cible (E10US007).

    Renvoie `None` pour une session **admin** valide, le `Poste` pour un jeton de poste de cible —
    **que l'appelant doit utiliser pour borner la saisie à CETTE cible**. ⚠️ **Un écran de salle est
    refusé ici** : `Poste.cible_index` devenu facultatif transformait la garde en `None != None`,
    donnant un droit d'écriture à un appareil public. Deux barrières, pas une : celle-ci et
    `ServiceArchers._verifier_poste_sert_l_archer` (garde-fou `test_acces_public`).
    """
    service_auth: ServiceAuth = request.app.state.service_auth
    if service_auth.session_valide(extraire_jeton(request)):
        return None
    service_postes: ServicePostes = request.app.state.service_postes
    poste = service_postes.resoudre_session(extraire_jeton_poste(request))
    if poste is None:
        raise NonAuthentifie("Session requise pour saisir un score (admin ou poste de cible).")
    return _refuser_ecran(poste)


def autoriser_forfait_duel(request: Request) -> Scoreur | None:
    """Autorise la déclaration d'un **forfait de duel** : admin **ou** scoreur (E16US008).

    Renvoie `None` pour l'**admin**, le `Scoreur` sinon — que l'appelant doit utiliser pour borner
    l'action à **son** tournoi et tracer qui a déclaré. ⚠️ L'admin, lui, n'est borné à aucun
    tournoi : son secret vaut pour l'instance (`D-13`). Jumelle d'`autoriser_saisie` — une route,
    deux identités, jamais une route admin parallèle (ADR-0099 : le pourquoi est en `stories/`).
    """
    service_auth: ServiceAuth = request.app.state.service_auth
    if service_auth.session_valide(extraire_jeton(request)):
        return None
    service_scoreurs: ServiceScoreurs = request.app.state.service_scoreurs
    scoreur = service_scoreurs.resoudre_session(extraire_jeton_scoreur(request))
    if scoreur is None:
        raise NonAuthentifie("Session requise pour déclarer un forfait (admin ou scoreur).")
    return scoreur
