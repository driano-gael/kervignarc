"""Gestionnaire de fermeture de console (E11US006, CA 7) — la décision, sans l'API Windows.

Installation réelle (`SetConsoleCtrlHandler`) vérifiée à la main : `docs/fonctionnel/E11US006.md`.
"""

from __future__ import annotations

import threading
from typing import Any

import pytest
from fastapi import FastAPI

import run
from release.arret_console import ATTENTE_CONNEXIONS_S, DELAI_ARRET_S, traiter_evenement

_CTRL_C, _CTRL_BREAK, _CLOSE, _LOGOFF, _SHUTDOWN = 0, 1, 2, 5, 6


@pytest.mark.parametrize("evenement", [_CLOSE, _LOGOFF, _SHUTDOWN])
def test_une_fermeture_demande_l_arret_et_attend_qu_il_soit_fini(evenement: int) -> None:
    arrete = threading.Event()
    demandes: list[str] = []

    def demander() -> None:
        demandes.append("arret")
        arrete.set()  # l'arrêt se termine aussitôt

    assert traiter_evenement(evenement, demander, arrete, delai=5)
    assert demandes == ["arret"]


def test_l_attente_est_bornee_si_l_arret_traine() -> None:
    arrete = threading.Event()  # jamais posé

    assert traiter_evenement(_CLOSE, lambda: None, arrete, delai=0.01)


@pytest.mark.parametrize("evenement", [_CTRL_C, _CTRL_BREAK])
def test_ctrl_c_et_ctrl_break_restent_aux_signaux(evenement: int) -> None:
    demandes: list[str] = []

    assert not traiter_evenement(evenement, lambda: demandes.append("x"), threading.Event(), 0)
    assert demandes == []


def test_le_budget_d_arret_tient_sous_le_delai_de_windows() -> None:
    # Windows tue le processus ~5 s après la croix ; l'attente des connexions doit laisser au
    # moins une seconde au drain de la file avant ce délai.
    assert ATTENTE_CONNEXIONS_S + 1 <= DELAI_ARRET_S < 5


class _ServeurFactice:
    def __init__(self, config: Any, *, started: bool, interruption: bool = False) -> None:
        self.started = started
        self.should_exit = False
        self._interruption = interruption

    def run(self) -> None:
        if self._interruption:
            raise KeyboardInterrupt


def _servir_avec(monkeypatch: pytest.MonkeyPatch, *, started: bool, interruption: bool) -> None:
    # Patché à la source : `run` résout `uvicorn.Server` et `arret_console.installer` à l'appel.
    monkeypatch.setattr("release.arret_console.installer", lambda *_: None)
    monkeypatch.setattr(
        "uvicorn.Server",
        lambda config: _ServeurFactice(config, started=started, interruption=interruption),
    )
    run._servir(FastAPI())


def test_un_demarrage_rate_sort_en_erreur(monkeypatch: pytest.MonkeyPatch) -> None:
    # La garde défensive de `_servir` (uvicorn 0.51 sort déjà en 3 de lui-même).
    with pytest.raises(SystemExit) as sortie:
        _servir_avec(monkeypatch, started=False, interruption=False)

    assert sortie.value.code == 3


def test_ctrl_c_apres_demarrage_sort_proprement(monkeypatch: pytest.MonkeyPatch) -> None:
    _servir_avec(monkeypatch, started=True, interruption=True)
