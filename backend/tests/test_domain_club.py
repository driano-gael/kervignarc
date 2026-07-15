"""Tests de l'agrégat `Club` (E02US001) — domaine pur, sans base ni serveur."""

from __future__ import annotations

import dataclasses

import pytest

from domain.club import Club, cle_nom
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

    # `setattr` plutôt qu'une affectation directe : mypy refuserait l'affectation sur une dataclass
    # gelée, ce qui imposerait un `type: ignore` — le backend n'en compte aucun, gardons-le ainsi
    # (même parti que `test_domain_grain_validation`).
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(club, "nom", "Autre")  # noqa: B010


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


@pytest.mark.parametrize(
    ("gauche", "droite"),
    [
        ("Arc Club Rennes", "arc club rennes"),  # casse
        ("Arc Club Rennes", "  Arc Club Rennes  "),  # espaces de bord
        ("Élan de Fougères", "élan de fougères"),  # casse d'une lettre accentuée
        ("Élan de Fougères", "Elan de Fougeres"),  # accents absents (saisie tablette)
        ("Élan de Fougères", "ELAN DE FOUGERES"),  # les deux à la fois
    ],
)
def test_cle_nom_replie_casse_accents_et_espaces(gauche: str, droite: str) -> None:
    """Deux noms de même clé désignent le même club (E02US001)."""
    assert cle_nom(gauche) == cle_nom(droite)


@pytest.mark.parametrize(
    ("gauche", "droite"),
    [
        ("Arc Club Rennes", "Arc Club Vitré"),
        ("Élan de Fougères", "Éveil de Fougères"),
        ("Arc Club Rennes", "ArcClubRennes"),  # les espaces internes restent significatifs
    ],
)
def test_cle_nom_distingue_des_clubs_differents(gauche: str, droite: str) -> None:
    assert cle_nom(gauche) != cle_nom(droite)


def test_cle_nom_ordonne_les_accentues_a_leur_place_alphabetique() -> None:
    """Un tri sur le nom brut classerait « Élan » (U+00C9) après « Zénith » : pas la clé."""
    noms = ["Zénith Archerie", "Élan de Fougères", "Arc Club Rennes", "Bretagne Archerie"]

    assert sorted(noms, key=cle_nom) == [
        "Arc Club Rennes",
        "Bretagne Archerie",
        "Élan de Fougères",
        "Zénith Archerie",
    ]


def test_un_club_n_appartient_a_aucun_tournoi() -> None:
    """Garde-fou de conception : le référentiel est global (réutilisable entre tournois).

    Ajouter un `tournoi_id` à `Club` casserait le « réutilisable entre tournois » d'E02US001
    et ferait entrer la table dans la descendance de `tournoi` (DETTE-001).
    """
    champs = {champ.name for champ in dataclasses.fields(Club)}

    assert champs == {"nom", "id"}
