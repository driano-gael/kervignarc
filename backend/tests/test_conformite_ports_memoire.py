"""Conformité de port : adapters **in-memory** vs adapters **SQL** (E15US002, ADR-0054 §5).

Le risque d'un second jeu d'adapters (in-memory, pour la simulation), c'est qu'il **diverge** de la
sémantique SQL — un `par_tournoi` qui ne filtre pas, un `par_id` introuvable qui ne rend pas `None`,
un ordre non garanti. Ces tests **partagés** exécutent le **même** contrat sur les deux
implémentations : ce qui passe sur SQL doit passer à l'identique en mémoire.

Sous-ensemble représentatif (extensible port par port) : `TournoiRepository` (cas sans FK :
`par_id`/`lister`) et `PhaseRepository` (filtrage `par_tournoi` **et** ordre par `ordre`, plus
`par_tournoi_et_type`). Le contrat vit dans les fonctions `_contrat_*`, jouées une fois par adapter.
"""

from __future__ import annotations

import datetime
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from domain.phase import Phase, TypePhase
from domain.ports import PhaseRepository, TournoiRepository
from domain.tournoi import Tournoi
from infrastructure.db import Database, PhaseRepositorySQL, TournoiRepositorySQL
from infrastructure.memory.repositories import (
    InMemoryPhaseRepository,
    InMemoryTournoiRepository,
)

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)


@pytest.fixture
def base_sql(tmp_path: Path) -> Iterator[Database]:
    """Une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    database = Database(url)
    try:
        yield database
    finally:
        database.engine.dispose()


# --- Contrats partagés (indépendants de l'adapter) ---------------------------------------------


def _contrat_tournoi(repo: TournoiRepository) -> None:
    assert repo.par_id(999) is None, "par_id sur un identifiant absent → None."
    a = repo.ajouter(Tournoi.creer("Salle A", _DATE))
    b = repo.ajouter(Tournoi.creer("Salle B", _DATE))
    assert (
        a.id is not None and b.id is not None and a.id != b.id
    ), "Identifiants attribués, distincts."
    relu = repo.par_id(a.id)
    assert relu is not None and relu.nom == "Salle A", "par_id relit l'entité ajoutée."
    assert {t.nom for t in repo.lister()} == {"Salle A", "Salle B"}, "lister renvoie tout."


def _contrat_phase(tournois: TournoiRepository, phases: PhaseRepository) -> None:
    assert phases.par_id(999) is None, "par_id sur un identifiant absent → None."
    tournoi = tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
    autre = tournois.ajouter(Tournoi.creer("Autre salle", _DATE))
    assert tournoi.id is not None and autre.id is not None

    # Ajoutées dans le désordre (ordres 3, 1, 2) : `par_tournoi` doit les rendre **triées**.
    # (On évite le type `qualification`, qui exigerait un barème — hors sujet ici.)
    phases.ajouter(Phase.creer(tournoi.id, 3, TypePhase.ELIMINATION_DIRECTE))
    phases.ajouter(Phase.creer(tournoi.id, 1, TypePhase.PLACEMENT))
    phases.ajouter(Phase.creer(tournoi.id, 2, TypePhase.ELIMINATION_DIRECTE))
    phases.ajouter(Phase.creer(autre.id, 1, TypePhase.PLACEMENT))  # d'un autre tournoi

    du_tournoi = phases.par_tournoi(tournoi.id)
    assert [p.ordre for p in du_tournoi] == [1, 2, 3], "par_tournoi filtre puis trie par ordre."

    placement = phases.par_tournoi_et_type(tournoi.id, TypePhase.PLACEMENT)
    assert placement is not None and placement.ordre == 1, "par_tournoi_et_type résout la phase."
    assert (
        phases.par_tournoi_et_type(tournoi.id, TypePhase.QUALIFICATION) is None
    ), "par_tournoi_et_type → None si le type est absent."


# --- Un test par (contrat, adapter) ; les deux adapters passent le même contrat -------------------


def test_tournoi_memoire() -> None:
    _contrat_tournoi(InMemoryTournoiRepository())


def test_tournoi_sql(base_sql: Database) -> None:
    _contrat_tournoi(TournoiRepositorySQL(base_sql.session_factory))


def test_phase_memoire() -> None:
    _contrat_phase(InMemoryTournoiRepository(), InMemoryPhaseRepository())


def test_phase_sql(base_sql: Database) -> None:
    _contrat_phase(
        TournoiRepositorySQL(base_sql.session_factory),
        PhaseRepositorySQL(base_sql.session_factory),
    )
