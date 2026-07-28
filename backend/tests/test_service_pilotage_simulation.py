"""Tests du service `ServicePilotageSimulation` (E15US003) — depuis le CA (ADR-0055).

La **règle métier** de l'US vit ici, dérivée des critères d'acceptation :

- **CA bot pausable** : le bot génère des scores plausibles et fait avancer la simulation
  (qualif → duels → classement) ; il est pausable puis reprend.
- **CA cockpit interactif** : en pause, l'humain saisit à la place d'un rôle (une volée pour la
  cible, un vainqueur pour le scoreur), puis rend la main au bot.
- **CA diffusion** (mécanisme service) : chaque mutation **signale** la session sur le port de
  diffusion (l'isolement du canal — un `Broadcaster` dédié — est éprouvé côté API).
- **Déterminisme** (règle 9) : à graine égale, même déroulé. - **Non-pollution** (invariant d'épic)
: après un déroulé complet, les repositories **réels** sont
  inchangés — le bot n'écrit que dans le harnais jetable.

On monte le côté « réel » avec les adapters in-memory de production (`infrastructure/memory`), comme
les tests d'E15US002 ; le harnais est fabriqué neuf par l'usine **de production**
(`fabriquer_harnais_simulation`) — le harnais éprouvé est celui déployé.
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.erreurs import (
    PhaseQualificationAbsente,
    PilotageSimulationInvalide,
    SessionSimulationIntrouvable,
    SimulationTournoiDemarre,
    UniteSimulationInvalide,
)
from application.generateur_scores import GenerateurScoresPlausibles, valeur_zone
from application.pilotage_simulation import (
    DiffusionSimulation,
    EtapeSimulation,
    EtatPilote,
    ProchaineDuel,
    ProchaineVolee,
    RegistreSessionsSimulation,
    ServicePilotageSimulation,
)
from bootstrap.composition import fabriquer_harnais_simulation
from domain.archer import Archer
from domain.bareme import BaremeQualification
from domain.blason import Blason, ZoneScore
from domain.categorie import Categorie
from domain.duel import Cote
from domain.inscription import Inscription
from domain.phase import Phase, TypePhase
from domain.tournoi import StatutTournoi, Tournoi
from infrastructure.memory.repositories import (
    InMemoryArcherRepository,
    InMemoryBlasonRepository,
    InMemoryCategorieRepository,
    InMemoryGabaritSalleRepository,
    InMemoryInscriptionRepository,
    InMemoryPhaseRepository,
    InMemorySerieRepository,
    InMemoryTournoiRepository,
)

_DATE = datetime.date(2026, 3, 14)


class _DiffusionFausse:
    """Doublure du port `DiffusionSimulation` : mémorise les signaux (le service reste testable sans
    WebSocket, ADR-0055 §5)."""

    def __init__(self) -> None:
        self.signaux: list[int] = []

    def signaler(self, session_id: int) -> None:
        self.signaux.append(session_id)


class _Contexte:
    """Un tournoi **avant démarrage** peuplé d'archers **sans série** (le bot les fait tirer).

    Une phase de qualification (barème court, pour un déroulé rapide) et, en option, une phase de
    tableau. Les archers portent une catégorie armée en arc classique (duels en sets) et un blason
    aux zones par défaut (toute valeur générée est légale).
    """

    def __init__(
        self,
        *,
        nb_archers: int = 4,
        avec_duels: bool = True,
        nb_volees: int = 2,
        nb_fleches: int = 3,
        avec_qualif: bool = True,
    ) -> None:
        self.tournois = InMemoryTournoiRepository()
        self.archers = InMemoryArcherRepository()
        self.categories = InMemoryCategorieRepository()
        self.blasons = InMemoryBlasonRepository()
        self.gabarits = InMemoryGabaritSalleRepository()
        self.inscriptions = InMemoryInscriptionRepository()
        self.phases = InMemoryPhaseRepository()
        self.series = InMemorySerieRepository()
        self.diffusion = _DiffusionFausse()

        tournoi = self.tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
        assert tournoi.id is not None
        self.tournoi_id = tournoi.id

        blason = self.blasons.ajouter(Blason.creer(self.tournoi_id, "Blason 40", 0.25, 1))
        assert blason.id is not None
        categorie = self.categories.ajouter(
            Categorie.creer(
                self.tournoi_id, "Sénior Homme", arme="Arc Classique", blason_id=blason.id
            )
        )
        assert categorie.id is not None
        self.categorie_id = categorie.id

        if avec_qualif:
            self.phases.ajouter(
                Phase.qualification(
                    self.tournoi_id, BaremeQualification.creer(nb_volees, nb_fleches)
                )
            )
        if avec_duels:
            self.phases.ajouter(Phase.creer(self.tournoi_id, 2, TypePhase.ELIMINATION_DIRECTE))

        self.archer_ids: list[int] = []
        for indice in range(nb_archers):
            archer = self.archers.ajouter(
                Archer(
                    nom=f"Nom{indice}",
                    prenom=f"Prenom{indice}",
                    tournoi_id=self.tournoi_id,
                    categorie_id=self.categorie_id,
                )
            )
            assert archer.id is not None
            self.archer_ids.append(archer.id)
            self.inscriptions.ajouter(Inscription(archer_id=archer.id, depart_id=1))

    def service(self, diffusion: DiffusionSimulation | None = None) -> ServicePilotageSimulation:
        return ServicePilotageSimulation(
            self.tournois,
            self.archers,
            self.categories,
            self.blasons,
            self.gabarits,
            self.inscriptions,
            self.phases,
            self.series,
            fabriquer_harnais_simulation,
            GenerateurScoresPlausibles(),
            RegistreSessionsSimulation(),
            diffusion if diffusion is not None else self.diffusion,
        )

    def statut(self, statut: StatutTournoi) -> None:
        base = self.tournois.par_id(self.tournoi_id)
        assert base is not None
        self.tournois.enregistrer(dataclasses.replace(base, statut=statut))


# --- CA bot pausable : déroulé complet qualif → duels → classement ------------------------------


def test_le_bot_deroule_jusqu_au_classement_et_au_podium() -> None:
    """CA bot : lancée puis terminée, la simulation classe tous les archers et couronne un
    podium."""
    ctx = _Contexte(nb_archers=4)
    service = ctx.service()

    depart = service.demarrer(ctx.tournoi_id, graine=1)
    assert depart.etat_pilote is EtatPilote.EN_COURS
    assert depart.etape is EtapeSimulation.QUALIFICATION

    etat = service.terminer(depart.session_id)

    assert etat.etat_pilote is EtatPilote.TERMINEE
    assert etat.etape is EtapeSimulation.TERMINEE
    # Tous les archers classés, avec un total (ils ont tiré) et un rang scratch attribué.
    assert len(etat.classement.lignes) == 4
    assert all(ligne.total > 0 for ligne in etat.classement.lignes)
    rangs = [ligne.rang_scratch for ligne in etat.classement.lignes]
    assert None not in rangs
    assert sorted(rang for rang in rangs if rang is not None) == [1, 2, 3, 4]
    # Le tableau de duels s'est joué jusqu'au bout : podium peuplé (or/argent/bronze).
    assert len(etat.tableaux) == 1
    assert etat.tableaux[0].est_termine
    assert len(etat.tableaux[0].podium) >= 3


def test_avancer_pas_a_pas_progresse_puis_termine() -> None:
    """CA bot : `avancer` fait progresser une unité à la fois ; épuisé, l'état passe `terminée`."""
    ctx = _Contexte(nb_archers=2, avec_duels=False, nb_volees=2, nb_fleches=3)
    service = ctx.service()
    depart = service.demarrer(ctx.tournoi_id, graine=7)

    un_pas = service.avancer(depart.session_id, nb_pas=1)
    assert un_pas.progression.volees_faites == 1
    assert un_pas.progression.volees_total == 2 * 2  # 2 volées x 2 archers

    # Beaucoup de pas d'un coup : la qualif (4 volées) s'épuise, la session se termine.
    fin = service.avancer(depart.session_id, nb_pas=50)
    assert fin.etat_pilote is EtatPilote.TERMINEE
    assert fin.progression.volees_faites == 4


