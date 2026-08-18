"""Le **tour** — unité d'avancement générique d'une phase ([ADR-0090], E05US032).

Toute phase avance par tours, quel que soit son format, et **un tour n'est pas un braquet** : le
tour dit *où on en est*, le braquet dit *quels rangs ce tour attribue*. Certaines phases classent
au fil des tours (l'élimination directe : la *Règle R*), d'autres ne classent qu'à la fin (la
qualification : le total, pas la volée 12). Confondre les deux est ce que le code faisait jusqu'ici
— `domain.suivi_deroule` dérivait ses tours des braquets, d'où une qualification, une poule ou un
système suisse en cours qui affichaient « zéro tour ».

**Ce module ne porte que la résolution en libellé.** L'**unité** elle-même vit au registre de
contrat (`domain.contrat_phase.UniteDeTour`), avec les six autres questions du contrat — la séparer
d'eux obligerait le contrat à importer ce module pendant que ce module importe le contrat, soit
exactement le cycle qu'E05US023 avait déjà eu à défaire en déplaçant `TypePhase`. Le **nombre** de
tours se calcule là où vit la donnée qui le détermine (la projection pour un tableau, le réglage
pour un suisse), et le **tour courant** se demande au service qui déroule la phase — port
`LecteurAvancementDePhase`, ADR-0090 §5.

Module **pur et synchrone** (règle 1) : aucune lecture, aucun état.
"""

from __future__ import annotations

from domain.contrat_phase import TypePhase, UniteDeTour, contrat_de
from domain.plage import Plage
from domain.tableau import libelle_tour

__all__ = ["UniteDeTour", "libelle_de_tour", "unite_de_tour"]

_MOT_DE_LA_SALLE: dict[UniteDeTour, str] = {
    UniteDeTour.TOUR: "Tour",
    UniteDeTour.RONDE: "Ronde",
    UniteDeTour.MANCHE: "Manche",
}


def unite_de_tour(type_phase: TypePhase) -> UniteDeTour:
    """Dans quelle unité ce type de phase avance-t-il.

    Lit le **registre de contrat** plutôt qu'une table locale : une table jumelle divergerait du
    jour où un type entrerait au catalogue. C'est la leçon de `TYPES_SIGNALES_EN_ECART` en
    E05US023 — une table dérivée n'est sûre que si elle répond exactement à la même question.
    """
    return contrat_de(type_phase).unite_de_tour


def libelle_de_tour(
    unite: UniteDeTour,
    tour: int,
    nb_tours: int,
    place_en_jeu: tuple[int, int] | None = None,
    plage: Plage | None = None,
) -> str | None:
    """Le nom que la salle donne à ce tour, ou `None` si elle n'en donne aucun.

    `None` plutôt qu'une chaîne vide pour `PHASE_ENTIERE` : une qualification en cours se lit
    « Qualification », jamais « Qualification — tour 1 sur 1 ». L'appelant décide de n'afficher
    rien, et un `None` explicite l'empêche de concaténer un séparateur orphelin.

    ⚠️ **`TOUR_DE_TABLEAU` délègue, il ne recalcule pas.** `DETTE-020` compte déjà **deux**
    domiciles pour le libellé de tour d'un arbre (`domain.tableau.libelle_tour` et le front
    `saisie-duels/duel.ts`), et `E07US005` a failli en ouvrir un troisième avant de le refermer en
    servant le libellé du domaine au DTO. Réimplémenter « à rebours de la finale » ici en ouvrirait
    un quatrième — et surtout perdrait les deux règles que la fonction du tableau porte et qu'un
    générique ne devinerait pas : la petite finale se dispute **au même tour** que la finale, et un
    match de placement se nomme par sa **plage** et non par sa distance au titre.

    `place_en_jeu` et `plage` ne concernent donc que le tableau ; les autres unités les ignorent,
    n'ayant pas d'arbre où se perdre.
    """
    if unite is UniteDeTour.PHASE_ENTIERE:
        return None
    if unite is UniteDeTour.TOUR_DE_TABLEAU:
        return libelle_tour(tour, nb_tours, place_en_jeu, plage)
    return f"{_MOT_DE_LA_SALLE[unite]} {tour}"
