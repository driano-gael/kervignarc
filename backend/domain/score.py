"""Agrégat `Score` — une flèche marquée par un archer (tranche verticale E00US011).

Modèle minimal du walking skeleton : une **valeur de flèche** (0 à 10 ; le « 10 » couvre
le 10 et le X). Le scoring réel (volées, barème configurable, sets de duel) viendra en E04/E05 ;
ici on ne persiste qu'un point marqué, cumulé par le calcul de classement.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.archer import ArcherId
from domain.erreurs import ScoreInvalide

ScoreId = int
"""Identifiant technique d'un score, attribué par la persistance."""

POINTS_MIN = 0
POINTS_MAX = 10


@dataclass(frozen=True)
class Score:
    """Une flèche marquée par un archer. `id` vaut `None` tant qu'il n'est pas persisté."""

    archer_id: ArcherId
    points: int
    id: ScoreId | None = None

    @staticmethod
    def creer(archer_id: ArcherId, points: int) -> Score:
        """Crée un score valide ; lève `ScoreInvalide` hors de la plage 0-10."""
        if not POINTS_MIN <= points <= POINTS_MAX:
            raise ScoreInvalide(
                f"Un score de flèche doit être compris entre {POINTS_MIN} et {POINTS_MAX}."
            )
        return Score(archer_id=archer_id, points=points)