# --- Déterminisme (règle 9) ---------------------------------------------------------------------


def test_meme_graine_meme_deroule() -> None:
    """Règle 9 : deux simulations de même graine produisent le **même** classement."""
    totaux = []
    for _ in range(2):
        ctx = _Contexte(nb_archers=5, avec_duels=False, nb_volees=3)
        service = ctx.service()
        depart = service.demarrer(ctx.tournoi_id, graine=99)
        etat = service.terminer(depart.session_id)
        totaux.append([ligne.total for ligne in etat.classement.lignes])
    assert totaux[0] == totaux[1]


def test_scores_generes_bornes_et_etales() -> None:
    """CA bot « scores plausibles » : les totaux tiennent dans le barème et **s'étalent**."""
    ctx = _Contexte(nb_archers=6, avec_duels=False, nb_volees=3, nb_fleches=3)
    service = ctx.service()
    etat = service.terminer(service.demarrer(ctx.tournoi_id, graine=3).session_id)

    score_max = BaremeQualification.creer(3, 3).score_max  # 3 volées x 3 flèches x 10 = 90
    totaux = [ligne.total for ligne in etat.classement.lignes]
    assert all(0 <= total <= score_max for total in totaux)
    # Des niveaux distincts par archer → des totaux distincts (déterministe, donc non flaky).
    assert len(set(totaux)) > 1


