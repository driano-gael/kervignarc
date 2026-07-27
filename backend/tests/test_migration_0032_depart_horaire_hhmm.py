"""Migration 0032 — reprise des horaires libres en `HH:MM` + colonne NOT NULL (E02US010).

La suite d'API migre toujours une base **vide** jusqu'à `head` : ni le **backfill best-effort**
(`_vers_hhmm`) ni le passage **NOT NULL** par `batch_alter_table` (qui recrée la table) ne sont
exercés par un autre test. Ici, on insère des `depart` à l'ancien schéma (horaire libre nullable)
sur la révision `0031`, on applique `0032`, et on vérifie : la conversion de chaque cas, le NOT
NULL, et surtout la **survie de la contrainte `UNIQUE(tournoi_id, numero)`** à la recréation de
table (un `batch_alter_table` mal fait la perdrait en silence).

Les clés étrangères sont désactivées côté Alembic (`env.py`) : on insère un `tournoi_id` fictif sans
matérialiser le tournoi parent — même geste que les tests de migration 0018/0020.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import IntegrityError

_BACKEND_ROOT = Path(__file__).resolve().parents[1]

# horaire libre (ancien schéma) → HH:MM attendu après upgrade. Couvre : libellés convertibles,
# inconvertibles (→ sentinelle 00:00), et un HH:MM déjà valide (inchangé). Le cas NULL est traité à
# part (INSERT dédié).
_CAS = [
    ("9h00", "09:00"),  # libellé libre courant → converti
    ("8h", "08:00"),  # heure seule → minute 00
    ("9:00", "09:00"),  # séparateur « : » à un chiffre d'heure → complété
    ("09h30", "09:30"),  # deux chiffres + « h »
    ("14h00", "14:00"),
    ("  9h00  ", "09:00"),  # espaces de bord tolérés
    ("matin", "00:00"),  # inconvertible → sentinelle
    ("", "00:00"),  # vide → sentinelle
    ("25:00", "00:00"),  # heure hors plage → sentinelle (ni HH:MM valide, ni h/minute valide)
    ("23:99", "00:00"),  # minute hors plage → sentinelle
    ("09:30", "09:30"),  # déjà HH:MM valide → inchangé
]


def _config(url: str) -> Config:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _inserer_depart(conn: sa.Connection, identifiant: int, horaire: str | None) -> None:
    """Insère un départ à l'ancien schéma 0031 (horaire nullable, libre)."""
    conn.execute(
        sa.text(
            "INSERT INTO depart (id, tournoi_id, numero, horaire, tarif_centimes, quota) "
            "VALUES (:id, 1, :numero, :horaire, 800, NULL)"
        ),
        {"id": identifiant, "numero": identifiant, "horaire": horaire},
    )


def test_upgrade_reprend_les_horaires_en_hhmm(tmp_path: Path) -> None:
    """Après `0032`, chaque horaire libre est converti en `HH:MM` valide (best-effort ; défaut
    `00:00`), y compris un horaire `NULL`."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, "0031_forfait")

    engine = sa.create_engine(url)
    try:
        with engine.begin() as conn:
            for identifiant, (horaire, _attendu) in enumerate(_CAS, start=1):
                _inserer_depart(conn, identifiant, horaire)
            # Cas NULL séparé (numéro distinct pour respecter l'unicité).
            _inserer_depart(conn, len(_CAS) + 1, None)

        command.upgrade(cfg, "0032_depart_horaire_hhmm")

        with engine.connect() as conn:
            lignes = conn.execute(sa.text("SELECT id, horaire FROM depart")).all()
        horaire_par_id = {int(ligne[0]): ligne[1] for ligne in lignes}
        for identifiant, (_horaire, attendu) in enumerate(_CAS, start=1):
            assert horaire_par_id[identifiant] == attendu
        assert horaire_par_id[len(_CAS) + 1] == "00:00"  # NULL → sentinelle
        # Toutes les valeurs reprises sont des HH:MM valides (aucune ne violerait la validation
        # domaine à la relecture).
        assert all(value is not None for value in horaire_par_id.values())
    finally:
        engine.dispose()


def test_upgrade_rend_la_colonne_not_null(tmp_path: Path) -> None:
    """Après `0032`, `depart.horaire` est NOT NULL : insérer un horaire NULL est rejeté."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, "0032_depart_horaire_hhmm")

    engine = sa.create_engine(url)
    try:
        with engine.connect() as conn:
            colonnes = {
                ligne[1]: ligne[3]  # nom -> notnull (0/1)
                for ligne in conn.execute(sa.text("PRAGMA table_info(depart)"))
            }
        assert colonnes["horaire"] == 1

        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO depart (tournoi_id, numero, horaire, tarif_centimes) "
                    "VALUES (1, 1, NULL, 800)"
                )
            )
    finally:
        engine.dispose()


def test_upgrade_preserve_la_contrainte_unique(tmp_path: Path) -> None:
    """La contrainte `UNIQUE(tournoi_id, numero)` **survit** au `batch_alter_table` : deux créneaux
    de même (tournoi, numéro) restent refusés après la recréation de table."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, "0032_depart_horaire_hhmm")

    engine = sa.create_engine(url)
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO depart (tournoi_id, numero, horaire, tarif_centimes) "
                    "VALUES (1, 1, '09:00', 800)"
                )
            )
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO depart (tournoi_id, numero, horaire, tarif_centimes) "
                    "VALUES (1, 1, '10:00', 900)"
                )
            )
    finally:
        engine.dispose()


def test_downgrade_redonne_l_horaire_nullable(tmp_path: Path) -> None:
    """Le downgrade rend `horaire` de nouveau nullable (les valeurs reprises restent en place)."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = _config(url)
    command.upgrade(cfg, "0032_depart_horaire_hhmm")
    command.downgrade(cfg, "0031_forfait")

    engine = sa.create_engine(url)
    try:
        with engine.connect() as conn:
            colonnes = {
                ligne[1]: ligne[3] for ligne in conn.execute(sa.text("PRAGMA table_info(depart)"))
            }
        assert colonnes["horaire"] == 0  # nullable de nouveau
    finally:
        engine.dispose()
