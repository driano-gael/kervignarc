"""Anomalies d'un déroulé — **deux gravités**, et la ligne de partage est la contribution de l'US.
**Bloquante** : vraie *quel que soit l'effectif*. **Avertissement** : vraie *à cet effectif-là*
seulement — la bloquer reviendrait à interdire les plages relatives.

⚠️ **Aucune règle n'est recopiée** : une anomalie **porte** l'erreur typée existante, qui a déjà
son code et son message. ADR-0063
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from domain.erreurs import DomainError


class Gravite(str, Enum):
    """Ce qu'une anomalie empêche : appliquer le format, ou seulement rassurer."""

    BLOQUANTE = "bloquante"
    """Vrai à tout effectif — `appliquer` refuse."""

    AVERTISSEMENT = "avertissement"
    """Vrai à cet effectif seulement — le dessin le montre, l'application reste permise."""


@dataclass(frozen=True)
class Anomalie:
    """Un défaut constaté, **localisé** sur la phase qu'il concerne.

    `ordre` vaut `None` quand le défaut porte sur la séquence entière (des ordres non contigus ne
    désignent aucune phase) — c'est ce qui permet au front de coller le défaut sur le bon bloc du
    schéma, comme le CA l'exige. ⚠️ L'erreur est **portée, pas levée** : `Anomalie` n'hérite pas de
    `DomainError` ; les enveloppes font `raise anomalie.erreur`, de sorte que le code HTTP reste
    exactement celui d'avant l'US.
    """

    erreur: DomainError
    ordre: int | None = None
    gravite: Gravite = Gravite.BLOQUANTE

    @property
    def code(self) -> str:
        """Le code stable de l'erreur portée (celui que l'API expose déjà)."""
        return self.erreur.code

    @property
    def message(self) -> str:
        """Le message métier de l'erreur portée — rédigé pour un organisateur, pas pour un log."""
        return self.erreur.message
