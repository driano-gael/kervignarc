"""Tests d'intégration du repository SQL des gabarits de salle (E01US007).

Exerce l'adapter sur une **vraie base** créée par les migrations (`alembic upgrade head`) :
persistance (avec sérialisation JSON de la config), relecture, absence (None), listing, mise à
jour et suppression. Les gabarits sont autonomes (aucun tournoi requis).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from domain.gabarit_salle import GabaritSalle
from infrastructure.db import Database, GabaritSalleORM, GabaritSalleRepositorySQL
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


def test_ajouter_puis_relire(tmp_path: Path) -> None:
    """`ajouter` attribue un id ; `par_id` relit l'agrégat (config JSON comprise)."""
    db = _base(tmp_path)
    try:
        repository = GabaritSalleRepositorySQL(db.session_factory)
        cree = repository.ajouter(GabaritSalle.creer("Salle A", 3, 2))
        assert cree.id is not None
        assert cree.nb_cibles == 3
        assert cree.capacites == (2, 2, 2)
        assert repository.par_id(cree.id) == cree
    finally:
        db.engine.dispose()


def test_par_id_inexistant_renvoie_none(tmp_path: Path) -> None:
    """`par_id` renvoie None pour un identifiant absent (pas d'exception)."""
    db = _base(tmp_path)
    try:
        assert GabaritSalleRepositorySQL(db.session_factory).par_id(999) is None
    finally:
        db.engine.dispose()


def test_lister_dans_l_ordre_de_creation(tmp_path: Path) -> None:
    """`lister` renvoie les gabarits dans l'ordre de création."""
    db = _base(tmp_path)
    try:
        repository = GabaritSalleRepositorySQL(db.session_factory)
        assert repository.lister() == []
        repository.ajouter(GabaritSalle.creer("A", 1))
        repository.ajouter(GabaritSalle.creer("B", 2))
        assert [g.nom for g in repository.lister()] == ["A", "B"]
    finally:
        db.engine.dispose()


def test_enregistrer_met_a_jour(tmp_path: Path) -> None:
    """`enregistrer` persiste l'édition (nom, nombre de cibles, plafond)."""
    db = _base(tmp_path)
    try:
        repository = GabaritSalleRepositorySQL(db.session_factory)
        cree = repository.ajouter(GabaritSalle.creer("Ancien", 2, 4))
        assert cree.id is not None
        enregistre = repository.enregistrer(cree.modifier("Nouveau", 5, 1))
        assert enregistre.nom == "Nouveau"
        assert enregistre.nb_cibles == 5
        assert enregistre.capacites == (1,) * 5
        assert repository.par_id(cree.id) == enregistre
    finally:
        db.engine.dispose()


def test_supprimer_retire_la_ligne(tmp_path: Path) -> None:
    """`supprimer` retire la ligne ; `par_id` renvoie ensuite None."""
    db = _base(tmp_path)
    try:
        repository = GabaritSalleRepositorySQL(db.session_factory)
        cree = repository.ajouter(GabaritSalle.creer("Salle", 1))
        assert cree.id is not None
        repository.supprimer(cree.id)
        assert repository.par_id(cree.id) is None
        assert repository.lister() == []
    finally:
        db.engine.dispose()


def test_config_corrompue_leve_infrastructure_error(tmp_path: Path) -> None:
    """Une `config` illisible en base est enveloppée en `InfrastructureError` (pas de 500 brut)."""
    db = _base(tmp_path)
    try:
        with db.session_factory() as session:
            session.add(GabaritSalleORM(nom="Cassé", nb_cibles=1, config="pas du json"))
            session.commit()
        with pytest.raises(InfrastructureError):
            GabaritSalleRepositorySQL(db.session_factory).lister()
    finally:
        db.engine.dispose()
