"""Value object `BaremeQualification` — structure de l'épreuve de qualification (E01US009).

Un barème de qualification décrit **comment se tire et se compte** la qualification : un nombre de
**volées** de chacune un nombre de **flèches**, le classement se faisant au **cumul** des points
(glossaire : *Barème*, *Volée*). Le total de flèches et le score maximum en découlent (une flèche
vaut au plus 10). Le preset FFTA 18 m est **20 volées de 3 flèches = 60 flèches**
(`referentiel-ffta.md` §6.1) ; conformément au principe « le règlement est un template », il reste
**modifiable** (§10.2).

Value object de domaine **pur** (immuable, sans dépendance framework), validé à la construction.
Le mode de comptage est ici **implicitement le cumul** : les autres barèmes (sets, shoot-off, Big
Shoot Off) concernent les duels et relèvent du moteur de phases (EPIC-05, ADR-0004).
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.erreurs import NombreFlechesParVoleeInvalide, NombreVoleesInvalide

# Preset FFTA 18 m (art. A.7.3 / référentiel §6.1) : 60 flèches en 20 volées de 3.
PRESET_FFTA_18M_NB_VOLEES = 20
PRESET_FFTA_18M_NB_FLECHES_PAR_VOLEE = 3

# Valeur maximale d'une flèche (le « 10 ») : sert à dériver le score maximum d'un barème.
VALEUR_FLECHE_MAX = 10


@dataclass(frozen=True)
class BaremeQualification:
    """Barème de qualification : `nb_volees` volées de `nb_fleches_par_volee` flèches, au cumul."""

    nb_volees: int
    nb_fleches_par_volee: int

    @staticmethod
    def creer(nb_volees: int, nb_fleches_par_volee: int) -> BaremeQualification:
        """Crée un barème valide : chaque grandeur doit être un entier `>= 1`.

        Lève `NombreVoleesInvalide` ou `NombreFlechesParVoleeInvalide` selon la valeur fautive.
        """
        if nb_volees < 1:
            raise NombreVoleesInvalide(
                "Un barème de qualification doit compter au moins une volée."
            )
        if nb_fleches_par_volee < 1:
            raise NombreFlechesParVoleeInvalide("Une volée doit compter au moins une flèche.")
        return BaremeQualification(nb_volees=nb_volees, nb_fleches_par_volee=nb_fleches_par_volee)

    @staticmethod
    def preset_ffta_18m() -> BaremeQualification:
        """Le barème officiel FFTA 18 m : 20 volées de 3 flèches (60 flèches, référentiel §6.1)."""
        return BaremeQualification.creer(
            PRESET_FFTA_18M_NB_VOLEES, PRESET_FFTA_18M_NB_FLECHES_PAR_VOLEE
        )

    @property
    def nb_fleches_total(self) -> int:
        """Nombre total de flèches tirées sur la qualification."""
        return self.nb_volees * self.nb_fleches_par_volee

    @property
    def score_max(self) -> int:
        """Score maximum atteignable (toutes les flèches au maximum)."""
        return self.nb_fleches_total * VALEUR_FLECHE_MAX
