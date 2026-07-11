"""Tests unitaires de l'agrégat Tournoi (E00US009) — domaine pur, sans base ni serveur."""

from __future__ import annotations

import pytest

from domain.erreurs import NomTournoiInvalide
from domain.tournoi import Tournoi


def test_creer_un_tournoi_valide() -> None:
    """Un nom non vide produit un tournoi non persisté (id à None)."""
    tournoi = Tournoi.creer("Salle 18m")
    assert tournoi == Tournoi(nom="Salle 18m", id=None)


def test_creer_normalise_les_espaces() -> None:
    """Le nom est normalisé (espaces de bord retirés)."""
    assert Tournoi.creer("  Trophée  ").nom == "Trophée"


@pytest.mark.parametrize("nom", ["", "   ", "\t\n"])
def test_creer_refuse_un_nom_vide(nom: str) -> None:
    """Un nom vide ou blanc lève une erreur de domaine typée."""
    with pytest.raises(NomTournoiInvalide):
        Tournoi.creer(nom)
