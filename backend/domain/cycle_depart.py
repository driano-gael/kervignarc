"""Graduation de l'état d'un départ — **dérivé, jamais saisi** (E12US008).

`Depart` reste un agrégat figé, sans colonne de statut. Ce module ne porte que la règle de
graduation ; le **comptage** lit des repositories, il vit donc au service.

⚠️ **Ce qui fait basculer *ouvert → lancé* est la présence d'un SCORE, pas l'heure** : `horaire` est
un libellé libre, pas une heure comparable — « heure atteinte » n'est pas dérivable (ADR-0018).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EtatDepart(str, Enum):
    """État de cycle de vie d'un départ — l'échelle du garde-fou d'édition d'un créneau.

    `(str, Enum)` : slug stable, sérialisable tel quel à la frontière API. Trois crans : `OUVERT`
    (rien de réel n'a été tiré → **librement éditable**, comportement E02US009), `LANCE` (session
    de tir en cours → édition/suppression **confirmées**), `CLOS` (session finie → mêmes garde-fous
    que `LANCE`).
    """

    OUVERT = "ouvert"
    LANCE = "lance"
    CLOS = "clos"


@dataclass(frozen=True)
class AvancementDepart:
    """Décomptes d'un créneau à un instant donné, d'où l'on dérive son `EtatDepart`.

    `nb_places` : archers **placés** ; `nb_ayant_tire` : ceux ayant **au moins une flèche validée**
    ; `nb_series_closes` : ceux dont la série est close — barème validé **ou** forfait (E04US015,
    même notion que `ServiceCompletude._serie_close`). Immuable (règle 4) : une photo de
    l'avancement au moment du calcul, jamais mutée après coup.
    """

    nb_places: int
    nb_ayant_tire: int
    nb_series_closes: int

    @property
    def etat(self) -> EtatDepart:
        """Dérive l'état de cycle de vie (la règle métier du CA).

        L'échelle s'appuie sur un **tir réel** : sans flèche consignée le créneau est `OUVERT`, y
        compris si des séries sont « closes » par forfait — rien à protéger, et l'échelle reste
        **monotone** (on ne saute pas *ouvert → clos*). Une fois qu'on a tiré : `CLOS` si
        **toutes** les séries des archers placés sont closes, `LANCE` sinon.
        """
        if self.nb_ayant_tire == 0:
            return EtatDepart.OUVERT
        if self.nb_places > 0 and self.nb_series_closes == self.nb_places:
            return EtatDepart.CLOS
        return EtatDepart.LANCE
