"""Participant d'un duel (E13US001, ADR-0028) — l'abstraction sur laquelle le moteur oppose.

Un tournoi oppose des **archers** (épreuve individuelle) ou des **équipes** (épreuve par équipes,
FFTA §6.3/§7). Pour que le moteur de duels (E05US005+) n'ait **aucune branche `if équipe`**
(ADR-0028, décision n°3), il ne connaît ni l'un ni l'autre : il oppose des `Participant`, une
identité **opaque** qu'il compare et place au podium sans jamais l'interpréter.

La résolution `Participant → {archer | équipe}` (nom à afficher, cible, membres) vit dans une couche
**haute** (classement, saisie E04US013, écrans) — jamais dans le moteur. C'est la « porte » qu'a
franchie ADR-0028 : un moteur pensé « participants » fait de l'ajout des équipes (E13US002+) une
**réalisation**, pas une refonte.

**Portée E13US001.** Ce module livre l'abstraction et ses deux formes (individuel / équipe).
L'entité `Equipe` (composition, CRUD) est E13US002 ; le moteur qui consomme les `Participant` est
E05US005. Value object **pur** et immuable (règles 1 et 4).
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
