"""Classement de phase à partir de poules jouées **en parallèle** (ADR-0083, ADR-0081).

Les rangs vont par **blocs** : sur `P` poules, `1..P` sont les vainqueurs, `P+1..2P` les deuxièmes.

⚠️ **Dans un bloc les archers sont EX ÆQUO**, et un ex æquo interne à une poule **lie deux blocs**
sur la plage qu'il enjambe. Sans cette liaison, « les rangs 5 à 6 » prendrait un archer pour un 3ᵉ
avéré : bien formé, plausible, et faux.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from functools import cmp_to_key
from typing import TYPE_CHECKING

from domain.archer import ArcherId
from domain.classement import Classement, LigneClassement
from domain.classement_de_tableau import ClassementSource, situee_au_rang
from domain.participant import GenreParticipant
from domain.politiques import Tiebreak
from domain.poule import ModeDeComposition, RangPoule

if TYPE_CHECKING:  # pragma: no cover — le protocole de tri de la stdlib, invisible à l'exécution
    from _typeshed import SupportsRichComparison


def classement_de_poules(
    classements: Sequence[Sequence[RangPoule]],
    lignes: Mapping[ArcherId, LigneClassement],
    *,
    departage: Tiebreak | None = None,
    mode: ModeDeComposition,
) -> ClassementSource:
    """Le classement de la phase, blocs de rang concaténés, et ce qu'il a d'encore indécis.

    `classements` porte le classement **de chaque poule** ; `lignes` l'identité des archers,
    reprise telle quelle — seul `rang_scratch` est réécrit. `departage` ordonne l'intérieur de
    chaque bloc (§10.1) ; absent, tout bloc de plus d'un occupant est indécis. ⚠️ `rang_premier`
    n'est **pas** posé ici, et `mode` est **sans valeur par défaut** (ADR-0094 §2) : un défaut
    rendrait l'oubli silencieux et donnerait le mauvais ordre. Équipes écartées (ADR-0028).
    """
    retenus = [_retenus(classement, lignes) for classement in classements]
    if mode is ModeDeComposition.PAR_NIVEAU:
        par_groupe, liaisons = _par_groupe(retenus)
        return _en_classement(par_groupe, liaisons, lignes)
    hauteur = max((len(classement) for classement in retenus), default=0)

    ordonnes: list[ArcherId] = []
    plages: list[tuple[int, int]] = []
    # `(poule, niveau) → rang dans le classement de phase`. Indispensable pour situer les ex æquo
    # internes : le départage peut réordonner un bloc, donc la position d'un archer ne se déduit pas
    # de « niveau fois le nombre de poules » — un dernier bloc incomplet suffit à la fausser.
    positions: dict[tuple[int, int], int] = {}
    ordre_du_bloc = None if departage is None else _comparateur(departage)
    for niveau in range(hauteur):
        bloc = [
            (index, classement[niveau])
            for index, classement in enumerate(retenus)
            if len(classement) > niveau
        ]
        if ordre_du_bloc is not None:
            # Tri **stable** : à décompte égal, l'ordre des poules est conservé. Ces archers-là sont
            # de toute façon déclarés indécis ci-dessous — la stabilité ne sert qu'à rendre
            # l'affichage reproductible d'une lecture à l'autre.
            bloc.sort(key=ordre_du_bloc)
        debut = len(ordonnes) + 1
        for index, ligne in bloc:
            ordonnes.append(ligne.participant.ref_id)
            positions[(index, niveau)] = len(ordonnes)
        plages.extend(_indecises_du_bloc([ligne for _, ligne in bloc], debut, departage))

    plages.extend(_liaisons_internes(retenus, positions))
    return _en_classement(ordonnes, plages, lignes)


def _en_classement(
    ordonnes: Sequence[ArcherId],
    plages: Sequence[tuple[int, int]],
    lignes: Mapping[ArcherId, LigneClassement],
) -> ClassementSource:
    """Le `ClassementSource` d'un ordre déjà arrêté — commun aux deux modes de composition.

    Extrait en E05US029 : les deux ordres diffèrent, leur mise en forme non. La partager garantit
    surtout que `rang_scratch` est renuméroté **au même endroit** — c'est lui que `preleves` lit,
    et deux numérotations concurrentes seraient exactement la seconde vérité qu'ADR-0081 traque.
    """
    return ClassementSource(
        classement=Classement(
            lignes=tuple(
                situee_au_rang(lignes[archer_id], rang)
                for rang, archer_id in enumerate(ordonnes, start=1)
            )
        ),
        plages_indecises=_fusionner(plages),
    )


def _par_groupe(
    retenus: Sequence[Sequence[RangPoule]],
) -> tuple[list[ArcherId], list[tuple[int, int]]]:
    """L'ordre d'une phase de **poules de niveau** : chaque groupe en entier, l'un après l'autre.

    ⚠️ **C'est l'exact inverse du raisonnement du préambule de ce module, et c'est voulu** :
    l'ordre « par rang de poule d'abord » suppose qu'aucune poule n'est plus relevée qu'une autre,
    ce que `PAR_NIVEAU` révoque — la poule A réunit les rangs 1-6, la F les 31-36. Chaque groupe a
    donc **son propre espace de rangs** (CA E05US029), le `rang_premier` **unique** de la phase
    décalant l'ensemble. Aucun bloc indécis inter-poules ; le `departage` est ignoré, pas refusé.
    """
    ordonnes: list[ArcherId] = []
    positions: dict[tuple[int, int], int] = {}
    for index, classement in enumerate(retenus):
        for niveau, ligne in enumerate(classement):
            ordonnes.append(ligne.participant.ref_id)
            positions[(index, niveau)] = len(ordonnes)
    return ordonnes, _liaisons_internes(retenus, positions)


def _comparateur(departage: Tiebreak) -> Callable[[tuple[int, RangPoule]], SupportsRichComparison]:
    """La clé de tri d'un bloc, dérivée du **comparateur** de la politique.

    `Tiebreak` expose un comparateur à trois valeurs (ADR-0004), pas une clé : c'est ce qui lui
    permet de porter un ordre non lexicographique. `cmp_to_key` fait le pont, une fois, plutôt que
    de recopier ici l'ordre des cinq critères — ce qui créerait la seconde vérité que la politique
    existe pour empêcher.
    """

    def ordonner(entree: tuple[int, RangPoule], suivante: tuple[int, RangPoule]) -> int:
        return departage.departager(entree[1].decompte, suivante[1].decompte)

    return cmp_to_key(ordonner)


def _retenus(
    classement: Sequence[RangPoule], lignes: Mapping[ArcherId, LigneClassement]
) -> list[RangPoule]:
    """Les lignes de cette poule dont l'archer existe au classement — l'ordre est conservé.

    Filtrer **avant** de numéroter, et non après : `preleves` lit `rang_scratch`, donc une
    numérotation trouée ferait manquer des archers à une fenêtre par ailleurs correcte.
    """
    return [
        ligne
        for ligne in classement
        if ligne.participant.genre is GenreParticipant.INDIVIDUEL
        and ligne.participant.ref_id in lignes
    ]


def _indecises_du_bloc(
    bloc: Sequence[RangPoule], debut: int, departage: Tiebreak | None
) -> list[tuple[int, int]]:
    """Les plages indécises **à l'intérieur** d'un bloc, bornes absolues dans le classement rendu.

    Sans départage, le bloc entier est indécis dès qu'il compte plus d'un occupant : c'est le régime
    par défaut du CA. Avec, on coupe le bloc en séries de décomptes **égaux** — le comparateur
    rendant `0` est la définition même de l'ex æquo pour la politique choisie —, et seules les
    séries de plus d'un occupant restent indécises. Un bloc à un seul occupant ne l'est jamais.
    """
    if len(bloc) < 2:
        return []
    if departage is None:
        return [(debut, debut + len(bloc) - 1)]
    plages: list[tuple[int, int]] = []
    debut_serie = 0
    for index in range(1, len(bloc) + 1):
        fini = index == len(bloc)
        if fini or departage.departager(bloc[index - 1].decompte, bloc[index].decompte) != 0:
            if index - debut_serie > 1:
                plages.append((debut + debut_serie, debut + index - 1))
            debut_serie = index
    return plages


def _liaisons_internes(
    retenus: Sequence[Sequence[RangPoule]], positions: Mapping[tuple[int, int], int]
) -> list[tuple[int, int]]:
    """Les plages qu'un ex æquo **interne à une poule** rend indécises en enjambant des blocs.

    Deux membres consécutifs au **même rang de poule** sont interchangeables : le §10.1 s'est arrêté
    sans les séparer. Ils tombent pourtant dans deux blocs distincts du classement de phase, donc la
    plage qui les sépare — eux compris — ne peut pas être découpée. Les égalités à trois membres se
    chaînent d'elles-mêmes : les paires consécutives se recouvrent, et `_fusionner` les soude.
    """
    return [
        (positions[(index, niveau)], positions[(index, niveau + 1)])
        for index, classement in enumerate(retenus)
        for niveau in range(len(classement) - 1)
        if classement[niveau].rang == classement[niveau + 1].rang
    ]


def _fusionner(plages: Sequence[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    """Les plages indécises, triées et **fusionnées quand elles se chevauchent**.

    ⚠️ Deux plages **adjacentes** (1-2 puis 3-4) ne fusionnent pas : elles décrivent deux blocs que
    rien ne relie, et les souder refuserait « les rangs 1 à 2 », qui est décidé. Seul un **rang
    commun** vaut liaison — c'est ce que produit un ex æquo interne, et lui seul.
    """
    fusionnees: list[tuple[int, int]] = []
    for debut, fin in sorted(plages):
        if fusionnees and debut <= fusionnees[-1][1]:
            fusionnees[-1] = (fusionnees[-1][0], max(fusionnees[-1][1], fin))
        else:
            fusionnees.append((debut, fin))
    return tuple(fusionnees)
