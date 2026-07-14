"""Tests du value object `GrainValidation` (E01US015, `D-11`) — domaine pur, sans infrastructure."""

from __future__ import annotations

import pytest

from domain.erreurs import (
    NombreVoleesParValidationInvalide,
    NombreVoleesParValidationManquant,
)
from domain.grain_validation import GrainValidation, TypeGrain


def test_fin_de_serie_na_pas_de_cadence() -> None:
    grain = GrainValidation.fin_de_serie()

    assert grain.type is TypeGrain.FIN_DE_SERIE
    assert grain.n_volees is None


def test_fin_de_duel_na_pas_de_cadence() -> None:
    grain = GrainValidation.fin_de_duel()

    assert grain.type is TypeGrain.FIN_DE_DUEL
    assert grain.n_volees is None


def test_toutes_les_n_volees_porte_sa_cadence() -> None:
    grain = GrainValidation.toutes_les_n_volees(2)

    assert grain.type is TypeGrain.TOUTES_LES_N_VOLEES
    assert grain.n_volees == 2


@pytest.mark.parametrize("cadence", [0, -1])
def test_une_cadence_inferieure_a_une_volee_est_refusee(cadence: int) -> None:
    with pytest.raises(NombreVoleesParValidationInvalide):
        GrainValidation.toutes_les_n_volees(cadence)


def test_creer_exige_une_cadence_pour_le_grain_toutes_les_n_volees() -> None:
    with pytest.raises(NombreVoleesParValidationManquant):
        GrainValidation.creer(TypeGrain.TOUTES_LES_N_VOLEES, None)


@pytest.mark.parametrize("type_grain", [TypeGrain.FIN_DE_SERIE, TypeGrain.FIN_DE_DUEL])
def test_creer_ignore_une_cadence_sur_un_grain_de_fin(type_grain: TypeGrain) -> None:
    # Une cadence sur un grain de fin serait une donnée morte : jamais lue, et trompeuse à la
    # relecture. Le domaine la laisse tomber plutôt que de la conserver.
    grain = GrainValidation.creer(type_grain, 3)

    assert grain.type is type_grain
    assert grain.n_volees is None


def test_creer_valide_la_cadence_du_grain_toutes_les_n_volees() -> None:
    with pytest.raises(NombreVoleesParValidationInvalide):
        GrainValidation.creer(TypeGrain.TOUTES_LES_N_VOLEES, 0)


def test_le_grain_est_immuable() -> None:
    grain = GrainValidation.fin_de_serie()

    # `setattr` plutôt qu'une affectation directe : mypy refuserait l'affectation sur une dataclass
    # gelée, ce qui imposerait un `type: ignore` — le backend n'en compte aucun, gardons-le ainsi.
    with pytest.raises(AttributeError):
        setattr(grain, "type", TypeGrain.FIN_DE_DUEL)  # noqa: B010


def test_deux_grains_de_memes_valeurs_sont_egaux() -> None:
    assert GrainValidation.toutes_les_n_volees(2) == GrainValidation.toutes_les_n_volees(2)
    assert GrainValidation.fin_de_serie() != GrainValidation.fin_de_duel()
