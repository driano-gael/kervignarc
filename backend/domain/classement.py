"""Calcul du classement — logique de domaine **pure** (tranche verticale E00US011).

`calculer_classement` agrège les scores par archer (somme des flèches) et ordonne du
meilleur total au moins bon. Deux archers à égalité de total partagent le même rang
(classement « à égalités », ex. 1-2-2-4). Le vrai départage FFTA (nombre de 10 puis de 9,
barrages) relève d'E06 : ici, à total égal, on ordonne par nom pour un rendu déterministe.

Fonction pure sur des agrégats : testable sans base ni serveur, réutilisable par les US de
classement à venir.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from domain.archer import Archer, ArcherId
from domain.score import Score


@dataclass(frozen=True)
class LigneClassement:
    """Une ligne de classement : rang, archer et total marqué."""

    rang: int
    archer_id: ArcherId
    nom: str
    cible: int | None
    total: int


@dataclass(frozen=True)
class Classement:
    """Classement ordonné d'un tournoi (du meilleur total au moins bon)."""

    lignes: tuple[LigneClassement, ...]


def calculer_classement(archers: Iterable[Archer], scores: Iterable[Score]) -> Classement:
    """Construit le classement des `archers` à partir de leurs `scores` (agrégats persistés).

    Les scores dont l'`archer_id` n'appartient pas au lot d'archers sont ignorés.
    """
    entrees: list[tuple[Archer, ArcherId]] = []
    for archer in archers:
        archer_id = archer.id
        assert archer_id is not None, "Le classement se calcule sur des archers persistés."
        entrees.append((archer, archer_id))

    totaux: dict[ArcherId, int] = {archer_id: 0 for _, archer_id in entrees}
    for score in scores:
        if score.archer_id in totaux:
            totaux[score.archer_id] += score.points

    ordonnees = sorted(entrees, key=lambda e: (-totaux[e[1]], e[0].nom))

    lignes: list[LigneClassement] = []
    rang = 0
    total_precedent: int | None = None
    for index, (archer, archer_id) in enumerate(ordonnees):
        total = totaux[archer_id]
        if total != total_precedent:  # égalité de total → même rang que le précédent
            rang = index + 1
            total_precedent = total
        lignes.append(
            LigneClassement(
                rang=rang,
                archer_id=archer_id,
                nom=archer.nom,
                cible=archer.cible,
                total=total,
            )
        )
    return Classement(lignes=tuple(lignes))
