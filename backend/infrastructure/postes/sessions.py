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

from domain.poste import PosteId


class PosteSessionStore:
    """Sessions de poste ouvertes, indexées par jeton opaque → identité de la cible (poste)."""

    def __init__(self) -> None:
        self._sessions: dict[str, PosteId] = {}
        self._verrou = threading.Lock()

    def ouvrir(self, poste_id: PosteId) -> str:
        """Ouvre une session pour un poste et renvoie son jeton opaque."""
        jeton = secrets.token_urlsafe(32)
        with self._verrou:
            self._sessions[jeton] = poste_id
        return jeton

    def poste_de(self, jeton: str | None) -> PosteId | None:
        """Identifiant du poste derrière un jeton (non vide) valide, ou `None`."""
        if not jeton:
            return None
        with self._verrou:
            return self._sessions.get(jeton)

    def fermer(self, jeton: str) -> None:
        """Ferme la session ; sans effet si le jeton est inconnu."""
        with self._verrou:
            self._sessions.pop(jeton, None)
