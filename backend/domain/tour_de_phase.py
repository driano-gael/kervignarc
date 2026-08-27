"""Libellé du **tour** d'une phase — un tour n'est pas un braquet (ADR-0090).

Ce module ne porte que la résolution en libellé : l'**unité** vit au registre de contrat, le
**nombre** là où vit la donnée qui le détermine, le **tour courant** au service qui déroule.

⚠️ **Ne pas rapatrier l'unité ici** : le contrat devrait alors importer ce module pendant que ce
module l'importe — le cycle qu'E05US023 avait déjà eu à défaire.
"""

from __future__ import annotations

from domain.contrat_phase import TypePhase, UniteDeTour, contrat_de
from domain.plage import Plage
from domain.tableau import libelle_tour

# ⚠️ `UniteDeTour` n'est **pas** ré-exporté : il vit dans `domain.contrat_phase`, et deux chemins
# d'import pour un même type sont l'amorce exacte de la divergence que ce module combat par ailleurs
# (`DETTE-020`). Relevé en revue par deux axes.
__all__ = ["libelle_de_tour", "unite_de_tour"]

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

    ⚠️ **La même clause vaut pour toute phase à un seul tour**, pas seulement pour `PHASE_ENTIERE` :
    une poule de deux archers, un système suisse dont l'effectif n'autorise qu'une ronde, un Big
    Shoot Off à manche unique n'annoncent **rien**. C'est la lettre du CA (« il n'y a rien à
    distinguer »), et la première rédaction ne l'appliquait qu'au premier cas — relevé en revue
    (axe B), avec la précision qui compte : le test censé couvrir ce CA n'exerçait que le cas qui
    passait déjà. Le **tableau** fait exception et n'a pas besoin de la garde : son tour unique
    s'appelle « Finale », qui est un nom.

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
        # Pas de garde `nb_tours <= 1` ici : le tour unique d'un tableau de 2 s'appelle
        # « Finale » — un **nom**, pas un numéro. La clause du CA vise les numéros nus.
        return libelle_tour(tour, nb_tours, place_en_jeu, plage)
    if nb_tours <= 1:
        return None
    return f"{_MOT_DE_LA_SALLE[unite]} {tour}"
