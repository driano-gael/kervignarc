"""Tests des services applicatifs Archers et Classement (E00US011) — repositories factices.

Les services sont testés **en isolation** : de faux repositories en mémoire (conformes aux
ports) suffisent — ni base ni serveur.
"""

from __future__ import annotations

import datetime

import pytest

from application.archers import ServiceArchers
from application.classements import ServiceClassement
from application.erreurs import ArcherIntrouvable, ClubIntrouvable, TournoiIntrouvable
from domain.archer import Archer, ArcherId
from domain.club import Club, ClubId
from domain.erreurs import CibleInvalide, NomArcherInvalide, ScoreInvalide
from domain.score import Score
from domain.tournoi import Tournoi, TournoiId
from tests.conftest import FauxClubRepository

_DATE = datetime.date(2026, 3, 14)


class FauxTournoiRepository:
    """Repository en mémoire conforme au port `TournoiRepository`."""

    def __init__(self) -> None:
        self._tournois: dict[int, Tournoi] = {}
        self._sequence = 0

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        self._sequence += 1
        persiste = Tournoi(
            nom=tournoi.nom,
            date=tournoi.date,
            lieu=tournoi.lieu,
            type_tournoi=tournoi.type_tournoi,
            id=self._sequence,
        )
        self._tournois[self._sequence] = persiste
        return persiste

    def par_id(self, tournoi_id: TournoiId) -> Tournoi | None:
        return self._tournois.get(tournoi_id)

    def lister(self) -> list[Tournoi]:
        return list(self._tournois.values())

    def enregistrer(self, tournoi: Tournoi) -> Tournoi:
        assert tournoi.id is not None
        self._tournois[tournoi.id] = tournoi
        return tournoi

    def supprimer(self, tournoi_id: TournoiId) -> None:
        del self._tournois[tournoi_id]


class FauxArcherRepository:
    """Repository en mémoire conforme au port `ArcherRepository`."""

    def __init__(self) -> None:
        self._archers: dict[int, Archer] = {}
        self._sequence = 0

    def ajouter(self, archer: Archer) -> Archer:
        self._sequence += 1
        # `club_id` est **recopié** : un faux qui le laisserait tomber ferait passer au vert un
        # service incapable de rattacher un archer à son club.
        persiste = Archer(
            nom=archer.nom,
            tournoi_id=archer.tournoi_id,
            cible=archer.cible,
            club_id=archer.club_id,
            id=self._sequence,
        )
        self._archers[self._sequence] = persiste
        return persiste

    def par_id(self, archer_id: ArcherId) -> Archer | None:
        return self._archers.get(archer_id)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Archer]:
        return [a for a in self._archers.values() if a.tournoi_id == tournoi_id]

    def par_club(self, club_id: ClubId) -> list[Archer]:
        # Sans filtre sur le tournoi : le référentiel des clubs est global (E02US001).
        return [a for a in self._archers.values() if a.club_id == club_id]

    def enregistrer(self, archer: Archer) -> Archer:
        assert archer.id is not None
        self._archers[archer.id] = archer
        return archer


class FauxScoreRepository:
    """Repository en mémoire conforme au port `ScoreRepository`."""

    def __init__(self, archers: FauxArcherRepository) -> None:
        self._archers = archers
        self._scores: list[Score] = []
        self._sequence = 0

    def ajouter(self, score: Score) -> Score:
        self._sequence += 1
        persiste = Score(archer_id=score.archer_id, points=score.points, id=self._sequence)
        self._scores.append(persiste)
        return persiste

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Score]:
        ids = {a.id for a in self._archers.par_tournoi(tournoi_id)}
        return [s for s in self._scores if s.archer_id in ids]


def _monter() -> tuple[ServiceArchers, ServiceClassement, TournoiId]:
    tournois = FauxTournoiRepository()
    archers = FauxArcherRepository()
    scores = FauxScoreRepository(archers)
    clubs = FauxClubRepository()
    tournoi = tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
    assert tournoi.id is not None
    return (
        ServiceArchers(tournois, archers, scores, clubs),
        ServiceClassement(tournois, archers, scores),
        tournoi.id,
    )


def _monter_avec_club() -> tuple[ServiceArchers, FauxClubRepository, TournoiId]:
    """Variante exposant le référentiel des clubs, pour le rattachement (E02US001)."""
    tournois = FauxTournoiRepository()
    archers = FauxArcherRepository()
    scores = FauxScoreRepository(archers)
    clubs = FauxClubRepository()
    tournoi = tournois.ajouter(Tournoi.creer("Salle 18m", _DATE))
    assert tournoi.id is not None
    return ServiceArchers(tournois, archers, scores, clubs), clubs, tournoi.id


