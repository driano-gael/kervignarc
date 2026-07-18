"""Calcul du classement — logique de domaine **pure** (tranche verticale E00US011).

`calculer_classement` agrège les scores par archer (somme des flèches) et ordonne du
meilleur total au moins bon. Deux archers à égalité de total partagent le même rang
(classement « à égalités », ex. 1-2-2-4). Le vrai départage FFTA (nombre de 10 puis de 9,
barrages) relève d'E06 : ici, à total égal, on ordonne par **nom, puis prénom, puis
identifiant** — un départage **total** pour un rendu déterministe. Le prénom et l'identifiant
ne sont pas décoratifs : depuis E02US002 deux homonymes (un père et son fils, mêmes nom **et**
prénom) coexistent ; sur le seul nom, leurs deux lignes à total égal permuteraient au gré de
l'ordre rendu par `ArcherRepository.par_tournoi` (un `SELECT` sans `ORDER BY`), sur l'écran même
où on doit les distinguer. Même départage que `ServiceArchers.lister`.

Fonction pure sur des agrégats : testable sans base ni serveur, réutilisable par les US de
classement à venir.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from domain.archer import Archer, ArcherId
from domain.club import ClubId
from domain.score import Score


@dataclass(frozen=True)
class LigneClassement:
    """Une ligne de classement : rang, archer et total marqué.

    Porte `prenom` et `club_id` depuis E02US002, pour deux raisons distinctes : le classement
    est la seule surface où un archer **inscrit** apparaît, donc (a) c'est ici que se **signale**
    un club encore inconnu (`club_id is None`), l'anomalie que le CA impose de rendre visible
    (ADR-0014) — sans quoi « on complétera plus tard » n'aurait aucun support ; et (b) deux
    homonymes confirmés (un père et son fils) seraient indiscernables sur le seul patronyme,
    alors que l'US vient précisément d'autoriser leur coexistence.

    `club_id` et non le nom du club : le classement ne charge pas le référentiel — signaler une
    absence ne demande pas de résoudre les présences.
    """

    rang: int
    archer_id: ArcherId
    nom: str
    prenom: str
    cible: int | None
    club_id: ClubId | None
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

    ordonnees = sorted(entrees, key=lambda e: (-totaux[e[1]], e[0].nom, e[0].prenom, e[1]))

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
                prenom=archer.prenom,
                cible=archer.cible,
                club_id=archer.club_id,
                total=total,
            )
        )
    return Classement(lignes=tuple(lignes))
