"""Placement **par bloc de couloirs** — l'unité placée est le groupe, jamais l'archer (ADR-0083).

⚠️ **Le tireur au repos change à chaque tour**, et c'est toute la raison du bloc : une poule de 5
tient sur 4 couloirs parce qu'un membre se repose, mais jamais le même ; une ronde de suisse
ré-apparie tout le plateau. Persister « archer → couloir » écrirait une information **fausse**, pas
seulement incomplète. Le bloc est matérialisé, les couloirs de chaque rencontre sont **dérivés**.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from domain.gabarit_salle import GabaritSalle


@dataclass(frozen=True)
class BlocDeCouloirs:
    """La plage de couloirs contigus attribuée à un groupe.

    `places` porte la liste **ordonnée** des couloirs occupés, chacun `(index de cible, lettre)`.
    C'est le seul champ d'état : `cible_index`, `position_depart` et `nb_couloirs` s'en déduisent,
    plutôt que d'être stockés en double et de pouvoir diverger. Un bloc traverse librement plusieurs
    cibles — c'est même son intérêt.
    """

    groupe: int
    places: tuple[tuple[int, str], ...]

    def __post_init__(self) -> None:
        if not self.places:
            raise ValueError(f"Le groupe {self.groupe} n'occuperait aucun couloir.")

    @property
    def cible_index(self) -> int:
        """L'index (1-based) de la cible où le groupe **commence**."""
        return self.places[0][0]

    @property
    def position_depart(self) -> str:
        """La lettre du premier couloir occupé (A..D)."""
        return self.places[0][1]

    @property
    def nb_couloirs(self) -> int:
        """Le nombre de couloirs du bloc — l'empreinte du groupe."""
        return len(self.places)

    def couloirs(self) -> tuple[tuple[int, str], ...]:
        """Les couloirs occupés, cible par cible, dans l'ordre de remplissage.

        Ce que lisent le plan de salle et la feuille de poule : un bloc annoncé « cible 1, couloir
        A, 6 couloirs » reste illisible pour qui doit poser les archers, alors que la liste dit
        exactement où ils vont.
        """
        return self.places


class RaisonConflitBloc(str, Enum):
    """Pourquoi un groupe n'a pas pu être posé."""

    SALLE_PLEINE = "salle_pleine"
    """Il ne reste pas assez de couloirs contigus pour l'empreinte de ce groupe."""

    SANS_RENCONTRE = "sans_rencontre"
    """Le groupe n'apparie personne — moins de deux tireurs —, donc il n'occupe rien."""

    NON_POSEE = "non_posee"
    """Aucun bloc ne porte cette poule — plan non posé, ou posé sur une autre composition.

    ⚠️ **Cette raison ne naît jamais de `placer_les_blocs`**, qui pose ou rapporte `SALLE_PLEINE` :
    elle naît à la **lecture**, quand la composition du jour ne retrouve pas son bloc en base
    (E05US023). Normal avant la première pose, **signal** après (l'effectif a bougé, il faut
    reposer). La distinguer de `SALLE_PLEINE` évite d'annoncer une salle trop petite à tort.
    """


@dataclass(frozen=True)
class ConflitDeBloc:
    """Un groupe que le placement n'a pas pu poser, et pourquoi.

    Même parti que `PlanDeCibles.conflits` en qualification (ADR-0024) : le placement **rapporte**
    ce qu'il n'a pas pu faire au lieu de tronquer en silence. L'organisateur doit voir à l'atelier
    qu'une poule n'a pas de cible, pas le découvrir le jour J.
    """

    groupe: int
    raison: RaisonConflitBloc


@dataclass(frozen=True)
class PlanDeBlocs:
    """Résultat du placement : les blocs posés + les groupes restés sans cible."""

    blocs: tuple[BlocDeCouloirs, ...]
    conflits: tuple[ConflitDeBloc, ...] = ()


def couloirs_de_la_paire(
    bloc: BlocDeCouloirs | None, position: int
) -> tuple[tuple[int, str], tuple[int, str]] | None:
    """Les deux couloirs qu'une **rencontre** occupe — dérivés du bloc, jamais persistés.

    La *n*-ième rencontre d'un tour prend les couloirs `2n` et `2n+1` du bloc, donc les adversaires
    sont **côte à côte** (intention d'ADR-0048, obtenue sans réordonnancement puisque le bloc est
    contigu). `None` si le bloc manque ou est trop court — un plan incomplet doit se **voir**. ⚠️
    **La position se compte par tour, jamais sur le groupe entier** : cumulée, elle ferait glisser
    le groupe d'un cran par tour et déborder de son propre bloc. Hissée ici en E05US026.
    """
    if bloc is None:
        return None
    debut = 2 * position
    if debut + 1 >= len(bloc.places):
        return None
    return bloc.places[debut], bloc.places[debut + 1]


def _couloirs_du_gabarit(gabarit: GabaritSalle) -> tuple[tuple[int, str], ...]:
    """Tous les couloirs de la salle, à plat et dans l'ordre de remplissage.

    Mettre la salle à plat est ce qui rend la contiguïté triviale : « la poule suivante démarre au
    couloir libre juste après » devient un simple curseur qui avance, et le débordement d'une cible
    sur la suivante n'est plus un cas particulier à traiter. La **capacité réelle de chaque cible**
    est respectée au passage (`GabaritSalle` l'autorise de 1 à 4, et variable d'une cible à l'autre
    depuis `ajuster`) : c'est elle qui décide où l'on déborde, jamais un 4 supposé.
    """
    return tuple(
        (cible.index, position) for cible in gabarit.cibles for position in cible.positions
    )


def placer_les_blocs(empreintes: Sequence[int], gabarit: GabaritSalle) -> PlanDeBlocs:
    """Pose les groupes **dans l'ordre**, chacun sur un bloc de couloirs contigus.

    `empreintes[i]` est le **nombre de couloirs** du groupe `i + 1` — son parallélisme, pas son
    effectif ; l'appelant le calcule car il dépend du format (`poule.couloirs_occupes`, ou `2 *
    (effectif // 2)` pour une ronde suisse). ⚠️ **Au premier groupe qui ne tient pas, on s'arrête**
    : poser le suivant dans le trou casserait l'ordre du plan, et une salle où l'ordre saute coûte
    plus cher qu'une salle où deux groupes manquent visiblement. Pure et déterministe.
    """
    disponibles = _couloirs_du_gabarit(gabarit)
    curseur = 0
    blocs: list[BlocDeCouloirs] = []
    conflits: list[ConflitDeBloc] = []
    salle_pleine = False

    for index, besoin in enumerate(empreintes, start=1):
        if besoin == 0:
            conflits.append(ConflitDeBloc(index, RaisonConflitBloc.SANS_RENCONTRE))
            continue
        if salle_pleine or curseur + besoin > len(disponibles):
            salle_pleine = True
            conflits.append(ConflitDeBloc(index, RaisonConflitBloc.SALLE_PLEINE))
            continue
        blocs.append(BlocDeCouloirs(index, disponibles[curseur : curseur + besoin]))
        curseur += besoin

    return PlanDeBlocs(blocs=tuple(blocs), conflits=tuple(conflits))
