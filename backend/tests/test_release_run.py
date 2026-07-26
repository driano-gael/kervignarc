"""Tests du câblage du point d'entrée release (E11US001).

Tests **après implémentation** (composition/câblage, pas d'oracle — règle 9). On couvre la
subtilité de `_configurer_environnement` : il **pose des défauts** (base à côté de l'exe, front
embarqué) mais via `setdefault`, donc **sans écraser** une surcharge posée par l'exploitant
(chemin réseau, base de test). `main()` n'est pas testé : il démarre un serveur bloquant.
"""

from __future__ import annotations

import os

import pytest

import run


def test_pose_les_defauts_quand_rien_n_est_defini(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sans variables d'environnement, base et front reçoivent les valeurs par défaut."""
    monkeypatch.delenv("KERVIGNARC_DATABASE_URL", raising=False)
    monkeypatch.delenv("KERVIGNARC_FRONTEND_DIST", raising=False)

    run._configurer_environnement()

    assert os.environ["KERVIGNARC_DATABASE_URL"].startswith("sqlite:///")
    assert os.environ["KERVIGNARC_FRONTEND_DIST"]


def test_respecte_une_surcharge_de_l_exploitant(monkeypatch: pytest.MonkeyPatch) -> None:
    """Une valeur déjà posée (base de test, chemin réseau) n'est PAS écrasée (`setdefault`)."""
    monkeypatch.setenv("KERVIGNARC_DATABASE_URL", "sqlite:///deja-choisi.db")
    monkeypatch.setenv("KERVIGNARC_FRONTEND_DIST", "/chemin/perso/dist")

    run._configurer_environnement()

    assert os.environ["KERVIGNARC_DATABASE_URL"] == "sqlite:///deja-choisi.db"
    assert os.environ["KERVIGNARC_FRONTEND_DIST"] == "/chemin/perso/dist"
