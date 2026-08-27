"""Grain de validation — la validation est un acte **de fin** (CDC UX §7.3). L'article B.6.1.2
(« scores toutes les 2 volées ») porte sur le **cumul**, pas sur la validation par un tiers.

⚠️ **Le grain dimensionne la charge des scoreurs** : à 3 scoreurs pour 30 cibles, valider toutes
les 2 volées fait ~180 passages par départ — une toutes les 40 s, intenable — contre ~60 en fin de
série.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from domain.erreurs import NombreVoleesParValidationInvalide, NombreVoleesParValidationManquant


class TypeGrain(str, Enum):
    """Les trois grains de validation (`D-11`).

    `FIN_DE_DUEL` n'a de sens que pour une phase à duels (élimination directe) : il est déclaré ici
    parce qu'il fait partie du choix cible, mais aucune phase d'E01US015 ne l'accepte encore (seule
    la `qualification` existe, ADR-0011) — c'est `Phase` qui arbitre la compatibilité.
    """

    FIN_DE_SERIE = "fin_de_serie"
    FIN_DE_DUEL = "fin_de_duel"
    TOUTES_LES_N_VOLEES = "toutes_les_n_volees"


@dataclass(frozen=True)
class GrainValidation:
    """Grain de validation d'une phase : un `type`, et un `n_volees` **si et seulement si** le type
    est `TOUTES_LES_N_VOLEES`.

    Pour les grains `FIN_DE_SERIE` et `FIN_DE_DUEL`, `n_volees` vaut `None` : la cadence découle du
    déroulé de l'épreuve, pas d'un compteur.
    """

    type: TypeGrain
    n_volees: int | None = None

    @staticmethod
    def fin_de_serie() -> GrainValidation:
        """Validation à la **fin de la série** — le preset de la qualification (`D-11`)."""
        return GrainValidation(type=TypeGrain.FIN_DE_SERIE)

    @staticmethod
    def fin_de_duel() -> GrainValidation:
        """Validation à la **fin du duel** — le preset de l'élimination directe (`D-11`)."""
        return GrainValidation(type=TypeGrain.FIN_DE_DUEL)

    @staticmethod
    def toutes_les_n_volees(n_volees: int) -> GrainValidation:
        """Validation **toutes les `n_volees` volées** ; `n_volees` doit être un entier `>= 1`.

        Lève `NombreVoleesParValidationInvalide` si la cadence est inférieure à 1.
        """
        if n_volees < 1:
            raise NombreVoleesParValidationInvalide(
                "Une validation toutes les N volées suppose au moins une volée."
            )
        return GrainValidation(type=TypeGrain.TOUTES_LES_N_VOLEES, n_volees=n_volees)

    @staticmethod
    def creer(type_grain: TypeGrain, n_volees: int | None = None) -> GrainValidation:
        """Crée un grain valide à partir de son type et, pour `TOUTES_LES_N_VOLEES`, de sa cadence.

        `n_volees` est **requis** pour `TOUTES_LES_N_VOLEES` et **ignoré** pour les autres grains :
        une cadence sur un grain de fin serait une donnée morte, jamais lue et trompeuse.

        Lève `NombreVoleesParValidationManquant` si la cadence manque,
        `NombreVoleesParValidationInvalide` si elle est `< 1`.
        """
        if type_grain is not TypeGrain.TOUTES_LES_N_VOLEES:
            return GrainValidation(type=type_grain)
        if n_volees is None:
            raise NombreVoleesParValidationManquant(
                "Une validation toutes les N volées suppose de préciser N."
            )
        return GrainValidation.toutes_les_n_volees(n_volees)
