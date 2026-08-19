"""Le déroulé **rempli par la réalité** — l'avancement d'un tournoi en cours (E07US004, ADR-0064).

CA : *« l'écran affiche le **même schéma à braquets** que l'atelier (E01US024), mais **rempli par la
réalité** : phase terminée / en cours / à venir, **tour en cours**, duels joués sur duels attendus,
braquets qui **se remplissent** au fur et à mesure »*.

**Ce module ne recalcule rien de la projection.** `domain.deroule.projeter` dit ce qui est
**attendu** — les braquets, la *Règle R*, le nombre de duels par tour ; ce module y superpose ce qui
est **fait**. La séparation est le cœur du CA : un suivi qui recalculerait les duels attendus
pourrait diverger du schéma que l'atelier a montré, alors que le CA demande explicitement *le même*
schéma. C'est aussi ce qui évite de dupliquer un invariant du moteur (le reproche que le registre de
dette adresse à toute recopie de règle).

Pur et synchrone (règle 1) : la « réalité » arrive en paramètre, dénombrée par le service qui, lui,
sait reconstruire un `Tableau` et lire les statuts de phase.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from domain.deroule import TourBraquet
from domain.phase import StatutPhase

STATUTS_DEMARRES = frozenset({StatutPhase.EN_COURS, StatutPhase.EN_PAUSE})
"""Les statuts où un « tour en cours » a un sens.

