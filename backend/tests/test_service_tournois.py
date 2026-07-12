"""Tests du service applicatif Tournois (E00US009, E01US001) — repository factice.

Le service est testé **en isolation** du domaine d'infrastructure : un faux repository
en mémoire (conforme au port `TournoiRepository`) suffit — ni base ni serveur.
"""

from __future__ import annotations

import datetime

import pytest

from application.erreurs import TournoiIntrouvable
from application.tournois import ServiceTournois
from domain.erreurs import NomTournoiInvalide
from domain.tournoi import Tournoi, TournoiId, TypeTournoi

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


def test_creer_persiste_et_attribue_un_id() -> None:
    """`creer` délègue au repository, qui attribue l'identifiant."""
    service = ServiceTournois(FauxTournoiRepository())
    tournoi = service.creer("Salle 18m", _DATE, "Quimper", TypeTournoi.OFFICIEL)
    assert tournoi.id == 1
    assert tournoi.nom == "Salle 18m"
    assert tournoi.date == _DATE
    assert tournoi.lieu == "Quimper"
    assert tournoi.type_tournoi is TypeTournoi.OFFICIEL


def test_creer_propage_l_erreur_de_domaine() -> None:
    """Un nom invalide fait remonter l'erreur du domaine (non persisté)."""
    service = ServiceTournois(FauxTournoiRepository())
    with pytest.raises(NomTournoiInvalide):
        service.creer("  ", _DATE)


def test_consulter_relit_un_tournoi_existant() -> None:
    """`consulter` renvoie l'agrégat persisté."""
    service = ServiceTournois(FauxTournoiRepository())
    cree = service.creer("Trophée", _DATE)
    assert cree.id is not None
    assert service.consulter(cree.id) == cree


def test_consulter_leve_si_introuvable() -> None:
    """`consulter` lève `TournoiIntrouvable` pour un identifiant inconnu."""
    service = ServiceTournois(FauxTournoiRepository())
    with pytest.raises(TournoiIntrouvable):
        service.consulter(404)


def test_lister_renvoie_tous_les_tournois() -> None:
    """`lister` renvoie tous les tournois créés."""
    service = ServiceTournois(FauxTournoiRepository())
    assert service.lister() == []
    service.creer("A", _DATE)
    service.creer("B", _DATE)
    assert [t.nom for t in service.lister()] == ["A", "B"]
