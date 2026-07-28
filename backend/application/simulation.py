"""Service applicatif Simulation — rejouer le moteur **sans rien persister** (E15US002, ADR-0054).

Cœur technique d'EPIC-15 : offrir un **substrat d'exécution éphémère** du moteur (qualif → duels →
classement) sur lequel E15US003 posera le bot pilote et le cockpit. La simulation câble les
**mêmes** services applicatifs (`ServiceClassement`, `ServicePlacementDuels`, `ServiceSaisieDuels`)
et les **mêmes** politiques (serpent / byes / élimination sèche) que la production, mais sur un jeu
d'adapters **in-memory** au lieu des adapters SQL : « ne rien persister » devient une propriété
**structurelle** — aucun chemin de ces adapters vers SQLite ni vers la file d'écriture (règle 7).

**Application sans infrastructure (convention du projet).** Ce service n'importe **aucun** adapter
concret : la composition root (règle 8) lui injecte une **usine** (`usine_harnais`) qui fabrique un
`HarnaisSimulation` vierge — le seul point qui connaît les adapters in-memory et les politiques par
défaut. Le service **remplit** ce harnais (hydratation) puis fait tourner ses services.

**Garde-fou (ADR-0054 §4).** On ne simule qu'un tournoi **avant démarrage** (`brouillon`/`prêt`) :
lancer une simulation sur un tournoi démarré/figé lève `SimulationTournoiDemarre` (409) — même
borne, même raison que `PeuplementTournoiDemarre` d'E15US001 (« ne pollue jamais le réel »).

**Hydratation par les ports.** L'hydratation lit le tournoi réel via les ports (lecture hors file,
règle 7) et recopie dans le harnais en **préservant les identifiants** (intégrité). Duels, plans de
duels et forfaits ne sont **pas** hydratés : le garde-fou garantit un tournoi avant démarrage, où
ils sont toujours vides (ils naissent du jeu, absent avant `en_cours`).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from application.classements import ServiceClassement
from application.erreurs import SimulationTournoiDemarre, TournoiIntrouvable
from application.placement_duels import ServicePlacementDuels
from application.saisie_duels import EtatTableau, ServiceSaisieDuels
from domain.classement import Classement
from domain.erreurs import EffectifTableauInvalide
from domain.phase import TypePhase
from domain.ports import (
    ArcherRepository,
    BlasonRepository,
    CategorieRepository,
    GabaritSalleRepository,
    InscriptionRepository,
    PhaseRepository,
    SerieRepository,
    TournoiRepository,
)
from domain.tournoi import StatutTournoi, Tournoi, TournoiId

# Statuts simulables : **avant démarrage** seulement (ADR-0054 §4), comme le peuplement (E15US001).
_STATUTS_SIMULABLES = frozenset({StatutTournoi.BROUILLON, StatutTournoi.PRET})


@dataclass(frozen=True)
class HarnaisSimulation:
    """Un jeu d'adapters in-memory **vierge** + les services moteur câblés dessus.

    Fabriqué par la composition root (règle 8) à chaque simulation — un harnais neuf par appel, pas
    de fuite d'état entre deux simulations. `ServiceSimulation` remplit les repositories
    (hydratation) puis exécute les trois services, sans jamais connaître les adapters concrets.
    """

    tournois: TournoiRepository
    archers: ArcherRepository
    categories: CategorieRepository
    blasons: BlasonRepository
    gabarits: GabaritSalleRepository
    inscriptions: InscriptionRepository
    phases: PhaseRepository
    series: SerieRepository
    classement: ServiceClassement
    placement_duels: ServicePlacementDuels
    saisie_duels: ServiceSaisieDuels


@dataclass(frozen=True)
class ResultatSimulation:
    """L'état **éphémère** d'une simulation : le classement de qualif et les tableaux joués.

    Ces objets vivent en mémoire le temps de l'appel ; rien n'est persisté. `tableaux` porte un
    `EtatTableau` par phase d'élimination directe **jouable** (vide s'il n'y a pas de phase de
    tableau, ou si aucune n'a assez de duellistes classés — cas d'un tournoi avant démarrage).
    """

    tournoi_id: TournoiId
    classement: Classement
    tableaux: tuple[EtatTableau, ...]


class ServiceSimulation:
    """Cas d'usage de la simulation : rejouer le moteur d'un tournoi non démarré, sans persister."""

    def __init__(
        self,
        tournois: TournoiRepository,
        archers: ArcherRepository,
        categories: CategorieRepository,
        blasons: BlasonRepository,
        gabarits: GabaritSalleRepository,
        inscriptions: InscriptionRepository,
        phases: PhaseRepository,
        series: SerieRepository,
        usine_harnais: Callable[[], HarnaisSimulation],
    ) -> None:
        # Repositories **réels** (SQL en production) : lecture seule, pour le garde-fou et
        # l'hydratation. Aucune écriture ne les touche.
        self._tournois = tournois
        self._archers = archers
        self._categories = categories
        self._blasons = blasons
        self._gabarits = gabarits
        self._inscriptions = inscriptions
        self._phases = phases
        self._series = series
        self._usine_harnais = usine_harnais

    def simuler(self, tournoi_id: TournoiId) -> ResultatSimulation:
        """Rejoue le moteur d'un tournoi **avant démarrage**, en mémoire, et renvoie l'état simulé.

        Lève `TournoiIntrouvable` (404) si le tournoi n'existe pas, `SimulationTournoiDemarre` (409)
        s'il est déjà démarré/figé (hors `brouillon`/`prêt`). Aucune écriture n'atteint la base
        réelle ni la file d'écriture (ADR-0054) : les repositories réels ne sont lus que pour
        hydrater un harnais in-memory jetable.
        """
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        if tournoi.statut not in _STATUTS_SIMULABLES:
            raise SimulationTournoiDemarre(
                f"Le tournoi « {tournoi.nom} » est {tournoi.statut.value} : on ne simule "
                "(rejeu éphémère du moteur) qu'un tournoi avant démarrage (brouillon ou prêt), "
                "pour ne pas interférer avec une compétition en cours ou figée."
            )

        harnais = self._usine_harnais()
        self._hydrater(tournoi_id, tournoi, harnais)

        classement = harnais.classement.pour_tournoi(tournoi_id)
        gabarit_present = harnais.gabarits.par_tournoi(tournoi_id) is not None
        tableaux: list[EtatTableau] = []
        for phase in harnais.phases.par_tournoi(tournoi_id):
            if phase.type is not TypePhase.ELIMINATION_DIRECTE or phase.id is None:
                continue
            try:
                # `regenerer` (si une salle est définie) exerce `ServicePlacementDuels` ; son plan
                # atterrit dans le harnais in-memory, jamais observé ici — exécution de « fumée ».
                # L'état du tableau, lui, est reconstruit du classement (indépendant du plan).
                if gabarit_present:
                    harnais.placement_duels.regenerer(tournoi_id, phase.id)
                tableaux.append(harnais.saisie_duels.etat_tableau(tournoi_id, phase.id))
            except EffectifTableauInvalide:
                # Tournoi *avant démarrage* : une phase de tableau peut exister alors que moins de
                # deux duellistes sont classés (personne n'a encore tiré). Elle n'est **pas encore
                # jouable** — on la saute plutôt que de faire échouer toute la simulation (le CA
                # promet « n'importe quel tournoi créé »). E15US003 la rejouera quand le bot aura
                # généré des scores.
                continue

        return ResultatSimulation(tournoi_id, classement, tuple(tableaux))

    def _hydrater(
        self, tournoi_id: TournoiId, tournoi: Tournoi, harnais: HarnaisSimulation
    ) -> None:
        """Recopie le tournoi réel dans le harnais in-memory (par les ports, `id` préservés).

        Duels / plans de duels / forfaits ne sont pas recopiés : un tournoi avant démarrage n'en a
        pas (ADR-0054 §3). Les séries sont recopiées telles quelles — le classement en dérive.
        """
        harnais.tournois.ajouter(tournoi)
        for categorie in self._categories.par_tournoi(tournoi_id):
            harnais.categories.ajouter(categorie)
        for blason in self._blasons.par_tournoi(tournoi_id):
            harnais.blasons.ajouter(blason)
        gabarit = self._gabarits.par_tournoi(tournoi_id)
        if gabarit is not None:
            harnais.gabarits.ajouter(gabarit)
        for archer in self._archers.par_tournoi(tournoi_id):
            harnais.archers.ajouter(archer)
            assert archer.id is not None, "Un archer relu est persisté."
            for inscription in self._inscriptions.par_archer(archer.id):
                harnais.inscriptions.ajouter(inscription)
        for phase in self._phases.par_tournoi(tournoi_id):
            harnais.phases.ajouter(phase)
        for serie in self._series.par_tournoi(tournoi_id):
            harnais.series.enregistrer(serie)
