"""Tests d'intégration du repository SQL des phases (E01US009 / ADR-0011).

Exerce l'adapter sur une **vraie base** créée par les migrations (`alembic upgrade head`) :
persistance du barème (sérialisation JSON `config.scoring`), relecture par tournoi + type, mise à
jour, et enveloppe d'une `config` illisible. Une phase requiert un tournoi (FK `tournoi_id`).
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from domain.bareme import BaremeQualification
from domain.phase import Phase, TypePhase
from domain.tournoi import Tournoi, TournoiId, TypeTournoi
from infrastructure.db import Database, PhaseORM, PhaseRepositorySQL, TournoiRepositorySQL
from infrastructure.erreurs import InfrastructureError

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


def _base(tmp_path: Path) -> Database:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    return Database(url)


def _tournoi(db: Database) -> TournoiId:
    """Persiste un tournoi (FK requise par une phase) et renvoie son identifiant."""
    tournoi = TournoiRepositorySQL(db.session_factory).ajouter(
        Tournoi(
            nom="Kervignarc",
            date=datetime.date(2026, 3, 14),
            lieu=None,
            type_tournoi=TypeTournoi.NON_OFFICIEL,
        )
    )
    assert tournoi.id is not None
    return tournoi.id


def test_ajouter_puis_relire_par_tournoi_et_type(tmp_path: Path) -> None:
    """`ajouter` attribue un id ; `par_tournoi_et_type` relit le barème (config JSON comprise)."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        repository = PhaseRepositorySQL(db.session_factory)
        assert repository.par_tournoi_et_type(tournoi_id, TypePhase.QUALIFICATION) is None

        cree = repository.ajouter(
            Phase.qualification(tournoi_id, BaremeQualification.preset_ffta_18m())
        )
        assert cree.id is not None
        assert cree.bareme.nb_volees == 20
        assert cree.bareme.nb_fleches_par_volee == 3

        relue = repository.par_tournoi_et_type(tournoi_id, TypePhase.QUALIFICATION)
        assert relue == cree
    finally:
        db.engine.dispose()


def test_enregistrer_met_a_jour_le_bareme(tmp_path: Path) -> None:
    """`enregistrer` persiste l'édition du barème et conserve l'identifiant."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        repository = PhaseRepositorySQL(db.session_factory)
        cree = repository.ajouter(Phase.qualification(tournoi_id, BaremeQualification.creer(20, 3)))
        assert cree.id is not None

        enregistre = repository.enregistrer(cree.avec_bareme(BaremeQualification.creer(10, 6)))
        assert enregistre.id == cree.id
        assert enregistre.bareme.nb_volees == 10
        assert enregistre.bareme.nb_fleches_par_volee == 6
        assert repository.par_id(cree.id) == enregistre
    finally:
        db.engine.dispose()


def test_par_tournoi_et_type_isole_les_tournois(tmp_path: Path) -> None:
    """`par_tournoi_et_type` ne renvoie que la phase du tournoi demandé."""
    db = _base(tmp_path)
    try:
        premier = _tournoi(db)
        second = _tournoi(db)
        repository = PhaseRepositorySQL(db.session_factory)
        repository.ajouter(Phase.qualification(premier, BaremeQualification.creer(20, 3)))

        assert repository.par_tournoi_et_type(second, TypePhase.QUALIFICATION) is None
        du_premier = repository.par_tournoi_et_type(premier, TypePhase.QUALIFICATION)
        assert du_premier is not None and du_premier.tournoi_id == premier
    finally:
        db.engine.dispose()


def test_config_corrompue_leve_infrastructure_error(tmp_path: Path) -> None:
    """Une `config` illisible en base est enveloppée en `InfrastructureError` (pas de 500 brut)."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        with db.session_factory() as session:
            session.add(
                PhaseORM(
                    tournoi_id=tournoi_id,
                    ordre=1,
                    type="qualification",
                    config="pas du json",
                    statut="a_venir",
                )
            )
            session.commit()
        with pytest.raises(InfrastructureError):
            PhaseRepositorySQL(db.session_factory).par_tournoi_et_type(
                tournoi_id, TypePhase.QUALIFICATION
            )
    finally:
        db.engine.dispose()
