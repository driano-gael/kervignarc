"""Calcul d'impact d'une écriture (E12US007, [ADR-0040]) — value objects **purs**.

L'appli ne demande confirmation **que quand ça compte** (`P-4`, `D-16`) : elle calcule l'impact
**réel** au moment où on agit, elle ne classe pas les actions d'avance. La **ligne de partage**
n'est
ni *brouillon / en cours*, ni *sportif / tiers*, mais : **est-ce que ça a déjà produit des données
réelles ?** ([CDC UX §9.1](../../cahier-des-charges-ux.md)).

Ce module ne porte que la **règle métier** de graduation — *quel* niveau d'alerte mérite *quel*
geste. Le **comptage** (combien d'archers, combien de cibles ont des scores) est de
l'orchestration :
il lit des repositories, il vit donc dans le service applicatif (`application/placement.py`), pas
ici
(règle 1, domaine pur et synchrone).

**Périmètre E12US007 (scope A, ADR-0040)** : la seule action câblée est la **régénération du plan de
cibles** (le cas « REPLACER » du CDC). `NiveauImpact` — l'échelle — est **générique** et se
réutilisera ; `ImpactRegeneration` — le calcul — est **spécifique** au placement. On n'abstrait pas
un `CalculateurImpact` avant la 3ᵉ action réelle (règle « remède structurel sur preuve »).

[ADR-0040]: ../../docs/adr/0040-alerte-par-calcul-d-impact.md
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
