"""Cycle de vie d'un **départ** (créneau) — value object **pur** `AvancementDepart` (E12US008).

Un départ (créneau horaire, cf. `domain.depart`) traverse trois états au fil de la journée :

- **ouvert** : aucun score n'y a encore été consigné → il se modifie et se supprime librement,
  exactement comme avant (E02US009 / ADR-0018) ;
- **lancé** : au moins une flèche y a été consignée, mais toutes les séries ne sont pas closes → une
  **session de tir est en cours**, l'éditer ou le supprimer doit être **confirmé** (E12US008) ;
- **clos** : toutes les séries des archers placés sont closes (barème validé **ou** forfait) → la
  session est finie, mêmes garde-fous que *lancé*.

**L'état est dérivé, jamais saisi** (CA E12US008) : `Depart` reste un agrégat figé sans colonne de
statut (règle 4). Ce module ne porte que la **règle de graduation** — *quels décomptes* donnent
*quel état* — comme `domain.impact` porte la graduation de l'alerte. Le **comptage** (combien
d'archers placés, combien ont tiré, combien de séries closes) est de l'orchestration : il lit des
repositories, il vit donc dans le service applicatif (`application/completude.py`), pas ici
(règle 1, domaine pur et synchrone).

Le fait réel qui fait basculer *ouvert → lancé* est la **présence d'un score** (`nb_ayant_tire`),
pas l'heure du créneau : `Depart.horaire` est un libellé libre (« 9h00 »), pas une heure comparable
— « heure atteinte » n'est donc pas dérivable d'un fait réel sans re-modéliser l'horaire, hors
périmètre de cette US (arbitrage reversé dans `stories/`, E12US008).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EtatDepart(str, Enum):
    """État de cycle de vie d'un départ — l'échelle du garde-fou d'édition d'un créneau.

    `(str, Enum)` : la valeur est un slug stable, sérialisable tel quel à la frontière API (comme
    `StatutTournoi`, `NiveauImpact`). Trois crans, du plus anodin au plus engageant :

    - `OUVERT` : rien de réel n'a été tiré → **librement éditable** (comportement E02US009) ;
    - `LANCE` : une session de tir est **en cours** → édition/suppression **confirmées** ;
    - `CLOS` : la session est **finie** → mêmes garde-fous que `LANCE`.
    """

    OUVERT = "ouvert"
    LANCE = "lance"
    CLOS = "clos"


@dataclass(frozen=True)
class AvancementDepart:
    """Décomptes d'un créneau à un instant donné, d'où l'on dérive son `EtatDepart`.

    - `nb_places` : combien d'archers sont **placés** dans le créneau (affectés à une cible) ;
    - `nb_ayant_tire` : combien d'entre eux ont **au moins une flèche validée** (un score réel) ;
    - `nb_series_closes` : combien ont leur série **close** — barème validé **ou** forfait
      (E04US015, même notion que `ServiceCompletude._serie_close`).

    Immuable (règle 4) : une photo de l'avancement au moment du calcul, jamais mutée après coup.
    """

    nb_places: int
    nb_ayant_tire: int
    nb_series_closes: int

    @property
    def etat(self) -> EtatDepart:
        """Dérive l'état de cycle de vie (la règle métier du CA).

        L'échelle s'appuie sur un **tir réel** : sans aucune flèche consignée, le créneau est
        `OUVERT` — y compris le cas dégénéré où des séries seraient « closes » par forfait sans
        qu'on ait tiré (rien à protéger, et l'échelle reste **monotone** : on ne saute pas
        *ouvert → clos*). Une fois qu'on a tiré, le créneau est `CLOS` si **toutes** les séries des
        archers placés sont closes, `LANCE` sinon (une seule série non close suffit à le maintenir
        lancé).
        """
        if self.nb_ayant_tire == 0:
            return EtatDepart.OUVERT
        if self.nb_places > 0 and self.nb_series_closes == self.nb_places:
            return EtatDepart.CLOS
        return EtatDepart.LANCE
