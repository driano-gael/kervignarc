"""Tests du service applicatif Tournois (E00US009) — orchestration, repository factice.

Le service est testé **en isolation** du domaine d'infrastructure : un faux repository
en mémoire (conforme au port `TournoiRepository`) suffit — ni base ni serveur.
"""

from __future__ import annotations

import pytest

from application.erreurs import TournoiIntrouvable
from application.tournois import ServiceTournois
from domain.erreurs import NomTournoiInvalide
from domain.tournoi import Tournoi, TournoiId


class FauxTournoiRepository:
    """Repository en mémoire conforme au port `TournoiRepository`."""

    def __init__(self) -> None:
        self._tournois: dict[int, Tournoi] = {}
        self._sequence = 0

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        self._sequence += 1
        persiste = Tournoi(nom=tournoi.nom, id=self._sequence)
        self._tournois[self._sequence] = persiste
        return persiste

    def par_id(self, tournoi_id: TournoiId) -> Tournoi | None:
        return self._tournois.get(tournoi_id)


def test_creer_persiste_et_attribue_un_id() -> None:
    """`creer` délègue au repository, qui attribue l'identifiant."""
    service = ServiceTournois(FauxTournoiRepository())
    tournoi = service.creer("Salle 18m")
    assert tournoi.id == 1
    assert tournoi.nom == "Salle 18m"


def test_creer_propage_l_erreur_de_domaine() -> None:
    """Un nom invalide fait remonter l'erreur du domaine (non persisté)."""
    service = ServiceTournois(FauxTournoiRepository())
    with pytest.raises(NomTournoiInvalide):
        service.creer("  ")


def test_consulter_relit_un_tournoi_existant() -> None:
    """`consulter` renvoie l'agrégat persisté."""
    service = ServiceTournois(FauxTournoiRepository())
    cree = service.creer("Trophée")
    assert cree.id is not None
    assert service.consulter(cree.id) == cree


def test_consulter_leve_si_introuvable() -> None:
    """`consulter` lève `TournoiIntrouvable` pour un identifiant inconnu."""
    service = ServiceTournois(FauxTournoiRepository())
    with pytest.raises(TournoiIntrouvable):
        service.consulter(404)
