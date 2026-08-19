"""L'**arrêt programmé** — couper le déroulé à la fin d'un tour ([ADR-0091], E05US033).

Le besoin du commanditaire n'est pas « déclencher chaque tour à la main » mais « **pouvoir
couper** » : une phase qui dure des heures doit pouvoir s'interrompre pour le repas, une
réorganisation de salle, une annonce. L'enchaînement **automatique reste donc le défaut** — une
phase sans arrêt programmé se comporte exactement comme avant cette US.

**Deux natures, délibérément séparées** ([ADR-0076] appliqué à la lettre) :

- `ArretProgramme` est une **définition** : « après le tour 3, portée départ ». Elle se pose à
  l'atelier, elle vit sur l'`EtapeDeroule` du tournoi comme le réglage de poules ou de suisse, et
  **tous les départs du tournoi la rejouent**. C'est le sens d'ADR-0076 : le déroulé se définit une
  fois, chaque créneau le rejoue — deux départs qui pourraient diverger sur leurs pauses seraient
  exactement la divergence silencieuse que cet ADR a rendue impossible.
- `FranchissementArret` est un **état d'avancement** : « cet arrêt-ci a coupé cette phase-là, et
  l'admin l'a relevé ». Il est propre au créneau, il vit dans sa propre table, et il est
  **persisté** — pas dérivé.

⚠️ **Pourquoi le franchissement doit être persisté**, alors que tout le reste de l'avancement est
dérivé à la lecture ([ADR-0090] §5) : parce que la condition de déclenchement est **monotone**. Une
fois le tour 2 achevé, « le tour 2 est achevé et un arrêt est posé après le tour 2 » reste vrai pour
toujours. Un déclencheur qui relirait cette condition sans mémoire remettrait la phase en pause à la
seconde suivant chaque reprise : l'organisateur perdrait la main **définitivement**, et la salle ne
repartirait jamais. La trace n'est donc pas un confort d'implémentation, c'est ce qui rend la
reprise possible.

**Pourquoi un état `ARME` intermédiaire.** Un arrêt de portée départ *« laisse chaque phase finir
son tour en cours »* (arbitrage du commanditaire, 18/08/2026) : il n'est **pas simultané**. Il faut
donc un moment où l'arrêt est décidé sans être encore appliqué partout — la salle s'éteint en
quelques minutes, pas d'un coup. Et comme aucun événement « tour fini » n'est écrit nulle part, on
note à l'armement le tour que chaque phase a en cours, et l'on constate qu'il est fini quand il a
**changé**. C'est la seule formulation compatible avec un avancement dérivé.

Module **pur et synchrone** (règle 1) : aucune lecture, aucun état, aucune horloge.

[ADR-0076]: ../../docs/adr/0076-la-definition-du-deroule-est-portee-par-le-tournoi.md
[ADR-0090]: ../../docs/adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md
[ADR-0091]: ../../docs/adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, replace
from enum import Enum

from domain.erreurs import ArretProgrammeInvalide
from domain.phase import PhaseId

__all__ = [
    "ArretProgramme",
    "EtatFranchissement",
    "FranchissementArret",
    "PorteeArret",
    "arrets_atteints",
    "phases_a_arreter",
    "verifier_arrets",
]


class PorteeArret(str, Enum):
    """Ce que l'arrêt éteint : cette phase seule, ou tout ce qui tire dans le créneau.

    Le **départ** est la portée sportive du projet ([ADR-0075]) et correspond à « ce qui tire en
    salle en ce moment ». Le statut du **tournoi** n'est pas une portée d'arrêt : il a déjà sa
    propre pause, à une autre maille (ADR-0026 §3), et la confondre avec celle-ci mélangerait « la
    salle s'arrête dix minutes » et « la compétition est suspendue ».

    [ADR-0075]: ../../docs/adr/0075-le-depart-est-la-portee-sportive.md
    """

    PHASE = "phase"
    DEPART = "depart"


class EtatFranchissement(str, Enum):
    """Où en est un arrêt qui a été atteint. Cycle **monotone**, comme celui d'une phase (ADR-0045).

    - `ARME` — le tour déclencheur est atteint ; les phases concernées s'arrêteront à la fin de leur
      tour courant. État transitoire, et seul un arrêt de portée **départ** y séjourne : un arrêt de
      portée phase est franchi d'emblée, puisque le tour qui vient de s'achever est le sien.
    - `FRANCHI` — toutes les phases concernées sont en pause. L'arrêt attend un geste d'admin.
    - `LEVE` — l'admin a relancé. L'arrêt est consommé et **ne se redéclenche plus jamais** ; la
      phase repart en automatique jusqu'au prochain arrêt.

    ⚠️ Il n'y a **pas** d'état « programmé » : c'est l'**absence** de franchissement. Un état de
    plus dupliquerait une information que la table porte déjà par une ligne manquante, et obligerait
    à écrire une ligne par arrêt dès la composition — donc à ré-écrire l'avancement de tous les
    créneaux à chaque édition du déroulé, ce qu'ADR-0076 a précisément supprimé.
    """

    ARME = "arme"
    FRANCHI = "franchi"
    LEVE = "leve"


@dataclass(frozen=True)
class ArretProgramme:
    """Une coupe **prévue** : après quel tour, et jusqu'où elle porte.

    Pas d'identifiant : un arrêt est identifié par son `apres_tour` au sein de son étape, et deux
    arrêts après le même tour sont refusés (`verifier_arrets`). C'est la même économie que
    `SourcePhase` — un value object de configuration, pas une entité.
    """

    apres_tour: int
    portee: PorteeArret = PorteeArret.PHASE

    def __post_init__(self) -> None:
        """Fait respecter l'invariant quelle que soit la porte d'entrée (`replace()` compris)."""
        if self.apres_tour < 1:
            raise ArretProgrammeInvalide(
                f"un arrêt se pose après un tour existant, pas après le tour {self.apres_tour}"
            )


@dataclass(frozen=True)
class FranchissementArret:
    """La trace d'un arrêt **atteint** dans un créneau donné, et de ce qu'il a coupé.

    `phase_id` est la phase **déclenchante** — celle qui portait l'arrêt et dont le tour s'est
    achevé. `apres_tour` désigne l'arrêt dans la définition de son étape : le couple
    (`phase_id`, `apres_tour`) est donc l'identité fonctionnelle, et c'est lui qui porte l'unicité
    en base.

    `tours_a_finir` n'est peuplé que pour une portée **départ** : c'est la photo, prise à
    l'armement, du tour que chaque autre phase avait en cours. Une paire `(phase, None)` dit « cette
    phase n'avait plus rien en cours » — elle s'arrête donc immédiatement.
    """

    phase_id: PhaseId
    apres_tour: int
    etat: EtatFranchissement
    tours_a_finir: tuple[tuple[PhaseId, int | None], ...] = ()
    phases_arretees: tuple[PhaseId, ...] = ()
    id: int | None = None

    def franchir(self, phases_arretees: Sequence[PhaseId]) -> FranchissementArret:
        """Constate que toutes les phases concernées sont en pause.

        Refuse de revenir d'un arrêt déjà `LEVE` : le cycle est monotone. Sans ce refus, une
        évaluation du déclencheur tombant après une reprise re-franchirait l'arrêt, ce qui est
        exactement la boucle infinie que l'en-tête de ce module décrit.
        """
        if self.etat is EtatFranchissement.LEVE:
            raise ArretProgrammeInvalide(
                "un arrêt levé ne se re-franchit pas : la phase est repartie en automatique"
            )
        return replace(
            self, etat=EtatFranchissement.FRANCHI, phases_arretees=tuple(phases_arretees)
        )

    def lever(self) -> FranchissementArret:
        """Le geste de l'admin : la salle repart. Les phases à relancer sont `phases_arretees`.

        Refuse un second levage — un arrêt déjà consommé n'a plus de phase à rendre, et le tolérer
        ferait d'un double-clic une relance de phases que l'organisateur avait suspendues depuis.
        """
        if self.etat is EtatFranchissement.LEVE:
            raise ArretProgrammeInvalide("cet arrêt a déjà été levé")
        return replace(self, etat=EtatFranchissement.LEVE)


def verifier_arrets(arrets: Sequence[ArretProgramme], nb_tours: int | None = None) -> None:
    """Vérifie qu'une **liste** d'arrêts est applicable. Lève `ArretProgrammeInvalide` sinon.

    Les invariants d'un arrêt seul sont à son `__post_init__` ; ceux du **couple** (deux arrêts
    entre eux, un arrêt face au nombre de tours) sont ici, là où l'information existe. C'est la
    même répartition que `ConfigurationSuisse` face à `EtapeDeroule._verifier_rondes_appariables` :
    le réglage refuse ce qu'il peut juger seul, l'étape refuse ce qui dépend de son contexte.

    `nb_tours=None` signifie « inconnu » et ne déclenche aucun refus : un système suisse réglé à
    7 rondes n'en joue que 5 si l'effectif ne permet pas plus, et l'atelier ne connaît pas toujours
    l'effectif. On ne refuse pas ce qu'on ne peut pas juger.
    """
    tours = [arret.apres_tour for arret in arrets]
    doublons = {tour for tour in tours if tours.count(tour) > 1}
    if doublons:
        pluriel = "s" if len(doublons) > 1 else ""
        liste = ", ".join(str(tour) for tour in sorted(doublons))
        raise ArretProgrammeInvalide(
            f"deux arrêts sont posés après le{pluriel} même{pluriel} tour{pluriel} {liste} : "
            "la phase ne peut pas être mise en pause deux fois au même endroit"
        )
    if nb_tours is None:
        return
    inertes = sorted(tour for tour in tours if tour >= nb_tours)
    if inertes:
        liste = ", ".join(str(tour) for tour in inertes)
        raise ArretProgrammeInvalide(
            f"un arrêt posé après le tour {liste} ne couperait rien : la phase n'en compte que "
            f"{nb_tours}, elle est terminée à ce moment-là"
        )


def arrets_atteints(
    arrets: Sequence[ArretProgramme],
    tour_acheve: int,
    deja_traites: Collection[int],
) -> tuple[ArretProgramme, ...]:
    """Les arrêts **dus** maintenant que `tour_acheve` est fini, du plus ancien au plus récent.

    `deja_traites` porte les `apres_tour` des arrêts qui ont déjà un franchissement, **quel qu'en
    soit l'état** — `ARME`, `FRANCHI` ou `LEVE`. C'est la mémoire qui empêche la boucle décrite en
    tête de module.

    ⚠️ **Le test est `<=`, pas `==`**, et c'est un choix. Rien ne garantit que le déclencheur soit
    évalué à chaque frontière de tour : une correction en cascade, un lot de validations ou une
    phase reprise après incident peuvent faire passer le tour courant de 2 à 5 entre deux
    évaluations. Comparer par égalité perdrait alors silencieusement les arrêts intermédiaires —
    l'organisateur aurait programmé trois pauses et n'en verrait aucune. On les rend tous : le
    service n'appliquera qu'une pause (la phase ne peut être en pause qu'une fois) mais marquera les
    autres traités, ce qui est la lecture honnête — ces pauses-là ont été **manquées**, pas
    annulées.
    """
    traites = set(deja_traites)
    return tuple(
        sorted(
            (
                arret
                for arret in arrets
                if arret.apres_tour <= tour_acheve and arret.apres_tour not in traites
            ),
            key=lambda arret: arret.apres_tour,
        )
    )


def phases_a_arreter(
    tours_a_finir: Mapping[PhaseId, int | None],
    tours_courants: Mapping[PhaseId, int | None],
) -> tuple[PhaseId, ...]:
    """Parmi les phases qu'un arrêt de départ doit couper, celles qui ont fini leur tour.

    Une phase a fini son tour quand son tour courant n'est **plus** celui noté à l'armement. Deux
    cas s'y ajoutent, et tous deux comptent comme « finie » :

    - `tours_a_finir[phase] is None` — elle n'avait déjà plus rien en cours à l'armement (convention
      d'`AvancementDePhase`, ADR-0090 : tout est joué même si la phase n'est pas clôturée). Lui
      faire attendre un changement qui ne viendra jamais la laisserait `EN_COURS` pour l'éternité,
      et l'arrêt resterait `ARME` sans jamais devenir relançable ;
    - la phase a disparu de `tours_courants` — clôturée à la main pendant l'armement (E12US008).
    Elle
      n'a plus d'avancement à lire ; l'attendre ferait d'un geste de clôture légitime un gel de la
      reprise.

    Rendu **trié par identifiant** pour que deux évaluations successives produisent la même liste :
    un ordre instable rendrait les diffs de trace illisibles et les tests dépendants du hasard.
    """
    return tuple(
        sorted(
            phase_id
            for phase_id, tour_a_finir in tours_a_finir.items()
            if tour_a_finir is None
            or phase_id not in tours_courants
            or tours_courants[phase_id] != tour_a_finir
        )
    )
