"""Tests unitaires de l'agrégat Blason (E01US005) — domaine pur, sans base."""

from __future__ import annotations

import pytest

from domain.blason import Blason
from domain.erreurs import CapaciteBlasonInvalide, NomBlasonInvalide, TailleBlasonInvalide


def test_creer_un_blason_valide() -> None:
    """Nom, taille et capacité valides : id à None, rattaché au tournoi."""
    blason = Blason.creer(1, "Trispot 40", 0.5, 3)
    assert blason == Blason(tournoi_id=1, nom="Trispot 40", taille=0.5, capacite=3, id=None)


def test_creer_normalise_le_nom() -> None:
    """Le nom est normalisé (espaces de bord retirés)."""
    blason = Blason.creer(1, "  Monospot 60  ", 1.0, 1)
    assert blason.nom == "Monospot 60"


@pytest.mark.parametrize("nom", ["", "   ", "\t\n"])
def test_creer_refuse_un_nom_vide(nom: str) -> None:
    """Un nom vide ou blanc lève une erreur de domaine typée."""
    with pytest.raises(NomBlasonInvalide):
        Blason.creer(1, nom, 0.5, 2)


def test_creer_accepte_taille_pleine() -> None:
    """La borne haute (taille = 1, place entière) est autorisée."""
    assert Blason.creer(1, "Monospot 60", 1.0, 1).taille == 1.0


@pytest.mark.parametrize("taille", [0.0, -0.5, 1.5, 2.0])
def test_creer_refuse_une_taille_hors_plage(taille: float) -> None:
    """Une taille hors de `]0, 1]` lève une erreur de domaine typée."""
    with pytest.raises(TailleBlasonInvalide):
        Blason.creer(1, "Blason", taille, 1)


@pytest.mark.parametrize("capacite", [0, -1])
def test_creer_refuse_une_capacite_inferieure_a_un(capacite: int) -> None:
    """Une capacité inférieure à 1 lève une erreur de domaine typée."""
    with pytest.raises(CapaciteBlasonInvalide):
        Blason.creer(1, "Blason", 0.5, capacite)


def test_modifier_met_a_jour_et_preserve_id_et_tournoi() -> None:
    """`modifier` change les attributs mais conserve `id` et `tournoi_id`."""
    blason = Blason(tournoi_id=3, nom="Ancien", taille=0.25, capacite=4, id=9)
    modifie = blason.modifier("Nouveau", 0.5, 2)
    assert modifie == Blason(tournoi_id=3, nom="Nouveau", taille=0.5, capacite=2, id=9)


def test_modifier_valide_les_attributs() -> None:
    """`modifier` applique les mêmes règles que `creer`."""
    blason = Blason.creer(1, "Blason", 0.5, 2)
    with pytest.raises(TailleBlasonInvalide):
        blason.modifier("Blason", 0.0, 2)
    with pytest.raises(CapaciteBlasonInvalide):
        blason.modifier("Blason", 0.5, 0)
    with pytest.raises(NomBlasonInvalide):
        blason.modifier("   ", 0.5, 2)
