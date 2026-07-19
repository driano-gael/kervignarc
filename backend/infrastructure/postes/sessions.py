"""Adapter : jetons de session de poste en mémoire (E04US001, ADR-0029).

Réalise le port `application.postes.StoreSessionsPoste`. Jetons **opaques**
(`secrets.token_urlsafe`), conservés dans un dictionnaire `jeton → poste_id` protégé par un verrou
(lectures/écritures peuvent venir de threads du threadpool). Le lien vers l'`id` du poste sert au
client à retrouver **sa cible** à la réouverture.

**Sans expiration**, comme la session scoreur (ADR-0025), et persisté côté client (`localStorage`)
pour survivre à la fermeture de l'onglet, au redémarrage de la tablette ou à une veille. Invalidé au
**redémarrage** du serveur (mémoire volontairement volatile) ou à la **déconnexion**. La révocation
« tournoi terminé » n'est **pas** portée ici : elle est appliquée à la **résolution** par le service
(`ServicePostes.resoudre_session`), qui seul connaît le cycle de vie du tournoi.
"""

from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass

from domain.depart import DepartId
from domain.poste import PosteId


@dataclass
class _EtatSession:
    """État en mémoire d'une session de poste : sa cible et son **départ courant** (ADR-0034).

    Mutable (au contraire des agrégats du domaine) : le départ courant se **fixe puis se change**
    en cours de session (« mode départ X »), sans rouvrir la session. `depart_id` vaut `None` tant
    qu'aucun départ n'a été fixé — le poste connaît son lieu mais ne sait pas encore qui saisir.
    """

    poste_id: PosteId
    depart_id: DepartId | None = None


class PosteSessionStore:
    """Sessions de poste ouvertes, indexées par jeton opaque → cible + départ courant.

    Le **départ courant** est porté ici (état de session, ADR-0034), pas persisté : il est propre au
    jeton — deux tablettes rattachées à la même cible ont chacune le leur, et un redémarrage serveur
    le remet à `None` (le poste re-fixe son départ), au même titre que la session elle-même.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, _EtatSession] = {}
        self._verrou = threading.Lock()

    def ouvrir(self, poste_id: PosteId) -> str:
        """Ouvre une session pour un poste (sans départ courant) et renvoie son jeton opaque."""
        jeton = secrets.token_urlsafe(32)
        with self._verrou:
            self._sessions[jeton] = _EtatSession(poste_id)
        return jeton

    def poste_de(self, jeton: str | None) -> PosteId | None:
        """Identifiant du poste derrière un jeton (non vide) valide, ou `None`."""
        if not jeton:
            return None
        with self._verrou:
            etat = self._sessions.get(jeton)
        return etat.poste_id if etat is not None else None

    def fixer_depart(self, jeton: str, depart_id: DepartId) -> None:
        """Fixe (ou change) le départ courant d'une session ; sans effet si le jeton est inconnu.

        L'appelant (`ServicePostes.fixer_depart_courant`) a déjà validé la session et la cohérence
        du départ ; on ne (re)crée jamais de session ici.
        """
        with self._verrou:
            etat = self._sessions.get(jeton)
            if etat is not None:
                etat.depart_id = depart_id

    def depart_de(self, jeton: str | None) -> DepartId | None:
        """Départ courant derrière un jeton valide, ou `None` (jeton inconnu ou départ non fixé)."""
        if not jeton:
            return None
        with self._verrou:
            etat = self._sessions.get(jeton)
        return etat.depart_id if etat is not None else None

    def fermer(self, jeton: str) -> None:
        """Ferme la session (cible **et** départ courant) ; sans effet si le jeton est inconnu."""
        with self._verrou:
            self._sessions.pop(jeton, None)
