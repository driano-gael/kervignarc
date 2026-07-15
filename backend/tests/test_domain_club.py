"""Tests de l'agrégat `Club` (E02US001) — domaine pur, sans base ni serveur."""

from __future__ import annotations

import dataclasses

import pytest

from domain.club import Club
from domain.erreurs import NomClubInvalide


def test_creer_un_club_valide() -> None:
    club = Club.creer("Compagnie d'Arc de Fougères")

    assert club.nom == "Compagnie d'Arc de Fougères"
    assert club.id is None, "Un club non persisté n'a pas encore d'identifiant."


def test_creer_normalise_les_espaces_de_bord() -> None:
    club = Club.creer("  Arc Club Rennes  ")

    assert club.nom == "Arc Club Rennes"


@pytest.mark.parametrize("nom_vide", ["", "   ", "\t\n"])
def test_creer_refuse_un_nom_vide(nom_vide: str) -> None:
    with pytest.raises(NomClubInvalide):
        Club.creer(nom_vide)


def test_le_club_est_immuable() -> None:
    club = Club.creer("Arc Club Rennes")

    with pytest.raises(dataclasses.FrozenInstanceError):
        club.nom = "Autre"  # type: ignore[misc]


def test_modifier_renvoie_une_copie_renommee_en_preservant_l_identifiant() -> None:
    club = dataclasses.replace(Club.creer("Arc Club Rennes"), id=7)

    renomme = club.modifier("  Arc Club de Rennes  ")

    assert renomme.nom == "Arc Club de Rennes"
    assert renomme.id == 7, "Renommer un club ne doit pas rompre le rattachement des archers."
    assert club.nom == "Arc Club Rennes", "L'agrégat d'origine reste inchangé (immuable)."


def test_modifier_refuse_un_nom_vide() -> None:
    club = dataclasses.replace(Club.creer("Arc Club Rennes"), id=7)

    with pytest.raises(NomClubInvalide):
        club.modifier("   ")


def test_un_club_n_appartient_a_aucun_tournoi() -> None:
    """Garde-fou de conception : le référentiel est global (réutilisable entre tournois).

    Ajouter un `tournoi_id` à `Club` casserait le « réutilisable entre tournois » d'E02US001
    et ferait entrer la table dans la descendance de `tournoi` (DETTE-001).
    """
    champs = {champ.name for champ in dataclasses.fields(Club)}

    assert champs == {"nom", "id"}