# --- CA bot pausable : la pause bloque le bot et ouvre la saisie ---------------------------------


def test_pause_bloque_le_bot_et_reprise_le_relance() -> None:
    """CA bot : en pause, `avancer` est refusé (409) ; reprendre rend la main au bot."""
    ctx = _Contexte(nb_archers=3, avec_duels=False)
    service = ctx.service()
    depart = service.demarrer(ctx.tournoi_id, graine=5)

    service.avancer(depart.session_id, nb_pas=1)
    en_pause = service.pause(depart.session_id)
    assert en_pause.etat_pilote is EtatPilote.EN_PAUSE

    with pytest.raises(PilotageSimulationInvalide):
        service.avancer(depart.session_id)

    reprise = service.reprendre(depart.session_id)
    assert reprise.etat_pilote is EtatPilote.EN_COURS
    service.avancer(depart.session_id)  # ne lève plus


# --- CA cockpit interactif : reprise en main en qualification -----------------------------------


def test_saisie_manuelle_qualif_pose_les_valeurs_de_l_humain() -> None:
    """CA cockpit : en pause, l'humain saisit une volée à la place de la cible ; le bot n'y touche
    plus ensuite."""
    ctx = _Contexte(nb_archers=3, avec_duels=False, nb_volees=2, nb_fleches=3)
    service = ctx.service()
    depart = service.demarrer(ctx.tournoi_id, graine=5)

    en_pause = service.pause(depart.session_id)
    unite = en_pause.prochaine_unite
    assert isinstance(unite, ProchaineVolee)
    # L'humain tire trois « 10 » pour cet archer (valeurs légales du blason par défaut).
    valeurs = (ZoneScore.DIX,) * unite.nb_fleches
    apres = service.saisir_volee(depart.session_id, unite.archer_id, unite.numero_volee, valeurs)
    assert apres.progression.volees_faites == 1

    detail = service.detail_archer(depart.session_id, unite.archer_id)
    volee = next(v for v in detail.volees if v.numero == unite.numero_volee)
    assert volee.valeurs == valeurs
    assert volee.validee_par == "Manuel"

    # Le bot reprend et déroule tout : il **ne réécrit pas** la volée validée par l'humain.
    service.reprendre(depart.session_id)
    service.terminer(depart.session_id)
    detail_final = service.detail_archer(depart.session_id, unite.archer_id)
    volee_finale = next(v for v in detail_final.volees if v.numero == unite.numero_volee)
    assert volee_finale.valeurs == valeurs
    assert volee_finale.validee_par == "Manuel"


def test_saisie_manuelle_refusee_hors_pause() -> None:
    """CA cockpit : la saisie manuelle n'est possible qu'en pause (bot en cours → 409)."""
    ctx = _Contexte(nb_archers=2, avec_duels=False)
    service = ctx.service()
    depart = service.demarrer(ctx.tournoi_id, graine=1)
    unite = depart.prochaine_unite
    assert isinstance(unite, ProchaineVolee)
    with pytest.raises(PilotageSimulationInvalide):
        service.saisir_volee(
            depart.session_id, unite.archer_id, unite.numero_volee, (ZoneScore.DIX,) * 3
        )


