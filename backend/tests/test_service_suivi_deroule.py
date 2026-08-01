"""Tests du service de suivi du déroulé (E07US004) — **dérivés du CA**, avant impl (règle 9).

Source : `stories/E07-affichage-public.md`, E07US004, puce « CA — le plan de tournoi, en suivi » :
*« le **même schéma à braquets** que l'atelier (E01US024), mais **rempli par la réalité** : phase
terminée / en cours / à venir, **tour en cours**, duels joués sur duels attendus, braquets qui **se
remplissent** au fur et à mesure »*.

Deux exigences se testent **ici** et non dans le domaine : elles portent sur la composition.

1. la projection rendue est **la même** que celle de l'atelier (c'est le mot « même » du CA) ;
2. un **exempt** (bye) n'est pas un duel joué — sans quoi le premier tour d'un tableau incomplet
   s'afficherait terminé avant que quiconque ait tiré.
"""

from __future__ import annotations

import dataclasses
import datetime
from collections.abc import Sequence

import pytest

from application.erreurs import TournoiIntrouvable
from application.suivi_deroule import ServiceSuiviDeroule
from domain.bareme import BaremeQualification
from domain.deroule import projeter
from domain.grain_validation import GrainValidation
from domain.participant import Participant
from domain.phase import NatureSource, Phase, PhaseId, SourcePhase, StatutPhase, TypePhase
from domain.politiques import (
    ByesAuxMieuxClasses,
    PlacementEnCascade,
    ProfondeurPodium,
    SeedingSerpent,
)
from domain.tableau import Tableau, construire_tableau
from domain.tournoi import StatutTournoi, Tournoi, TournoiId

_DATE = datetime.date(2026, 3, 14)


def _tableau(effectif: int) -> Tableau:
    """Un tableau d'élimination directe pour `effectif` participants, rangés par qualification."""
    return construire_tableau(
        [Participant.individuel(rang) for rang in range(1, effectif + 1)],
        SeedingSerpent(),
        ByesAuxMieuxClasses(),
        PlacementEnCascade(),
        ProfondeurPodium(),
    )


def _jouer(tableau: Tableau, numeros: Sequence[int]) -> Tableau:
    """Fait gagner le camp haut des matchs désignés, **dans l'ordre**.

    Le match est **relu dans le tableau courant** à chaque itération : `Tableau.jouer` rend une
    nouvelle instance où les occupants du tour suivant viennent d'être propagés. Itérer sur une
    photo prise avant le premier coup donnerait des occupants `None` dès le deuxième tour.
    """
    for numero in numeros:
        match = tableau.match(numero)
        assert match.haut is not None, f"Le match {numero} n'a pas d'occupant haut."
        tableau = tableau.jouer(numero, match.haut)
    return tableau


class FauxPhaseRepository:
    """Repository de phases en mémoire — juste ce que le service lit."""

    def __init__(self) -> None:
        self.phases: list[Phase] = []

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Phase]:
        return [p for p in self.phases if p.tournoi_id == tournoi_id]


class FauxTournoiRepository:
    def __init__(self) -> None:
        self._tournois: dict[int, Tournoi] = {}
        self._sequence = 0

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        self._sequence += 1
        persiste = dataclasses.replace(tournoi, id=self._sequence)
        self._tournois[self._sequence] = persiste
        return persiste

    def par_id(self, tournoi_id: TournoiId) -> Tournoi | None:
        return self._tournois.get(tournoi_id)


class FauxCompteurEngages:
    """Combien d'archers sont engagés — réglable, c'est l'effectif que la projection résout."""

    def __init__(self, nb: int = 0) -> None:
        self.nb = nb

    def nb_engages(self, tournoi_id: TournoiId) -> int:
        return self.nb


