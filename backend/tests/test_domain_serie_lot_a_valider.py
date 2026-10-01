"""Tests de `Serie.lot_a_valider` (E04US019) — domaine pur, sans base.

Dérivés du CA « ce qui est à valider » (`stories/E04-saisie-scores.md` § E04US019) : une feuille
est à valider **exactement quand la validation réussirait**, et la file ne doit ni proposer une
feuille que `valider` refuserait ni en cacher une qu'il accepterait.
"""

from __future__ import annotations

import pytest

from domain.blason import ZoneScore
from domain.erreurs import DomainError
from domain.grain_validation import GrainValidation
from domain.serie import Serie

_TRIO = (ZoneScore.DIX, ZoneScore.NEUF, ZoneScore.HUIT)
_PHASE = 4


def _serie(numeros: list[int], bareme: int) -> Serie:
    serie = Serie.vide(tournoi_id=1, archer_id=7, phase_id=_PHASE)
    for numero in numeros:
        serie = serie.saisir_volee(
            numero,
            _TRIO,
            zones_admises=tuple(ZoneScore),
            nb_fleches_par_volee=3,
            nb_volees_bareme=bareme,
        )
    return serie


def _numeros(serie: Serie, grain: GrainValidation, bareme: int) -> list[int]:
    return [v.numero for v in serie.lot_a_valider(grain=grain, nb_volees_bareme=bareme)]


def test_fin_de_serie_incomplete_n_a_rien_a_valider() -> None:
    assert _numeros(_serie([1, 2], 3), GrainValidation.fin_de_serie(), 3) == []


def test_fin_de_serie_complete_propose_toutes_les_volees() -> None:
    assert _numeros(_serie([1, 2, 3], 3), GrainValidation.fin_de_serie(), 3) == [1, 2, 3]


def test_fin_de_serie_deja_validee_n_a_plus_rien_a_valider() -> None:
    grain = GrainValidation.fin_de_serie()
    serie = _serie([1, 2, 3], 3).valider("RIOU", grain=grain, nb_volees_bareme=3)
    assert _numeros(serie, grain, 3) == []


def test_toutes_les_n_propose_le_premier_lot_complet() -> None:
    assert _numeros(_serie([1, 2, 3], 6), GrainValidation.toutes_les_n_volees(2), 6) == [1, 2]


def test_toutes_les_n_sans_lot_complet_ni_fin_de_bareme_n_a_rien() -> None:
    assert _numeros(_serie([1], 6), GrainValidation.toutes_les_n_volees(2), 6) == []


def test_toutes_les_n_propose_le_reliquat_en_fin_de_bareme() -> None:
    grain = GrainValidation.toutes_les_n_volees(4)
    serie = _serie([1, 2, 3, 4], 6).valider("RIOU", grain=grain, nb_volees_bareme=6)
    serie = serie.saisir_volee(
        5, _TRIO, zones_admises=tuple(ZoneScore), nb_fleches_par_volee=3, nb_volees_bareme=6
    )
    assert _numeros(serie, grain, 6) == []
    serie = serie.saisir_volee(
        6, _TRIO, zones_admises=tuple(ZoneScore), nb_fleches_par_volee=3, nb_volees_bareme=6
    )
    assert _numeros(serie, grain, 6) == [5, 6]


def test_une_correction_ouverte_sort_la_feuille_de_la_file() -> None:
    grain = GrainValidation.fin_de_serie()
    serie = _serie([1, 2, 3], 3).valider("RIOU", grain=grain, nb_volees_bareme=3)
    serie = serie.annuler_validation(2, par="RIOU")
    assert _numeros(serie, grain, 3) == []


_ETATS = [
    ([], 3, GrainValidation.fin_de_serie()),
    ([1, 2], 3, GrainValidation.fin_de_serie()),
    ([1, 2, 3], 3, GrainValidation.fin_de_serie()),
    ([1, 3], 3, GrainValidation.fin_de_serie()),
    ([1], 6, GrainValidation.toutes_les_n_volees(2)),
    ([2, 5], 6, GrainValidation.toutes_les_n_volees(2)),
    ([1, 2, 3, 4, 5], 6, GrainValidation.toutes_les_n_volees(2)),
    ([1, 2, 3, 4, 5, 6], 6, GrainValidation.toutes_les_n_volees(4)),
]


@pytest.mark.parametrize(("numeros", "bareme", "grain"), _ETATS)
def test_la_file_et_la_validation_lisent_la_meme_regle(
    numeros: list[int], bareme: int, grain: GrainValidation
) -> None:
    """Le lot proposé est **exactement** ce que `valider` verrouille ; vide ⇔ `valider` refuse."""
    serie = _serie(numeros, bareme)
    lot = _numeros(serie, grain, bareme)
    try:
        validee = serie.valider("RIOU", grain=grain, nb_volees_bareme=bareme)
    except DomainError:
        assert lot == []
        return
    verrouillees = [v.numero for v in validee.volees if v.verrouillee]
    assert lot == verrouillees
