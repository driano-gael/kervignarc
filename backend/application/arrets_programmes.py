"""Service applicatif **Arrêts programmés** — la salle peut s'arrêter (E05US033, [ADR-0091]).

Trois cas d'usage, et un seul écrit :

- **`evaluer`** — le **déclencheur**. Appelé après chaque validation de score, il regarde où en est
  chaque phase du créneau et met en pause celles dont un arrêt programmé vient d'être atteint.
  Idempotent : rappelé sans que rien n'ait changé, il ne fait rien.
- **`lever`** — le **geste de l'admin**. La salle repart, et un arrêt de portée départ relance
  **toutes** les phases qu'il a coupées d'un seul geste.
- **`en_attente_de_relance`** — la lecture que le pilotage affiche : les arrêts franchis et pas
encore
  levés.

**Pourquoi un service et non un automate.** Le projet ne persiste pas l'avancement : chaque service
de format le **recalcule à la lecture** (ADR-0090 §5), et le lancement d'un tour est un *événement*,
pas un état (ADR-0056). Il n'existe donc aucun endroit où l'on pourrait accrocher « le tour vient de
se terminer ». Ce service **constate** au lieu d'écouter : il compare le tour courant de chaque
phase à ce que les arrêts attendent, et n'écrit que la trace du franchissement.

⚠️ **La couture d'avancement passe par `ServiceSuiviDeroule`, délibérément.** C'est le seul endroit
du projet qui sait répondre « quel tour tourne » pour **tous** les formats : les poules, le suisse
et le Big Shoot Off répondent par le port `LecteurAvancementDePhase`, mais l'élimination directe —
le format le plus courant — n'a pas de lecteur et voit son avancement reconstruit sur place à partir
des braquets. Tenir ici un second registre par type aurait donc, d'une part, laissé le tableau hors
du mécanisme, et d'autre part été la **quatrième** occurrence d'une résolution par type — ce dont la
docstring du port met explicitement en garde.

**Coût de lecture assumé, et tracé** : la couture d'avancement recompose chaque phase qui tourne à
chaque appel, et ce service l'appelle après chaque validation de score. `DETTE-031` est élargie en
conséquence — le marqueur est posé au point d'appel, pas ici.

[ADR-0056]: ../docs/adr/0056-le-lancement-est-un-evenement-pas-un-etat.md
[ADR-0090]: ../docs/adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md
[ADR-0091]: ../docs/adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md
"""

from __future__ import annotations

import logging
from typing import Protocol

from application.erreurs import ArretIntrouvable
from application.phases import ServicePhases
from domain.arret_programme import (
    ArretProgramme,
    EtatFranchissement,
    FranchissementArret,
    PorteeArret,
    arrets_atteints,
    phases_a_arreter,
)
from domain.depart import DepartId
from domain.deroule_etape import EtapeDeroule
from domain.phase import Phase, PhaseId, StatutPhase
from domain.ports import (
    DepartRepository,
    DerouleRepository,
    FranchissementArretRepository,
    PhaseRepository,
)
from domain.suivi_deroule import AvancementDePhase

_logger = logging.getLogger(__name__)


class LecteurAvancementDuDepart(Protocol):
    """Port étroit : « quel tour tourne dans chaque phase de ce créneau ? ».

    Réalisé par `ServiceSuiviDeroule`, et **volontairement plus large d'une maille** que
    `LecteurAvancementDePhase` : c'est le créneau entier qu'il faut, en un seul passage. Demander
    phase par phase obligerait ce service à connaître le cas particulier du tableau — dont personne
    ne réalise le port par phase — et rouvrirait la résolution par type que l'en-tête écarte.
    """

    def avancement_par_phase(self, depart_id: DepartId) -> dict[PhaseId, AvancementDePhase]:
        """L'avancement de chaque phase du créneau, par identifiant de phase."""
        ...


