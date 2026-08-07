"""Pilotage d'une simulation vivante — bot pausable + reprise en main (E15US003, ADR-0055).

Anime le **substrat** éphémère d'E15US002 (ADR-0054) : là où `ServiceSimulation.simuler` rejoue le
moteur d'un coup et fige le résultat, ce service tient une **session vivante** (état mutable en
mémoire serveur, hors file d'écriture — règle 7) qu'un **bot** fait avancer **pas à pas**, qu'on
**met en pause**, où l'on **saisit à la main à la place d'un rôle**, puis que l'on **reprend**.

**Cadence par pas, pas par boucle de fond (ADR-0055 §2).** « Avancer » est synchrone : le pilote
automatique est un *ticker côté front* qui appelle `avancer` sur un intervalle ; la pause, c'est
cesser d'appeler. La **logique** reste **déterministe** (règle 9) — pas de boucle de fond, pas
d'horloge : une même `(graine, suite d'actions séquentielle)` produit toujours le même déroulé, donc
des tests reproductibles. Les routes s'exécutent sur des threads (`run_in_threadpool`) ; ce
déterminisme ne vaut donc que si les opérations d'**une même** session sont **sérialisées** — ce que
garantit un **verrou par session** (`SessionSimulation.verrou`), pas une hypothèse tacite (revue).

**Une unité, deux acteurs (ADR-0055 §3).** Le bot et l'humain jouent la **même** unité atomique — la
prochaine volée manquante d'un archer (qualif), ou le prochain duel jouable (duels) —, exposée par
`prochaine_unite` pour peupler le formulaire de reprise en main. Le bot en **génère** les valeurs
(générateur plausible injecté, §4) ; l'humain les **fournit**. « Saisir à la place d'un rôle » n'est
donc pas un chemin parallèle : juste l'autre acteur sur le même curseur.

**Trois états gardés (ADR-0055 §2).** `en_cours` (le bot avance, l'humain ne saisit pas) ⇄
`en_pause` (l'humain saisit, le bot est suspendu) → `terminée` (plus d'unité). Demander une action
hors de son état est un conflit (`PilotageSimulationInvalide`, 409), comme le cycle de vie du
tournoi (ADR-0026).
"""

from __future__ import annotations

import random
import threading
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Protocol

from application.erreurs import (
    ArcherIntrouvable,
    PhaseQualificationAbsente,
    PilotageSimulationInvalide,
    SessionSimulationIntrouvable,
    UniteSimulationInvalide,
)
from application.generateur_scores import GenerateurScores, valeur_zone
from application.portee import qualification_du_tournoi
from application.saisie_duels import Duelliste, EtatDuel, EtatTableau
from application.simulation import (
    HarnaisSimulation,
    UsineHarnais,
    charger_tournoi_simulable,
    hydrater_harnais,
)
from domain.archer import Archer, ArcherId
from domain.bareme import BaremeQualification
from domain.blason import ZONES_DEFAUT, ZoneScore
from domain.classement import Classement
from domain.duel import Cote
from domain.erreurs import EffectifTableauInvalide
from domain.phase import PhaseId, TypePhase
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
from domain.serie import Serie, Volee, valider_valeurs_volee
from domain.tournoi import Tournoi, TournoiId

SessionId = int
"""Identifiant d'une session de simulation, attribué par le registre (en mémoire, éphémère)."""

# Auteurs déclaratifs des actes simulés (`saisie_par`/`validee_par` des volées, `scoreur` des duels)
# : tracent *qui* a joué l'unité — le bot ou un humain en reprise en main. Purement informatif
# (aucun audit n'est consigné en simulation, ADR-0054), mais visible dans le cockpit.
_AUTEUR_BOT = "Bot"
_AUTEUR_MANUEL = "Manuel"


class EtatPilote(str, Enum):
    """État du pilote d'une session (ADR-0055 §2). `en_cours` ⇄ `en_pause` → `terminee`."""

    EN_COURS = "en_cours"
    EN_PAUSE = "en_pause"
    TERMINEE = "terminee"


class EtapeSimulation(str, Enum):
    """Étape du déroulé, **dérivée** de la prochaine unité à jouer (jamais saisie)."""

    QUALIFICATION = "qualification"
    DUELS = "duels"
    TERMINEE = "terminee"