class FauxLecteurTableau:
    """Rend un `Tableau` pré-construit par phase ; lève si on l'interroge sur une phase inconnue."""

    def __init__(self) -> None:
        self.tableaux: dict[PhaseId, Tableau] = {}

    def reconstruire(self, tournoi_id: TournoiId, phase_id: PhaseId) -> tuple[Tableau, object]:
        return self.tableaux[phase_id], {}


def _qualification(
    tournoi_id: int, ordre: int = 1, statut: StatutPhase = StatutPhase.A_VENIR
) -> Phase:
    """La phase de qualification du tournoi, dans le statut voulu."""
    phase = Phase.qualification(
        tournoi_id=tournoi_id,
        bareme=BaremeQualification.creer(12, 3),
        validation=GrainValidation.fin_de_serie(),
    )
    phase = dataclasses.replace(phase, ordre=ordre)
    return phase.demarrer() if statut is StatutPhase.EN_COURS else phase


class Contexte:
    def __init__(self, nb_engages: int = 8) -> None:
        self.tournois = FauxTournoiRepository()
        self.phases = FauxPhaseRepository()
        self.engages = FauxCompteurEngages(nb_engages)
        self.tableaux = FauxLecteurTableau()
        tournoi = self.tournois.ajouter(
            dataclasses.replace(Tournoi.creer("Tournoi", _DATE), statut=StatutTournoi.EN_COURS)
        )
        assert tournoi.id is not None
        self.tournoi_id: TournoiId = tournoi.id
        self.service = ServiceSuiviDeroule(
            tournoi_repository=self.tournois,  # type: ignore[arg-type]
            phase_repository=self.phases,  # type: ignore[arg-type]
            engages=self.engages,
            tableaux=self.tableaux,
        )

    def ajouter_phase(self, phase: Phase, phase_id: PhaseId) -> Phase:
        persistee = dataclasses.replace(phase, id=phase_id)
        self.phases.phases.append(persistee)
        return persistee


@pytest.fixture
def ctx() -> Contexte:
    return Contexte()


def _tableau_ed(tournoi_id: int, ordre: int, statut: StatutPhase) -> Phase:
    """Une élimination directe alimentée par les rangs 1..8 de la qualification."""
    phase = Phase.creer(
        tournoi_id=tournoi_id,
        ordre=ordre,
        type=TypePhase.ELIMINATION_DIRECTE,
        sources=(SourcePhase(ordre_source=1, rang_debut=1, rang_fin=8, nature=NatureSource.RANGS),),
        effectif=8,
    )
    if statut is StatutPhase.EN_COURS:
        return phase.demarrer()
    if statut is StatutPhase.TERMINEE:
        return phase.demarrer().terminer()
    return phase


# --- « le **même** schéma qu'à l'atelier » -------------------------------------------------------


def test_la_projection_est_celle_de_l_atelier(ctx: Contexte) -> None:
    """Le CA dit « le **même** schéma à braquets » : on ne recalcule pas, on réutilise `projeter`.

    Le test compare au résultat brut de `domain.deroule.projeter` sur les mêmes étapes et le même
    effectif — si un jour le suivi se mettait à dessiner autrement, il échouerait.
    """
    ctx.ajouter_phase(_qualification(ctx.tournoi_id), 1)
    ctx.ajouter_phase(_tableau_ed(ctx.tournoi_id, 2, StatutPhase.A_VENIR), 2)

    suivi = ctx.service.pour_tournoi(ctx.tournoi_id)

    attendue = projeter(ctx.phases.par_tournoi(ctx.tournoi_id), 8)
    assert suivi.projection == attendue
    assert suivi.effectif == 8


def test_toutes_les_phases_sont_suivies_meme_sans_braquet(ctx: Contexte) -> None:
    """Une qualification n'a pas de braquet : elle reste dans le suivi, avec son statut."""
    ctx.ajouter_phase(_qualification(ctx.tournoi_id, statut=StatutPhase.EN_COURS), 1)
    ctx.ajouter_phase(_tableau_ed(ctx.tournoi_id, 2, StatutPhase.A_VENIR), 2)

    suivi = ctx.service.pour_tournoi(ctx.tournoi_id)

    assert [b.ordre for b in suivi.avancement.blocs] == [1, 2]
    assert suivi.avancement.blocs[0].statut is StatutPhase.EN_COURS
    assert suivi.avancement.blocs[0].tours == ()
    assert suivi.avancement.ordre_courant == 1


