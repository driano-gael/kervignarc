"""Tests de l'adapter de sauvegarde périodique (E11US003, CA « sauvegarde périodique »).

Infra (pas d'oracle de CA en jeu, règle 9) : on vérifie qu'une copie **horodatée et cohérente** est
déposée, que le contenu (y compris des pages encore en WAL) y figure, et que la **rétention** ne
garde que les N copies les plus récentes. L'horloge est **figée** et incrémentale pour obtenir des
noms distincts et déterministes (règle 9 — pas d'horloge non maîtrisée).
"""

from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path

import pytest

from infrastructure.backup import config
from infrastructure.backup.sauvegarde import SauvegardeSQLite


class _HorlogeIncrementale:
    """Horloge de test : renvoie un instant qui avance d'une minute à chaque appel."""

    def __init__(self, base: datetime.datetime) -> None:
        self._courant = base

    def maintenant(self) -> datetime.datetime:
        instant = self._courant
        self._courant = instant + datetime.timedelta(minutes=1)
        return instant


def _base_wal_avec_donnee(chemin: Path) -> None:
    """Crée une base en mode WAL avec une ligne, **sans checkpoint** (données dans le -wal)."""
    connexion = sqlite3.connect(str(chemin))
    try:
        connexion.execute("PRAGMA journal_mode=WAL")
        connexion.execute("CREATE TABLE t (x TEXT)")
        connexion.execute("INSERT INTO t (x) VALUES ('bonjour')")
        connexion.commit()
    finally:
        connexion.close()


def _horloge() -> _HorlogeIncrementale:
    return _HorlogeIncrementale(datetime.datetime(2026, 7, 26, 10, 0, tzinfo=datetime.UTC))


def test_sauvegarder_depose_une_copie_horodatee_coherente(tmp_path: Path) -> None:
    """La sauvegarde crée `kervignarc-<horodatage>.db` contenant la donnée (WAL compris)."""
    source = tmp_path / "kervignarc.db"
    _base_wal_avec_donnee(source)
    dossier = tmp_path / "backups"
    sauvegarde = SauvegardeSQLite(source, dossier, retention=5, horloge=_horloge())

    cible = sauvegarde.sauvegarder()

    assert cible.parent == dossier
    assert cible.name.startswith("kervignarc-")
    assert cible.suffix == ".db"
    copie = sqlite3.connect(str(cible))
    try:
        (valeur,) = copie.execute("SELECT x FROM t").fetchone()
    finally:
        copie.close()
    assert valeur == "bonjour"


def test_retention_ne_garde_que_les_plus_recentes(tmp_path: Path) -> None:
    """Au-delà de la rétention, les copies **les plus anciennes** sont purgées."""
    source = tmp_path / "kervignarc.db"
    _base_wal_avec_donnee(source)
    dossier = tmp_path / "backups"
    sauvegarde = SauvegardeSQLite(source, dossier, retention=3, horloge=_horloge())

    creees = [sauvegarde.sauvegarder() for _ in range(5)]

    restantes = sorted(p.name for p in dossier.glob("kervignarc-*.db"))
    assert len(restantes) == 3
    # Les trois dernières créées (horodatages croissants) sont celles conservées.
    assert restantes == sorted(p.name for p in creees[-3:])


def test_config_defauts_et_surcharges(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Les lecteurs de config appliquent les défauts, les surcharges env, et « 0 désactive »."""
    for var in ("KERVIGNARC_BACKUP_INTERVAL_SECONDS", "KERVIGNARC_BACKUP_RETENTION"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("KERVIGNARC_BACKUP_DIR", raising=False)
    # Défauts.
    assert config.intervalle_secondes() == config.INTERVALLE_DEFAUT_SECONDES
    assert config.retention() == config.RETENTION_DEFAUT
    # Surcharges valides.
    monkeypatch.setenv("KERVIGNARC_BACKUP_INTERVAL_SECONDS", "60")
    monkeypatch.setenv("KERVIGNARC_BACKUP_RETENTION", "5")
    monkeypatch.setenv("KERVIGNARC_BACKUP_DIR", str(tmp_path / "bak"))
    assert config.intervalle_secondes() == 60
    assert config.retention() == 5
    assert config.dossier_sauvegardes() == tmp_path / "bak"
    # « 0 désactive » (intervalle) et rétention plancher à 1.
    monkeypatch.setenv("KERVIGNARC_BACKUP_INTERVAL_SECONDS", "0")
    monkeypatch.setenv("KERVIGNARC_BACKUP_RETENTION", "0")
    assert config.intervalle_secondes() == 0
    assert config.retention() == 1
    # Valeurs invalides : repli sur le défaut.
    monkeypatch.setenv("KERVIGNARC_BACKUP_INTERVAL_SECONDS", "abc")
    monkeypatch.setenv("KERVIGNARC_BACKUP_RETENTION", "xyz")
    assert config.intervalle_secondes() == config.INTERVALLE_DEFAUT_SECONDES
    assert config.retention() == config.RETENTION_DEFAUT
