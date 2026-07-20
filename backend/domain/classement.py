"""Calcul du classement de qualification — logique de domaine **pure** (E06US001).

`calculer_classement` ordonne les archers d'un tournoi sur leur **score cumulé** (la somme de
leurs volées **validées**, cf. `Serie.cumul`), puis applique le **départage FFTA** à total égal :
plus grand nombre de **10**, puis de **9** (`docs/referentiel-ffta.md` §8.1, art. C.3 — spécifique
au tir à 18 m). Les deux critères sont **séquentiels** (le nombre de 9 ne départage que si les 10
sont à égalité) et ne jouent **qu'à** total égal. Si l'égalité subsiste après les 10 et les 9, la
qualification laisse l'**ex æquo** : les deux archers partagent le rang (le barrage de tir, §8.2, ne
concerne que les duels, pas ce classement). Le X (mouche) n'est pas un score distinct (ADR-0020) :
on départage sur les 10, pas sur les X.

Chaque ligne porte **deux rangs** (arbitrage produit du 20/07/2026, reversé dans `stories/`) :

- `rang_scratch` : le classement **global**, toutes catégories confondues ;
- `rang_categorie` : le classement **au sein de la catégorie** de l'archer, dense (1..N).

Les deux se calculent avec le **même** ordre ; ils ne diffèrent que par la numérotation (le scratch
saute les places prises par les autres catégories, la catégorie repart de 1). Le décompte de 10 et
de 9 est **restitué** dans la ligne : le CA veut le départage « traçable », c.-à-d. vérifiable à
l'œil sans rejouer le calcul.

Ce n'est **pas** encore la politique `tiebreak` injectable d'ADR-0004 : il n'existe qu'une règle (la
FFTA), et son moteur relève d'EPIC-05 (l'ADR se scope lui-même là-bas). On implémente donc la règle
comme une clé de tri **isolée et nommée** (`_cle_tri`, `_CLE_DEPARTAGE`) — la couture d'une future
injection — sans la plomberie de config prématurée (règle 12, « remède structurel sur preuve »).

Fonction pure sur des agrégats : testable sans base ni serveur.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from domain.archer import Archer, ArcherId
from domain.blason import ZoneScore
from domain.categorie import Categorie, CategorieId
from domain.club import ClubId
from domain.serie import Serie


@dataclass(frozen=True)
class LigneClassement:
    """Une ligne de classement : les deux rangs de l'archer, son identité et son décompte.

    Porte `prenom` et `club_id` depuis E02US002, pour deux raisons distinctes : le classement est
    la surface où un archer **inscrit** apparaît, donc (a) c'est ici que se **signale** un club
    encore inconnu (`club_id is None`), l'anomalie que le CA impose de rendre visible (ADR-0014) ;
    et (b) deux homonymes confirmés (un père et son fils) seraient indiscernables sur le seul
    patronyme. `club_id` et non le nom du club : le classement ne charge pas le référentiel —
    signaler une absence ne demande pas de résoudre les présences.

    `nb_dix`/`nb_neuf` rendent le départage **traçable** (CA) : on voit *pourquoi* deux archers à
    total égal sont ordonnés ainsi, sans rejouer le calcul.
    """

    rang_scratch: int
    rang_categorie: int
    archer_id: ArcherId
    nom: str
    prenom: str
    categorie_id: CategorieId
    categorie_libelle: str
    cible: int | None
    club_id: ClubId | None
    total: int
    nb_dix: int
    nb_neuf: int


@dataclass(frozen=True)
class Classement:
    """Classement d'un tournoi, ordonné par rang **scratch** (du meilleur au moins bon)."""

    lignes: tuple[LigneClassement, ...]


@dataclass(frozen=True)
class _Decompte:
    """Ce dont le classement a besoin pour un archer : total et décomptes de départage."""

    total: int
    nb_dix: int
    nb_neuf: int


def _decompte(serie: Serie | None) -> _Decompte:
    """Réduit la série d'un archer à son total et ses décomptes de 10/9 (volées validées).

    `None` (archer inscrit sans série encore ouverte) → tout à zéro : il figure au classement avec
    un total nul, comme l'exige le CA « un archer sans flèche apparaît quand même ».
    """
    if serie is None:
        return _Decompte(total=0, nb_dix=0, nb_neuf=0)
    return _Decompte(
        total=serie.cumul,
        nb_dix=serie.compter(ZoneScore.DIX),
        nb_neuf=serie.compter(ZoneScore.NEUF),
    )


