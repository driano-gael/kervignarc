"""Tests unitaires de l'agrégat Tournoi (E00US009, E01US001) — domaine pur, sans base."""

from __future__ import annotations

import datetime

import pytest

from domain.erreurs import NomTournoiInvalide
from domain.tournoi import Tournoi, TypeTournoi

_DATE = datetime.date(2026, 3, 14)


def test_creer_un_tournoi_valide() -> None:
    """Nom + date suffisent : lieu à None, type non officiel par défaut, id à None."""
    tournoi = Tournoi.creer("Salle 18m", _DATE)
    assert tournoi == Tournoi(
        nom="Salle 18m",
        date=_DATE,
        lieu=None,
        type_tournoi=TypeTournoi.NON_OFFICIEL,
        id=None,
    )


def test_creer_avec_lieu_et_type() -> None:
    """Lieu et type explicites sont conservés."""
    tournoi = Tournoi.creer("Trophée", _DATE, "Quimper", TypeTournoi.OFFICIEL)
    assert tournoi.lieu == "Quimper"
    assert tournoi.type_tournoi is TypeTournoi.OFFICIEL


def test_creer_normalise_nom_et_lieu() -> None:
    """Le nom et le lieu sont normalisés (espaces de bord retirés)."""
    tournoi = Tournoi.creer("  Trophée  ", _DATE, "  Quimper  ")
    assert tournoi.nom == "Trophée"
    assert tournoi.lieu == "Quimper"


def test_creer_lieu_vide_devient_none() -> None:
    """Un lieu vide ou blanc est facultatif → normalisé à None."""
    assert Tournoi.creer("Trophée", _DATE, "   ").lieu is None


@pytest.mark.parametrize("nom", ["", "   ", "\t\n"])
def test_creer_refuse_un_nom_vide(nom: str) -> None:
    """Un nom vide ou blanc lève une erreur de domaine typée."""
    with pytest.raises(NomTournoiInvalide):
        Tournoi.creer(nom, _DATE)
