"""Tests unitaires du value object `BaremeQualification` (E01US009) — domaine pur, sans base."""

from __future__ import annotations

import pytest

from domain.bareme import BaremeQualification
from domain.erreurs import NombreFlechesParVoleeInvalide, NombreVoleesInvalide


def test_creer_bareme_valide() -> None:
    """Un barème valide expose ses grandeurs et les valeurs dérivées."""
    bareme = BaremeQualification.creer(20, 3)
    assert bareme.nb_volees == 20
    assert bareme.nb_fleches_par_volee == 3
    assert bareme.nb_fleches_total == 60
    assert bareme.score_max == 600


def test_preset_ffta_18m() -> None:
    """Le preset FFTA 18 m est 20 volées de 3 flèches (60 flèches, 600 points max)."""
    preset = BaremeQualification.preset_ffta_18m()
    assert (preset.nb_volees, preset.nb_fleches_par_volee) == (20, 3)
    assert preset.nb_fleches_total == 60
    assert preset.score_max == 600


@pytest.mark.parametrize("nb_volees", [0, -1])
def test_creer_refuse_moins_d_une_volee(nb_volees: int) -> None:
    """Un barème doit compter au moins une volée."""
    with pytest.raises(NombreVoleesInvalide):
        BaremeQualification.creer(nb_volees, 3)


@pytest.mark.parametrize("nb_fleches", [0, -2])
def test_creer_refuse_moins_d_une_fleche(nb_fleches: int) -> None:
    """Une volée doit compter au moins une flèche."""
    with pytest.raises(NombreFlechesParVoleeInvalide):
        BaremeQualification.creer(10, nb_fleches)


def test_valeurs_derivees_sur_un_format_club() -> None:
    """Les dérivées suivent des valeurs non FFTA (format club libre)."""
    bareme = BaremeQualification.creer(5, 3)
    assert bareme.nb_fleches_total == 15
    assert bareme.score_max == 150
