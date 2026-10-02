"""Adapter SQL des équipes (E13US002) — l'équipe et ses membres s'écrivent dans une transaction."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from domain.archer import ArcherId
from domain.equipe import Equipe, EquipeId, TypeEquipe
from domain.tournoi import TournoiId
from infrastructure.db.models import EquipeORM, MembreEquipeORM
from infrastructure.erreurs import InfrastructureError


class EquipeRepositorySQL:
    """Adapter SQLite du port `EquipeRepository`."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def par_id(self, equipe_id: EquipeId) -> Equipe | None:
        try:
            with self._session_factory() as session:
                ligne = session.get(EquipeORM, equipe_id)
                return None if ligne is None else _vers_equipes(session, [ligne])[0]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de l'équipe.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Equipe]:
        try:
            with self._session_factory() as session:
                lignes = session.scalars(
                    select(EquipeORM)
                    .where(EquipeORM.tournoi_id == tournoi_id)
                    .order_by(EquipeORM.id)
                ).all()
                return _vers_equipes(session, lignes)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des équipes du tournoi.") from exc

    def par_archer(self, archer_id: ArcherId) -> list[Equipe]:
        try:
            with self._session_factory() as session:
                ids = select(MembreEquipeORM.equipe_id).where(
                    MembreEquipeORM.archer_id == archer_id
                )
                lignes = session.scalars(
                    select(EquipeORM).where(EquipeORM.id.in_(ids)).order_by(EquipeORM.id)
                ).all()
                return _vers_equipes(session, lignes)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des équipes de l'archer.") from exc

    def enregistrer(self, equipe: Equipe) -> Equipe:
        """⚠️ Les membres sont **réécrits** en entier : `ordre` est leur rang dans `membres`."""
        try:
            with self._session_factory() as session:
                if equipe.id is None:
                    ligne = EquipeORM(tournoi_id=equipe.tournoi_id)
                    session.add(ligne)
                else:
                    trouvee = session.get(EquipeORM, equipe.id)
                    if trouvee is None:
                        raise InfrastructureError("Équipe à mettre à jour introuvable en base.")
                    ligne = trouvee
                ligne.nom = equipe.nom
                ligne.type = equipe.type.value
                ligne.effectif_attendu = equipe.effectif_attendu
                session.flush()
                session.execute(
                    delete(MembreEquipeORM).where(MembreEquipeORM.equipe_id == ligne.id)
                )
                session.add_all(
                    MembreEquipeORM(equipe_id=ligne.id, archer_id=archer_id, ordre=rang)
                    for rang, archer_id in enumerate(equipe.membres)
                )
                session.commit()
                return _vers_equipes(session, [ligne])[0]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance de l'équipe.") from exc

    def supprimer(self, equipe_id: EquipeId) -> None:
        try:
            with self._session_factory() as session:
                session.execute(
                    delete(MembreEquipeORM).where(MembreEquipeORM.equipe_id == equipe_id)
                )
                session.execute(delete(EquipeORM).where(EquipeORM.id == equipe_id))
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression de l'équipe.") from exc


def _vers_equipes(session: Session, lignes: Iterable[EquipeORM]) -> list[Equipe]:
    """Une seule requête pour les membres de toutes les équipes lues, pas une par équipe."""
    lignes = list(lignes)
    membres: dict[int, list[ArcherId]] = defaultdict(list)
    for equipe_id, archer_id in session.execute(
        select(MembreEquipeORM.equipe_id, MembreEquipeORM.archer_id)
        .where(MembreEquipeORM.equipe_id.in_([ligne.id for ligne in lignes]))
        .order_by(MembreEquipeORM.equipe_id, MembreEquipeORM.ordre)
    ).tuples():
        membres[equipe_id].append(archer_id)
    return [
        Equipe(
            tournoi_id=ligne.tournoi_id,
            nom=ligne.nom,
            type=TypeEquipe(ligne.type),
            effectif_attendu=ligne.effectif_attendu,
            membres=tuple(membres[ligne.id]),
            id=ligne.id,
        )
        for ligne in lignes
    ]