def test_saisie_manuelle_valeurs_invalides_refusees() -> None:
    """Reprise en main : un mauvais nombre de flèches est refusé (erreur de domaine, 422)."""
    from domain.erreurs import NombreFlechesVoleeInvalide

    ctx = _Contexte(nb_archers=2, avec_duels=False, nb_fleches=3)
    service = ctx.service()
    depart = service.demarrer(ctx.tournoi_id, graine=1)
    service.pause(depart.session_id)
    unite = service.etat(depart.session_id).prochaine_unite
    assert isinstance(unite, ProchaineVolee)
    with pytest.raises(NombreFlechesVoleeInvalide):
        service.saisir_volee(
            depart.session_id,
            unite.archer_id,
            unite.numero_volee,
            (ZoneScore.DIX,),  # 1 ≠ 3
        )


# --- CA cockpit interactif : reprise en main en duels -------------------------------------------


def _avancer_jusqu_aux_duels(service: ServicePilotageSimulation, session_id: int) -> None:
    """Fait avancer le bot jusqu'à ce que l'étape courante soit les duels (qualif épuisée)."""
    for _ in range(500):
        etat = service.avancer(session_id, nb_pas=1)
        if etat.etape is EtapeSimulation.DUELS or etat.etat_pilote is EtatPilote.TERMINEE:
            return
    raise AssertionError("La simulation n'a jamais atteint l'étape des duels.")


def test_reprise_en_main_duel_designe_le_vainqueur() -> None:
    """CA cockpit : en pause pendant les duels, l'humain désigne le vainqueur d'un match
    (scoreur)."""
    ctx = _Contexte(nb_archers=4, avec_duels=True, nb_volees=2, nb_fleches=3)
    service = ctx.service()
    depart = service.demarrer(ctx.tournoi_id, graine=2)
    _avancer_jusqu_aux_duels(service, depart.session_id)

    en_pause = service.pause(depart.session_id)
    unite = en_pause.prochaine_unite
    assert isinstance(unite, ProchaineDuel)
    assert unite.haut is not None and unite.bas is not None

    apres = service.designer_vainqueur(
        depart.session_id, unite.phase_id, unite.match_numero, Cote.HAUT
    )
    # Le match désigné est tranché en faveur du camp haut (l'humain a joué le scoreur).
    tableau = apres.tableaux[0]
    match = next(d for d in tableau.duels if d.numero == unite.match_numero)
    assert match.duel is not None
    assert match.duel.validee_par == "Manuel"
    assert match.duel.resultat.vainqueur is Cote.HAUT


def test_designer_vainqueur_refuse_hors_pause() -> None:
    """CA cockpit : désigner un vainqueur n'est possible qu'en pause."""
    ctx = _Contexte(nb_archers=4, avec_duels=True, nb_volees=2)
    service = ctx.service()
    depart = service.demarrer(ctx.tournoi_id, graine=2)
    _avancer_jusqu_aux_duels(service, depart.session_id)
    unite = service.etat(depart.session_id).prochaine_unite
    assert isinstance(unite, ProchaineDuel)
    with pytest.raises(PilotageSimulationInvalide):
        service.designer_vainqueur(depart.session_id, unite.phase_id, unite.match_numero, Cote.HAUT)


# --- Non-pollution (invariant d'épic) -----------------------------------------------------------


def test_le_deroule_ne_pollue_pas_les_repositories_reels() -> None:
    """Invariant d'épic : après un déroulé complet, les repos réels (séries) restent **vides**.

    Le bot écrit toutes ses volées et ses duels dans le **harnais** jetable ; côté réel, aucune
    série n'apparaît (le tournoi de test partait sans aucune série)."""
    ctx = _Contexte(nb_archers=4)
    service = ctx.service()
    assert ctx.series.par_tournoi(ctx.tournoi_id) == []

    depart = service.demarrer(ctx.tournoi_id, graine=1)
    service.terminer(depart.session_id)

    assert ctx.series.par_tournoi(ctx.tournoi_id) == []


# --- Diffusion (mécanisme service) --------------------------------------------------------------


