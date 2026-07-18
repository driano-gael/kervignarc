"""Adapter : jetons de session scoreur **nominatifs** en mémoire (E10US003).

Réalise le port `application.scoreurs.StoreSessionsScoreur`. Jetons **opaques**
(`secrets.token_urlsafe`), conservés dans un dictionnaire `jeton → scoreur_id` protégé par un
verrou (lectures/écritures peuvent venir de threads du threadpool). Le lien vers l'identité du
scoreur — ce qui distingue ce store du `SessionStore` admin, un simple ensemble de jetons anonymes —
sert à **purger** les jetons d'un scoreur supprimé et, plus tard, à tracer la validation (E10US005).

**Sans expiration**, comme la session admin, et pour la même raison renforcée : le CA veut un jeton
qui « survit à la fermeture de l'onglet » le temps d'une journée de tournoi ; l'admin, plus
puissant, n'expire pas — le scoreur, moins, ne le ferait pas davantage. Les sessions sont invalidées
au **redémarrage** du serveur (mémoire volontairement volatile), à la **déconnexion**, ou à la
**suppression** du scoreur.
"""

from __future__ import annotations

import secrets
import threading

from domain.scoreur import ScoreurId


class ScoreurSessionStore:
    """Sessions scoreur ouvertes, indexées par jeton opaque → identité du scoreur."""

    def __init__(self) -> None:
        self._sessions: dict[str, ScoreurId] = {}
        self._verrou = threading.Lock()

    def ouvrir(self, scoreur_id: ScoreurId) -> str:
        """Ouvre une session pour un scoreur et renvoie son jeton opaque."""
        jeton = secrets.token_urlsafe(32)
        with self._verrou:
            self._sessions[jeton] = scoreur_id
        return jeton

    def scoreur_de(self, jeton: str | None) -> ScoreurId | None:
        """Identifiant du scoreur derrière un jeton (non vide) valide, ou `None`."""
        if not jeton:
            return None
        with self._verrou:
            return self._sessions.get(jeton)

    def fermer(self, jeton: str) -> None:
        """Ferme la session ; sans effet si le jeton est inconnu."""
        with self._verrou:
            self._sessions.pop(jeton, None)

    def invalider_scoreur(self, scoreur_id: ScoreurId) -> None:
        """Ferme **toutes** les sessions d'un scoreur (à sa suppression)."""
        with self._verrou:
            for jeton in [j for j, sid in self._sessions.items() if sid == scoreur_id]:
                del self._sessions[jeton]
