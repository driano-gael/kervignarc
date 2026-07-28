"""Génération de scores plausibles pour le bot de simulation (E15US003, ADR-0055 §4).

Stratégie **injectable** (règle 1/2) qui fabrique des volées vraisemblables pour le pilote
automatique : à partir des **zones légales** d'un blason, d'un nombre de flèches et d'un **niveau**
d'archer, elle tire une volée en favorisant le centre d'autant plus que l'archer est fort. Le but
n'est **pas** la fidélité statistique au tir réel (ce n'est pas une règle FFTA — c'est de
l'outillage de démo, comme `ServiceJeuEssai` d'E15US001), mais un déroulé **lisible** où les totaux
**s'étalent** pour que le classement ait du sens.

**Déterminisme (règle 9).** Toute l'aléa passe par un `random.Random` **injecté** (issu de la graine
de la session) — jamais le module `random` global. Même graine ⇒ même déroulé ⇒ tests
reproductibles.

**Application, pas domaine.** « Un score plausible » n'est pas un invariant métier : la stratégie
vit au niveau applicatif, injectée à la composition root (règle 8), substituable sans toucher au
domaine.
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
