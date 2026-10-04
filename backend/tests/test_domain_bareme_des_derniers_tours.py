"""Tests du barème des derniers tours d'une phase (E01US027) — domaine pur, écrits depuis le CA.

Les numéros cités renvoient aux points du CA d'`E01US027` (`stories/E01-configuration.md`).
`tours_restants` compte les tours **après** celui du duel : 0 au dernier tour.
"""

from __future__ import annotations

import pytest

from domain.deroule_etape import EtapeDeroule
from domain.duel import (
    BaremeDesDerniersTours,
    BaremeDuel,
    ModeDuel,
    ReglageBaremeDuel,
    SurchargeArme,
    memes_baremes,
)
from domain.erreurs import BaremeDuelInvalide
from domain.phase import TypePhase

CUMUL_5x3 = BaremeDuel(
    ModeDuel.CUMUL, nb_manches=5, nb_fleches_par_volee=3, points_pour_gagner=0, nb_fleches_barrage=1
)
SETS_4 = BaremeDuel(
    ModeDuel.SETS, nb_manches=5, nb_fleches_par_volee=3, points_pour_gagner=4, nb_fleches_barrage=1
)
SETS_6 = BaremeDuel(
    ModeDuel.SETS, nb_manches=5, nb_fleches_par_volee=3, points_pour_gagner=6, nb_fleches_barrage=1
)
POULIES = SurchargeArme("Arc à poulies", CUMUL_5x3)


def _club(nb_tours: int = 2) -> ReglageBaremeDuel:
    """Le format club du référentiel §10.1 : 4 points, puis 6 à partir des ½ finales."""
    return ReglageBaremeDuel(
        par_defaut=SETS_4,
        surcharges=(POULIES,),
        derniers_tours=BaremeDesDerniersTours(
            nb_tours=nb_tours, reglage=ReglageBaremeDuel(par_defaut=SETS_6, surcharges=(POULIES,))
        ),
    )


# --- CA 2 : le barème des K derniers tours, compté à rebours ---------------------------------


@pytest.mark.parametrize(("tours_restants", "attendu"), [(0, SETS_6), (1, SETS_6), (2, SETS_4)])
def test_les_k_derniers_tours_tirent_le_bareme_des_derniers_tours(
    tours_restants: int, attendu: BaremeDuel
) -> None:
    """K = 2 : la finale (0 tour après) et les ½ finales (1) à 6 points, les ¼ (2) à 4."""
    assert _club().pour("Arc classique", tours_restants=tours_restants) == attendu


def test_k_vaut_un_ne_couvre_que_le_dernier_tour() -> None:
    reglage = _club(nb_tours=1)

    assert reglage.pour("Arc classique", tours_restants=0) == SETS_6
    assert reglage.pour("Arc classique", tours_restants=1) == SETS_4


def test_sans_bareme_des_derniers_tours_le_tour_ne_change_rien() -> None:
    """CA 6 : une phase réglée sans lui garde exactement son comportement d'avant."""
    reglage = ReglageBaremeDuel(par_defaut=SETS_4)

    assert reglage.derniers_tours is None
    assert reglage.pour("Arc classique", tours_restants=0) == SETS_4
    assert reglage.pour("Arc classique", tours_restants=5) == SETS_4


# --- CA 1 : un réglage complet, défaut et surcharges par arme --------------------------------


def test_les_surcharges_par_arme_valent_aussi_aux_derniers_tours() -> None:
    """Les poulies restent au cumul en finale : le réglage des derniers tours a ses surcharges."""
    reglage = ReglageBaremeDuel(
        par_defaut=SETS_4,
        derniers_tours=BaremeDesDerniersTours(
            nb_tours=2, reglage=ReglageBaremeDuel(par_defaut=SETS_6, surcharges=(POULIES,))
        ),
    )

    assert reglage.pour("ARC À POULIES", tours_restants=0) == CUMUL_5x3
    assert reglage.pour("Arc à poulies", tours_restants=2) == SETS_4


@pytest.mark.parametrize("nb_tours", [0, -1])
def test_k_doit_couvrir_au_moins_un_tour(nb_tours: int) -> None:
    with pytest.raises(BaremeDuelInvalide):
        BaremeDesDerniersTours(nb_tours=nb_tours, reglage=ReglageBaremeDuel(par_defaut=SETS_6))


def test_le_reglage_des_derniers_tours_n_en_porte_pas_un_second() -> None:
    with pytest.raises(BaremeDuelInvalide):
        BaremeDesDerniersTours(nb_tours=1, reglage=_club())


# --- CA 5 : le verrou compare le réglage entier ----------------------------------------------


def test_poser_le_bareme_des_derniers_tours_change_le_reglage() -> None:
    sans = ReglageBaremeDuel(par_defaut=SETS_4, surcharges=(POULIES,))

    assert not memes_baremes(sans, _club())


def test_changer_k_change_le_reglage() -> None:
    assert not memes_baremes(_club(nb_tours=2), _club(nb_tours=3))


def test_changer_le_bareme_des_derniers_tours_change_le_reglage() -> None:
    autre = ReglageBaremeDuel(
        par_defaut=SETS_4,
        surcharges=(POULIES,),
        derniers_tours=BaremeDesDerniersTours(
            nb_tours=2, reglage=ReglageBaremeDuel(par_defaut=SETS_4)
        ),
    )

    assert not memes_baremes(_club(), autre)


def test_la_casse_d_une_arme_des_derniers_tours_ne_change_pas_le_reglage() -> None:
    """Même égalité sémantique qu'au barème principal (ADR-0117 §5)."""
    recasse = ReglageBaremeDuel(
        par_defaut=SETS_4,
        surcharges=(POULIES,),
        derniers_tours=BaremeDesDerniersTours(
            nb_tours=2,
            reglage=ReglageBaremeDuel(
                par_defaut=SETS_6, surcharges=(SurchargeArme("arc À Poulies", CUMUL_5x3),)
            ),
        ),
    )

    assert memes_baremes(_club(), recasse)


def test_les_baremes_d_une_arme_couvrent_les_deux_portees() -> None:
    """Ce que fige l'arme d'une catégorie (ADR-0117 §7) : l'un **ou** l'autre barème."""
    assert _club().baremes_pour("Arc classique") == (SETS_4, SETS_6)
    assert ReglageBaremeDuel(par_defaut=SETS_4).baremes_pour("Arc classique") == (SETS_4,)


# --- CA 6 : le réglage voyage avec l'étape -----------------------------------------------------


@pytest.mark.parametrize(
    "type_phase",
    [TypePhase.ELIMINATION_DIRECTE, TypePhase.POULES, TypePhase.SUISSE, TypePhase.COLLINE],
)
def test_toute_phase_de_duels_porte_un_bareme_des_derniers_tours(type_phase: TypePhase) -> None:
    etape = EtapeDeroule(tournoi_id=1, ordre=2, type=type_phase, bareme_duel=_club())

    etape.verifier_instanciable()
    assert etape.instancier(1).bareme_duel == _club()
