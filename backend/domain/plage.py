"""La **plage de rangs** — l'intervalle de classement qu'un participant peut encore atteindre.

Value object fondateur du placement intégral (E05US010). La *Règle R* de
[`moteur-placement-lucky-loser.md`](../../moteur-placement-lucky-loser.md) § 4 s'énonce entièrement
en ces termes : un participant engagé sur la plage `[a..b]` passe, selon l'issue de son match, dans
la **moitié haute** `[a..mid]` (gagnants) ou la **moitié basse** `[mid+1..b]` (perdants), jusqu'à
une plage de **largeur 2** où un match terminal fixe les deux rangs (*Règle T*, § 3).

Vit dans son propre module — et non dans `politiques.py` ou `tableau.py` — parce que les deux
l'utilisent : le **routing** décide vers quelle plage descend un perdant, le **tableau** engendre le
sous-groupe correspondant. Le loger dans l'un créerait un cycle d'import avec l'autre.

Domaine **pur** (règle 1) : aucun framework, aucune autre couche.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.erreurs import PlageInvalide


@dataclass(frozen=True)
class Plage:
    """Les rangs `debut..fin` inclus, toujours dans cet ordre et jamais vides.

    Une plage de placement est toujours de **largeur paire** dans un tableau construit (elle naît
    d'une division par deux), mais le value object n'en fait pas un invariant : c'est la structure
    de l'arbre qui le garantit, et une plage impaire reste une donnée lisible (« les rangs 5 à 9 »
    d'un peuplement par rangs). Le seul invariant porté ici est l'**ordre**.
    """

    debut: int
    fin: int

    def __post_init__(self) -> None:
        if self.debut < 1:
            raise PlageInvalide(f"Un rang commence à 1 (reçu {self.debut}).")
        if self.fin < self.debut:
            raise PlageInvalide(
                f"La plage {self.debut}-{self.fin} est vide : la fin précède le début."
            )

    @property
    def largeur(self) -> int:
        """Le nombre de rangs couverts (`[5..8]` → 4)."""
        return self.fin - self.debut + 1

    @property
    def est_terminale(self) -> bool:
        """Deux rangs restants : le prochain match les départage définitivement (*Règle T*)."""
        return self.largeur == 2

    @property
    def paire_terminale(self) -> tuple[int, int]:
        """Les deux rangs en jeu d'une plage terminale — `(gagnant, perdant)` par la *Règle T*."""
        if not self.est_terminale:
            raise PlageInvalide(
                f"La plage {self.debut}-{self.fin} n'est pas terminale (largeur {self.largeur})."
            )
        return (self.debut, self.fin)

    def moitie_haute(self) -> Plage:
        """La moitié où passent les **gagnants** (*Règle R*)."""
        return Plage(self.debut, self.debut + self._demi_largeur() - 1)

    def moitie_basse(self) -> Plage:
        """La moitié où descendent les **perdants** (*Règle R*)."""
        return Plage(self.debut + self._demi_largeur(), self.fin)

    def contient(self, rang: int) -> bool:
        """Ce rang tombe-t-il dans la plage ?"""
        return self.debut <= rang <= self.fin

    def _demi_largeur(self) -> int:
        """La demi-largeur, en refusant de diviser une plage déjà terminale.

        Diviser `[7..8]` n'a pas de sens : le match qui s'y joue **est** le match terminal. Laisser
        la division silencieuse produirait deux plages de largeur 1 et une récursion sans fin.
        """
        if self.largeur < 4:
            raise PlageInvalide(
                f"La plage {self.debut}-{self.fin} (largeur {self.largeur}) ne se divise plus : "
                "une plage terminale se joue, elle ne se subdivise pas."
            )
        return self.largeur // 2