@dataclass(frozen=True)
class ProchaineVolee:
    """L'unité de qualification à jouer : la prochaine volée manquante d'un archer.

    Peuple le formulaire de reprise en main « cible » : quel archer, quelle volée, combien de
    flèches, et les zones **légales** de son blason (le pavé de saisie).
    """

    archer_id: ArcherId
    archer_nom: str
    archer_prenom: str
    numero_volee: int
    nb_fleches: int
    zones: tuple[ZoneScore, ...]


@dataclass(frozen=True)
class ProchaineDuel:
    """L'unité de duels à jouer : le prochain duel jouable non tranché.

    Peuple le formulaire de reprise en main « scoreur » : quel match, entre qui, en quel mode
    (`sets`/`cumul`, résolu par le serveur) — l'humain n'a qu'à **désigner le vainqueur**.
    """

    phase_id: PhaseId
    match_numero: int
    tour: int
    haut: Duelliste | None
    bas: Duelliste | None
    mode: str


ProchaineUnite = ProchaineVolee | ProchaineDuel


@dataclass(frozen=True)
class Progression:
    """Compteurs d'avancement (approximatifs pendant la qualif : les tours de duels se révèlent au
    fur et à mesure). `duels_total` = somme des `effectif - 1` par tableau (une élimination directe
    à N duellistes se décide en N-1 duels)."""

    volees_faites: int
    volees_total: int
    duels_faits: int
    duels_total: int


@dataclass(frozen=True)
class DetailArcher:
    """Le détail de la « journée » d'un archer simulé (vue archer du cockpit)."""

    archer_id: ArcherId
    nom: str
    prenom: str
    cumul: int
    volees: tuple[Volee, ...]


@dataclass(frozen=True)
class EtatSession:
    """Instantané complet d'une session, servi au cockpit (public/scoreur/cible/archer en dérivent).

    Immuable : c'est une **photo** rendue à l'appelant, pas la session elle-même (mutable).
    """

    session_id: SessionId
    tournoi_id: TournoiId
    tournoi_nom: str
    graine: int
    etat_pilote: EtatPilote
    etape: EtapeSimulation
    progression: Progression
    classement: Classement
    tableaux: tuple[EtatTableau, ...]
    prochaine_unite: ProchaineUnite | None


class DiffusionSimulation(Protocol):
    """Port étroit de diffusion **isolée** (ADR-0055 §5) : signaler qu'une session a changé.

    L'implémentation (infra) publie sur un `Broadcaster` **dédié** (endpoint `/ws/simulation`),
    distinct du temps réel réel. Le service reste sans infrastructure (règle 8) et testable sans
    WebSocket (une doublure suffit). On ne pousse **pas** l'état par le socket : on **signale** le
    changement, le front re-lit l'état par REST — comme le canal réel (générique + invalidation).
    """

    def signaler(self, session_id: SessionId) -> None: ...


@dataclass
class SessionSimulation:
    """L'état **mutable** d'une simulation vivante (en mémoire, éphémère — ADR-0055 §1).

    Détient le harnais in-memory hydraté (le substrat E15US002), la configuration figée au démarrage
    (barème, phases, ordre des archers, niveaux tirés de la graine) et l'état courant du pilote. Les
    compteurs `volees_jouees`/`duels_joues` suivent l'avancement (chaque unité jouée les
    incrémente).
    """

    id: SessionId
    tournoi_id: TournoiId
    tournoi_nom: str
    graine: int
    harnais: HarnaisSimulation
    bareme: BaremeQualification
    phase_qualif_id: PhaseId
    phases_duels: tuple[PhaseId, ...]
    archers_ordonnes: tuple[ArcherId, ...]
    niveaux: dict[ArcherId, float]
    alea: random.Random
    etat_pilote: EtatPilote = EtatPilote.EN_COURS
    volees_jouees: int = 0
    duels_joues: int = 0
    # Sérialise les opérations concurrentes sur **cette** session (revue axe A/C1/D) : les routes
    # tournent sur des threads (`run_in_threadpool`), et deux admins abonnés au même canal
    # pourraient piloter la même session en parallèle (double `avancer` → sur-comptage, harnais
    # incohérent). Un verrou **par session** suffit — deux sessions distinctes ne se bloquent pas.
    # `compare=False` (un `Lock` n'est ni comparable ni pertinent à l'égalité de session).
    verrou: threading.Lock = field(default_factory=threading.Lock, compare=False, repr=False)


