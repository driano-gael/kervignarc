"""Tests du réglage de barème de duel d'une phase (E01US011) — domaine pur, écrits depuis le CA.

Les numéros cités renvoient aux points du CA d'`E01US011` (`stories/E01-configuration.md`).
"""

from __future__ import annotations

import pytest

from domain.bareme import BaremeQualification
from domain.deroule_etape import EtapeDeroule
from domain.duel import BaremeDuel, ModeDuel, ReglageBaremeDuel, SurchargeArme
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


# --- CA 1 : un défaut et des surcharges par arme explicites -----------------------------------


def test_une_arme_sans_surcharge_tire_le_bareme_par_defaut() -> None:
    reglage = ReglageBaremeDuel(par_defaut=SETS_4)

    assert reglage.pour("Arc classique", tours_restants=0) == SETS_4
    assert reglage.pour(None, tours_restants=0) == SETS_4


def test_une_arme_surchargee_tire_sa_surcharge() -> None:
    reglage = ReglageBaremeDuel(
        par_defaut=SETS_6, surcharges=(SurchargeArme("Arc à poulies", CUMUL_5x3),)
    )

    assert reglage.pour("Arc à poulies", tours_restants=0) == CUMUL_5x3
    assert reglage.pour("Arc classique", tours_restants=0) == SETS_6


def test_l_arme_se_compare_sans_casse_ni_espaces_de_bord() -> None:
    reglage = ReglageBaremeDuel(
        par_defaut=SETS_6, surcharges=(SurchargeArme("Arc à poulies", CUMUL_5x3),)
    )

    assert reglage.pour("  ARC À POULIES ", tours_restants=0) == CUMUL_5x3


def test_la_surcharge_n_est_pas_une_devinette_sur_le_libelle() -> None:
    """La surcharge est **explicite** : un libellé qui contient « poulie » ne suffit pas."""
    reglage = ReglageBaremeDuel(
        par_defaut=SETS_6, surcharges=(SurchargeArme("Poulies", CUMUL_5x3),)
    )

    assert reglage.pour("Arc à poulies", tours_restants=0) == SETS_6


def test_deux_surcharges_pour_la_meme_arme_sont_refusees() -> None:
    with pytest.raises(BaremeDuelInvalide):
        ReglageBaremeDuel(
            par_defaut=SETS_6,
            surcharges=(
                SurchargeArme("Arc à poulies", CUMUL_5x3),
                SurchargeArme("arc à POULIES ", SETS_4),
            ),
        )


def test_une_surcharge_sans_arme_est_refusee() -> None:
    with pytest.raises(BaremeDuelInvalide):
        SurchargeArme("   ", CUMUL_5x3)


def test_le_libelle_d_une_surcharge_est_normalise() -> None:
    assert SurchargeArme("  Arc nu ", SETS_4).arme == "Arc nu"


# --- Égalité sémantique : le verrou (CA 4) compare des réglages ------------------------------


def test_l_ordre_des_surcharges_ne_change_pas_le_reglage() -> None:
    """Le même réglage renvoyé dans un autre ordre n'est pas un changement de barème (409)."""
    poulies = SurchargeArme("Arc à poulies", CUMUL_5x3)
    nu = SurchargeArme("Arc nu", SETS_4)

    assert ReglageBaremeDuel(SETS_6, (poulies, nu)) == ReglageBaremeDuel(SETS_6, (nu, poulies))


# --- CA 1 : seules les phases de duels portent un barème de duel ------------------------------


@pytest.mark.parametrize(
    "type_phase",
    [TypePhase.ELIMINATION_DIRECTE, TypePhase.POULES, TypePhase.SUISSE, TypePhase.COLLINE],
)
def test_une_phase_de_duels_accepte_un_bareme_de_duel(type_phase: TypePhase) -> None:
    etape = EtapeDeroule(
        tournoi_id=1,
        ordre=2,
        type=type_phase,
        bareme_duel=ReglageBaremeDuel(par_defaut=SETS_4),
    )

    etape.verifier_instanciable()
    assert etape.instancier(1).bareme_duel == ReglageBaremeDuel(par_defaut=SETS_4)


@pytest.mark.parametrize(
    "type_phase", [TypePhase.BIG_SHOOT_OFF, TypePhase.BARRAGE, TypePhase.ECHAUFFEMENT]
)
def test_une_phase_sans_duel_refuse_un_bareme_de_duel(type_phase: TypePhase) -> None:
    etape = EtapeDeroule(
        tournoi_id=1, ordre=2, type=type_phase, bareme_duel=ReglageBaremeDuel(par_defaut=SETS_4)
    )

    with pytest.raises(BaremeDuelInvalide):
        etape.verifier_instanciable()


def test_une_phase_de_duels_sans_reglage_reste_licite() -> None:
    """CA 3 : l'absence de réglage est un état normal, pas un brouillon à compléter."""
    etape = EtapeDeroule(tournoi_id=1, ordre=2, type=TypePhase.ELIMINATION_DIRECTE)

    etape.verifier_instanciable()
    assert etape.bareme_duel is None


# --- CA 5 : le preset club de qualification ---------------------------------------------------


def test_preset_club_de_qualification_cinq_volees_de_trois() -> None:
    bareme = BaremeQualification.preset_club()

    assert (bareme.nb_volees, bareme.nb_fleches_par_volee) == (5, 3)
