"""Tests d'intégration du repository SQL des gabarits de salle (E01US007, E01US008).

Exerce l'adapter sur une **vraie base** créée par les migrations (`alembic upgrade head`) :
persistance (avec sérialisation JSON de la config), relecture, absence (None), listing, mise à
jour et suppression. Couvre aussi l'application à un tournoi (E01US008) : `lister` ne renvoie que
les **modèles** et `par_tournoi` récupère l'**instance** rattachée.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from domain.gabarit_salle import GabaritSalle
from domain.tournoi import Tournoi, TournoiId, TypeTournoi
from infrastructure.db import (
    Database,
    GabaritSalleORM,
    GabaritSalleRepositorySQL,
    TournoiRepositorySQL,
)
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
    """Persiste un tournoi (nécessaire à la FK d'une instance de gabarit) et renvoie son id."""
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


def test_lister_exclut_les_instances_de_tournoi(tmp_path: Path) -> None:
    """`lister` ne renvoie que les modèles ; une instance rattachée à un tournoi est exclue."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        repository = GabaritSalleRepositorySQL(db.session_factory)
        modele = repository.ajouter(GabaritSalle.creer("Modèle", 2, 4))
        repository.ajouter(modele.pour_tournoi(tournoi_id))
        assert [g.nom for g in repository.lister()] == ["Modèle"]
    finally:
        db.engine.dispose()


def test_par_tournoi_renvoie_l_instance_rattachee(tmp_path: Path) -> None:
    """`par_tournoi` relit l'instance appliquée (avec son `tournoi_id`), ou None si absente."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        repository = GabaritSalleRepositorySQL(db.session_factory)
        assert repository.par_tournoi(tournoi_id) is None
        modele = repository.ajouter(GabaritSalle.creer("Salle municipale", 3, 4))
        instance = repository.ajouter(modele.pour_tournoi(tournoi_id))
        relue = repository.par_tournoi(tournoi_id)
        assert relue == instance
        assert relue is not None and relue.tournoi_id == tournoi_id
        assert relue.capacites == (4, 4, 4)
    finally:
        db.engine.dispose()


def test_ajuster_une_instance_persiste_le_plafond_par_cible(tmp_path: Path) -> None:
    """L'ajustement cible par cible d'une instance est bien persisté (config JSON)."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        repository = GabaritSalleRepositorySQL(db.session_factory)
        modele = repository.ajouter(GabaritSalle.creer("Salle", 4, 4))
        instance = repository.ajouter(modele.pour_tournoi(tournoi_id))
        assert instance.id is not None
        repository.enregistrer(instance.ajuster("Salle adaptée", (4, 2, 2, 1)))
        relue = repository.par_tournoi(tournoi_id)
        assert relue is not None
        assert relue.nom == "Salle adaptée"
        assert relue.capacites == (4, 2, 2, 1)
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
