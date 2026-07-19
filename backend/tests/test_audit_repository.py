"""Tests d'intégration du repository SQL du journal d'audit (E10US005, socle).

Exerce l'adapter sur une **vraie base** migrée (`alembic upgrade head`) : persistance et relecture
de tous les champs (dont l'`horodatage`, qui doit revenir *aware* UTC après un aller-retour SQLite),
`avant`/`apres` nullables, restriction au tournoi, et **ordre chronologique** (id croissant). Une
entrée référence un tournoi (FK) : chaque test en crée un d'abord.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config

from domain.entree_audit import ActionAuditee, EntreeAudit
from domain.tournoi import Tournoi
from infrastructure.db import AuditRepositorySQL, Database, TournoiRepositorySQL

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)
_QUAND = datetime.datetime(2026, 3, 14, 10, 42, tzinfo=datetime.UTC)


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


def _base_avec_tournoi(tmp_path: Path) -> tuple[Database, int]:
    """Migre une base jetable et y crée un tournoi ; renvoie la base et l'id du tournoi."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    tournoi = TournoiRepositorySQL(db.session_factory).ajouter(Tournoi.creer("Salle 18m", _DATE))
    assert tournoi.id is not None
    return db, tournoi.id


def _entree(tournoi_id: int, objet: str) -> EntreeAudit:
    return EntreeAudit.creer(
        tournoi_id=tournoi_id,
        action=ActionAuditee.VALIDATION,
        auteur="DURAND Jean",
        horodatage=_QUAND,
        objet=objet,
    )


def test_consigner_puis_relire(tmp_path: Path) -> None:
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = AuditRepositorySQL(db.session_factory)
        consignee = repository.consigner(_entree(tournoi_id, "Série 3 — cible 4A"))

        assert consignee.id is not None
        assert repository.par_tournoi(tournoi_id) == [consignee]
    finally:
        db.engine.dispose()


def test_horodatage_revient_aware_utc(tmp_path: Path) -> None:
    """SQLite stocke un `DateTime` sans fuseau : l'adapter réattache UTC → round-trip fidèle."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = AuditRepositorySQL(db.session_factory)
        consignee = repository.consigner(_entree(tournoi_id, "Série 3"))

        (relue,) = repository.par_tournoi(tournoi_id)
        assert relue.horodatage == _QUAND
        assert relue.horodatage.tzinfo is not None
        assert consignee.horodatage == _QUAND
    finally:
        db.engine.dispose()


def test_correction_conserve_avant_apres(tmp_path: Path) -> None:
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = AuditRepositorySQL(db.session_factory)
        repository.consigner(
            EntreeAudit.creer(
                tournoi_id=tournoi_id,
                action=ActionAuditee.CORRECTION_SCORE,
                auteur="ROUX Sophie",
                horodatage=_QUAND,
                objet="Série 3, flèche 2",
                avant="8",
                apres="9",
            )
        )

        (relue,) = repository.par_tournoi(tournoi_id)
        assert relue.action is ActionAuditee.CORRECTION_SCORE
        assert (relue.avant, relue.apres) == ("8", "9")
    finally:
        db.engine.dispose()


def test_avant_apres_nullables(tmp_path: Path) -> None:
    """Une validation n'a ni avant ni après : les colonnes reviennent `None`."""
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = AuditRepositorySQL(db.session_factory)
        repository.consigner(_entree(tournoi_id, "Série 3"))

        (relue,) = repository.par_tournoi(tournoi_id)
        assert relue.avant is None
        assert relue.apres is None
    finally:
        db.engine.dispose()


def test_par_tournoi_ne_renvoie_que_le_tournoi(tmp_path: Path) -> None:
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        tournois = TournoiRepositorySQL(db.session_factory)
        autre = tournois.ajouter(Tournoi.creer("Autre", _DATE))
        assert autre.id is not None
        repository = AuditRepositorySQL(db.session_factory)
        repository.consigner(_entree(tournoi_id, "Série 1"))
        repository.consigner(_entree(autre.id, "Série 2"))

        objets = [e.objet for e in repository.par_tournoi(tournoi_id)]
        assert objets == ["Série 1"]
    finally:
        db.engine.dispose()


def test_par_tournoi_ordre_chronologique(tmp_path: Path) -> None:
    db, tournoi_id = _base_avec_tournoi(tmp_path)
    try:
        repository = AuditRepositorySQL(db.session_factory)
        repository.consigner(_entree(tournoi_id, "Série 1"))
        repository.consigner(_entree(tournoi_id, "Série 2"))
        repository.consigner(_entree(tournoi_id, "Série 3"))

        objets = [e.objet for e in repository.par_tournoi(tournoi_id)]
        assert objets == ["Série 1", "Série 2", "Série 3"]
    finally:
        db.engine.dispose()
