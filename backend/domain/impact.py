"""Graduation de l'**alerte d'impact** — quel niveau mérite quel geste (ADR-0040).

Ce module ne porte que la règle ; le **comptage** lit des repositories et vit au service.

⚠️ **`NiveauImpact` est générique, `ImpactRegeneration` est spécifique au placement** : on
n'abstrait pas un `CalculateurImpact` avant la 3ᵉ action réelle (remède structurel sur preuve).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class NiveauImpact(str, Enum):
    """Gravité d'une écriture — l'échelle transverse de l'alerte par calcul d'impact.

    `(str, Enum)` : la valeur est un slug stable, sérialisable tel quel à la frontière API (comme
    `StatutTournoi`, `RaisonConflit`). Trois crans, du plus anodin au plus lourd :

    - `AUCUN` : rien de réel n'est touché → **aucune alerte**, l'action passe directement ;
    - `CONFIRMATION` : impact réel mais **réversible** → alerte chiffrée, confirmation par un
    bouton ;
    - `MASSIF` : des **données réelles produites** sont en jeu → **geste délibéré** (taper un mot)
    et
      **trace d'audit**. « Une alerte qui ne chiffre pas son impact est un clic de plus » (`P-4`).
    """

    AUCUN = "aucun"
    CONFIRMATION = "confirmation"
    MASSIF = "massif"


@dataclass(frozen=True)
class ImpactRegeneration:
    """Impact chiffré de **régénérer le plan de cibles** d'un départ (écrase le placement courant).

    - `archers_deplaces` : combien d'archers sont actuellement placés — tous seront re-brassés par
    le
      glouton déterministe (« 156 archers perdront leur place ») ;
    - `cibles_avec_scores` : combien de cibles du plan courant ont **au moins un archer avec une
      série** — leurs scores sont **conservés** (la régénération ne réécrit que le placement, pas
      les
      séries), mais leur présence marque des **données réelles** et fait basculer en massif.

    Immuable (règle 4) : une photo de l'impact au moment du calcul, jamais mutée après coup.
    """

    archers_deplaces: int
    cibles_avec_scores: int

    @property
    def niveau(self) -> NiveauImpact:
        """Dérive le niveau d'alerte (la règle métier du CA).

        Aucun archer placé → `AUCUN` (première génération, rien à écraser). Sinon, la présence de
        **scores** — pas le seul volume d'archers — départage : au moins une cible avec score →
        `MASSIF` (données réelles) ; aucune → `CONFIRMATION` (placement réversible, ADR-0024).
        """
        if self.archers_deplaces == 0:
            return NiveauImpact.AUCUN
        if self.cibles_avec_scores > 0:
            return NiveauImpact.MASSIF
        return NiveauImpact.CONFIRMATION
