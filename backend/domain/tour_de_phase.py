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

    `None` plutôt qu'une chaîne vide : une qualification se lit « Qualification », jamais «
    Qualification — tour 1 sur 1 » ; un `None` explicite empêche un séparateur orphelin. ⚠️ **La
    clause vaut pour toute phase à un seul tour**, pas seulement `PHASE_ENTIERE` ; le **tableau**
    fait exception, son tour unique s'appelant « Finale ». ⚠️ **`TOUR_DE_TABLEAU` délègue, il ne
    recalcule pas** : `DETTE-020` compte deux domiciles, et un générique perdrait la petite finale.
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