class RegistreSessionsSimulation:
    """Registre en mémoire des sessions vivantes (câblé à la composition root, règle 8).

    Attribue les identifiants (compteur monotone) et garde les sessions ; `arreter` les retire (le
    harnais et ses `dict` sont alors collectés). Volatil comme les sessions de poste/scoreur : un
    redémarrage du serveur les efface — acceptable pour un outil de démo mono-club (règle 12).
    """

    def __init__(self) -> None:
        self._sessions: dict[SessionId, SessionSimulation] = {}
        self._compteur = 0
        # Protège l'attribution d'identifiant et le dict des sessions des accès concurrents (routes
        # sur threads, `run_in_threadpool`) : `_compteur += 1` n'est pas atomique (revue axe A/D).
        self._verrou = threading.Lock()

    def ajouter(self, session: SessionSimulation) -> SessionSimulation:
        with self._verrou:
            self._compteur += 1
            session.id = self._compteur
            self._sessions[session.id] = session
        return session

    def obtenir(self, session_id: SessionId) -> SessionSimulation:
        with self._verrou:
            session = self._sessions.get(session_id)
        if session is None:
            raise SessionSimulationIntrouvable(
                f"Aucune session de simulation d'identifiant {session_id} "
                "(jamais créée, déjà arrêtée, ou perdue au redémarrage)."
            )
        return session

    def retirer(self, session_id: SessionId) -> None:
        # Idempotent : arrêter une session déjà partie n'est pas une erreur (le front peut rejouer).
        with self._verrou:
            self._sessions.pop(session_id, None)


