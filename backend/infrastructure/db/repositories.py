"""Adapters repository SQLAlchemy (E00US009) — implémentent les ports du domaine.

`TournoiRepositorySQL` réalise `domain.ports.TournoiRepository` (conformité structurelle,
vérifiée au câblage). Chaque opération ouvre une **session courte** (une par opération,
ADR-0005) et traduit les lignes ORM en agrégats de domaine. Les pannes SQLAlchemy sont
**enveloppées** en `InfrastructureError` — le domaine ne voit jamais d'exception brute.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from domain.archer import Archer, ArcherId
from domain.score import Score
from domain.tournoi import Tournoi, TournoiId, TypeTournoi
from infrastructure.db.models import ArcherORM, ScoreORM, TournoiORM
from infrastructure.erreurs import InfrastructureError


def _vers_tournoi(ligne: TournoiORM) -> Tournoi:
    """Traduit une ligne ORM en agrégat de domaine `Tournoi`."""
    return Tournoi(
        nom=ligne.nom,
        date=ligne.date,
        lieu=ligne.lieu,
        type_tournoi=TypeTournoi(ligne.type_tournoi),
        id=ligne.id,
    )


def _vers_archer(ligne: ArcherORM) -> Archer:
    """Traduit une ligne ORM en agrégat de domaine `Archer`."""
    return Archer(nom=ligne.nom, tournoi_id=ligne.tournoi_id, cible=ligne.cible, id=ligne.id)


class TournoiRepositorySQL:
    """Adapter SQLite du port `TournoiRepository`."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        """Persiste le tournoi et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = TournoiORM(
                    nom=tournoi.nom,
                    date=tournoi.date,
                    lieu=tournoi.lieu,
                    type_tournoi=tournoi.type_tournoi.value,
                )
                session.add(ligne)
                session.commit()
                return _vers_tournoi(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du tournoi.") from exc

    def par_id(self, tournoi_id: TournoiId) -> Tournoi | None:
        """Relit le tournoi d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(TournoiORM, tournoi_id)
                return None if ligne is None else _vers_tournoi(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du tournoi.") from exc

    def lister(self) -> list[Tournoi]:
        """Renvoie tous les tournois, du plus récent au plus ancien (par identifiant)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(TournoiORM).order_by(TournoiORM.id.desc())
                ).scalars()
                return [_vers_tournoi(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des tournois.") from exc


class ArcherRepositorySQL:
    """Adapter SQLite du port `ArcherRepository` (E00US011)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, archer: Archer) -> Archer:
        """Persiste l'archer et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = ArcherORM(tournoi_id=archer.tournoi_id, nom=archer.nom, cible=archer.cible)
                session.add(ligne)
                session.commit()
                return _vers_archer(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance de l'archer.") from exc

    def par_id(self, archer_id: ArcherId) -> Archer | None:
        """Relit l'archer d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(ArcherORM, archer_id)
                return None if ligne is None else _vers_archer(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de l'archer.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Archer]:
        """Renvoie tous les archers d'un tournoi (liste éventuellement vide)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(ArcherORM).where(ArcherORM.tournoi_id == tournoi_id)
                ).scalars()
                return [_vers_archer(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des archers du tournoi.") from exc

    def enregistrer(self, archer: Archer) -> Archer:
        """Met à jour un archer déjà persisté (ex. placement) et le renvoie.

        **Contrat** : l'appelant (le service applicatif) garantit l'existence de l'archer
        (vérifiée en amont). La ligne absente est donc une **incohérence technique**, non
        un cas métier — d'où `InfrastructureError` (et non une erreur applicative « 404 »).
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(ArcherORM, archer.id)
                if ligne is None:
                    raise InfrastructureError("Archer à mettre à jour introuvable en base.")
                ligne.nom = archer.nom
                ligne.cible = archer.cible
                session.commit()
                return _vers_archer(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour de l'archer.") from exc


class ScoreRepositorySQL:
    """Adapter SQLite du port `ScoreRepository` (E00US011)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, score: Score) -> Score:
        """Persiste le score et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = ScoreORM(archer_id=score.archer_id, points=score.points)
                session.add(ligne)
                session.commit()
                return Score(archer_id=ligne.archer_id, points=ligne.points, id=ligne.id)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du score.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Score]:
        """Renvoie tous les scores des archers d'un tournoi (jointure archer→tournoi)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(ScoreORM)
                    .join(ArcherORM, ScoreORM.archer_id == ArcherORM.id)
                    .where(ArcherORM.tournoi_id == tournoi_id)
                ).scalars()
                return [
                    Score(archer_id=ligne.archer_id, points=ligne.points, id=ligne.id)
                    for ligne in lignes
                ]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des scores du tournoi.") from exc