# --- « duels joués sur duels attendus » -----------------------------------------------------------


def test_un_tableau_neuf_n_a_aucun_duel_joue(ctx: Contexte) -> None:
    ctx.ajouter_phase(_qualification(ctx.tournoi_id), 1)
    ctx.ajouter_phase(_tableau_ed(ctx.tournoi_id, 2, StatutPhase.EN_COURS), 2)
    ctx.tableaux.tableaux[2] = _tableau(8)

    bloc = ctx.service.pour_tournoi(ctx.tournoi_id).avancement.blocs[1]

    assert bloc.duels_joues == 0
    assert bloc.duels_attendus == 7
    assert bloc.tour_courant == 1


def test_les_duels_tranches_remplissent_leur_braquet(ctx: Contexte) -> None:
    """« braquets qui **se remplissent** au fur et à mesure »."""
    ctx.ajouter_phase(_qualification(ctx.tournoi_id), 1)
    ctx.ajouter_phase(_tableau_ed(ctx.tournoi_id, 2, StatutPhase.EN_COURS), 2)
    tableau = _tableau(8)
    ctx.tableaux.tableaux[2] = _jouer(
        tableau, [m.numero for m in tableau.matchs if m.tour == 1][:2]
    )

    bloc = ctx.service.pour_tournoi(ctx.tournoi_id).avancement.blocs[1]

    assert bloc.tours[0].duels_joues == 2
    assert bloc.tours[0].duels_attendus == 4
    assert bloc.tour_courant == 1


def test_la_petite_finale_ne_termine_pas_la_phase(ctx: Contexte) -> None:
    """**Non-régression** (trouvée par la revue adversariale) : le dernier tour a **deux** branches.

    Une élimination directe en placement (`PlacementEnCascade` + `ProfondeurPodium`) fait rejouer
    les perdants des demies : au dernier tour, il y a la **finale** (places 1-2) *et* la **petite
    finale** (places 3-4). Le braquet projeté, lui, ne suit que la branche des gagnants et n'annonce
    qu'**un** duel — c'est délibéré (E01US024), et le CA impose de garder *le même* schéma.

    Le défaut : en comptant les deux matchs sous le même numéro de tour, on obtenait « 2 joués sur 1
    attendu », plafonné à 1. La petite finale étant souvent tranchée **avant** la finale (ou en
    parallèle), l'écran projeté affichait « phase terminée · 7/7 duels » **pendant que la finale se
    tirait** — au moment de la journée où il est le plus regardé.

    Ce test joue la petite finale et **pas** la finale : c'est exactement le couple qui ouvrait le
    trou. Jouer tout le tableau ne prouverait rien, et n'en jouer qu'un tour non plus — ce que
    faisaient les tests d'origine.
    """
    ctx.ajouter_phase(_qualification(ctx.tournoi_id), 1)
    ctx.ajouter_phase(_tableau_ed(ctx.tournoi_id, 2, StatutPhase.EN_COURS), 2)
    tableau = _tableau(8)
    petite_finale = next(m.numero for m in tableau.matchs if m.place_en_jeu == (3, 4))
    # Tous les duels **sauf la finale** : les 4 du tour 1, les 2 demies, puis la petite finale.
    ordre = [m.numero for m in tableau.matchs if m.tour < 3] + [petite_finale]
    ctx.tableaux.tableaux[2] = _jouer(tableau, ordre)

    bloc = ctx.service.pour_tournoi(ctx.tournoi_id).avancement.blocs[1]

    # Le dernier braquet reste **ouvert** : la finale n'est pas tirée.
    assert bloc.tours[-1].duels_joues == 0
    assert bloc.tour_courant == 3
    assert bloc.duels_joues == 6
    assert bloc.duels_attendus == 7


