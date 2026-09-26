"""Adapter d'écriture de l'import des inscrits (E02US007) — un plan, une transaction. ADR-0115."""

from __future__ import annotations

import datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from domain.archer import Archer, ArcherId
from domain.club import Club, ClubId, cle_nom
from domain.import_inscrits import Decision, LignePlan, PlanImport
from domain.tournoi import TournoiId
from infrastructure.db.models import ArcherORM, ClubORM, InscriptionORM
from infrastructure.erreurs import InfrastructureError


class ImportInscritsRepositorySQL:
    """⚠️ Un seul `commit`, à la fin : une ligne qui échoue annule tout le fichier — le contraire
    d'un import partiel silencieux (CA « rapport »)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def appliquer(
        self, tournoi_id: TournoiId, plan: PlanImport, cree_le: datetime.datetime
    ) -> None:
        try:
            with self._session_factory() as session:
                clubs: dict[str, ClubId] = {}
                fiches: dict[int, ArcherId] = {}
                for ligne in plan.importables:
                    archer_id = self._archer(session, tournoi_id, ligne, clubs, fiches)
                    assert ligne.depart_id is not None
                    session.add(
                        InscriptionORM(
                            archer_id=archer_id, depart_id=ligne.depart_id, cree_le=cree_le
                        )
                    )
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError(
                "Échec de l'import des inscrits : rien n'a été écrit."
            ) from exc

    def _archer(
        self,
        session: Session,
        tournoi_id: TournoiId,
        ligne: LignePlan,
        clubs: dict[str, ClubId],
        fiches: dict[int, ArcherId],
    ) -> ArcherId:
        if ligne.decision is Decision.INSCRIRE:
            if ligne.archer_id is not None:
                return ligne.archer_id
            assert ligne.fiche_de_la_ligne is not None
            return fiches[ligne.fiche_de_la_ligne]
        assert ligne.categorie_id is not None
        archer = Archer.creer(
            ligne.ligne.nom or "",
            ligne.ligne.prenom or "",
            tournoi_id,
            ligne.categorie_id,
            ligne.club_id if ligne.club_a_creer is None else self._club(session, ligne, clubs),
            ligne.licence,
        )
        orm = ArcherORM(
            tournoi_id=archer.tournoi_id,
            nom=archer.nom,
            prenom=archer.prenom,
            categorie_id=archer.categorie_id,
            club_id=archer.club_id,
            licence=archer.licence,
        )
        session.add(orm)
        session.flush()
        fiches[ligne.ligne.numero] = orm.id
        return orm.id

    @staticmethod
    def _club(session: Session, ligne: LignePlan, clubs: dict[str, ClubId]) -> ClubId:
        """Un club absent n'est créé qu'une fois, même nommé par cent lignes."""
        assert ligne.club_a_creer is not None
        cle = cle_nom(ligne.club_a_creer)
        if cle not in clubs:
            orm = ClubORM(nom=Club.creer(ligne.club_a_creer).nom)
            session.add(orm)
            session.flush()
            clubs[cle] = orm.id
        return clubs[cle]
