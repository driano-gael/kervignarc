"""Une **anomalie** : un défaut de composition *rendu* au lieu d'être levé (E01US024, ADR-0063).

Jusqu'ici le domaine n'avait qu'un mode de signalement — l'exception. C'était suffisant tant qu'un
format ne s'écrivait que valide : la construction refusait, l'appelant corrigeait. Le CA d'E01US024
demande l'inverse — « *on doit pouvoir sauvegarder le brouillon tout le temps* » — et donc un mode
où l'on **énumère** les défauts au lieu de s'arrêter au premier.

**Aucune règle n'est recopiée pour autant** : une anomalie *porte* l'erreur typée existante
(`SourceApresPhase`, `PhaseQualificationIncomplete`…), qui porte déjà son `code` et son message.
C'est ce qui évite la duplication d'invariant que le registre de dette proscrit : les versions
levantes (`verifier_sequence`, `verifier_coherence_etape`) deviennent de minces enveloppes qui
lèvent la première anomalie produite.

**Deux gravités**, et la ligne de partage est la contribution de conception de l'US :

- **bloquante** — le défaut est vrai *quel que soit l'effectif* (une source postérieure, un ordre en
  doublon, une qualification sans barème). Il interdit d'appliquer le format à un tournoi.
- **avertissement** — le défaut n'est vrai qu'*à cet effectif-là* (« les rangs 33 à 120 » sur 82
  inscrits). Le format n'est pas faux : il ne tient pas *ici*. Le bloquer reviendrait à interdire
  les plages relatives, que le CA d'E05US010 demande précisément.
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
    désignent aucune phase en particulier) — c'est ce qui permet au front de coller le défaut sur le
    bon bloc du schéma plutôt que de l'afficher en message abstrait, comme le CA l'exige.

    L'erreur est **portée**, pas levée : `Anomalie` n'hérite pas de `DomainError` et ne se `raise`
    pas. Les enveloppes levantes font `raise anomalie.erreur`, de sorte que le type d'exception vu
    par l'API — et donc son code HTTP — reste **exactement** celui d'avant l'US.
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
