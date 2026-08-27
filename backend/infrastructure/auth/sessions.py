"""Adapter : jetons de session admin en mémoire (E10US002).

Jetons opaques (`secrets.token_urlsafe`) dans un ensemble sous verrou — les accès viennent
des threads du threadpool. Invalidés au redémarrage du serveur, ou à la déconnexion.

⚠️ **Sans expiration**, délibérément (E10US003 a tranché de même pour le scoreur) : un jeton
doit survivre à la fermeture de l'onglet, le temps d'une journée de tournoi.
"""

from __future__ import annotations

import secrets
import threading


class SessionStore:
    """Ensemble en mémoire des jetons de session admin ouverts."""

    def __init__(self) -> None:
        self._jetons: set[str] = set()
        self._verrou = threading.Lock()

    def ouvrir(self) -> str:
        """Ouvre une session et renvoie son jeton opaque."""
        jeton = secrets.token_urlsafe(32)
        with self._verrou:
            self._jetons.add(jeton)
        return jeton

    def est_valide(self, jeton: str | None) -> bool:
        """Vrai si le jeton (non vide) correspond à une session ouverte."""
        if not jeton:
            return False
        with self._verrou:
            return jeton in self._jetons

    def fermer(self, jeton: str) -> None:
        """Ferme la session ; sans effet si le jeton est inconnu."""
        with self._verrou:
            self._jetons.discard(jeton)
