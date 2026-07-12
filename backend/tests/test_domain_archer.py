"""Tests unitaires des agrégats Archer et Score (E00US011) — domaine pur, sans base."""

from __future__ import annotations

import pytest

from domain.archer import Archer
from domain.erreurs import CibleInvalide, NomArcherInvalide, ScoreInvalide
from domain.score import Score


def test_creer_un_archer_valide() -> None:
    """Un nom non vide produit un archer non persisté, non placé (cible et id à None)."""
    archer = Archer.creer("Robin", tournoi_id=1)
    assert archer == Archer(nom="Robin", tournoi_id=1, cible=None, id=None)


def test_creer_normalise_les_espaces() -> None:
    """Le nom d'archer est normalisé (espaces de bord retirés)."""
    assert Archer.creer("  Marion  ", tournoi_id=1).nom == "Marion"


@pytest.mark.parametrize("nom", ["", "   ", "\t\n"])
def test_creer_refuse_un_nom_vide(nom: str) -> None:
    """Un nom vide ou blanc lève une erreur de domaine typée."""
    with pytest.raises(NomArcherInvalide):
        Archer.creer(nom, tournoi_id=1)


def test_placer_pose_la_cible_sans_muter_l_original() -> None:
    """`placer` renvoie une copie placée ; l'agrégat d'origine reste inchangé (immuable)."""
    archer = Archer(nom="Robin", tournoi_id=1, id=7)
    place = archer.placer(3)
    assert place == Archer(nom="Robin", tournoi_id=1, cible=3, id=7)
    assert archer.cible is None


@pytest.mark.parametrize("cible", [0, -1])
def test_placer_refuse_une_cible_non_positive(cible: int) -> None:
    """Un numéro de cible non strictement positif lève une erreur de domaine typée."""
    with pytest.raises(CibleInvalide):
        Archer(nom="Robin", tournoi_id=1, id=7).placer(cible)


def test_creer_un_score_valide() -> None:
    """Une valeur de flèche dans la plage produit un score non persisté (id à None)."""
    assert Score.creer(archer_id=7, points=9) == Score(archer_id=7, points=9, id=None)


@pytest.mark.parametrize("points", [0, 10])
def test_creer_score_accepte_les_bornes(points: int) -> None:
    """Les bornes 0 et 10 sont acceptées."""
    assert Score.creer(archer_id=7, points=points).points == points


@pytest.mark.parametrize("points", [-1, 11])
def test_creer_score_refuse_hors_plage(points: int) -> None:
    """Une valeur hors de 0-10 lève une erreur de domaine typée."""
    with pytest.raises(ScoreInvalide):
        Score.creer(archer_id=7, points=points)
