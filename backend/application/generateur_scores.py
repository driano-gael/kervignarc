"""Générateur de scores plausibles pour la démo — pas de fidélité statistique visée, mais un
déroulé **lisible** où les totaux s'étalent, pour que le classement ait du sens.

⚠️ **Toute l'aléa passe par un `random.Random` INJECTÉ**, jamais le module global : même graine,
même déroulé, tests reproductibles (règle 9). « Un score plausible » n'étant pas un invariant
métier, la stratégie vit au niveau applicatif, substituable sans toucher au domaine. ADR-0055
"""

from __future__ import annotations

import random
from typing import Protocol

from domain.blason import ZoneScore

# Amplitude de l'effet du niveau sur la préférence pour le centre : un exposant de poids qui va de
# `_EXPOSANT_BASE` (débutant, tir dispersé) à `_EXPOSANT_BASE + _EXPOSANT_NIVEAU` (expert, tir
# groupé au centre). Valeurs choisies pour un étalement net des totaux sans écraser la variété.
_EXPOSANT_BASE = 1.0
_EXPOSANT_NIVEAU = 3.0


def valeur_zone(zone: ZoneScore) -> int:
    """Points d'une zone : sa valeur numérique, le manqué (`M`) valant 0.

    Duplique délibérément `domain.serie._points_zone` (privé) plutôt que d'exposer ce dernier : deux
    lignes triviales, 2ᵉ occurrence — la règle 16 tranche « dupliquer et attendre le 3ᵉ cas ».
    """
    return 0 if zone is ZoneScore.MANQUE else int(zone.value)


class GenerateurScores(Protocol):
    """Port applicatif : produire une volée plausible de `nb_fleches` flèches dans `zones`.

    `niveau` ∈ [0, 1] gradue la force de l'archer (0 = débutant, 1 = expert) ; `alea` est le
    générateur pseudo-aléatoire **injecté** (déterminisme, règle 9). Renvoie les **valeurs** des
    flèches (l'appelant les emballe en `Volee` validée) — la stratégie ignore la validation.
    """

    def volee(
        self,
        zones: tuple[ZoneScore, ...],
        nb_fleches: int,
        niveau: float,
        alea: random.Random,
    ) -> tuple[ZoneScore, ...]: ...


class GenerateurScoresPlausibles:
    """Implémentation par défaut : tir pondéré vers le centre, modulé par le niveau de l'archer."""

    def volee(
        self,
        zones: tuple[ZoneScore, ...],
        nb_fleches: int,
        niveau: float,
        alea: random.Random,
    ) -> tuple[ZoneScore, ...]:
        """Tire `nb_fleches` flèches indépendantes parmi `zones`, pondérées par `_poids`."""
        poids = [self._poids(zone, niveau) for zone in zones]
        # `choices` tire **avec remise** (plusieurs flèches peuvent tomber dans la même zone) — le
        # comportement voulu : une volée réelle groupe souvent au centre.
        tirees = alea.choices(zones, weights=poids, k=nb_fleches)
        return tuple(tirees)

    def _poids(self, zone: ZoneScore, niveau: float) -> float:
        """Poids d'une zone : croît avec sa valeur, d'autant plus vite que l'archer est fort.

        `(valeur + 1) ** exposant` : le `+ 1` évite un poids nul pour le manqué (il reste possible,
        rare) ; l'exposant, fonction croissante du `niveau`, concentre le tir des experts sur les
        hautes valeurs tout en laissant les débutants disperser.
        """
        exposant = _EXPOSANT_BASE + _EXPOSANT_NIVEAU * max(0.0, min(1.0, niveau))
        return float((valeur_zone(zone) + 1) ** exposant)
