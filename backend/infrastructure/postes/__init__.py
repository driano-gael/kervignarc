"""Adapters d'infrastructure des postes (E04US001) : génération de code + sessions en mémoire.

Le store de sessions réalise le port `application.postes.StoreSessionsPoste` ; le générateur de code
est injecté tel quel dans `ServicePostes` au composition root. Aucune dépendance externe (stdlib
`secrets`/`threading`).
"""

from infrastructure.postes.codes import ALPHABET_CODE, LONGUEUR_CODE, generer_code_poste
from infrastructure.postes.consignes import RegistreConsignesMemoire
from infrastructure.postes.presence import RegistrePresenceMemoire
from infrastructure.postes.sessions import PosteSessionStore

__all__ = [
    "ALPHABET_CODE",
    "LONGUEUR_CODE",
    "PosteSessionStore",
    "RegistreConsignesMemoire",
    "RegistrePresenceMemoire",
    "generer_code_poste",
]
