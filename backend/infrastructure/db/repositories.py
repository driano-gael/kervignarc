"""Adapters repository SQLAlchemy (E00US009) — implémentent les ports du domaine.

`TournoiRepositorySQL` réalise `domain.ports.TournoiRepository` (conformité structurelle,
vérifiée au câblage). Chaque opération ouvre une **session courte** (une par opération,
ADR-0005) et traduit les lignes ORM en agrégats de domaine. Les pannes SQLAlchemy sont
**enveloppées** en `InfrastructureError` — le domaine ne voit jamais d'exception brute.
"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from domain.archer import Archer, ArcherId
from domain.blason import Blason, BlasonId
from domain.categorie import Categorie, CategorieId, SexeCategorie
from domain.gabarit_salle import GabaritSalle, GabaritSalleId
from domain.score import Score
from domain.tournoi import StatutTournoi, Tournoi, TournoiId, TypeTournoi
from infrastructure.db.models import (
    ArcherORM,
    BlasonORM,
    CategorieORM,
    GabaritSalleORM,
    ScoreORM,
    TournoiORM,
)
from infrastructure.erreurs import InfrastructureError


def _vers_tournoi(ligne: TournoiORM) -> Tournoi:
    """Traduit une ligne ORM en agrégat de domaine `Tournoi`."""
    return Tournoi(
        nom=ligne.nom,
        date=ligne.date,
        lieu=ligne.lieu,
        type_tournoi=TypeTournoi(ligne.type_tournoi),
        statut=StatutTournoi(ligne.statut),
        id=ligne.id,
    )


def _vers_archer(ligne: ArcherORM) -> Archer:
    """Traduit une ligne ORM en agrégat de domaine `Archer`."""
    return Archer(nom=ligne.nom, tournoi_id=ligne.tournoi_id, cible=ligne.cible, id=ligne.id)


def _vers_blason(ligne: BlasonORM) -> Blason:
    """Traduit une ligne ORM en agrégat de domaine `Blason`."""
    return Blason(
        tournoi_id=ligne.tournoi_id,
        nom=ligne.nom,
        taille=ligne.taille,
        capacite=ligne.capacite,
        id=ligne.id,
    )


def _vers_gabarit(ligne: GabaritSalleORM) -> GabaritSalle:
    """Traduit une ligne ORM en agrégat de domaine `GabaritSalle` (config JSON → tuple)."""
    config = json.loads(ligne.config)
    capacites = tuple(int(c) for c in config["capacites"])
    return GabaritSalle(nom=ligne.nom, capacites=capacites, id=ligne.id)


def _config_gabarit(gabarit: GabaritSalle) -> str:
    """Sérialise le plafond par cible d'un gabarit en JSON (`{"capacites": [...]}`)."""
    return json.dumps({"capacites": list(gabarit.capacites)})


