"""Adapters d'infrastructure des scoreurs (E10US003) : génération de code + sessions en mémoire.

Le store de sessions réalise le port `application.scoreurs.StoreSessionsScoreur` ; le générateur de
code est injecté tel quel dans `ServiceScoreurs` au composition root. Aucune dépendance externe
(stdlib `secrets`/`threading`).
"""

from infrastructure.scoreurs.codes import ALPHABET_CODE, LONGUEUR_CODE, generer_code_scoreur
from infrastructure.scoreurs.sessions import ScoreurSessionStore

__all__ = [
    "ALPHABET_CODE",
    "LONGUEUR_CODE",
    "ScoreurSessionStore",
    "generer_code_scoreur",
]