def test_la_finale_tranchee_ferme_le_dernier_braquet(ctx: Contexte) -> None:
    """Le pendant du test précédent : c'est bien **la finale** qui clôt le dernier braquet."""
    ctx.ajouter_phase(_qualification(ctx.tournoi_id), 1)
    ctx.ajouter_phase(_tableau_ed(ctx.tournoi_id, 2, StatutPhase.EN_COURS), 2)
    tableau = _tableau(8)
    finale = next(m.numero for m in tableau.matchs if m.place_en_jeu == (1, 2))
    ordre = [m.numero for m in tableau.matchs if m.tour < 3] + [finale]
    ctx.tableaux.tableaux[2] = _jouer(tableau, ordre)

    bloc = ctx.service.pour_tournoi(ctx.tournoi_id).avancement.blocs[1]

    assert bloc.tours[-1].duels_joues == 1
    assert bloc.tour_courant is None
    assert bloc.duels_joues == bloc.duels_attendus == 7


def test_un_exempt_n_est_pas_un_duel_joue() -> None:
    """Piège central : un tableau **incomplet** distribue des exempts, gagnés d'office.

    Les compter ferait afficher « premier tour terminé » avant que quiconque ait tiré — et la
    projection, elle, ne les compte pas (`_braquets` : « 24 duellistes dans un tableau de 32 →
    8 duels, 8 exemptés »). Les deux comptes doivent parler de la même chose.
    """
    ctx = Contexte(nb_engages=6)
    ctx.ajouter_phase(_qualification(ctx.tournoi_id), 1)
    phase = Phase.creer(
        tournoi_id=ctx.tournoi_id,
        ordre=2,
        type=TypePhase.ELIMINATION_DIRECTE,
        sources=(SourcePhase(ordre_source=1, rang_debut=1, rang_fin=6, nature=NatureSource.RANGS),),
        effectif=6,
    ).demarrer()
    ctx.ajouter_phase(phase, 2)
    ctx.tableaux.tableaux[2] = _tableau(6)

    bloc = ctx.service.pour_tournoi(ctx.tournoi_id).avancement.blocs[1]

    assert bloc.tours[0].duels_attendus == 2
    assert bloc.tours[0].duels_joues == 0
    assert bloc.tour_courant == 1


# --- Robustesse -----------------------------------------------------------------------------------


def test_un_tournoi_inconnu_est_refuse(ctx: Contexte) -> None:
    with pytest.raises(TournoiIntrouvable):
        ctx.service.pour_tournoi(9999)


def test_un_tournoi_sans_phase_rend_un_suivi_vide(ctx: Contexte) -> None:
    """Avant qu'un format soit appliqué, l'écran doit afficher « rien à suivre », pas planter."""
    suivi = ctx.service.pour_tournoi(ctx.tournoi_id)

    assert suivi.avancement.blocs == ()
    assert suivi.avancement.ordre_courant is None


def test_un_tableau_illisible_ne_fait_pas_tomber_le_suivi(ctx: Contexte) -> None:
    """Robustesse jour J : un tableau qu'on ne sait pas reconstruire (format changé, phase mal
    câblée) laisse un bloc **à zéro joué**, jamais une page d'erreur — l'écran de salle tourne
    en permanence et personne n'est devant pour le relancer.
    """
    ctx.ajouter_phase(_qualification(ctx.tournoi_id), 1)
    ctx.ajouter_phase(_tableau_ed(ctx.tournoi_id, 2, StatutPhase.EN_COURS), 2)
    # aucun tableau enregistré pour la phase 2 : le lecteur lèvera un KeyError

    bloc = ctx.service.pour_tournoi(ctx.tournoi_id).avancement.blocs[1]

    assert bloc.duels_joues == 0
    assert bloc.duels_attendus == 7
