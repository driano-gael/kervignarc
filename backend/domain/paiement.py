"""Règle de calcul du paiement — **dérivée**, jamais stockée.

dû = somme des tarifs inscrits ; payé = somme des tarifs marqués payés ; reste = dû - payé.

⚠️ **Le `reste` est une PROPRIÉTÉ, jamais un champ** : un dû et un payé ne peuvent pas contredire
leur reste s'il n'existe aucune troisième valeur à désynchroniser. `reste ≥ 0` est une conséquence
du calcul, pas une garde à poser. ADR-0017
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
