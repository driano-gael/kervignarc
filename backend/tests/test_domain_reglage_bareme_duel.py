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

CUMUL_5x3 = BaremeDuel(ModeDuel.CUMUL, nb_manches=5, nb_fleches_par_volee=3, points_pour_gagner=0)
SETS_4 = BaremeDuel(ModeDuel.SETS, nb_manches=5, nb_fleches_par_volee=3, points_pour_gagner=4)
SETS_6 = BaremeDuel(ModeDuel.SETS, nb_manches=5, nb_fleches_par_volee=3, points_pour_gagner=6)


# --- CA 1 : un défaut et des surcharges par arme explicites -----------------------------------


def test_une_arme_sans_surcharge_tire_le_bareme_par_defaut() -> None:
    reglage = ReglageBaremeDuel(par_defaut=SETS_4)

    assert reglage.pour("Arc classique") == SETS_4
    assert reglage.pour(None) == SETS_4


def test_une_arme_surchargee_tire_sa_surcharge() -> None:
    reglage = ReglageBaremeDuel(
        par_defaut=SETS_6, surcharges=(SurchargeArme("Arc à poulies", CUMUL_5x3),)
    )

    assert reglage.pour("Arc à poulies") == CUMUL_5x3
    assert reglage.pour("Arc classique") == SETS_6


def test_l_arme_se_compare_sans_casse_ni_espaces_de_bord() -> None:
    reglage = ReglageBaremeDuel(
        par_defaut=SETS_6, surcharges=(SurchargeArme("Arc à poulies", CUMUL_5x3),)
    )

    assert reglage.pour("  ARC À POULIES ") == CUMUL_5x3


def test_la_surcharge_n_est_pas_une_devinette_sur_le_libelle() -> None:
    """La surcharge est **explicite** : un libellé qui contient « poulie » ne suffit pas."""
    reglage = ReglageBaremeDuel(
        par_defaut=SETS_6, surcharges=(SurchargeArme("Poulies", CUMUL_5x3),)
    )

    assert reglage.pour("Arc à poulies") == SETS_6


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


# --- CA 2 : les deux presets ------------------------------------------------------------------


def test_preset_ffta_sets_a_6_et_poulies_au_cumul() -> None:
    reglage = ReglageBaremeDuel.preset_ffta(("Arc classique", "Arc à poulies", "Arc nu"))

    assert reglage.par_defaut == SETS_6
    assert reglage.pour("Arc à poulies") == CUMUL_5x3
    assert reglage.pour("Arc classique") == SETS_6
    assert reglage.pour("Arc nu") == SETS_6


def test_preset_club_sets_a_4_et_poulies_au_cumul_aussi() -> None:
    """Les poulies au cumul sont une règle d'**arme** : le preset club la pose aussi (CA 2)."""
    reglage = ReglageBaremeDuel.preset_club(("Arc classique", "Compound"))

    assert reglage.par_defaut == SETS_4
    assert reglage.pour("Compound") == CUMUL_5x3
    assert reglage.pour("Arc classique") == SETS_4


def test_un_preset_ne_surcharge_que_les_armes_a_poulies() -> None:
    reglage = ReglageBaremeDuel.preset_ffta(("Arc classique", "Arc nu"))

    assert reglage.surcharges == ()


def test_un_preset_ne_double_pas_une_arme_repetee() -> None:
    """Les armes viennent des catégories : deux catégories peuvent partager la même arme."""
    reglage = ReglageBaremeDuel.preset_ffta(("Arc à poulies", "arc à poulies", "Arc à poulies"))

    assert len(reglage.surcharges) == 1


def test_la_surcharge_posee_par_un_preset_reste_modifiable() -> None:
    """« Modifiables » (CA 2) : un preset est un point de départ, pas une valeur figée."""
    reglage = ReglageBaremeDuel.preset_ffta(("Arc à poulies",))
    modifie = ReglageBaremeDuel(
        par_defaut=reglage.par_defaut, surcharges=(SurchargeArme("Arc à poulies", SETS_4),)
    )

    assert modifie.pour("Arc à poulies") == SETS_4


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