def _cle_tri(archer: Archer, decompte: _Decompte) -> tuple[int, int, int, str, str, int]:
    """Clé de tri **totale** d'une entrée : critères FFTA d'abord, départage déterministe ensuite.

    `(-total, -nb_dix, -nb_neuf)` = le classement FFTA (mieux classé = clé plus petite car les
    valeurs sont niées). Puis `(nom, prenom, archer_id)` : à égalité **parfaite** au sens FFTA, on
    fixe un ordre d'affichage stable (mêmes homonymes, même écran — sinon l'ordre suivrait le
    `SELECT` sans `ORDER BY` de `par_tournoi`). Ce suffixe **n'entre pas** dans le partage de rang.
    """
    archer_id = archer.id
    assert archer_id is not None, "Le classement se calcule sur des archers persistés."
    return (
        -decompte.total,
        -decompte.nb_dix,
        -decompte.nb_neuf,
        archer.nom,
        archer.prenom,
        archer_id,
    )


def _cle_departage(decompte: _Decompte) -> tuple[int, int, int]:
    """Ce qui fait deux archers **ex æquo** : même total, mêmes 10, mêmes 9 (§8.1). Le suffixe de
    `_cle_tri` (nom, prénom, id) n'est qu'un ordre d'affichage — il ne crée pas de rangs distincts.
    """
    return (decompte.total, decompte.nb_dix, decompte.nb_neuf)


def _ranger(entrees_ordonnees: list[tuple[Archer, _Decompte]]) -> dict[ArcherId, int]:
    """Attribue un rang à des entrées **déjà triées**, ex æquo partagés (ex. 1-2-2-4).

    Deux entrées consécutives de même `_cle_departage` gardent le même rang ; on repart du rang
    « index + 1 » dès que la clé change — d'où les sauts après un groupe d'ex æquo.
    """
    rangs: dict[ArcherId, int] = {}
    rang = 0
    cle_precedente: tuple[int, int, int] | None = None
    for index, (archer, decompte) in enumerate(entrees_ordonnees):
        assert archer.id is not None
        cle = _cle_departage(decompte)
        if cle != cle_precedente:
            rang = index + 1
            cle_precedente = cle
        rangs[archer.id] = rang
    return rangs


def calculer_classement(
    archers: Iterable[Archer],
    series: Iterable[Serie],
    categories: Iterable[Categorie],
) -> Classement:
    """Construit le classement des `archers` à partir de leurs `series`, avec départage FFTA.

    - `series` dont l'`archer_id` n'appartient pas au lot d'archers sont ignorées ;
    - `categories` sert à libeller la catégorie de chaque ligne (jointure par `categorie_id`).

    Renvoie les lignes ordonnées par **rang scratch**. Chaque ligne porte aussi son rang **dans sa
    catégorie** (dense), calculé sur le même ordre restreint aux archers de la catégorie.
    """
    entrees: list[tuple[Archer, _Decompte]] = []
    serie_par_archer = {s.archer_id: s for s in series}
    libelle_par_categorie = {c.id: c.libelle for c in categories if c.id is not None}
    for archer in archers:
        assert archer.id is not None, "Le classement se calcule sur des archers persistés."
        entrees.append((archer, _decompte(serie_par_archer.get(archer.id))))

    ordre_scratch = sorted(entrees, key=lambda e: _cle_tri(e[0], e[1]))
    rangs_scratch = _ranger(ordre_scratch)

    # Rangs par catégorie : même comparateur, appliqué au sous-ensemble de chaque catégorie. L'ordre
    # relatif y est **identique** à l'ordre scratch (mêmes archers, même clé) — seule la
    # numérotation diffère (dense). On regroupe donc à partir de l'ordre scratch déjà trié.
    rangs_categorie: dict[ArcherId, int] = {}
    par_categorie: dict[CategorieId, list[tuple[Archer, _Decompte]]] = {}
    for archer, decompte in ordre_scratch:
        par_categorie.setdefault(archer.categorie_id, []).append((archer, decompte))
    for groupe in par_categorie.values():
        rangs_categorie.update(_ranger(groupe))

    lignes: list[LigneClassement] = []
    for archer, decompte in ordre_scratch:
        assert archer.id is not None
        lignes.append(
            LigneClassement(
                rang_scratch=rangs_scratch[archer.id],
                rang_categorie=rangs_categorie[archer.id],
                archer_id=archer.id,
                nom=archer.nom,
                prenom=archer.prenom,
                categorie_id=archer.categorie_id,
                categorie_libelle=libelle_par_categorie.get(archer.categorie_id, ""),
                cible=archer.cible,
                club_id=archer.club_id,
                total=decompte.total,
                nb_dix=decompte.nb_dix,
                nb_neuf=decompte.nb_neuf,
            )
        )
    return Classement(lignes=tuple(lignes))