class EvaluateurArrets(Protocol):
    """Port étroit dans l'autre sens : « quelque chose vient d'être validé dans ce créneau ».

    Réalisé par `ServiceArretsProgrammes` et consommé par les services de **saisie**, qui sont les
    seuls à savoir qu'un résultat vient d'être écrit. Un port plutôt qu'une dépendance au service
    entier : la saisie n'a pas à connaître les arrêts, seulement à **signaler**. C'est le même parti
    que `DiffusionSimulation` (ADR-0055 §5).

    Branché **tardivement** au composition root (`brancher_evaluateur_arrets`), comme
    `ServiceSuiviDeroule.brancher_lecteur_avancement` : ce service est construit après la saisie, et
    un cycle qu'on ne voit pas est un cycle qu'on réintroduit.
    """

    def evaluer(self, depart_id: DepartId) -> tuple[PhaseId, ...]:
        """Applique les arrêts devenus dus et renvoie les phases mises en pause."""
        ...


class ServiceArretsProgrammes:
    """Cas d'usage : « la salle s'arrête après ce tour, et repart quand je le dis »."""

    def __init__(
        self,
        phases: PhaseRepository,
        deroules: DerouleRepository,
        departs: DepartRepository,
        franchissements: FranchissementArretRepository,
        suivi: LecteurAvancementDuDepart,
        cycle_de_vie: ServicePhases,
    ) -> None:
        self._phases = phases
        self._deroules = deroules
        self._departs = departs
        self._franchissements = franchissements
        self._suivi = suivi
        # ⚠️ **Le cycle de vie n'est pas réimplémenté ici** : `mettre_en_pause` et `reprendre` sont
        # les transitions gardées d'ADR-0045, et ce service les **appelle** (service→service, sur le
        # précédent de `ServicePilotageTour`). Muter le statut à la main dupliquerait l'automate, et
        # un automate en double finit toujours par diverger — c'est la leçon d'ADR-0076 appliquée au
        # comportement plutôt qu'à la donnée.
        self._cycle_de_vie = cycle_de_vie

    # --- Lecture ------------------------------------------------------------------------------

    def en_attente_de_relance(self, depart_id: DepartId) -> tuple[FranchissementArret, ...]:
        """Les arrêts **franchis et pas encore levés** de ce créneau : ce qui attend un geste.

        Ni les `ARME` — la coupe est décidée, pas faite : une phase finit son tour, et annoncer une
        relance possible ferait cliquer l'organisateur sur un bouton qui n'a rien à rendre — ni les
        `LEVE`, qui sont consommés.
        """
        return tuple(
            franchissement
            for franchissement in self._franchissements.par_depart(depart_id)
            if franchissement.etat is EtatFranchissement.FRANCHI
        )

    # --- Le déclencheur -----------------------------------------------------------------------

    def evaluer(self, depart_id: DepartId) -> tuple[PhaseId, ...]:
        """Applique les arrêts devenus dus. Renvoie les phases **mises en pause par cet appel**.

        Deux passes, dans cet ordre, et l'ordre compte :

        1. les arrêts déjà **armés** — un arrêt de portée départ attend que chaque phase finisse son
           tour. Passer en premier évite qu'un arrêt neuf ne prenne en photo un créneau où une phase
           aurait dû être arrêtée depuis la passe précédente ;
        2. les arrêts **atteints à l'instant**, phase par phase.

        Idempotent : sans changement d'avancement, le second appel ne trouve plus rien à faire, la
        mémoire étant portée par les franchissements persistés.
        """
        phases = {
            phase.id: phase for phase in self._phases.par_depart(depart_id) if phase.id is not None
        }
        if not phases:
            return ()
        # DETTE-031 : cette lecture recompose **intégralement** chaque phase qui tourne, chaîne de
        # sources amont comprise (`ServicePoules.etat` / `ServiceSuisse.etat` /
        # `ServiceBigShootOff.etat` et la reconstruction du tableau). Jusqu'ici seuls le pilotage et
        # l'écran de salle la payaient, toutes les 10 s ; ce service la paie après **chaque
        # validation de score**. Le facteur d'appel a donc changé de nature. L'ordre de grandeur
        # reste tenable — une ou deux phases actives par créneau, ~30 tablettes, SQLite en local,
        # aucune I/O réseau — et la dette est **élargie** plutôt que contournée par une mémoïsation
        # locale, qui serait un remède structurel posé au mauvais endroit (§ Dette). Cf.
        # docs/dette.md.
        tours = {
            phase_id: avancement.tour_courant
            for phase_id, avancement in self._suivi.avancement_par_phase(depart_id).items()
        }
        arretees: list[PhaseId] = []
        arretees.extend(self._resoudre_les_arrets_armes(depart_id, phases, tours))
        arretees.extend(self._declencher_les_arrets_atteints(depart_id, phases, tours))
        return tuple(arretees)

    def _resoudre_les_arrets_armes(
        self,
        depart_id: DepartId,
        phases: dict[PhaseId, Phase],
        tours: dict[PhaseId, int | None],
    ) -> list[PhaseId]:
        """Arrête les phases d'un arrêt armé qui viennent de finir leur tour, et clôt l'arrêt.

        Une phase déjà en pause n'est pas re-mise en pause mais **compte** comme arrêtée : c'est ce
        qui permet à l'arrêt de passer à `FRANCHI` au tour suivant sans attendre un changement qui
        n'aura plus lieu.
        """
        arretees: list[PhaseId] = []
        for franchissement in self._franchissements.par_depart(depart_id):
            if franchissement.etat is not EtatFranchissement.ARME:
                continue
            attendues = dict(franchissement.tours_a_finir)
            finies = phases_a_arreter(attendues, tours)
            deja_en_pause = list(franchissement.phases_arretees)
            for phase_id in finies:
                if phase_id in deja_en_pause:
                    continue
                if self._mettre_en_pause(depart_id, phases.get(phase_id)):
                    arretees.append(phase_id)
                deja_en_pause.append(phase_id)
            if len(finies) == len(attendues):
                self._franchissements.enregistrer(franchissement.franchir(deja_en_pause))
            elif deja_en_pause != list(franchissement.phases_arretees):
                # Encore armé, mais on retient déjà ce qui est arrêté : sans cette écriture
                # intermédiaire, une phase arrêtée puis reprise à la main sortirait de la liste de
                # relance, et le geste d'admin ne la rendrait jamais.
                self._franchissements.enregistrer(
                    FranchissementArret(
                        phase_id=franchissement.phase_id,
                        apres_tour=franchissement.apres_tour,
                        etat=EtatFranchissement.ARME,
                        tours_a_finir=franchissement.tours_a_finir,
                        phases_arretees=tuple(deja_en_pause),
                        id=franchissement.id,
                    )
                )
        return arretees

    def _declencher_les_arrets_atteints(
        self,
        depart_id: DepartId,
        phases: dict[PhaseId, Phase],
        tours: dict[PhaseId, int | None],
    ) -> list[PhaseId]:
        """Repère les arrêts que l'avancement vient d'atteindre, et les applique."""
        etapes = self._etapes_du_depart(depart_id)
        deja = self._traites_par_phase(depart_id)
        arretees: list[PhaseId] = []
        for phase_id, phase in phases.items():
            if phase.statut is not StatutPhase.EN_COURS:
                continue
            etape = etapes.get(phase.ordre)
            if etape is None or not etape.arrets:
                continue
            tour_acheve = self._tour_acheve(tours.get(phase_id), etape, phase_id)
            if tour_acheve is None:
                continue
            dus = arrets_atteints(etape.arrets, tour_acheve, deja.get(phase_id, ()))
            if not dus:
                continue
            arretees.extend(self._appliquer(depart_id, phase_id, phases, tours, dus))
        return arretees

    def _appliquer(
        self,
        depart_id: DepartId,
        phase_id: PhaseId,
        phases: dict[PhaseId, Phase],
        tours: dict[PhaseId, int | None],
        dus: tuple[ArretProgramme, ...],
    ) -> list[PhaseId]:
        """Applique **un seul** arrêt — le plus ancien dû — et consomme les autres.

        ⚠️ **Une phase ne peut pas être mise en pause deux fois.** Quand plusieurs arrêts sont dus
        au même instant (l'avancement a sauté plusieurs tours entre deux évaluations : correction en
        cascade, lot de validations, reprise après incident), on crédite le **plus ancien** — c'est
        la pause que l'organisateur voulait, appliquée en retard — et l'on **consomme** les
        suivants.

        Les laisser en attente serait le piège : ils se déclencheraient l'un après l'autre à chaque
        reprise, et l'organisateur devrait relancer trois fois pour une seule coupe. Ils sont donc
        marqués `LEVE` sans avoir rien arrêté, et **journalisés** : une pause manquée est un fait
        d'exploitation, pas un détail. La rendre visible à l'écran est le périmètre d'`E05US034`.
        """
        applique, *manques = dus
        arretees: list[PhaseId] = []
        if applique.portee is PorteeArret.PHASE:
            if self._mettre_en_pause(depart_id, phases.get(phase_id)):
                arretees.append(phase_id)
            self._franchissements.ajouter(
                FranchissementArret(
                    phase_id=phase_id,
                    apres_tour=applique.apres_tour,
                    etat=EtatFranchissement.FRANCHI,
                    phases_arretees=(phase_id,),
                )
            )
        else:
            arretees.extend(self._armer_sur_le_depart(depart_id, phase_id, phases, tours, applique))
        for manque in manques:
            _logger.warning(
                "Arrêt programmé après le tour %s de la phase %s manqué : l'avancement l'a "
                "dépassé avant évaluation, il est consommé sans mise en pause.",
                manque.apres_tour,
                phase_id,
            )
            self._franchissements.ajouter(
                FranchissementArret(
                    phase_id=phase_id,
                    apres_tour=manque.apres_tour,
                    etat=EtatFranchissement.LEVE,
                )
            )
        return arretees

    def _armer_sur_le_depart(
        self,
        depart_id: DepartId,
        phase_id: PhaseId,
        phases: dict[PhaseId, Phase],
        tours: dict[PhaseId, int | None],
        arret: ArretProgramme,
    ) -> list[PhaseId]:
        """Arme un arrêt de portée départ : la phase déclenchante s'arrête, les autres finissent.

        La photo des tours à finir ne retient que les phases **en cours**, et les deux exclusions
        ont chacune leur raison :

        - une phase **à venir** n'a rien à interrompre, et la marquer gèlerait l'avenir du créneau —
          l'organisateur qui démarre une phase pendant une pause fait un geste explicite qu'on n'a
          pas à contredire ;
        - une phase **déjà en pause** — suspendue à la main pour une autre raison — est déjà
        arrêtée.
          ⚠️ **L'inclure produisait un interblocage**, trouvé par
          `test_relancer_ne_touche_pas_une_phase_suspendue_a_la_main` : son tour courant ne bouge
          plus (rien ne se joue), donc `phases_a_arreter` ne la déclare jamais finie, donc l'arrêt
          reste `ARME` **pour toujours** — et un arrêt armé n'est pas relançable. L'organisateur
          perdait la main sur tout le créneau à cause d'une phase qu'il avait suspendue lui-même. La
          première rédaction filtrait sur `STATUTS_DEMARRES` (`EN_COURS` **ou** `EN_PAUSE`), qui est
          le bon ensemble pour *lire* un avancement et le mauvais pour *décider d'arrêter*.

        La phase déclenchante est notée avec `None`, c'est-à-dire « rien à finir » : son tour vient
        précisément de s'achever. C'est ce qui la fait passer en pause dès la résolution ci-dessous,
        sans cas particulier.
        """
        a_finir: dict[PhaseId, int | None] = {}
        for autre_id, autre in phases.items():
            if autre.statut is not StatutPhase.EN_COURS:
                continue
            a_finir[autre_id] = None if autre_id == phase_id else tours.get(autre_id)
        # L'écriture compte, pas la valeur rendue : la résolution ci-dessous **relit** les
        # franchissements du créneau, ce qui garantit qu'un arrêt neuf et un arrêt déjà armé suivent
        # exactement le même chemin. Garder la valeur ouvrirait deux traitements à maintenir.
        self._franchissements.ajouter(
            FranchissementArret(
                phase_id=phase_id,
                apres_tour=arret.apres_tour,
                etat=EtatFranchissement.ARME,
                tours_a_finir=tuple(a_finir.items()),
            )
        )
        # Résolution immédiate : la phase déclenchante, et toute phase qui n'avait déjà plus rien en
        # cours, s'arrêtent dans le même appel. Réutiliser la passe 1 plutôt que de dupliquer sa
        # logique garantit qu'un arrêt armé et un arrêt neuf se comportent exactement pareil.
        return self._resoudre_les_arrets_armes(depart_id, phases, tours)

    # --- Le geste de l'admin ------------------------------------------------------------------

    def lever(self, depart_id: DepartId, franchissement_id: int) -> tuple[PhaseId, ...]:
        """Relance la salle : toutes les phases coupées par cet arrêt repartent, d'un seul geste.

        `ArretIntrouvable` (→ 404) si l'identifiant est inconnu, s'il appartient à un autre créneau,
        s'il est encore `ARME` (la coupe n'est pas faite, il n'y a rien à relancer) ou s'il a déjà
        été levé — un double-clic ne doit pas relancer une seconde fois, car entre les deux clics
        l'organisateur peut avoir suspendu une phase à la main.

        Ne relance que les phases **effectivement en pause** : une phase clôturée entre-temps ne
        redémarre pas, et `reprendre` la refuserait de toute façon (ADR-0045).
        """
        franchissement = next(
            (
                item
                for item in self._franchissements.par_depart(depart_id)
                if item.id == franchissement_id and item.etat is EtatFranchissement.FRANCHI
            ),
            None,
        )
        if franchissement is None:
            raise ArretIntrouvable(
                f"Aucun arrêt à relancer sous l'identifiant {franchissement_id} dans ce créneau."
            )
        relancees: list[PhaseId] = []
        for phase_id in franchissement.phases_arretees:
            phase = self._phases.par_id(phase_id)
            if phase is None or phase.statut is not StatutPhase.EN_PAUSE:
                continue
            self._cycle_de_vie.reprendre(depart_id, phase_id)
            relancees.append(phase_id)
        self._franchissements.enregistrer(franchissement.lever())
        return tuple(relancees)

    # --- Rouages ------------------------------------------------------------------------------

    def _mettre_en_pause(self, depart_id: DepartId, phase: Phase | None) -> bool:
        """Met la phase en pause si elle est en cours. Renvoie `True` si le statut a changé.

        Silencieux sur une phase absente, déjà en pause, à venir ou terminée : le déclencheur est
        rejoué en permanence et sur un créneau qui bouge, donc il **constate** au lieu d'exiger.
        Lever `TransitionStatutInvalide` ici ferait échouer la validation de score qui l'a appelé —
        un archer verrait sa volée refusée parce qu'une phase voisine a été clôturée entre-temps.
        """
        if phase is None or phase.id is None or phase.statut is not StatutPhase.EN_COURS:
            return False
        self._cycle_de_vie.mettre_en_pause(depart_id, phase.id)
        return True

    def _etapes_du_depart(self, depart_id: DepartId) -> dict[int, EtapeDeroule]:
        """Le déroulé du tournoi de ce créneau, indexé par rang (ADR-0076)."""
        depart = self._departs.par_id(depart_id)
        if depart is None:
            return {}
        return {etape.ordre: etape for etape in self._deroules.par_tournoi(depart.tournoi_id)}

    def _traites_par_phase(self, depart_id: DepartId) -> dict[PhaseId, tuple[int, ...]]:
        """Pour chaque phase, les `apres_tour` déjà franchis — **quel qu'en soit l'état**.

        `ARME`, `FRANCHI` et `LEVE` comptent tous les trois. C'est la mémoire qui empêche un arrêt
        levé de se redéclencher, et donc la salle de se rebloquer aussitôt relancée.
        """
        traites: dict[PhaseId, list[int]] = {}
        for franchissement in self._franchissements.par_depart(depart_id):
            traites.setdefault(franchissement.phase_id, []).append(franchissement.apres_tour)
        return {phase_id: tuple(tours) for phase_id, tours in traites.items()}

    @staticmethod
    def _tour_acheve(
        tour_courant: int | None, etape: EtapeDeroule, phase_id: PhaseId
    ) -> int | None:
        """Quel tour vient de s'achever, sachant le tour en cours. `None` si aucun.

        `tour_courant is None` signifie « plus rien ne tourne » (ADR-0090) : tout est joué, donc le
        tour achevé est le **dernier**. On le prend comme le plus grand arrêt programmé plutôt que
        comme un nombre de tours qu'on ne connaît pas ici — c'est suffisant pour que tout arrêt
        restant soit dû, et cela évite de faire descendre `nb_tours` dans cette fonction pour un
        résultat identique.

        Au tour 1 en cours, aucun tour n'est achevé : la phase vient de démarrer.
        """
        if tour_courant is None:
            return max(arret.apres_tour for arret in etape.arrets)
        if tour_courant <= 1:
            return None
        return tour_courant - 1
