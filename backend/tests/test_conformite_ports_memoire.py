"""Conformité de port : adapters **in-memory** vs adapters **SQL** (E15US002, ADR-0054 §5).

Le risque d'un second jeu d'adapters (in-memory, pour la simulation), c'est qu'il **diverge** de la
sémantique SQL — un `par_tournoi` qui ne filtre pas, un `par_id` introuvable qui ne rend pas `None`,
un ordre non garanti. Ces tests **partagés** exécutent le **même** contrat sur les deux
implémentations : ce qui passe sur SQL doit passer à l'identique en mémoire.

Sous-ensemble représentatif (extensible port par port) : `TournoiRepository` (sans FK :
`par_id`/`lister`), `PhaseRepository` (filtrage `par_tournoi` **et** ordre par `ordre`, plus
`par_tournoi_et_type`), `ArcherRepository` (filtrage `par_tournoi` **porteur de FK** — celui dont
l'hydratation dépend pour l'intégrité référentielle) et `GabaritSalleRepository` (le partage
**modèles (`tournoi_id is None`) vs instance** que la simulation exploite). Le contrat vit dans les
fonctions `_contrat_*`, jouées une fois par adapter.
"""

from __future__ import annotations

import datetime
from collections.abc import Iterator
from pathlib import Path

import pytest

from domain.archer import Archer
from domain.categorie import Categorie
from domain.gabarit_salle import GabaritSalle
from domain.phase import Phase, TypePhase
from domain.ports import (
    ArcherRepository,
    CategorieRepository,
    GabaritSalleRepository,
    PhaseRepository,
    TournoiRepository,
)
from domain.tournoi import Tournoi
from infrastructure.db import (
    ArcherRepositorySQL,
    CategorieRepositorySQL,
    Database,
    GabaritSalleRepositorySQL,
    PhaseRepositorySQL,
    TournoiRepositorySQL,
)
from infrastructure.memory.repositories import (
    InMemoryArcherRepository,
    InMemoryCategorieRepository,
    InMemoryGabaritSalleRepository,
    InMemoryPhaseRepository,
    InMemoryTournoiRepository,
)
from tests.base_migree import preparer_base

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)


@pytest.fixture
def base_sql(tmp_path: Path) -> Iterator[Database]:
    """Une base migrée jetable ; l'engine est libéré en fin de test."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    preparer_base(url)
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

    placement = phases.par_depart_et_type(tournoi.id, TypePhase.PLACEMENT)
    assert placement is not None and placement.ordre == 1, "par_tournoi_et_type résout la phase."
    assert (
        phases.par_depart_et_type(tournoi.id, TypePhase.QUALIFICATION) is None
    ), "par_tournoi_et_type → None si le type est absent."


def _contrat_archer(
    tournois: TournoiRepository, categories: CategorieRepository, archers: ArcherRepository
) -> None:
    assert archers.par_id(999) is None, "par_id sur un identifiant absent → None."
    tournoi = tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
    autre = tournois.ajouter(Tournoi.creer("Autre salle", _DATE))
    assert tournoi.id is not None and autre.id is not None
    cat = categories.ajouter(Categorie.creer(tournoi.id, "Sénior"))
    cat_autre = categories.ajouter(Categorie.creer(autre.id, "Sénior"))
    assert cat.id is not None and cat_autre.id is not None

    ici = archers.ajouter(
        Archer(nom="Martin", prenom="Alice", tournoi_id=tournoi.id, categorie_id=cat.id)
    )
    archers.ajouter(Archer(nom="Durand", prenom="Bob", tournoi_id=tournoi.id, categorie_id=cat.id))
    archers.ajouter(
        Archer(nom="Petit", prenom="Chloé", tournoi_id=autre.id, categorie_id=cat_autre.id)
    )

    du_tournoi = archers.par_tournoi(tournoi.id)
    assert {a.nom for a in du_tournoi} == {
        "Martin",
        "Durand",
    }, "par_tournoi filtre par tournoi (aucune fuite inter-tournois)."
    assert ici.id is not None
    relu = archers.par_id(ici.id)
    assert relu is not None and relu.nom == "Martin", "par_id relit l'entité ajoutée."


def _contrat_gabarit(tournois: TournoiRepository, gabarits: GabaritSalleRepository) -> None:
    assert gabarits.par_id(999) is None, "par_id sur un identifiant absent → None."
    tournoi = tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
    assert tournoi.id is not None
    gabarits.ajouter(GabaritSalle(nom="Modèle", capacites=(4,), tournoi_id=None))  # bibliothèque
    gabarits.ajouter(GabaritSalle(nom="Instance", capacites=(4,), tournoi_id=tournoi.id))

    assert [g.nom for g in gabarits.lister()] == [
        "Modèle"
    ], "lister ne renvoie que les modèles (tournoi_id is None)."
    instance = gabarits.par_tournoi(tournoi.id)
    assert instance is not None and instance.nom == "Instance", "par_tournoi rend l'instance."
    assert gabarits.par_tournoi(999) is None, "par_tournoi → None si le tournoi n'a pas d'instance."


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


def test_archer_memoire() -> None:
    _contrat_archer(
        InMemoryTournoiRepository(),
        InMemoryCategorieRepository(),
        InMemoryArcherRepository(),
    )


def test_archer_sql(base_sql: Database) -> None:
    fabrique = base_sql.session_factory
    _contrat_archer(
        TournoiRepositorySQL(fabrique),
        CategorieRepositorySQL(fabrique),
        ArcherRepositorySQL(fabrique),
    )


def test_gabarit_memoire() -> None:
    _contrat_gabarit(InMemoryTournoiRepository(), InMemoryGabaritSalleRepository())


def test_gabarit_sql(base_sql: Database) -> None:
    fabrique = base_sql.session_factory
    _contrat_gabarit(TournoiRepositorySQL(fabrique), GabaritSalleRepositorySQL(fabrique))