def _vers_categorie(ligne: CategorieORM) -> Categorie:
    """Traduit une ligne ORM en agrégat de domaine `Categorie`."""
    return Categorie(
        tournoi_id=ligne.tournoi_id,
        libelle=ligne.libelle,
        arme=ligne.arme,
        tranche_age=ligne.tranche_age,
        sexe=None if ligne.sexe is None else SexeCategorie(ligne.sexe),
        blason_id=ligne.blason_id,
        id=ligne.id,
    )


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
                    statut=tournoi.statut.value,
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

    def enregistrer(self, tournoi: Tournoi) -> Tournoi:
        """Met à jour un tournoi déjà persisté (édition, transition de statut) et le renvoie.

        **Contrat** : l'appelant (le service) garantit l'existence du tournoi (vérifiée en
        amont). La ligne absente est donc une **incohérence technique**, non un cas métier
        — d'où `InfrastructureError` (et non une erreur applicative « 404 »).
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(TournoiORM, tournoi.id)
                if ligne is None:
                    raise InfrastructureError("Tournoi à mettre à jour introuvable en base.")
                ligne.nom = tournoi.nom
                ligne.date = tournoi.date
                ligne.lieu = tournoi.lieu
                ligne.type_tournoi = tournoi.type_tournoi.value
                ligne.statut = tournoi.statut.value
                session.commit()
                return _vers_tournoi(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour du tournoi.") from exc

    def supprimer(self, tournoi_id: TournoiId) -> None:
        """Supprime le tournoi d'identifiant donné (existence garantie par l'appelant)."""
        try:
            with self._session_factory() as session:
                ligne = session.get(TournoiORM, tournoi_id)
                if ligne is None:
                    raise InfrastructureError("Tournoi à supprimer introuvable en base.")
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression du tournoi.") from exc


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


class CategorieRepositorySQL:
    """Adapter SQLite du port `CategorieRepository` (E01US003)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, categorie: Categorie) -> Categorie:
        """Persiste la catégorie et la renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = CategorieORM(
                    tournoi_id=categorie.tournoi_id,
                    libelle=categorie.libelle,
                    arme=categorie.arme,
                    tranche_age=categorie.tranche_age,
                    sexe=None if categorie.sexe is None else categorie.sexe.value,
                    blason_id=categorie.blason_id,
                )
                session.add(ligne)
                session.commit()
                return _vers_categorie(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance de la catégorie.") from exc

    def par_id(self, categorie_id: CategorieId) -> Categorie | None:
        """Relit la catégorie d'identifiant donné, ou `None` si elle n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(CategorieORM, categorie_id)
                return None if ligne is None else _vers_categorie(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de la catégorie.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Categorie]:
        """Renvoie toutes les catégories d'un tournoi (liste éventuellement vide)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(CategorieORM)
                    .where(CategorieORM.tournoi_id == tournoi_id)
                    .order_by(CategorieORM.id)
                ).scalars()
                return [_vers_categorie(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des catégories du tournoi.") from exc

    def par_blason(self, blason_id: BlasonId) -> list[Categorie]:
        """Renvoie les catégories dont le blason par défaut est `blason_id` (E01US006)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(CategorieORM)
                    .where(CategorieORM.blason_id == blason_id)
                    .order_by(CategorieORM.id)
                ).scalars()
                return [_vers_categorie(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des catégories par blason.") from exc

    def enregistrer(self, categorie: Categorie) -> Categorie:
        """Met à jour une catégorie déjà persistée (édition) et la renvoie.

        **Contrat** : l'appelant (le service) garantit l'existence (vérifiée en amont). La ligne
        absente est une **incohérence technique** (non un cas métier) → `InfrastructureError`.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(CategorieORM, categorie.id)
                if ligne is None:
                    raise InfrastructureError("Catégorie à mettre à jour introuvable en base.")
                ligne.libelle = categorie.libelle
                ligne.arme = categorie.arme
                ligne.tranche_age = categorie.tranche_age
                ligne.sexe = None if categorie.sexe is None else categorie.sexe.value
                ligne.blason_id = categorie.blason_id
                session.commit()
                return _vers_categorie(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour de la catégorie.") from exc

    def supprimer(self, categorie_id: CategorieId) -> None:
        """Supprime la catégorie d'identifiant donné (existence garantie par l'appelant)."""
        try:
            with self._session_factory() as session:
                ligne = session.get(CategorieORM, categorie_id)
                if ligne is None:
                    raise InfrastructureError("Catégorie à supprimer introuvable en base.")
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression de la catégorie.") from exc


class BlasonRepositorySQL:
    """Adapter SQLite du port `BlasonRepository` (E01US005)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, blason: Blason) -> Blason:
        """Persiste le blason et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = BlasonORM(
                    tournoi_id=blason.tournoi_id,
                    nom=blason.nom,
                    taille=blason.taille,
                    capacite=blason.capacite,
                )
                session.add(ligne)
                session.commit()
                return _vers_blason(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du blason.") from exc

    def par_id(self, blason_id: BlasonId) -> Blason | None:
        """Relit le blason d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(BlasonORM, blason_id)
                return None if ligne is None else _vers_blason(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du blason.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Blason]:
        """Renvoie tous les blasons d'un tournoi (liste éventuellement vide)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(BlasonORM)
                    .where(BlasonORM.tournoi_id == tournoi_id)
                    .order_by(BlasonORM.id)
                ).scalars()
                return [_vers_blason(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des blasons du tournoi.") from exc

    def enregistrer(self, blason: Blason) -> Blason:
        """Met à jour un blason déjà persisté (édition) et le renvoie.

        **Contrat** : l'appelant (le service) garantit l'existence (vérifiée en amont). La ligne
        absente est une **incohérence technique** (non un cas métier) → `InfrastructureError`.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(BlasonORM, blason.id)
                if ligne is None:
                    raise InfrastructureError("Blason à mettre à jour introuvable en base.")
                ligne.nom = blason.nom
                ligne.taille = blason.taille
                ligne.capacite = blason.capacite
                session.commit()
                return _vers_blason(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour du blason.") from exc

    def supprimer(self, blason_id: BlasonId) -> None:
        """Supprime le blason d'identifiant donné (existence garantie par l'appelant)."""
        try:
            with self._session_factory() as session:
                ligne = session.get(BlasonORM, blason_id)
                if ligne is None:
                    raise InfrastructureError("Blason à supprimer introuvable en base.")
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression du blason.") from exc


class GabaritSalleRepositorySQL:
    """Adapter SQLite du port `GabaritSalleRepository` (E01US007)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, gabarit: GabaritSalle) -> GabaritSalle:
        """Persiste le gabarit et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = GabaritSalleORM(
                    nom=gabarit.nom,
                    nb_cibles=gabarit.nb_cibles,
                    config=_config_gabarit(gabarit),
                )
                session.add(ligne)
                session.commit()
                return _vers_gabarit(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du gabarit de salle.") from exc

    def par_id(self, gabarit_id: GabaritSalleId) -> GabaritSalle | None:
        """Relit le gabarit d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(GabaritSalleORM, gabarit_id)
                return None if ligne is None else _vers_gabarit(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du gabarit de salle.") from exc

    def lister(self) -> list[GabaritSalle]:
        """Renvoie tous les gabarits, dans l'ordre de création (par identifiant)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(GabaritSalleORM).order_by(GabaritSalleORM.id)
                ).scalars()
                return [_vers_gabarit(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des gabarits de salle.") from exc

    def enregistrer(self, gabarit: GabaritSalle) -> GabaritSalle:
        """Met à jour un gabarit déjà persisté (édition) et le renvoie.

        **Contrat** : l'appelant (le service) garantit l'existence (vérifiée en amont). La ligne
        absente est une **incohérence technique** (non un cas métier) → `InfrastructureError`.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(GabaritSalleORM, gabarit.id)
                if ligne is None:
                    raise InfrastructureError("Gabarit à mettre à jour introuvable en base.")
                ligne.nom = gabarit.nom
                ligne.nb_cibles = gabarit.nb_cibles
                ligne.config = _config_gabarit(gabarit)
                session.commit()
                return _vers_gabarit(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour du gabarit de salle.") from exc

    def supprimer(self, gabarit_id: GabaritSalleId) -> None:
        """Supprime le gabarit d'identifiant donné (existence garantie par l'appelant)."""
        try:
            with self._session_factory() as session:
                ligne = session.get(GabaritSalleORM, gabarit_id)
                if ligne is None:
                    raise InfrastructureError("Gabarit à supprimer introuvable en base.")
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression du gabarit de salle.") from exc


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
