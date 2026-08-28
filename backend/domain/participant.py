"""Value object **Participant** — individuel ou équipe, traité de façon opaque par le moteur.

La résolution `Participant → {archer | équipe}` vit en couche **haute**, jamais dans le moteur.

⚠️ **C'est la porte qu'ADR-0028 a franchie** : un moteur pensé « participants » fait de l'ajout des
équipes une **réalisation**, pas une refonte. L'entité `Equipe` n'existe pas encore.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class GenreParticipant(str, Enum):
    """Ce qu'un participant *est* — connu des couches hautes, **ignoré** du moteur (ADR-0028)."""

    INDIVIDUEL = "individuel"  # un archer
    EQUIPE = "equipe"  # une équipe (E13US002)


@dataclass(frozen=True)
class Participant:
    """Qui s'oppose dans un duel : un archer (individuel) **ou** une équipe, de façon opaque.

    Le moteur ne lit **que** l'identité (`genre` + `ref_id`) pour comparer deux participants et les
    reporter dans l'arbre — jamais pour décider d'un comportement. `ref_id` désigne l'archer
    (`ArcherId`) en individuel, l'équipe (`EquipeId`, E13US002) en équipe. Deux participants sont
    **égaux** ssi même genre **et** même référence (égalité de dataclass `frozen`) : c'est ce qui
    permet au moteur de reconnaître un vainqueur parmi les deux camps d'un match.
    """

    genre: GenreParticipant
    ref_id: int

    @staticmethod
    def individuel(archer_id: int) -> Participant:
        """Participant d'un tournoi **individuel** : un archer *est* un participant (ADR-0028)."""
        return Participant(GenreParticipant.INDIVIDUEL, archer_id)

    @staticmethod
    def equipe(equipe_id: int) -> Participant:
        """Le participant d'une épreuve **par équipes** (E13US002 en composera les membres)."""
        return Participant(GenreParticipant.EQUIPE, equipe_id)
