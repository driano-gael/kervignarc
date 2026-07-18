"""Adapters de persistance SQLite (guide §7, ADR-0005).

Accès **synchrones** (SQLAlchemy sync), base en **mode WAL**, migrations Alembic.
Le domaine ignore tout de SQLAlchemy : ces adapters vivent dans l'infrastructure,
derrière les ports repository (`domain.ports`), dont `TournoiRepositorySQL` est la
première implémentation (E00US009).
"""

from infrastructure.db.base import Base
from infrastructure.db.config import DEFAULT_DATABASE_URL, default_database_url
from infrastructure.db.engine import Database, create_database_engine
from infrastructure.db.models import (
    ArcherORM,
    BlasonORM,
    CategorieORM,
    ClubORM,
    DepartORM,
    GabaritSalleORM,
    InscriptionORM,
    PhaseORM,
    PlacementORM,
    PosteORM,
    ScoreORM,
    ScoreurORM,
    TournoiORM,
)
from infrastructure.db.repositories import (
    ArcherRepositorySQL,
    BlasonRepositorySQL,
    CategorieRepositorySQL,
    ClubRepositorySQL,
    DepartRepositorySQL,
    GabaritSalleRepositorySQL,
    InscriptionRepositorySQL,
    PhaseRepositorySQL,
    PlacementRepositorySQL,
    PosteRepositorySQL,
    ScoreRepositorySQL,
    ScoreurRepositorySQL,
    TournoiRepositorySQL,
)
from infrastructure.db.write_queue import (
    PostCommitListener,
    WriteCommand,
    WriteQueue,
    WriteQueueClosedError,
)

__all__ = [
    "DEFAULT_DATABASE_URL",
    "ArcherORM",
    "ArcherRepositorySQL",
    "Base",
    "BlasonORM",
    "BlasonRepositorySQL",
    "CategorieORM",
    "CategorieRepositorySQL",
    "ClubORM",
    "ClubRepositorySQL",
    "Database",
    "DepartORM",
    "DepartRepositorySQL",
    "GabaritSalleORM",
    "GabaritSalleRepositorySQL",
    "InscriptionORM",
    "InscriptionRepositorySQL",
    "PhaseORM",
    "PhaseRepositorySQL",
    "PlacementORM",
    "PlacementRepositorySQL",
    "PostCommitListener",
    "PosteORM",
    "PosteRepositorySQL",
    "ScoreORM",
    "ScoreRepositorySQL",
    "ScoreurORM",
    "ScoreurRepositorySQL",
    "TournoiORM",
    "TournoiRepositorySQL",
    "WriteCommand",
    "WriteQueue",
    "WriteQueueClosedError",
    "create_database_engine",
    "default_database_url",
]
