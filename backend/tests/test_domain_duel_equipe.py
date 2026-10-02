"""Tests unitaires du match d'équipe porté par le barème de duel (E13US003) — domaine pur.

Dérivés des **CA** d'E13US003 (`stories/E13-equipes.md`) et du référentiel FFTA (§6.4, §7, §8.2),
**avant** l'implémentation (règle 9) : volée d'un camp = cumul de ses flèches quel qu'en soit le
tireur ; nombre de flèches de barrage porté par le barème ; barrage à N flèches, plus haut total
puis désignation ; cas de référence 4-4 → 5-4.
"""

from __future__ import annotations

import pytest

from domain.blason import ZoneScore
from domain.duel import BaremeDuel, Cote, Duel, ModeDuel
from domain.erreurs import BaremeDuelInvalide, BarrageIndecis, NombreFlechesVoleeInvalide
from domain.participant import Participant

ZONES = (
    ZoneScore.DIX,
    ZoneScore.NEUF,
    ZoneScore.HUIT,
    ZoneScore.SEPT,
    ZoneScore.SIX,
    ZoneScore.MANQUE,
)

EQUIPE_A = Participant.equipe(1)
EQUIPE_B = Participant.equipe(2)

# FFTA §6.4 / §7 : sets, 4 manches de 6 flèches (2 par archer), premier à 5 ; barrage 3 (§8.2).
CLASSIQUE_EQUIPE = BaremeDuel(
    ModeDuel.SETS, nb_manches=4, nb_fleches_par_volee=6, points_pour_gagner=5, nb_fleches_barrage=3
)
POULIES_EQUIPE = BaremeDuel(
    ModeDuel.CUMUL, nb_manches=4, nb_fleches_par_volee=6, points_pour_gagner=0, nb_fleches_barrage=3
)


def _f(*valeurs: str) -> tuple[ZoneScore, ...]:
    return tuple(ZoneScore(v) for v in valeurs)


def _quatre_partout() -> Duel:
    """Quatre manches d'équipe : gagnée, perdue, nulle, nulle → 4-4, barrage requis (§7)."""
    duel = Duel.vide(CLASSIQUE_EQUIPE, EQUIPE_A, EQUIPE_B)
    manches = [
        (_f("10", "10", "9", "9", "9", "9"), _f("9", "9", "9", "9", "9", "9")),  # 56-54 : 2-0
        (_f("8", "8", "8", "8", "8", "8"), _f("9", "9", "9", "9", "9", "9")),  # 48-54 : 0-2
        (_f("9", "9", "9", "9", "9", "9"), _f("10", "8", "9", "9", "9", "9")),  # 54-54 : 1-1
        (_f("10", "10", "10", "10", "10", "10"), _f("10", "10", "10", "10", "10", "10")),  # 1-1
    ]
    for numero, (haut, bas) in enumerate(manches, start=1):
        duel = duel.saisir_manche(numero, haut, bas, zones_admises=ZONES, nb_fleches_par_volee=6)
    return duel


# --- CA 1 : la volée d'un camp est le cumul de ses flèches -------------------------------------


def test_une_manche_d_equipe_compare_le_cumul_des_six_fleches() -> None:
    duel = Duel.vide(CLASSIQUE_EQUIPE, EQUIPE_A, EQUIPE_B).saisir_manche(
        1,
        _f("10", "10", "10", "10", "10", "6"),  # 56
        _f("9", "9", "9", "9", "9", "9"),  # 54
        zones_admises=ZONES,
        nb_fleches_par_volee=6,
    )
    assert (duel.resultat.points_haut, duel.resultat.points_bas) == (2, 0)


def test_au_cumul_l_equipe_au_plus_haut_total_des_quatre_volees_gagne() -> None:
    duel = Duel.vide(POULIES_EQUIPE, EQUIPE_A, EQUIPE_B)
    for numero in range(1, 5):
        duel = duel.saisir_manche(
            numero,
            _f("10", "10", "10", "10", "10", "10"),
            _f("10", "10", "10", "10", "10", "9"),
            zones_admises=ZONES,
            nb_fleches_par_volee=6,
        )
    resultat = duel.resultat
    assert (resultat.points_haut, resultat.points_bas) == (240, 236)
    assert duel.vainqueur == EQUIPE_A


