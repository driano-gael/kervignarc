"""Tests de résolution des chemins gel-conscients du binaire de release (E11US001).

Tests **après implémentation** : packaging/câblage, sans oracle métier (règle 9). On simule
les deux mondes PyInstaller en posant sur `sys` les attributs qu'un binaire gelé exposerait
(`sys.frozen`, `sys._MEIPASS`) — ce que fait PyInstaller au lancement.

Invariant central vérifié : les **ressources** (front, migrations) se lisent dans `_MEIPASS`
(volatile, effacé à la sortie), mais la **base** vit **à côté de l'exécutable** (persistante).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from release import chemins

_BACKEND_ROOT = Path(chemins.__file__).resolve().parents[1]


def test_hors_gel_pointe_vers_le_depot(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sans `sys.frozen`, tout se résout dans l'arborescence du dépôt (dev, tests)."""
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    assert chemins.est_gele() is False
    assert chemins.dossier_ressources() == _BACKEND_ROOT
    assert chemins.dossier_donnees() == _BACKEND_ROOT
    assert chemins.dossier_migrations() == _BACKEND_ROOT / "migrations"
    assert chemins.dossier_front() == _BACKEND_ROOT.parent / "frontend" / "dist"


def test_gele_lit_les_ressources_dans_meipass(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Gelé, front et migrations se lisent sous `_MEIPASS` (dossier embarqué en lecture seule)."""
    meipass = tmp_path / "_MEI"
    exe = tmp_path / "install" / "kervignarc.exe"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)
    monkeypatch.setattr(sys, "executable", str(exe), raising=False)

    assert chemins.est_gele() is True
    assert chemins.dossier_ressources() == meipass
    assert chemins.dossier_migrations() == meipass / "migrations"
    assert chemins.dossier_front() == meipass / "frontend" / "dist"


def test_gele_ecrit_la_base_a_cote_de_l_exe(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Gelé, la base persistante vit à côté de l'exe, **pas** dans le `_MEIPASS` volatile."""
    meipass = tmp_path / "_MEI"
    exe = tmp_path / "install" / "kervignarc.exe"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)
    monkeypatch.setattr(sys, "executable", str(exe), raising=False)

    assert chemins.dossier_donnees() == exe.parent
    url = chemins.url_base_donnees()
    assert url.startswith("sqlite:///")
    assert (exe.parent / "kervignarc.db").as_posix() in url
    assert str(meipass) not in url  # la base ne doit jamais atterrir dans le temporaire