class ServicePilotageSimulation:
    """Cas d'usage : piloter une simulation vivante (démarrer, avancer, pause, reprendre,
    saisir)."""

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
        usine_harnais: UsineHarnais,
        generateur: GenerateurScores,
        registre: RegistreSessionsSimulation,
        diffusion: DiffusionSimulation,
    ) -> None:
        # Repositories **réels** (SQL en prod) : lecture seule, pour le garde-fou et l'hydratation.
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
        self._generateur = generateur
        self._registre = registre
        self._diffusion = diffusion

    # --- Cycle de vie de la session -------------------------------------------------------------

    def demarrer(self, tournoi_id: TournoiId, graine: int) -> EtatSession:
        """Ouvre une session : garde-fou + hydratation, puis état initial (bot prêt à avancer).

        Lève `TournoiIntrouvable` (404) / `SimulationTournoiDemarre` (409) — mêmes bornes que le
        rejeu one-shot (avant démarrage seulement) — et `PhaseQualificationAbsente` (404) si le
        tournoi n'a pas de phase de qualification avec barème (sans quoi le bot n'a pas de déroulé à
        générer). La graine rend le déroulé **déterministe** (règle 9) : niveaux d'archers et tirs
        en découlent.
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
        return self.ouvrir_sur_harnais(harnais, tournoi, graine)

    def ouvrir_sur_harnais(
        self, harnais: HarnaisSimulation, tournoi: Tournoi, graine: int
    ) -> EtatSession:
        """Ouvre une session sur un harnais **déjà rempli**, quelle qu'en soit la provenance.

        Extrait de `demarrer` en E01US024 : la simulation d'un **format**
        (`ServiceSimulationFormat`)
        remplit son harnais de toutes pièces — tournoi éphémère, archers fictifs, phases du
        format — sans qu'aucun tournoi réel n'existe à hydrater. Tout ce qui suit l'hydratation est
        identique dans les deux cas ; le partager évite deux bots qui dériveraient.
        """
        assert tournoi.id is not None, "Un tournoi de simulation porte un identifiant."
        tournoi_id = tournoi.id
        phase_qualif = qualification_du_tournoi(harnais.phases, tournoi_id)
        if phase_qualif is None or phase_qualif.bareme is None or phase_qualif.id is None:
            raise PhaseQualificationAbsente(
                "Pour simuler le déroulé, le tournoi doit avoir une phase de qualification avec un "
                "barème (E01US009) : c'est lui qui dit combien de volées le bot doit générer."
            )
        archers = sorted(harnais.archers.par_tournoi(tournoi_id), key=lambda a: a.id or 0)
        archers_ordonnes = tuple(a.id for a in archers if a.id is not None)
        alea = random.Random(graine)
        # Niveau tiré **une fois** par archer, dans l'ordre (déterministe) : il module le générateur
        # pour que les totaux s'étalent et que le classement ait du sens (ADR-0055 §4).
        niveaux = {aid: alea.uniform(0.15, 1.0) for aid in archers_ordonnes}
        phases_duels = tuple(
            p.id
            for p in harnais.phases.par_tournoi(tournoi_id)
            if p.type is TypePhase.ELIMINATION_DIRECTE and p.id is not None
        )
        session = self._registre.ajouter(
            SessionSimulation(
                id=0,
                tournoi_id=tournoi_id,
                tournoi_nom=tournoi.nom,
                graine=graine,
                harnais=harnais,
                bareme=phase_qualif.bareme,
                phase_qualif_id=phase_qualif.id,
                phases_duels=phases_duels,
                archers_ordonnes=archers_ordonnes,
                niveaux=niveaux,
                alea=alea,
            )
        )
        self._diffusion.signaler(session.id)
        return self._etat(session)

    def arreter(self, session_id: SessionId) -> None:
        """Retire la session (le harnais est collecté). Idempotent (ADR-0055 §1)."""
        self._registre.retirer(session_id)

    def etat(self, session_id: SessionId) -> EtatSession:
        """Instantané courant de la session (lecture ; le front poll après un signal de
        diffusion)."""
        session = self._registre.obtenir(session_id)
        with session.verrou:
            return self._etat(session)

    def detail_archer(self, session_id: SessionId, archer_id: ArcherId) -> DetailArcher:
        """La « journée » d'un archer simulé (vue archer) : ses volées et son cumul courant."""
        session = self._registre.obtenir(session_id)
        with session.verrou:
            archer = session.harnais.archers.par_id(archer_id)
            if archer is None or archer.tournoi_id != session.tournoi_id:
                raise ArcherIntrouvable(
                    f"Aucun archer d'identifiant {archer_id} dans la simulation {session_id}."
                )
            serie = session.harnais.series.par_archer(session.tournoi_id, archer_id)
            return DetailArcher(
                archer_id=archer_id,
                nom=archer.nom,
                prenom=archer.prenom,
                cumul=serie.cumul if serie is not None else 0,
                volees=serie.volees if serie is not None else (),
            )

    # --- Pilote automatique (bot) ---------------------------------------------------------------

    def avancer(self, session_id: SessionId, nb_pas: int = 1) -> EtatSession:
        """Fait avancer le bot de `nb_pas` unités (le ticker front appelle en boucle, ADR-0055 §2).

        N'est permis qu'`en_cours` (`PilotageSimulationInvalide`, 409, si en pause ou terminée) : le
        bot n'avance que lorsqu'il tient les commandes. S'il n'y a plus d'unité, la session passe
        `terminée`.
        """
        session = self._registre.obtenir(session_id)
        with session.verrou:
            if session.etat_pilote is not EtatPilote.EN_COURS:
                raise PilotageSimulationInvalide(
                    "Le bot n'avance que lorsqu'il est aux commandes (en cours) : reprends-lui la "
                    "main avant de le laisser jouer."
                )
            for _ in range(max(1, nb_pas)):
                if not self._jouer_prochaine(session):
                    session.etat_pilote = EtatPilote.TERMINEE
                    break
            self._diffusion.signaler(session_id)
            return self._etat(session)

    def terminer(self, session_id: SessionId) -> EtatSession:
        """Déroule tout ce qui reste d'un coup (QA : « va jusqu'au classement »), puis `terminée`.

        Permis `en_cours` **ou** `en_pause` (un raccourci de fin force l'aboutissement). Borné par
        un plafond de pas (filet anti-boucle si un tableau restait bloqué, cf. avertissement du
        moteur).
        """
        session = self._registre.obtenir(session_id)
        with session.verrou:
            if session.etat_pilote is EtatPilote.TERMINEE:
                raise PilotageSimulationInvalide("La simulation est déjà terminée.")
            for _ in range(self._plafond_pas(session)):
                if not self._jouer_prochaine(session):
                    break
            session.etat_pilote = EtatPilote.TERMINEE
            self._diffusion.signaler(session_id)
            return self._etat(session)

    def pause(self, session_id: SessionId) -> EtatSession:
        """Suspend le bot (`en_cours` → `en_pause`). 409 si la session n'est pas en cours."""
        session = self._registre.obtenir(session_id)
        with session.verrou:
            if session.etat_pilote is not EtatPilote.EN_COURS:
                raise PilotageSimulationInvalide(
                    "Seule une simulation en cours peut être mise en pause."
                )
            session.etat_pilote = EtatPilote.EN_PAUSE
            self._diffusion.signaler(session_id)
            return self._etat(session)

    def reprendre(self, session_id: SessionId) -> EtatSession:
        """Rend la main au bot (`en_pause` → `en_cours`). 409 si la session n'est pas en pause."""
        session = self._registre.obtenir(session_id)
        with session.verrou:
            if session.etat_pilote is not EtatPilote.EN_PAUSE:
                raise PilotageSimulationInvalide("Seule une simulation en pause peut reprendre.")
            session.etat_pilote = EtatPilote.EN_COURS
            self._diffusion.signaler(session_id)
            return self._etat(session)

    # --- Reprise en main (humain, en pause) -----------------------------------------------------

    def saisir_volee(
        self,
        session_id: SessionId,
        archer_id: ArcherId,
        numero_volee: int,
        valeurs: tuple[ZoneScore, ...],
    ) -> EtatSession:
        """L'humain joue la **cible** : saisit la prochaine volée d'un archer à la place du bot.

        N'est permis qu'`en_pause` (`PilotageSimulationInvalide`, 409). Refuse une unité qui n'a pas
        de sens (`UniteSimulationInvalide`, 409 : archer hors tournoi, volée hors barème ou déjà
        validée) et des valeurs invalides (erreurs de domaine, 422 : mauvais nombre de flèches, zone
        hors blason). La volée est posée **validée** (comme le bot).
        """
        session = self._registre.obtenir(session_id)
        with session.verrou:
            self._exiger_pause(session)
            if archer_id not in session.archers_ordonnes:
                raise UniteSimulationInvalide(
                    f"L'archer {archer_id} ne participe pas à cette simulation."
                )
            if not 1 <= numero_volee <= session.bareme.nb_volees:
                raise UniteSimulationInvalide(
                    f"La volée {numero_volee} est hors du barème (1 à {session.bareme.nb_volees})."
                )
            if self._volee_validee(session, archer_id, numero_volee):
                raise UniteSimulationInvalide(
                    f"La volée {numero_volee} de l'archer {archer_id} est déjà validée."
                )
            archer = session.harnais.archers.par_id(archer_id)
            assert archer is not None, "L'archer est dans archers_ordonnes, donc hydraté."
            # Valide les valeurs par le **domaine** (source unique de « qu'est-ce qu'une volée
            # valide » ; lève les erreurs de domaine → 422), sans repasser par le workflow de grain.
            valider_valeurs_volee(
                valeurs, self._zones_archer(session, archer), session.bareme.nb_fleches_par_volee
            )
            self._poser_volee(session, archer_id, numero_volee, valeurs, _AUTEUR_MANUEL)
            self._diffusion.signaler(session_id)
            return self._etat(session)

    def designer_vainqueur(
        self,
        session_id: SessionId,
        phase_id: PhaseId,
        match_numero: int,
        cote: Cote,
    ) -> EtatSession:
        """L'humain joue le **scoreur** : désigne le vainqueur d'un duel à la place du bot.

        N'est permis qu'`en_pause` (409). Refuse un duel qui n'est pas jouable
        (`UniteSimulationInvalide`, 409 : phase hors tableau, match inexistant, bye, déjà tranché).
        Les scores sont fabriqués décisifs pour le camp désigné (comme le bot).
        """
        session = self._registre.obtenir(session_id)
        with session.verrou:
            self._exiger_pause(session)
            if phase_id not in session.phases_duels:
                raise UniteSimulationInvalide(
                    f"La phase {phase_id} n'est pas une phase de duels de cette simulation."
                )
            etat_duel = self._duel_jouable(session, phase_id, match_numero)
            self._jouer_duel(session, phase_id, etat_duel, cote, _AUTEUR_MANUEL)
            self._diffusion.signaler(session_id)
            return self._etat(session)

    # --- Moteur interne : jouer une unité -------------------------------------------------------

    def _jouer_prochaine(self, session: SessionSimulation) -> bool:
        """Joue la prochaine unité par le **bot** ; renvoie `False` s'il n'en reste aucune."""
        volee = self._prochaine_volee(session)
        if volee is not None:
            numero, archer_id = volee
            self._jouer_volee_bot(session, archer_id, numero)
            return True
        duel = self._prochain_duel(session)
        if duel is not None:
            phase_id, etat_duel = duel
            cote = self._cote_gagnante_bot(session, etat_duel)
            self._jouer_duel(session, phase_id, etat_duel, cote, _AUTEUR_BOT)
            return True
        return False

    def _jouer_volee_bot(
        self, session: SessionSimulation, archer_id: ArcherId, numero: int
    ) -> None:
        archer = session.harnais.archers.par_id(archer_id)
        assert archer is not None, "archer_id vient de archers_ordonnes (hydraté)."
        zones = self._zones_archer(session, archer)
        valeurs = self._generateur.volee(
            zones, session.bareme.nb_fleches_par_volee, session.niveaux[archer_id], session.alea
        )
        self._poser_volee(session, archer_id, numero, valeurs, _AUTEUR_BOT)

    def _poser_volee(
        self,
        session: SessionSimulation,
        archer_id: ArcherId,
        numero: int,
        valeurs: tuple[ZoneScore, ...],
        auteur: str,
    ) -> None:
        """Pose une volée **validée** (verrouillée) dans la série de l'archer, et compte l'unité.

        Court-circuite délibérément le workflow de validation par grain d'E04US002 (ADR-0055 §3) :
        produire une donnée plausible n'est pas rejouer la cérémonie de saisie. Le `_avec_volee`
        local duplique trivialement l'assemblage privé de `domain.serie` (2ᵉ occurrence, règle 16).
        """
        serie = session.harnais.series.par_archer(session.tournoi_id, archer_id)
        if serie is None:
            serie = Serie.vide(session.tournoi_id, archer_id)
        volee = Volee(numero=numero, valeurs=valeurs, saisie_par=auteur, validee_par=auteur)
        autres = tuple(v for v in serie.volees if v.numero != numero)
        volees = tuple(sorted((*autres, volee), key=lambda v: v.numero))
        session.harnais.series.enregistrer(replace(serie, volees=volees))
        session.volees_jouees += 1

    def _jouer_duel(
        self,
        session: SessionSimulation,
        phase_id: PhaseId,
        etat_duel: EtatDuel,
        gagnant: Cote,
        auteur: str,
    ) -> None:
        """Score un duel jusqu'au vainqueur `gagnant`, le valide (le tableau avance ensuite,
        ADR-0049).

        Scores **décisifs** (gagnant au maximum, perdant strictement en dessous) : le duel se
        tranche toujours par les manches, sans barrage. Le barrage reste géré par sécurité (ne
        devrait pas se déclencher). Vaut en `sets` comme en `cumul` : la condition d'arrêt
        `resultat.termine` n'est vraie avant la dernière manche qu'en sets (en cumul, on saisit
        toutes les manches).
        """
        tid = session.tournoi_id
        n = etat_duel.numero
        bareme = etat_duel.bareme
        assert bareme is not None, "Un duel jouable porte son barème (ADR-0049)."
        v_gagnante, v_perdante = self._volees_duel(
            session, etat_duel.zones, bareme.nb_fleches_par_volee
        )
        v_haut, v_bas = (
            (v_gagnante, v_perdante) if gagnant is Cote.HAUT else (v_perdante, v_gagnante)
        )
        dernier: EtatDuel | None = None
        for manche in range(1, bareme.nb_manches + 1):
            dernier = session.harnais.saisie_duels.saisir_manche(
                tid, phase_id, n, manche, v_haut, v_bas
            )
            if dernier.duel is not None and dernier.duel.resultat.termine:
                break
        if (
            dernier is not None
            and dernier.duel is not None
            and dernier.duel.resultat.barrage_requis
        ):
            session.harnais.saisie_duels.saisir_barrage(
                tid, phase_id, n, v_haut[0], v_bas[0], gagnant_designe=gagnant
            )
        session.harnais.saisie_duels.valider(tid, phase_id, n, auteur)
        session.duels_joues += 1

    def _volees_duel(
        self, session: SessionSimulation, zones: tuple[ZoneScore, ...], nb_fleches: int
    ) -> tuple[tuple[ZoneScore, ...], tuple[ZoneScore, ...]]:
        """Une volée gagnante (maximum) et une volée perdante (plausible, strictement
        inférieure)."""
        markantes = tuple(z for z in zones if z is not ZoneScore.MANQUE)
        z_max = max(markantes, key=valeur_zone) if markantes else ZoneScore.MANQUE
        v_gagnante = (z_max,) * nb_fleches
        total_max = valeur_zone(z_max) * nb_fleches
        v_perdante = self._generateur.volee(zones, nb_fleches, 0.4, session.alea)
        if sum(valeur_zone(z) for z in v_perdante) >= total_max:
            # Cas extrême (perdante tirée aussi au maximum) : on dégrade une flèche pour garantir la
            # stricte infériorité — donc un duel toujours tranché, jamais de barrage.
            v_perdante = (ZoneScore.MANQUE, *v_perdante[1:])
        return v_gagnante, v_perdante

    def _cote_gagnante_bot(self, session: SessionSimulation, etat_duel: EtatDuel) -> Cote:
        """Le camp que le bot fait gagner : biaisé vers le meilleur niveau, sans être
        déterministe."""
        niveau_haut = session.niveaux.get(etat_duel.haut.archer_id, 0.5) if etat_duel.haut else 0.5
        niveau_bas = session.niveaux.get(etat_duel.bas.archer_id, 0.5) if etat_duel.bas else 0.5
        proba_haut = min(0.9, max(0.1, 0.5 + 0.4 * (niveau_haut - niveau_bas)))
        return Cote.HAUT if session.alea.random() < proba_haut else Cote.BAS

    # --- Curseur : la prochaine unité -----------------------------------------------------------

    def _prochaine_volee(self, session: SessionSimulation) -> tuple[int, ArcherId] | None:
        """La prochaine volée manquante en ordre *volée-major* (tout le monde tire la volée k, puis
        k+1) : déroulé lisible et déterministe. `None` si la qualif est complète."""
        for numero in range(1, session.bareme.nb_volees + 1):
            for archer_id in session.archers_ordonnes:
                if not self._volee_validee(session, archer_id, numero):
                    return (numero, archer_id)
        return None

    def _prochain_duel(self, session: SessionSimulation) -> tuple[PhaseId, EtatDuel] | None:
        """Le prochain duel jouable non tranché (phases dans l'ordre, puis tour, puis n° de match).

        Une phase pas encore jouable (moins de deux duellistes classés) lève
        `EffectifTableauInvalide` et est **sautée** — comme le rejeu one-shot (ADR-0054) ; elle
        deviendra jouable quand la qualif aura produit assez de classés. `None` si plus aucun duel
        n'est jouable (tout est tranché)."""
        for phase_id in session.phases_duels:
            try:
                etat = session.harnais.saisie_duels.etat_tableau(session.tournoi_id, phase_id)
            except EffectifTableauInvalide:
                continue
            if etat.est_termine:
                continue
            jouables = [
                d
                for d in etat.duels
                if not d.est_bye
                and d.haut is not None
                and d.bas is not None
                and (d.duel is None or d.duel.validee_par is None)
            ]
            if jouables:
                # Ordre stable (tour croissant, puis n° de match) : le tour courant d'abord.
                return (phase_id, min(jouables, key=lambda d: (d.tour, d.numero)))
        return None

    def _duel_jouable(
        self, session: SessionSimulation, phase_id: PhaseId, match_numero: int
    ) -> EtatDuel:
        """Retrouve et valide un duel jouable désigné à la main ; lève `UniteSimulationInvalide`
        sinon."""
        try:
            etat = session.harnais.saisie_duels.etat_tableau(session.tournoi_id, phase_id)
        except EffectifTableauInvalide as exc:
            raise UniteSimulationInvalide(
                f"La phase {phase_id} n'a pas encore assez de duellistes classés "
                "pour jouer un duel."
            ) from exc
        for d in etat.duels:
            if d.numero != match_numero:
                continue
            if (
                d.est_bye
                or d.haut is None
                or d.bas is None
                or (d.duel is not None and d.duel.validee_par is not None)
            ):
                raise UniteSimulationInvalide(
                    f"Le duel {match_numero} de la phase {phase_id} n'est pas jouable "
                    "(exempt, incomplet ou déjà tranché)."
                )
            return d
        raise UniteSimulationInvalide(
            f"Aucun duel {match_numero} jouable dans la phase {phase_id}."
        )

    # --- Lecture / assemblage de l'état ---------------------------------------------------------

    def _volee_validee(self, session: SessionSimulation, archer_id: ArcherId, numero: int) -> bool:
        serie = session.harnais.series.par_archer(session.tournoi_id, archer_id)
        if serie is None:
            return False
        volee = serie.volee(numero)
        return volee is not None and volee.verrouillee

    def _zones_archer(self, session: SessionSimulation, archer: Archer) -> tuple[ZoneScore, ...]:
        """Les zones légales du blason de l'archer (catégorie → blason par défaut), sinon le
        défaut."""
        if archer.categorie_id is not None:
            categorie = session.harnais.categories.par_id(archer.categorie_id)
            if categorie is not None and categorie.blason_id is not None:
                blason = session.harnais.blasons.par_id(categorie.blason_id)
                if blason is not None:
                    return blason.zones
        return ZONES_DEFAUT

    def _tableaux(self, session: SessionSimulation) -> tuple[EtatTableau, ...]:
        """Les tableaux **jouables** (une phase pas encore prête est sautée, comme le one-shot)."""
        tableaux: list[EtatTableau] = []
        for phase_id in session.phases_duels:
            try:
                tableaux.append(
                    session.harnais.saisie_duels.etat_tableau(session.tournoi_id, phase_id)
                )
            except EffectifTableauInvalide:
                continue
        return tuple(tableaux)

    def _prochaine_unite(self, session: SessionSimulation) -> ProchaineUnite | None:
        volee = self._prochaine_volee(session)
        if volee is not None:
            numero, archer_id = volee
            archer = session.harnais.archers.par_id(archer_id)
            assert archer is not None
            return ProchaineVolee(
                archer_id=archer_id,
                archer_nom=archer.nom,
                archer_prenom=archer.prenom,
                numero_volee=numero,
                nb_fleches=session.bareme.nb_fleches_par_volee,
                zones=self._zones_archer(session, archer),
            )
        duel = self._prochain_duel(session)
        if duel is not None:
            phase_id, etat_duel = duel
            return ProchaineDuel(
                phase_id=phase_id,
                match_numero=etat_duel.numero,
                tour=etat_duel.tour,
                haut=etat_duel.haut,
                bas=etat_duel.bas,
                mode=etat_duel.bareme.mode.value if etat_duel.bareme is not None else "",
            )
        return None

    def _etat(self, session: SessionSimulation) -> EtatSession:
        depart_simule = session.harnais.departs.par_tournoi(session.tournoi_id)[0]
        assert depart_simule.id is not None, "Le magasin in-memory attribue un identifiant."
        classement = session.harnais.classement.pour_depart(depart_simule.id)
        tableaux = self._tableaux(session)
        prochaine = self._prochaine_unite(session)
        if isinstance(prochaine, ProchaineVolee):
            etape = EtapeSimulation.QUALIFICATION
        elif isinstance(prochaine, ProchaineDuel):
            etape = EtapeSimulation.DUELS
        else:
            etape = EtapeSimulation.TERMINEE
        progression = Progression(
            volees_faites=session.volees_jouees,
            volees_total=session.bareme.nb_volees * len(session.archers_ordonnes),
            duels_faits=session.duels_joues,
            duels_total=sum(max(0, etat.effectif - 1) for etat in tableaux),
        )
        return EtatSession(
            session_id=session.id,
            tournoi_id=session.tournoi_id,
            tournoi_nom=session.tournoi_nom,
            graine=session.graine,
            etat_pilote=session.etat_pilote,
            etape=etape,
            progression=progression,
            classement=classement,
            tableaux=tableaux,
            prochaine_unite=prochaine,
        )

    def _exiger_pause(self, session: SessionSimulation) -> None:
        if session.etat_pilote is not EtatPilote.EN_PAUSE:
            raise PilotageSimulationInvalide(
                "La saisie manuelle (reprise en main) n'est possible qu'en pause : mets d'abord la "
                "simulation en pause."
            )

    def _plafond_pas(self, session: SessionSimulation) -> int:
        """Borne de sécurité pour `terminer` : plus qu'assez d'unités pour tout jouer
        (anti-boucle)."""
        n = len(session.archers_ordonnes)
        return session.bareme.nb_volees * n + n * (len(session.phases_duels) + 1) + 50
