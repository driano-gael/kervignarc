"""Service applicatif d'accès administrateur (E10US002).

L'authentification est un concern **technique**, pas métier : il n'y a donc **pas d'entité
domaine**. Le service orchestre deux adapters, exprimés ici comme **contrats** (Protocols) que
l'application possède et que l'infrastructure implémente (dépendance pointant vers l'intérieur) :

- un **store d'identifiants** (login + mot de passe), persistés dans un fichier `.env` local —
  compromis de sécurité **assumé** pour un outil mono-club LAN (cf. story E10US002) ;
- un **store de sessions** délivrant/validant des **jetons opaques** en mémoire.

Le flux : au 1ᵉʳ accès (aucun identifiant), l'admin **définit** l'accès (`configurer`) ; ensuite
il se **connecte** (`connexion`). Une réussite ouvre une session dont le jeton est joint aux
actions admin. Comparaison des secrets en **temps constant** (`hmac.compare_digest`).
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Protocol

from application.erreurs import (
    AccesDejaConfigure,
    AccesNonConfigure,
    IdentifiantsInvalides,
)


@dataclass(frozen=True)
class IdentifiantsAdmin:
    """Couple login / mot de passe de l'accès administrateur (contrat inter-couches)."""

    login: str
    mot_de_passe: str


class StoreIdentifiantsAdmin(Protocol):
    """Port : lecture/écriture des identifiants admin (implémenté en infrastructure)."""

    def lire(self) -> IdentifiantsAdmin | None:
        """Identifiants configurés, ou `None` si l'accès n'est pas encore défini."""

    def ecrire(self, identifiants: IdentifiantsAdmin) -> None:
        """Persiste (crée ou remplace) les identifiants admin."""


class StoreSessions(Protocol):
    """Port : délivrance et validation de jetons de session admin (en mémoire)."""

    def ouvrir(self) -> str:
        """Ouvre une session et renvoie son jeton opaque."""

    def est_valide(self, jeton: str | None) -> bool:
        """Vrai si le jeton correspond à une session ouverte."""

    def fermer(self, jeton: str) -> None:
        """Ferme la session (déconnexion) ; sans effet si le jeton est inconnu."""


class ServiceAuth:
    """Cas d'usage de l'accès admin : configurer, se connecter, se déconnecter, valider."""

    def __init__(self, identifiants: StoreIdentifiantsAdmin, sessions: StoreSessions) -> None:
        self._identifiants = identifiants
        self._sessions = sessions

    def est_configure(self) -> bool:
        """Vrai si un accès administrateur a déjà été défini."""
        return self._identifiants.lire() is not None

    def configurer(self, login: str, mot_de_passe: str) -> str:
        """Définit l'accès admin au 1ᵉʳ usage et ouvre aussitôt une session (jeton).

        Lève `AccesDejaConfigure` si un accès existe déjà (la modification passe par un autre
        cas d'usage, E10US006), `IdentifiantsInvalides` si login/mot de passe sont vides.
        """
        if self._identifiants.lire() is not None:
            raise AccesDejaConfigure("L'accès administrateur est déjà configuré.")
        identifiants = self._valider(login, mot_de_passe)
        self._identifiants.ecrire(identifiants)
        return self._sessions.ouvrir()

    def connexion(self, login: str, mot_de_passe: str) -> str:
        """Vérifie les identifiants et ouvre une session (jeton).

        Lève `AccesNonConfigure` si aucun accès n'est défini, `IdentifiantsInvalides` si le
        couple login/mot de passe ne correspond pas.
        """
        actuels = self._identifiants.lire()
        if actuels is None:
            raise AccesNonConfigure("Aucun accès administrateur n'est configuré.")
        if not self._correspond(actuels, login, mot_de_passe):
            raise IdentifiantsInvalides("Identifiant ou mot de passe invalide.")
        return self._sessions.ouvrir()

    def deconnexion(self, jeton: str) -> None:
        """Ferme la session associée au jeton."""
        self._sessions.fermer(jeton)

    def session_valide(self, jeton: str | None) -> bool:
        """Vrai si le jeton correspond à une session admin ouverte."""
        return self._sessions.est_valide(jeton)

    @staticmethod
    def _valider(login: str, mot_de_passe: str) -> IdentifiantsAdmin:
        login_net = login.strip()
        if login_net == "" or mot_de_passe == "":
            raise IdentifiantsInvalides("Login et mot de passe sont requis.")
        return IdentifiantsAdmin(login=login_net, mot_de_passe=mot_de_passe)

    @staticmethod
    def _correspond(actuels: IdentifiantsAdmin, login: str, mot_de_passe: str) -> bool:
        # Comparaison en temps constant ; les deux comparaisons sont toujours évaluées.
        login_ok = hmac.compare_digest(actuels.login, login.strip())
        mot_de_passe_ok = hmac.compare_digest(actuels.mot_de_passe, mot_de_passe)
        return login_ok and mot_de_passe_ok
