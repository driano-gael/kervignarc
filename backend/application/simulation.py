"""Service de **simulation** — « ne rien persister » est une propriété **structurelle** (ADR-0054).

Le harnais est fait d'adapters in-memory : aucun chemin vers SQLite ni vers la file. La composition
root injecte une **usine**, ce service n'importe aucun adapter concret.

⚠️ **On ne simule qu'un tournoi AVANT démarrage** (409 sinon) : c'est ce garde-fou qui autorise à ne
pas hydrater duels, plans de duels et forfaits — avant `en_cours`, ils sont toujours vides.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from application.classements import ServiceClassement
from application.erreurs import (
    PrelevementEnAttente,
    SimulationTournoiDemarre,
    TournoiIntrouvable,
    TournoiSansDepart,
)
from application.placement_duels import ServicePlacementDuels
from application.saisie_duels import EtatTableau, ServiceSaisieDuels
from domain.classement import Classement
from domain.erreurs import EffectifTableauInvalide
from domain.phase import TypePhase
from domain.ports import (
    ArcherRepository,
    BlasonRepository,
    CategorieRepository,
    DepartRepository,
    DerouleRepository,
    GabaritSalleRepository,
    InscriptionRepository,
    PhaseRepository,
    SerieRepository,
    TournoiRepository,
)
from domain.tournoi import StatutTournoi, Tournoi, TournoiId

# Statuts simulables : **avant démarrage** seulement (ADR-0054 §4), comme le peuplement (E15US001).
_STATUTS_SIMULABLES = frozenset({StatutTournoi.BROUILLON, StatutTournoi.PRET})


def charger_tournoi_simulable(tournois: TournoiRepository, tournoi_id: TournoiId) -> Tournoi:
    """Lit le tournoi et applique le garde-fou de simulation (ADR-0054 §4) — **source unique**.

    Partagé par le rejeu one-shot (`ServiceSimulation`, E15US002) et le pilotage vivant
    (`ServicePilotageSimulation`, E15US003) : les deux refusent exactement les mêmes tournois, au
    même endroit. Lève `TournoiIntrouvable` (404) si absent, `SimulationTournoiDemarre` (409) s'il
    est hors `brouillon`/`prêt` — mêmes bornes qu'`E15US001`, « ne pollue jamais le réel ».
    """
    tournoi = tournois.par_id(tournoi_id)
    if tournoi is None:
        raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
    if tournoi.statut not in _STATUTS_SIMULABLES:
        raise SimulationTournoiDemarre(
            f"Le tournoi « {tournoi.nom} » est {tournoi.statut.value} : on ne simule "
            "(rejeu éphémère du moteur) qu'un tournoi avant démarrage (brouillon ou prêt), "
            "pour ne pas interférer avec une compétition en cours ou figée."
        )
    return tournoi


def hydrater_harnais(
    harnais: HarnaisSimulation,
    tournoi: Tournoi,
    *,
    tournois: TournoiRepository,
    archers: ArcherRepository,
    categories: CategorieRepository,
    blasons: BlasonRepository,
    gabarits: GabaritSalleRepository,
    inscriptions: InscriptionRepository,
    departs: DepartRepository,
    deroules: DerouleRepository,
    phases: PhaseRepository,
    series: SerieRepository,
) -> None:
    """Recopie le tournoi réel dans le harnais in-memory par les ports (ADR-0054 §3).

    **Source unique** de l'hydratation, partagée par le rejeu one-shot et le pilotage vivant.
    Duels, plans de duels et forfaits ne sont pas recopiés : un tournoi avant démarrage n'en a
    pas. Les séries sont recopiées telles quelles — le classement en dérive. Les repositories
    `tournois`… sont les ports **réels** (lecture seule, hors file, règle 7) ; `harnais.*` sont
    les magasins in-memory.
    """
    assert tournoi.id is not None, "Un tournoi relu est persisté."
    tournoi_id = tournoi.id
    harnais.tournois.ajouter(tournoi)
    # **Les créneaux d'abord** (E01US025, ADR-0075) : ils portent les phases et le classement, et
    # les identifiants sont **préservés** par les magasins in-memory — sans eux, les phases
    # recopiées pointeraient un départ absent, et le harnais rendrait un classement vide.
    for depart in departs.par_tournoi(tournoi_id):
        harnais.departs.ajouter(depart)
    # Le déroulé **avant** les phases : celles-ci n'ont de sens qu'assemblées avec leur étape.
    for etape in deroules.par_tournoi(tournoi_id):
        harnais.deroules.ajouter(etape)
    for categorie in categories.par_tournoi(tournoi_id):
        harnais.categories.ajouter(categorie)
    for blason in blasons.par_tournoi(tournoi_id):
        harnais.blasons.ajouter(blason)
    gabarit = gabarits.par_tournoi(tournoi_id)
    if gabarit is not None:
        harnais.gabarits.ajouter(gabarit)
    for archer in archers.par_tournoi(tournoi_id):
        harnais.archers.ajouter(archer)
        assert archer.id is not None, "Un archer relu est persisté."
        for inscription in inscriptions.par_archer(archer.id):
            harnais.inscriptions.ajouter(inscription)
    for phase in phases.par_tournoi(tournoi_id):
        harnais.phases.ajouter(phase)
    for serie in series.par_tournoi(tournoi_id):
        harnais.series.enregistrer(serie)


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
    # Le harnais porte ses **créneaux** depuis E01US025 (ADR-0075) : la portée sportive est le
    # départ, donc une simulation sans départ n'aurait ni phase ni classement.
    departs: DepartRepository
    # Le **déroulé** du tournoi simulé : la définition, une fois (ADR-0076). Les phases n'en
    # portent plus que l'avancement, et le magasin les assemble à la lecture.
    deroules: DerouleRepository
    phases: PhaseRepository
    series: SerieRepository
    classement: ServiceClassement
    placement_duels: ServicePlacementDuels
    saisie_duels: ServiceSaisieDuels


UsineHarnais = Callable[[], HarnaisSimulation]
"""Fabrique d'un harnais **neuf** (règle 8) : le seul point qui connaît les adapters in-memory.