def test_chaque_mutation_signale_la_session() -> None:
    """CA diffusion (mécanisme) : démarrer, avancer, pause, reprendre, saisir signalent la
    session."""
    ctx = _Contexte(nb_archers=2, avec_duels=False)
    diffusion = _DiffusionFausse()
    service = ctx.service(diffusion=diffusion)

    depart = service.demarrer(ctx.tournoi_id, graine=1)  # 1 signal
    service.avancer(depart.session_id)  # 2
    service.pause(depart.session_id)  # 3
    unite = service.etat(depart.session_id).prochaine_unite
    assert isinstance(unite, ProchaineVolee)
    service.saisir_volee(
        depart.session_id, unite.archer_id, unite.numero_volee, (ZoneScore.NEUF,) * 3
    )  # 4
    service.reprendre(depart.session_id)  # 5

    assert diffusion.signaux == [depart.session_id] * 5


# --- Garde-fous ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "statut",
    [StatutTournoi.EN_COURS, StatutTournoi.TERMINE, StatutTournoi.ARCHIVE],
)
def test_demarrer_sur_tournoi_demarre_refuse(statut: StatutTournoi) -> None:
    """Garde-fou (ADR-0054/0055) : on ne pilote qu'un tournoi avant démarrage."""
    ctx = _Contexte(nb_archers=2)
    ctx.statut(statut)
    with pytest.raises(SimulationTournoiDemarre):
        ctx.service().demarrer(ctx.tournoi_id, graine=1)


def test_demarrer_sans_qualif_refuse() -> None:
    """Sans phase de qualification (donc sans barème), le bot n'a pas de déroulé : refus (404)."""
    ctx = _Contexte(nb_archers=2, avec_qualif=False, avec_duels=False)
    with pytest.raises(PhaseQualificationAbsente):
        ctx.service().demarrer(ctx.tournoi_id, graine=1)


def test_reprendre_hors_pause_refuse() -> None:
    ctx = _Contexte(nb_archers=2, avec_duels=False)
    service = ctx.service()
    depart = service.demarrer(ctx.tournoi_id, graine=1)  # en_cours
    with pytest.raises(PilotageSimulationInvalide):
        service.reprendre(depart.session_id)


def test_avancer_apres_fin_refuse() -> None:
    ctx = _Contexte(nb_archers=2, avec_duels=False)
    service = ctx.service()
    depart = service.demarrer(ctx.tournoi_id, graine=1)
    service.terminer(depart.session_id)
    with pytest.raises(PilotageSimulationInvalide):
        service.avancer(depart.session_id)


def test_session_introuvable() -> None:
    ctx = _Contexte(nb_archers=1, avec_duels=False)
    with pytest.raises(SessionSimulationIntrouvable):
        ctx.service().etat(4242)


def test_arreter_retire_la_session() -> None:
    ctx = _Contexte(nb_archers=1, avec_duels=False)
    service = ctx.service()
    depart = service.demarrer(ctx.tournoi_id, graine=1)
    service.arreter(depart.session_id)
    with pytest.raises(SessionSimulationIntrouvable):
        service.etat(depart.session_id)
    service.arreter(depart.session_id)  # idempotent : ne lève pas


def test_designer_vainqueur_match_inexistant_refuse() -> None:
    """Reprise en main duel : viser un match inexistant est refusé (unité invalide)."""
    ctx = _Contexte(nb_archers=4, avec_duels=True, nb_volees=2)
    service = ctx.service()
    depart = service.demarrer(ctx.tournoi_id, graine=2)
    _avancer_jusqu_aux_duels(service, depart.session_id)
    unite = service.etat(depart.session_id).prochaine_unite
    assert isinstance(unite, ProchaineDuel)
    service.pause(depart.session_id)
    with pytest.raises(UniteSimulationInvalide):
        service.designer_vainqueur(depart.session_id, unite.phase_id, 9999, Cote.HAUT)


def test_valeur_zone_manque_vaut_zero() -> None:
    """Cohérence du barème du générateur : `M` vaut 0, les zones marquantes leur valeur."""
    assert valeur_zone(ZoneScore.MANQUE) == 0
    assert valeur_zone(ZoneScore.DIX) == 10
