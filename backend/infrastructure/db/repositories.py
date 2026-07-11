"""Adapters repository SQLAlchemy (E00US009) — implémentent les ports du domaine.

`TournoiRepositorySQL` réalise `domain.ports.TournoiRepository` (conformité structurelle,
vérifiée au câblage). Chaque opération ouvre une **session courte** (une par opération,
ADR-0005) et traduit les lignes ORM en agrégats de domaine. Les pannes SQLAlchemy sont
**enveloppées** en `InfrastructureError` — le domaine ne voit jamais d'exception brute.
"""

from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from domain.tournoi import Tournoi, TournoiId
from infrastructure.db.models import TournoiORM
from infrastructure.erreurs import InfrastructureError


class TournoiRepositorySQL:
    """Adapter SQLite du port `TournoiRepository`."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        """Persiste le tournoi et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = TournoiORM(nom=tournoi.nom)
                session.add(ligne)
                session.commit()
                return Tournoi(nom=ligne.nom, id=ligne.id)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du tournoi.") from exc

    def par_id(self, tournoi_id: TournoiId) -> Tournoi | None:
        """Relit le tournoi d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(TournoiORM, tournoi_id)
                return None if ligne is None else Tournoi(nom=ligne.nom, id=ligne.id)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du tournoi.") from exc