Injectée à `ServiceSimulation` (rejeu one-shot) **et** `ServicePilotageSimulation` (session
vivante) : un harnais par appel, aucune fuite d'état entre deux simulations."""


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
        departs: DepartRepository,
        deroules: DerouleRepository,
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
        # Les créneaux : le harnais les hydrate en premier (ADR-0075).
        self._departs = departs
        self._deroules = deroules
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
        tournoi = charger_tournoi_simulable(self._tournois, tournoi_id)

        harnais = self._usine_harnais()
        hydrater_harnais(
            harnais,
            tournoi,
            tournois=self._tournois,
            archers=self._archers,
            categories=self._categories,
            blasons=self._blasons,
            gabarits=self._gabarits,
            inscriptions=self._inscriptions,
            departs=self._departs,
            deroules=self._deroules,
            phases=self._phases,
            series=self._series,
        )

        # La simulation rejoue **un** créneau : le premier du tournoi simulé (le harnais n'en
        # fabrique qu'un — cf. `simulation_format`). Le rejeu multi-départs relève de DETTE-045.
        #
        # ⚠️ La garde n'est pas décorative : un tournoi `brouillon` **sans aucun créneau** est le
        # chemin normal de l'atelier (on crée le tournoi, puis les départs), et l'indexation nue
        # levait un `IndexError` — donc un **500**, sans message exploitable, sur une simulation
        # parfaitement légitime. Les services voisins lèvent déjà `TournoiSansDepart` (409 — conflit
        # d'état : créer un créneau rend la requête acceptable) ; on ne laisse pas une route se
        # comporter autrement que ses sœurs sur le même état.
        creneaux = harnais.departs.par_tournoi(tournoi_id)
        if not creneaux:
            raise TournoiSansDepart(
                "Ce tournoi n'a aucun créneau : il n'y a rien à rejouer en simulation."
            )
        depart_simule = creneaux[0]
        assert depart_simule.id is not None, "Le magasin in-memory attribue un identifiant."
        classement = harnais.classement.pour_depart(depart_simule.id)
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
            # PrelevementEnAttente rejoint la garde (E05US024, ADR-0081) : « la source n'a pas
            # encore
            # départagé les places prélevées » est le **même** cas métier qu'« effectif insuffisant
            # »
            # — il est trop tôt. Sans cet élargissement, la nouvelle exception traversait ce point
            # de
            # tolérance et faisait échouer en bloc ce que le site s'engage à dégrader (relevé par
            # trois axes de revue : régression introduite par le refus typé lui-même).
            except (EffectifTableauInvalide, PrelevementEnAttente):
                # Tournoi *avant démarrage* : une phase de tableau peut exister alors que moins de
                # deux duellistes sont classés (personne n'a encore tiré). Elle n'est **pas encore
                # jouable** — on la saute plutôt que de faire échouer toute la simulation (le CA
                # promet « n'importe quel tournoi créé »). E15US003 la rejouera quand le bot aura
                # généré des scores.
                continue

        return ResultatSimulation(tournoi_id, classement, tuple(tableaux))
