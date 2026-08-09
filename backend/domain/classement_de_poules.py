"""Le **classement d'une phase de poules** — « par rang de poule d'abord » (E05US023).

ADR-0083 §6.

Jumeau de [`classement_de_tableau`](classement_de_tableau.py), et pour la même raison : une phase
aval prélève « les rangs 1 à 8 » sans avoir à savoir de quel **type** de phase ces rangs viennent.
`application/prelevement.py` consomme un `ClassementSource` ; ce module en fabrique un à partir de
ce que le moteur de poule produit — un classement **par groupe** (`classement_de_poule`), pas un
classement de phase.

## La règle, et pourquoi elle n'est pas « poule après poule »

Les poules se jouent **en parallèle** : elles commencent et finissent ensemble, et rien ne rend la
poule 1 plus relevée que la poule 2. Concaténer les groupes (les trois de la poule 1, puis les trois
de la poule 2) placerait donc le **2ᵉ** d'un groupe devant le **vainqueur** du suivant, ce qu'aucune
compétition ne fait. L'ordre est celui du CA, arbitré le 09/08/2026 : sur `P` poules, les rangs
`1..P` sont les vainqueurs, `P+1..2P` les deuxièmes, et ainsi de suite. On appelle **bloc** chacune
de ces tranches.

Deux conséquences du CA, toutes deux voulues :

- **le classement porte tout le monde**, pas seulement les qualifiés — c'est le *prélèvement* qui
  sélectionne, ce qui rend une consolante « les rangs 9 à 16 » composable sans réglage neuf ;
- **le dernier bloc peut être incomplet** (7 poules dont deux de 5 → deux occupants au 5ᵉ bloc), et
  les surnuméraires vont **en dernier**.

## Ce que ce module refuse de prétendre savoir

À l'intérieur d'un bloc, **les archers sont ex æquo**. Les ordonner par numéro de poule donnerait au
vainqueur de la poule 1 la tête de série n°1, au seul motif que sa poule porte le n°1 — c'est
exactement la faute que `qualifies_de_poule` refuse déjà (« qualifier sur l'ordre d'affichage »).
Les blocs sont donc déclarés **indécis** (ADR-0081), ce qui fait refuser une fenêtre qui les coupe
(« les rangs 1 à 2 » sur 4 poules) et honorer celle qui les contient (« les rangs 1 à 4 »).

Le **départage optionnel** (`departage`, les cinq critères du référentiel §10.1) referme les blocs
quand l'organisateur le demande. Il est optionnel parce que comparer des décomptes obtenus **contre
des adversaires différents** n'a de valeur que si l'on en a besoin ; ADR-0081 rend l'option
auto-régulée — elle n'est nécessaire que quand la phase avale prélève *à l'intérieur* d'un bloc, et
l'outil le dit au lieu de qualifier en silence.

⚠️ **Un ex æquo *interne* à une poule enjambe deux blocs, et les lie.** Deux archers que les cinq
critères ne séparent pas aux 3ᵉ et 4ᵉ places de leur groupe occupent le 3ᵉ et le 4ᵉ bloc — mais on
ne sait pas lequel est où. Les deux blocs deviennent alors **indécis ensemble**, sur la seule plage
que l'égalité enjambe. Sans cette liaison, « les rangs 5 à 6 » passerait en prenant un archer pour
un 3ᵉ avéré : une population bien formée, plausible, et fausse — la classe de défaut qu'ADR-0081
existe pour fermer. La liaison est **locale** : elle ne contamine pas les blocs que l'égalité
n'enjambe pas, sans quoi un ex æquo de fond de poule rendrait toute la phase illisible.

**Pourquoi le domaine.** La fonction croise des `RangPoule`, un `LigneClassement` et une politique
`Tiebreak` — trois notions du domaine, aucune infrastructure, aucun repository. C'est l'argument
exact de `classement_de_tableau`, et il n'y a aucune raison que les deux jumeaux vivent dans deux
couches. *(ADR-0083 §« Restent à écrire » plaçait cette fonction en `application/poules.py` ; elle
descend ici pour cette raison, et l'ADR est corrigé en conséquence.)*

Domaine **pur** : aucun framework, aucune autre couche (règle 1).

[ADR-0083]: ../../docs/adr/0083-le-contrat-de-phase-jouable.md
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
from domain.poule import RangPoule

if TYPE_CHECKING:  # pragma: no cover — le protocole de tri de la stdlib, invisible à l'exécution
    from _typeshed import SupportsRichComparison


def classement_de_poules(
    classements: Sequence[Sequence[RangPoule]],
    lignes: Mapping[ArcherId, LigneClassement],
    *,
    departage: Tiebreak | None = None,
) -> ClassementSource:
    """Le classement de la phase, blocs de rang concaténés, et ce qu'il a d'encore indécis.

    `classements` porte le classement **de chaque poule**, dans l'ordre des poules ; c'est ce que
    `classement_de_poule` rend, groupe par groupe. `lignes` porte l'identité des archers (nom,
    catégorie, club), reprise telle quelle : un classement de poule n'est pas un objet d'une autre
    nature, c'est le **même** archer situé autrement. Seul `rang_scratch` est réécrit — c'est ce que
    `preleves` lit.

    `departage`, s'il est fourni, ordonne l'intérieur de chaque bloc par le décompte (§10.1) et
    referme les plages qu'il sépare. Absent, tout bloc de plus d'un occupant est indécis.

    ⚠️ **`rang_premier` n'est pas posé ici**, comme pour `classement_de_tableau` : une phase ne sait
    pas quelle tranche du tournoi elle dispute — c'est une propriété de sa place dans le déroulé,
    que seul le service qui remonte la chaîne connaît (`application/prelevement.py:tranche`).

    Les participants **équipe** sont écartés (leur `ref_id` n'est pas un archer, ADR-0028), comme le
    fait déjà `classement_de_tableau` ; la résolution viendra avec les équipes (E13US002).
    """
    retenus = [_retenus(classement, lignes) for classement in classements]
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
    return ClassementSource(
        classement=Classement(
            lignes=tuple(
                situee_au_rang(lignes[archer_id], rang)
                for rang, archer_id in enumerate(ordonnes, start=1)
            )
        ),
        plages_indecises=_fusionner(plages),
    )


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