Une phase **à venir** n'en a pas encore ; une phase **terminée** n'en a plus, même si des duels
manquent à l'appel (forfaits, clôture décidée par l'organisateur, E12US008) — le suivi ne
contredit pas le geste de clôture. Une phase **en pause** en garde un : la pause suspend le tir, pas
le tour, et l'organisateur doit lire *où* il a suspendu.
"""


@dataclass(frozen=True)
class AvancementTour:
    """Un braquet en train de se remplir : combien de duels y sont **joués** sur ceux **attendus**.

    « Joué » signifie **disputé et tranché** — un vainqueur est désigné à l'issue d'un tir. Les
    **exempts (byes)**, gagnés d'office dès la construction du tableau, **ne sont pas comptés** :
    ils occupent une place du braquet, mais ce ne sont pas des duels, et la projection ne les compte
    pas davantage (`domain.deroule._braquets` : « 24 duellistes dans un tableau de 32 → 8 duels,
    8 exemptés »). Les deux comptes doivent parler de la même chose.

    ⚠️ C'est **le** piège de ce module, et il est ici plutôt qu'au service parce que c'est ici qu'on
    vient lire la définition de « joué ». Les compter afficherait « premier tour terminé » avant que
    quiconque ait tiré. *(La première version de cette docstring disait l'inverse du code livré —
    trois relecteurs l'ont relevé.)*
    """

    tour: int
    duels_attendus: int
    duels_joues: int

    @property
    def est_termine(self) -> bool:
        """Tous les duels attendus de ce tour sont tranchés."""
        return self.duels_joues >= self.duels_attendus


@dataclass(frozen=True)
class AvancementDePhase:
    """*Où en est cette phase ?* — la réponse d'un service de format ([ADR-0090] §5).

    Deux nombres, et rien d'autre : combien de tours cette phase compte **aujourd'hui** (un suisse
    réglé à 7 rondes n'en joue que 5 si l'effectif ne permet pas plus), et lequel tourne. Le
    **libellé** ne passe pas par ici : il se résout du type de phase (`domain.tour_de_phase`), et le
    faire voyager obligerait chaque service à connaître le vocabulaire de la salle.

    `tour_courant` vaut `None` quand plus rien ne tourne — tout est joué, même si la phase n'est pas
    clôturée. C'est la même convention que `tour_courant()` plus bas, délibérément : deux notions de
    « rien en cours » divergeraient au premier écran qui les mélange.

    [ADR-0090]: ../../docs/adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md
    """

    nb_tours: int
    tour_courant: int | None


@dataclass(frozen=True)
class AvancementBloc:
    """L'avancement d'une phase : son statut, ses braquets remplis, et le tour qui tourne.

    ⚠️ **`nb_tours` n'est pas `len(tours)`** ([ADR-0090]). `tours` porte les **braquets** — les
    tranches de rangs qu'un tableau attribue au fil de l'eau —, et une phase qui ne classe
    pas au fil de l'eau n'en a aucun tout en avançant par tours : un système suisse en compte
    cinq, une poule en compte autant que son round-robin. Dériver l'un de l'autre est ce que ce
    module faisait jusqu'à E05US032, et c'est pourquoi toute phase hors tableau s'affichait à
    « zéro tour ».

    [ADR-0090]: ../../docs/adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md
    """

    ordre: int
    statut: StatutPhase
    tours: tuple[AvancementTour, ...]
    tour_courant: int | None
    nb_tours: int
    duels_joues: int
    duels_attendus: int


def avancement_bloc(
    *,
    ordre: int,
    statut: StatutPhase,
    tours: Sequence[TourBraquet],
    joues_par_tour: Mapping[int, int],
    avancement_lu: AvancementDePhase | None = None,
) -> AvancementBloc:
    """Superpose le réel (`joues_par_tour`) sur les braquets projetés (`tours`).

    `joues_par_tour` est indexé par **numéro de tour** (1-based, celui de `TourBraquet.tour` et de
    `Match.tour`). Deux gardes de robustesse, parce que projection et réalité peuvent diverger — un
    format modifié en cours de route, une phase rejouée :

    - un compte **supérieur** à l'attendu est **plafonné** plutôt qu'affiché tel quel (« 9 duels sur
      8 » ferait douter du reste du schéma) ; la divergence n'est pas masquée, le tour est
      simplement lu comme terminé ;
    - un numéro de tour **inconnu** de la projection est **ignoré** — pas de braquet fantôme dans un
      schéma censé être *le même* qu'à l'atelier.

    **Une phase sans braquet avance quand même** ([ADR-0090], E05US032). Elle n'a pas de braquet à
    remplir — elle ne classe pas au fil de l'eau —, mais elle a des tours, et `avancement_lu` les
    porte : c'est ce que le service de son format a répondu au port `LecteurAvancementDePhase`. Sans
    lecteur branché, le bloc retombe sur **un** tour, sans tour courant : dégradation lisible plutôt
    qu'exception, parce que l'écran de salle tourne en permanence, souvent sans personne devant pour
    le relancer.

    ⚠️ **Le braquet prime sur le lu quand il existe**, et ce n'est pas arbitraire : la règle des
    braquets connaît le détail (« ce tour est terminé quand ses N duels sont tranchés ») là où un
    service ne rend qu'un numéro. Les deux ne se contredisent pas, l'un est plus fin.

    **`nb_tours` ne descend jamais sous 1, `tour_courant` est filtré par le statut.** Les deux
    asymétries sont voulues et se lisent ensemble : un *compte* de tours est **structurel** — une
    phase à venir en compte déjà autant qu'elle en comptera —, tandis qu'un *tour courant* est la
    conséquence d'un geste de l'organisateur. Le plancher à 1 est une ceinture : un lecteur qui
    répondrait `0` (le suisse le faisait, sous deux tireurs) ferait réapparaître le « zéro tour »
    que cette US supprime, et le repli `else 1` ne joue que quand le lecteur est **absent**. Les
    deux gardes ont été posées sur relevé de revue (axes B, C1).

    ⚠️ **Limite connue** : une phase **en tableau** dont la tranche d'entrée est indéterminable
    (plusieurs sources) ne produit aucun braquet et retombe donc sur `1`, ce qui est faux — elle en
    compte autant que son arbre. Sans effet visible aujourd'hui (`nb_tours` n'est rendu par aucun
    écran), mais `E05US033` consommera ce champ : à reprendre là-bas, où le besoin le nommera.
    """
    remplis = tuple(
        AvancementTour(
            tour=braquet.tour,
            duels_attendus=braquet.duels,
            duels_joues=min(max(0, joues_par_tour.get(braquet.tour, 0)), braquet.duels),
        )
        for braquet in tours
    )
    demarree = statut in STATUTS_DEMARRES
    lu = avancement_lu if demarree else None
    return AvancementBloc(
        ordre=ordre,
        statut=statut,
        tours=remplis,
        tour_courant=(
            tour_courant(statut, remplis)
            if remplis
            else (lu.tour_courant if lu is not None else None)
        ),
        nb_tours=(
            len(remplis)
            if remplis
            else max(1, avancement_lu.nb_tours if avancement_lu is not None else 1)
        ),
        duels_joues=sum(t.duels_joues for t in remplis),
        duels_attendus=sum(t.duels_attendus for t in remplis),
    )


def tour_courant(statut: StatutPhase, tours: Sequence[AvancementTour]) -> int | None:
    """Le **premier tour non terminé** d'une phase démarrée, ou `None`.

    « Non terminé » et non « entamé » : entre deux tours, l'organisateur veut lire « on attaque les
    quarts », pas « rien en cours » — et c'est exactement ce que le feu vert d'E12US002 s'apprête à
    lancer. Rend `None` quand tous les duels sont tranchés : plus rien ne tourne, même si la phase
    n'est pas encore clôturée.
    """
    if statut not in STATUTS_DEMARRES:
        return None
    for tour in tours:
        if not tour.est_termine:
            return tour.tour
    return None


@dataclass(frozen=True)
class AvancementDeroule:
    """Le déroulé d'une édition, phase par phase, avec la phase qui tourne.

    Le pendant *live* de `domain.deroule.ProjectionDeroule` : celle-ci porte le dessin (blocs,
    flèches, braquets), celui-ci le remplissage. L'écran les superpose ; ils ne fusionnent pas, pour
    que la projection reste **la même** à l'atelier et au pilotage.
    """

    blocs: tuple[AvancementBloc, ...]

    @property
    def ordre_courant(self) -> int | None:
        """L'ordre de la phase en cours — la première démarrée non terminée.

        Une seule phase tourne en pratique, mais rien ne l'impose dans le modèle (l'organisateur
        peut avoir démarré la suivante avant de clôturer la précédente) : on rend la **première**,
        celle qui doit se refermer d'abord.
        """
        for bloc in self.blocs:
            if bloc.statut in STATUTS_DEMARRES:
                return bloc.ordre
        return None