# --- CA 2 : le barème porte un nombre de flèches de barrage ≥ 1 ---------------------------------


@pytest.mark.parametrize("nb", [0, -1])
def test_un_bareme_sans_fleche_de_barrage_est_refuse(nb: int) -> None:
    with pytest.raises(BaremeDuelInvalide):
        BaremeDuel(ModeDuel.SETS, 4, 6, 5, nb_fleches_barrage=nb)


def test_les_presets_individuels_gardent_un_barrage_a_une_fleche() -> None:
    for preset in (
        BaremeDuel.preset_ffta_classique(),
        BaremeDuel.preset_ffta_poulies(),
        BaremeDuel.preset_club(),
    ):
        assert preset.nb_fleches_barrage == 1


# --- CA 3 : le barrage se saisit avec exactement N flèches par camp ------------------------------


@pytest.mark.parametrize(
    ("haut", "bas"),
    [
        (("10", "10"), ("9", "9", "9")),  # trop peu en haut
        (("10", "10", "10"), ("9", "9", "9", "9")),  # trop en bas
        (("10",), ("9",)),  # le barrage individuel n'est pas celui d'une équipe
    ],
)
def test_un_barrage_d_equipe_au_mauvais_nombre_de_fleches_est_refuse(
    haut: tuple[str, ...], bas: tuple[str, ...]
) -> None:
    with pytest.raises(NombreFlechesVoleeInvalide):
        _quatre_partout().saisir_barrage(_f(*haut), _f(*bas), zones_admises=ZONES)


def test_le_barrage_va_au_plus_haut_total_meme_sans_la_plus_haute_fleche() -> None:
    # Le bas tire le seul 10 du barrage, mais 10+6+6 = 22 < 9+9+9 = 27 : le total fait foi.
    duel = _quatre_partout().saisir_barrage(
        _f("9", "9", "9"), _f("10", "6", "6"), zones_admises=ZONES
    )
    assert duel.resultat.vainqueur is Cote.HAUT


def test_un_barrage_a_totaux_egaux_exige_une_designation() -> None:
    with pytest.raises(BarrageIndecis):
        _quatre_partout().saisir_barrage(_f("10", "9", "8"), _f("9", "9", "9"), zones_admises=ZONES)


def test_un_barrage_a_totaux_egaux_se_tranche_par_designation() -> None:
    duel = _quatre_partout().saisir_barrage(
        _f("10", "9", "8"), _f("9", "9", "9"), zones_admises=ZONES, gagnant_designe=Cote.BAS
    )
    assert duel.vainqueur == EQUIPE_B


def test_le_barrage_individuel_reste_a_une_fleche() -> None:
    bareme = BaremeDuel.preset_ffta_classique()
    duel = Duel.vide(bareme, Participant.individuel(1), Participant.individuel(2))
    for numero in range(1, 6):
        duel = duel.saisir_manche(
            numero,
            _f("9", "9", "9"),
            _f("9", "9", "9"),
            zones_admises=ZONES,
            nb_fleches_par_volee=3,
        )
    duel = duel.saisir_barrage(_f("10"), _f("9"), zones_admises=ZONES)
    assert duel.resultat.points_haut == 6


# --- CA 6 : cas de référence §7 — 4-4 en équipe, barrage à 3 flèches, score final 5-4 -------------


def test_oracle_match_d_equipe_quatre_partout_puis_barrage_cinq_a_quatre() -> None:
    duel = _quatre_partout()
    assert duel.resultat.barrage_requis
    assert (duel.resultat.points_haut, duel.resultat.points_bas) == (4, 4)

    duel = duel.saisir_barrage(_f("10", "9", "9"), _f("9", "9", "8"), zones_admises=ZONES)

    resultat = duel.resultat
    assert (resultat.points_haut, resultat.points_bas) == (5, 4)
    assert resultat.termine
    assert duel.vainqueur == EQUIPE_A
