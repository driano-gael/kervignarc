"""Tests unitaires de l'agrégat Tournoi (E00US009, E01US001, E01US002) — domaine pur, sans base."""

from __future__ import annotations

import datetime

import pytest

from domain.erreurs import NomTournoiInvalide
from domain.tournoi import StatutTournoi, Tournoi, TypeTournoi

_DATE = datetime.date(2026, 3, 14)


def test_creer_un_tournoi_valide() -> None:
    """Nom + date suffisent : lieu à None, type non officiel, statut brouillon, id à None."""
    tournoi = Tournoi.creer("Salle 18m", _DATE)
    assert tournoi == Tournoi(
        nom="Salle 18m",
        date=_DATE,
        lieu=None,
        type_tournoi=TypeTournoi.NON_OFFICIEL,
        statut=StatutTournoi.BROUILLON,
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


# --- Édition des métadonnées (E01US002) ---


def test_modifier_met_a_jour_et_preserve_id_et_statut() -> None:
    """`modifier` change nom/date/lieu/type mais conserve `id` et `statut`."""
    tournoi = Tournoi(
        nom="Ancien",
        date=_DATE,
        lieu=None,
        type_tournoi=TypeTournoi.NON_OFFICIEL,
        statut=StatutTournoi.EN_COURS,
        id=7,
    )
    modifie = tournoi.modifier("Nouveau", _DATE, "Quimper", TypeTournoi.OFFICIEL)
    assert modifie == Tournoi(
        nom="Nouveau",
        date=_DATE,
        lieu="Quimper",
        type_tournoi=TypeTournoi.OFFICIEL,
        statut=StatutTournoi.EN_COURS,
        id=7,
    )


def test_modifier_normalise_et_valide_le_nom() -> None:
    """`modifier` applique les mêmes règles que `creer` (normalisation, nom non vide)."""
    tournoi = Tournoi.creer("Trophée", _DATE)
    assert tournoi.modifier("  Renommé  ", _DATE, "  ").nom == "Renommé"
    with pytest.raises(NomTournoiInvalide):
        tournoi.modifier("   ", _DATE)


# --- Cycle de vie (E01US002) : les transitions renvoient une copie ---


def test_demarrer_passe_en_cours() -> None:
    """`demarrer` renvoie une copie au statut `en_cours` (le reste inchangé)."""
    tournoi = Tournoi.creer("Trophée", _DATE)
    demarre = tournoi.demarrer()
    assert demarre.statut is StatutTournoi.EN_COURS
    assert demarre.nom == tournoi.nom


def test_terminer_passe_termine() -> None:
    """`terminer` renvoie une copie au statut `termine`."""
    tournoi = Tournoi.creer("Trophée", _DATE).demarrer()
    assert tournoi.terminer().statut is StatutTournoi.TERMINE
