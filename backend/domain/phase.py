"""Agrégat `Phase` — une étape d'un tournoi (introduction **minimale**, E01US009 / ADR-0011).

Le modèle cible (ADR-0004) fait de la phase le porteur des **politiques injectables** du moteur
(routage, barème, seeding, byes, départage, profondeur), stockées dans sa `config`. Ce moteur
relève d'EPIC-05 ; E01US009 n'introduit que ce qu'il faut pour héberger le **barème de
qualification** là où le modèle de données l'attend : une phase de type `qualification` par
tournoi, portant un `BaremeQualification` (sérialisé dans `config.scoring`).

Périmètre volontairement réduit (cf. ADR-0011) : `ordre` et `statut` sont conformes au modèle de
données mais **passifs** (aucune transition, aucune séquence) — le moteur les exploitera. Agrégat
de domaine **pur** (immuable, sans dépendance framework).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from domain.bareme import BaremeQualification
from domain.tournoi import TournoiId

PhaseId = int
"""Identifiant technique d'une phase, attribué par la persistance."""


class TypePhase(str, Enum):
    """Type d'une phase. E01US009 n'utilise que `qualification` ; le moteur (EPIC-05) ajoutera
    les autres (barrage, tableau, placement, finale, big_shoot_off)."""

    QUALIFICATION = "qualification"


class StatutPhase(str, Enum):
    """Cycle de vie d'une phase (modèle de données). Passif en E01US009 : aucune transition n'est
    encore définie (elles viendront avec le moteur, EPIC-05)."""

    A_VENIR = "a_venir"
    EN_COURS = "en_cours"
    TERMINEE = "terminee"


@dataclass(frozen=True)
class Phase:
    """Une phase d'un tournoi. `id` vaut `None` tant qu'elle n'est pas persistée.

    En E01US009, seules des phases `qualification` existent ; `bareme` porte alors le barème de
    qualification. `ordre` (position dans la future séquence) et `statut` sont conformes au modèle
    cible mais non encore exploités (ADR-0011).
    """

    tournoi_id: TournoiId
    ordre: int
    type: TypePhase
    bareme: BaremeQualification
    statut: StatutPhase = StatutPhase.A_VENIR
    id: PhaseId | None = None

    @staticmethod
    def qualification(tournoi_id: TournoiId, bareme: BaremeQualification) -> Phase:
        """Crée la phase de **qualification** d'un tournoi (première de la séquence, `ordre=1`)."""
        return Phase(
            tournoi_id=tournoi_id,
            ordre=1,
            type=TypePhase.QUALIFICATION,
            bareme=bareme,
            statut=StatutPhase.A_VENIR,
        )

    def avec_bareme(self, bareme: BaremeQualification) -> Phase:
        """Renvoie une copie au barème mis à jour ; `id`, `tournoi_id`, `ordre` et `statut` sont
        préservés."""
        return replace(self, bareme=bareme)
