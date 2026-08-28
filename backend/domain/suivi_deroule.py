"""Superpose ce qui est **fait** à ce que la projection dit **attendu** — sans rien recalculer.

⚠️ **Un suivi qui recalculerait les duels attendus pourrait diverger du schéma que l'atelier a
montré**, alors que le CA demande *le même* schéma. C'est aussi ce qui évite de dupliquer un
invariant du moteur. La « réalité » arrive donc en paramètre, dénombrée par le service.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from domain.bareme import BaremeQualification
from domain.deroule import TourBraquet
from domain.phase import StatutPhase
from domain.qualification import DecoupageEnTours, volees_par_tour

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

    « Joué » = disputé et tranché. ⚠️ **Les exempts (byes) ne sont pas comptés** : ils occupent une
    place du braquet mais ne sont pas des duels, et la projection ne les compte pas davantage
    (`domain.deroule._braquets`). C'est **le** piège de ce module — les compter afficherait «
    premier tour terminé » avant que quiconque ait tiré.
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
    """*Où en est cette phase ?* — la réponse d'un service de format (ADR-0090 §5).

    Deux nombres : combien de tours cette phase compte **aujourd'hui** (un suisse réglé à 7 rondes
    n'en joue que 5 si l'effectif ne permet pas plus), et lequel tourne. Le **libellé** ne passe
    pas par ici : il se résout du type de phase (`domain.tour_de_phase`). `tour_courant` vaut
    `None` quand plus rien ne tourne — même convention que `tour_courant()` plus bas, délibérément.
    """

    nb_tours: int
    tour_courant: int | None


def avancement_de_qualification(
    volees_du_plus_lent: int,
    bareme: BaremeQualification,
    decoupage: DecoupageEnTours | None,
) -> AvancementDePhase:
    """*Où en est cette qualification ?* — sa réponse au port `LecteurAvancementDePhase`.

    `volees_du_plus_lent` compte les volées **saisies** par l'archer le moins avancé, non validées
    : un tour est fini quand la salle a **tiré**, pas quand le scoreur a signé. ⚠️ **Ce compte
    DIVERGE de celui d'`avancement_cible` depuis E05US035, et c'est assumé** : la console compte le
    cardinal, ce lecteur reçoit le **préfixe contigu** (`ServiceSaisie._volees_enchainees`), sans
    quoi une volée hors d'ordre franchirait une frontière de tour et déclencherait un arrêt.
    """
    par_tour = volees_par_tour(bareme, decoupage)
    nb_tours = decoupage.nb_tours if decoupage is not None else 1
    if par_tour < 1:
        # Défensif : `verifier_decoupage` interdit ce cas à la composition, mais un barème relu
        # d'une base plus ancienne pourrait le produire. ⚠️ **`nb_tours=1` et non
        # `decoupage.nb_tours`** — la nuance décide de couper la salle : `(nb_tours > 1,
        # tour_courant=None)` est lu par `ServiceArretsProgrammes` comme « je sais, et tout est
        # joué », et les arrêts seraient consommés en « manqués ». `(1, None)` = « je ne sais pas ».
        return AvancementDePhase(nb_tours=1, tour_courant=None)
    tour = volees_du_plus_lent // par_tour + 1
    return AvancementDePhase(nb_tours=nb_tours, tour_courant=tour if tour <= nb_tours else None)


@dataclass(frozen=True)
class AvancementBloc:
    """L'avancement d'une phase : son statut, ses braquets remplis, et le tour qui tourne.

    ⚠️ **`nb_tours` n'est pas `len(tours)`** (ADR-0090). `tours` porte les **braquets** — les
    tranches de rangs qu'un tableau attribue au fil de l'eau —, et une phase qui ne classe pas au
    fil de l'eau n'en a aucun tout en avançant par tours. Dériver l'un de l'autre est ce que ce
    module faisait jusqu'à E05US032 : toute phase hors tableau s'affichait à « zéro tour ».
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

    `joues_par_tour` est indexé par **numéro de tour** (1-based) ; un compte supérieur à l'attendu
    est **plafonné**, un tour inconnu de la projection **ignoré**. Une phase sans braquet avance
    quand même (ADR-0090) — ⚠️ le braquet **prime** sur le lu quand il existe, `nb_tours` ne
    descend jamais sous 1 et `tour_courant` est filtré par le statut. ⚠️ `# DETTE-074` : un tableau
    à tranche d'entrée indéterminable retombe sur `(1, None)`, son arrêt programmé ne part jamais.
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
