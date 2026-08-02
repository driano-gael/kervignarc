"""Tests du **suivi** du déroulé (E07US004) — écrits **depuis le CA** (règle 9).

CA : « l'écran affiche le **même schéma à braquets** que l'atelier (E01US024), mais **rempli par la
réalité** : phase terminée / en cours / à venir, **tour en cours**, duels joués sur duels attendus,
braquets qui **se remplissent** au fur et à mesure ».

Le module ne recalcule **rien** de la projection : `domain.deroule.projeter` dit ce qui est
**attendu** (les braquets, la *Règle R*), ce module y superpose ce qui est **fait**. La séparation
est volontaire — un suivi qui recalculerait les duels attendus pourrait diverger du schéma que
l'atelier a montré, et le CA demande explicitement *le même* schéma.
"""

from __future__ import annotations

import pytest

from domain.deroule import TourBraquet
from domain.phase import StatutPhase
from domain.suivi_deroule import AvancementTour, avancement_bloc


def _tours(*duels: int) -> tuple[TourBraquet, ...]:
    """Des braquets dont seuls les `duels` comptent (les plages sont testées avec `projeter`)."""
    return tuple(
        TourBraquet(numero, nb, (1, 1), (2, 2)) for numero, nb in enumerate(duels, start=1)
    )


# --- Duels joués sur duels attendus ---------------------------------------------------------------


def test_un_bloc_a_venir_n_a_rien_de_joue() -> None:
    """« phase […] à venir » : le braquet est dessiné, vide."""
    bloc = avancement_bloc(
        ordre=2, statut=StatutPhase.A_VENIR, tours=_tours(8, 4, 2, 1), joues_par_tour={}
    )

    assert bloc.statut is StatutPhase.A_VENIR
    assert bloc.duels_joues == 0
    assert bloc.duels_attendus == 15
    assert bloc.tour_courant is None
    assert bloc.tours == (
        AvancementTour(1, 8, 0),
        AvancementTour(2, 4, 0),
        AvancementTour(3, 2, 0),
        AvancementTour(4, 1, 0),
    )


def test_les_duels_joues_se_cumulent_sur_les_duels_attendus() -> None:
    """« duels joués sur duels attendus » — le compte d'un coup d'œil, tours confondus."""
    bloc = avancement_bloc(
        ordre=2,
        statut=StatutPhase.EN_COURS,
        tours=_tours(8, 4, 2, 1),
        joues_par_tour={1: 8, 2: 3},
    )

    assert bloc.duels_joues == 11
    assert bloc.duels_attendus == 15


def test_un_tour_sait_s_il_est_termine() -> None:
    """« braquets qui **se remplissent** » : chaque braquet porte son propre remplissage."""
    assert AvancementTour(1, 8, 8).est_termine
    assert not AvancementTour(2, 4, 1).est_termine
    assert not AvancementTour(3, 2, 0).est_termine


# --- Le tour en cours -----------------------------------------------------------------------------


def test_le_tour_en_cours_est_le_premier_tour_incomplet() -> None:
    """CA « **tour en cours** » : celui où il reste des duels à jouer, le plus tôt dans l'arbre."""
    bloc = avancement_bloc(
        ordre=2, statut=StatutPhase.EN_COURS, tours=_tours(8, 4, 2, 1), joues_par_tour={1: 8, 2: 3}
    )

    assert bloc.tour_courant == 2


def test_un_tour_termine_mais_non_entame_au_suivant_designe_deja_le_suivant() -> None:
    """Entre deux tours, l'organisateur veut lire « on attaque les quarts », pas « rien en cours ».

    Le tour en cours est donc le premier **non terminé**, entamé ou non — c'est aussi ce que le
    « feu vert » d'E12US002 s'apprête à lancer.
    """
    bloc = avancement_bloc(
        ordre=2, statut=StatutPhase.EN_COURS, tours=_tours(8, 4, 2, 1), joues_par_tour={1: 8}
    )

    assert bloc.tour_courant == 2


def test_aucun_tour_en_cours_quand_tout_est_joue() -> None:
    """Tous les duels tranchés : plus rien ne tourne, même si la phase n'est pas encore clôturée
    (le geste de clôture est de l'organisateur, E12US008 — le suivi ne le devine pas)."""
    bloc = avancement_bloc(
        ordre=2,
        statut=StatutPhase.EN_COURS,
        tours=_tours(8, 4, 2, 1),
        joues_par_tour={1: 8, 2: 4, 3: 2, 4: 1},
    )

    assert bloc.tour_courant is None
    assert bloc.duels_joues == bloc.duels_attendus


def test_une_phase_terminee_n_a_pas_de_tour_en_cours() -> None:
    """« phase **terminée** » : même si des duels manquent à l'appel (forfaits, clôture décidée),
    rien n'y tourne plus."""
    bloc = avancement_bloc(
        ordre=2, statut=StatutPhase.TERMINEE, tours=_tours(8, 4, 2, 1), joues_par_tour={1: 8}
    )

    assert bloc.tour_courant is None


def test_une_phase_en_pause_garde_son_tour_en_cours() -> None:
    """Une pause suspend le tir, pas le tour : l'organisateur doit lire **où** il a suspendu."""
    bloc = avancement_bloc(
        ordre=2, statut=StatutPhase.EN_PAUSE, tours=_tours(8, 4, 2, 1), joues_par_tour={1: 8, 2: 1}
    )

    assert bloc.tour_courant == 2


# --- Robustesse -----------------------------------------------------------------------------------


def test_une_phase_sans_braquet_reste_lisible() -> None:
    """Une qualification (ou un type dont le moteur ne déduit pas les tours, `# DETTE-028`) n'a pas
    de braquet : le bloc existe quand même, avec son statut — sinon le schéma perdrait une phase."""
    bloc = avancement_bloc(ordre=1, statut=StatutPhase.EN_COURS, tours=(), joues_par_tour={})

    assert bloc.tours == ()
    assert bloc.tour_courant is None
    assert bloc.duels_attendus == 0
    assert bloc.duels_joues == 0


def test_un_compte_joue_superieur_a_l_attendu_ne_deborde_pas() -> None:
    """Garde-fou : la réalité et la projection peuvent diverger (format modifié en cours de route).

    Le suivi **plafonne** plutôt que d'afficher « 9 duels joués sur 8 », qui ferait douter du reste
    du schéma. La divergence n'est pas masquée : le tour est simplement lu comme terminé.
    """
    bloc = avancement_bloc(
        ordre=2, statut=StatutPhase.EN_COURS, tours=_tours(8, 4), joues_par_tour={1: 9}
    )

    assert bloc.tours[0] == AvancementTour(1, 8, 8)
    assert bloc.duels_joues == 8


def test_un_tour_joue_hors_braquet_est_ignore() -> None:
    """Un numéro de tour que la projection ne connaît pas ne crée pas de braquet fantôme."""
    bloc = avancement_bloc(
        ordre=2, statut=StatutPhase.EN_COURS, tours=_tours(8, 4), joues_par_tour={1: 2, 7: 5}
    )

    assert len(bloc.tours) == 2
    assert bloc.duels_joues == 2


@pytest.mark.parametrize("statut", list(StatutPhase))
def test_tout_statut_de_phase_est_accepte(statut: StatutPhase) -> None:
    """Le suivi doit rendre les **quatre** états du cycle de vie d'une phase, sans trou."""
    bloc = avancement_bloc(ordre=1, statut=statut, tours=_tours(2, 1), joues_par_tour={})

    assert bloc.statut is statut
