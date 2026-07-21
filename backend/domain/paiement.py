"""Récapitulatif de paiement — dû / payé / reste (E08US002).

Le **fait** de paiement est stocké au plus bas niveau : le booléen `paye` d'une `Inscription` (un
archer sur un départ). Tout ce qui est *au-dessus* — combien un archer doit, a réglé, reste à payer,
et les mêmes totaux agrégés par club — se **dérive** de ces booléens et des tarifs des créneaux, à
la
lecture. Rien de nouveau n'est stocké (comme le montant dû d'E08US001, ADR-0017).

Ce module porte la **règle de calcul** de cette dérivation, pure et testable depuis le CA :

- **dû** = somme des tarifs des créneaux inscrits ;
- **payé** = somme des tarifs des créneaux **marqués payés** ;
- **reste** = dû - payé.

Le `reste` est une **propriété**, jamais un champ : un dû et un payé ne peuvent pas se contredire
avec leur reste s'il n'existe pas de troisième valeur à désynchroniser. Par construction (le payé
n'additionne que des tarifs qui figurent déjà dans le dû), `0 ≤ payé ≤ dû`, donc `reste ≥ 0` — c'est
une conséquence du calcul, pas une garde à poser.

Pur et synchrone (règle 1) : aucun import de framework ni d'autre couche.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class RecapPaiement:
    """Dû, payé et reste (en **centimes entiers**) d'un périmètre — un archer, un club, un tournoi.

    `du_centimes` et `paye_centimes` sont les deux seules valeurs stockées dans l'objet ; `reste`
    s'en déduit. Immuable (règle 4).
    """

    du_centimes: int
    paye_centimes: int

    @property
    def reste_centimes(self) -> int:
        """Reste à payer = dû - payé (jamais négatif : le payé n'agrège que des tarifs dus)."""
        return self.du_centimes - self.paye_centimes


def recapituler(lignes: Iterable[tuple[int, bool]]) -> RecapPaiement:
    """Récapitule un ensemble de `(tarif_centimes, paye)` en un `RecapPaiement`.

    `dû` additionne **tous** les tarifs ; `payé` n'additionne que ceux des lignes payées. Une entrée
    vide donne `0 / 0 / 0` (un archer sans inscription ne doit rien — il n'est pas une erreur).
    """
    du = 0
    paye = 0
    for tarif_centimes, est_paye in lignes:
        du += tarif_centimes
        if est_paye:
            paye += tarif_centimes
    return RecapPaiement(du_centimes=du, paye_centimes=paye)


def total(recaps: Iterable[RecapPaiement]) -> RecapPaiement:
    """Somme champ à champ de plusieurs `RecapPaiement` — le total d'un club, d'un tournoi.

    Le total d'un club est la somme des récapitulatifs de ses archers ; celui d'un tournoi, la somme
    de ceux de ses clubs. Une entrée vide donne `0 / 0 / 0`.
    """
    du = 0
    paye = 0
    for recap in recaps:
        du += recap.du_centimes
        paye += recap.paye_centimes
    return RecapPaiement(du_centimes=du, paye_centimes=paye)
