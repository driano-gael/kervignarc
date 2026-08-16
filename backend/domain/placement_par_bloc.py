"""Placement d'un **groupe de tireurs** sur un bloc de couloirs contigus (E05US023, [ADR-0083]).

Règle **fournie par le commanditaire le 09/08/2026**, elle n'est écrite nulle part ailleurs :

> Un groupe occupe un **bloc de couloirs contigus**. Quand il déborde d'une cible, il prend la
> suite sur la cible d'après, et **le groupe suivant démarre au couloir libre juste après** — on
> n'ouvre pas une cible neuve pour lui. La salle se remplit en continu, groupe après groupe.

**L'unité placée est le groupe, pas l'archer**, et c'est la différence de fond avec le placement de
qualification (`domain/placement.py`, un archer par couloir) comme avec le plan de duels
(`ServicePlacementDuels`, deux adversaires côte à côte). La raison tient en une phrase : **le
tireur au repos change à chaque tour**. Une poule de 5 tient sur 4 couloirs parce qu'un membre se
repose — mais jamais le même ; une ronde de système suisse ré-apparie **tout le plateau**, donc
aucun de ses tireurs n'a de couloir attitré non plus. Persister « archer → couloir » écrirait dans
les deux cas une information *fausse*, pas seulement incomplète.

Ce que le bloc porte est **matérialisé** ; les couloirs de chaque rencontre, tour par tour, sont
**dérivés** à la lecture — même parti que l'appariement d'un tableau, recalculé et jamais persisté
(ADR-0023/0048).

⚠️ **Ce module s'appelait `placement_poules` jusqu'à E05US026**, et le renommage n'est pas
cosmétique : il ne connaissait déjà **que le nombre de couloirs** d'un groupe, jamais la poule
elle-même. Le nom promettait une spécialisation que le code n'avait pas, et il aurait fait croire
qu'un second mécanisme était nécessaire pour le système suisse. La table et le port ont suivi
(`placement_poule` → `placement_par_bloc`, migration 0046).

Domaine **pur** : aucun framework, aucune autre couche (règle 1).

[ADR-0083]: ../../docs/adr/0083-le-contrat-de-phase-jouable.md
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
    """Aucun bloc ne porte cette poule — le plan n'a pas encore été posé, ou l'a été sur une autre
    composition (E05US023).

    ⚠️ **Cette raison ne naît jamais de `placer_les_blocs`**, qui pose ou rapporte `SALLE_PLEINE` :
    elle naît à la **lecture**, quand la composition du jour ne retrouve pas son bloc en base. Le
    cas est normal avant la première pose, et il est un **signal** après : l'effectif a bougé depuis
    que le plan a été écrit, donc il faut le reposer. Le distinguer de `SALLE_PLEINE` évite
    d'annoncer une salle trop petite à un organisateur qui a simplement oublié de générer son
    plan."""


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

    `empreintes[i]` est le **nombre de couloirs** dont le groupe `i + 1` a besoin — son
    parallélisme, pas son effectif. C'est l'appelant qui le calcule, parce qu'il dépend du format :
    `poule.couloirs_occupes` pour une poule (un membre se repose à chaque tour),
    `2 * (effectif // 2)` pour une ronde de système suisse (tout le monde tire, sauf le bye).

    ⚠️ **La signature ne prend plus une `Poule`, et c'est le cœur du renommage d'E05US026.** Elle
    n'en lisait déjà que `numero` et `len(membres)`, pour en tirer un nombre de couloirs : dépendre
    du type entier promettait une spécialisation que le code n'avait pas, et aurait fait croire
    qu'un second mécanisme était nécessaire pour le suisse. Le domaine gagne aussi une dépendance
    en moins (`placement_par_bloc` n'importe plus `poule`).

    ⚠️ **Au premier groupe qui ne tient pas, on s'arrête** : les suivants sont rapportés en conflit
    même si l'un d'eux, plus petit, serait entré dans la place restante. Poser le groupe 5 dans le
    trou laissé par le groupe 4 casserait l'ordre du plan — l'organisateur lit « le groupe *n* est à
    tel endroit », et une salle où l'ordre saute est plus coûteuse à exploiter qu'une salle où deux
    groupes manquent visiblement à la fin. On préfère un plan tronqué et lisible à un plan complet
    et surprenant.

    Fonction **pure et déterministe** (règle 9) : mêmes empreintes, même gabarit, même plan.
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