def test_ajouter_archer_persiste_et_attribue_un_id() -> None:
    """`ajouter` inscrit l'archer au tournoi et lui attribue un identifiant."""
    service, _, tournoi_id = _monter()
    archer = service.ajouter(tournoi_id, "Robin")
    assert archer.id == 1
    assert archer.tournoi_id == tournoi_id
    assert archer.cible is None


def test_ajouter_archer_tournoi_inconnu_leve() -> None:
    """Inscrire dans un tournoi inexistant lève `TournoiIntrouvable`."""
    service, _, _ = _monter()
    with pytest.raises(TournoiIntrouvable):
        service.ajouter(404, "Robin")


def test_ajouter_archer_propage_l_erreur_de_domaine() -> None:
    """Un nom d'archer vide fait remonter l'erreur du domaine (non persisté)."""
    service, _, tournoi_id = _monter()
    with pytest.raises(NomArcherInvalide):
        service.ajouter(tournoi_id, "  ")


def test_ajouter_archer_sans_club_laisse_le_rattachement_vide() -> None:
    """Le club est **facultatif** en E02US001 : sans lui, `club_id` reste `None`."""
    service, _, tournoi_id = _monter()
    archer = service.ajouter(tournoi_id, "Robin")
    assert archer.club_id is None


def test_ajouter_archer_avec_club_le_rattache() -> None:
    """Un `club_id` existant est porté par l'archer persisté (E02US001)."""
    service, clubs, tournoi_id = _monter_avec_club()
    club = clubs.ajouter(Club.creer("Arc Club Rennes"))
    archer = service.ajouter(tournoi_id, "Robin", club.id)
    assert archer.club_id == club.id


def test_ajouter_archer_club_inconnu_leve() -> None:
    """Inscrire avec un club inexistant lève `ClubIntrouvable` (rien n'est persisté)."""
    service, _, tournoi_id = _monter_avec_club()
    with pytest.raises(ClubIntrouvable):
        service.ajouter(tournoi_id, "Robin", 404)


def test_placer_archer_pose_la_cible() -> None:
    """`placer` met à jour la cible de l'archer persisté."""
    service, _, tournoi_id = _monter()
    archer = service.ajouter(tournoi_id, "Robin")
    assert archer.id is not None
    place = service.placer(archer.id, 4)
    assert place.cible == 4


def test_placer_archer_inconnu_leve() -> None:
    """Placer un archer inexistant lève `ArcherIntrouvable`."""
    service, _, _ = _monter()
    with pytest.raises(ArcherIntrouvable):
        service.placer(404, 1)


def test_placer_archer_propage_l_erreur_de_domaine() -> None:
    """Une cible invalide fait remonter l'erreur du domaine."""
    service, _, tournoi_id = _monter()
    archer = service.ajouter(tournoi_id, "Robin")
    assert archer.id is not None
    with pytest.raises(CibleInvalide):
        service.placer(archer.id, 0)


def test_saisir_score_persiste_la_fleche() -> None:
    """`saisir_score` enregistre une flèche pour un archer existant."""
    service, _, tournoi_id = _monter()
    archer = service.ajouter(tournoi_id, "Robin")
    assert archer.id is not None
    score = service.saisir_score(archer.id, 9)
    assert score.id == 1
    assert score.archer_id == archer.id
    assert score.points == 9


def test_saisir_score_archer_inconnu_leve() -> None:
    """Saisir un score pour un archer inexistant lève `ArcherIntrouvable`."""
    service, _, _ = _monter()
    with pytest.raises(ArcherIntrouvable):
        service.saisir_score(404, 9)


def test_saisir_score_propage_l_erreur_de_domaine() -> None:
    """Un score hors plage fait remonter l'erreur du domaine."""
    service, _, tournoi_id = _monter()
    archer = service.ajouter(tournoi_id, "Robin")
    assert archer.id is not None
    with pytest.raises(ScoreInvalide):
        service.saisir_score(archer.id, 11)


def test_classement_reflete_les_scores_saisis() -> None:
    """Le service de classement agrège les scores des archers du tournoi."""
    archers_service, classement_service, tournoi_id = _monter()
    alice = archers_service.ajouter(tournoi_id, "Alice")
    bob = archers_service.ajouter(tournoi_id, "Bob")
    assert alice.id is not None and bob.id is not None
    archers_service.saisir_score(alice.id, 10)
    archers_service.saisir_score(alice.id, 9)
    archers_service.saisir_score(bob.id, 8)

    lignes = classement_service.pour_tournoi(tournoi_id).lignes
    assert [(ligne.nom, ligne.rang, ligne.total) for ligne in lignes] == [
        ("Alice", 1, 19),
        ("Bob", 2, 8),
    ]


def test_classement_tournoi_inconnu_leve() -> None:
    """Consulter le classement d'un tournoi inexistant lève `TournoiIntrouvable`."""
    _, classement_service, _ = _monter()
    with pytest.raises(TournoiIntrouvable):
        classement_service.pour_tournoi(404)
