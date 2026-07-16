"""Tests unitaires des agrégats Archer et Score (E00US011, E02US002, E02US003) — sans base."""

from __future__ import annotations

import pytest

from domain.archer import Archer, cle_identite
from domain.erreurs import (
    CibleInvalide,
    NomArcherInvalide,
    PrenomArcherInvalide,
    ScoreInvalide,
)
from domain.score import Score


def test_creer_un_archer_valide() -> None:
    """Un archer valide est non persisté, non placé et sans club (cible, club_id et id à None)."""
    archer = Archer.creer("Robin", "Jean", tournoi_id=1, categorie_id=5)
    assert archer == Archer(
        nom="Robin", prenom="Jean", tournoi_id=1, categorie_id=5, cible=None, club_id=None, id=None
    )


def test_creer_normalise_les_espaces() -> None:
    """Le nom et le prénom d'archer sont normalisés (espaces de bord retirés)."""
    archer = Archer.creer("  Marion  ", "  Lise  ", tournoi_id=1, categorie_id=5)
    assert (archer.nom, archer.prenom) == ("Marion", "Lise")


@pytest.mark.parametrize("nom", ["", "   ", "\t\n"])
def test_creer_refuse_un_nom_vide(nom: str) -> None:
    """Un nom vide ou blanc lève une erreur de domaine typée."""
    with pytest.raises(NomArcherInvalide):
        Archer.creer(nom, "Jean", tournoi_id=1, categorie_id=5)


@pytest.mark.parametrize("prenom", ["", "   ", "\t\n"])
def test_creer_refuse_un_prenom_vide(prenom: str) -> None:
    """Un prénom vide ou blanc lève une erreur de domaine typée (E02US002 : CA « prénom »)."""
    with pytest.raises(PrenomArcherInvalide):
        Archer.creer("Robin", prenom, tournoi_id=1, categorie_id=5)


def test_creer_rattache_le_club_quand_il_est_fourni() -> None:
    """Le club reste **facultatif** (E02US002) : fourni, il est porté par l'archer."""
    archer = Archer.creer("Robin", "Jean", tournoi_id=1, categorie_id=5, club_id=3)
    assert archer.club_id == 3


def test_placer_pose_la_cible_sans_muter_l_original() -> None:
    """`placer` renvoie une copie placée ; l'agrégat d'origine reste inchangé (immuable)."""
    archer = Archer(nom="Robin", prenom="Jean", tournoi_id=1, categorie_id=5, id=7)
    place = archer.placer(3)
    assert place == Archer(nom="Robin", prenom="Jean", tournoi_id=1, categorie_id=5, cible=3, id=7)
    assert archer.cible is None


@pytest.mark.parametrize("cible", [0, -1])
def test_placer_refuse_une_cible_non_positive(cible: int) -> None:
    """Un numéro de cible non strictement positif lève une erreur de domaine typée."""
    with pytest.raises(CibleInvalide):
        Archer(nom="Robin", prenom="Jean", tournoi_id=1, categorie_id=5, id=7).placer(cible)


def test_modifier_remplace_les_quatre_champs_sans_muter_l_original() -> None:
    """`modifier` renvoie une copie éditée ; l'agrégat d'origine reste inchangé (immuable)."""
    archer = Archer(nom="Robin", prenom="Jean", tournoi_id=1, categorie_id=5, club_id=3, id=7)
    edite = archer.modifier(nom="Robin des Bois", prenom="Jeanne", categorie_id=6, club_id=4)
    assert edite == Archer(
        nom="Robin des Bois", prenom="Jeanne", tournoi_id=1, categorie_id=6, club_id=4, id=7
    )
    assert archer.nom == "Robin"


def test_modifier_preserve_le_tournoi_l_identifiant_et_le_placement() -> None:
    """Corriger l'état civil d'un archer ne le déplace pas et ne le sort pas de son tournoi.

    E02US003 : les champs éditables sont le nom, le prénom, la catégorie et le club — `cible`,
    `tournoi_id` et `id` n'en sont pas et doivent traverser l'édition intacts.
    """
    place = Archer(nom="Robin", prenom="Jean", tournoi_id=1, categorie_id=5, cible=3, id=7)
    edite = place.modifier(nom="Robin", prenom="Jeanne", categorie_id=5, club_id=None)
    assert (edite.cible, edite.tournoi_id, edite.id) == (3, 1, 7)


def test_modifier_normalise_les_espaces() -> None:
    """Le nom et le prénom édités sont normalisés, comme à la création."""
    archer = Archer(nom="Robin", prenom="Jean", tournoi_id=1, categorie_id=5, id=7)
    edite = archer.modifier(nom="  Marion  ", prenom="  Lise  ", categorie_id=5, club_id=None)
    assert (edite.nom, edite.prenom) == ("Marion", "Lise")


@pytest.mark.parametrize("nom", ["", "   ", "\t\n"])
def test_modifier_refuse_un_nom_vide(nom: str) -> None:
    """L'édition rejoue les contrôles de la création : un nom vide reste refusé (E02US003)."""
    archer = Archer(nom="Robin", prenom="Jean", tournoi_id=1, categorie_id=5, id=7)
    with pytest.raises(NomArcherInvalide):
        archer.modifier(nom=nom, prenom="Jean", categorie_id=5, club_id=None)


@pytest.mark.parametrize("prenom", ["", "   ", "\t\n"])
def test_modifier_refuse_un_prenom_vide(prenom: str) -> None:
    """L'édition rejoue les contrôles de la création : un prénom vide reste refusé (E02US003)."""
    archer = Archer(nom="Robin", prenom="Jean", tournoi_id=1, categorie_id=5, id=7)
    with pytest.raises(PrenomArcherInvalide):
        archer.modifier(nom="Robin", prenom=prenom, categorie_id=5, club_id=None)


def test_modifier_detache_le_club() -> None:
    """`club_id=None` **détache** le club au lieu de le laisser en place (E02US003).

    L'écran d'administration propose « Club inconnu » : le choisir doit ramener l'archer à
    l'état « club pas encore su » (ADR-0014). Si `modifier` traitait `None` comme « ne change
    rien », ce choix serait silencieusement sans effet.
    """
    archer = Archer(nom="Robin", prenom="Jean", tournoi_id=1, categorie_id=5, club_id=3, id=7)
    assert archer.modifier(nom="Robin", prenom="Jean", categorie_id=5, club_id=None).club_id is None


def test_cle_identite_replie_la_casse_et_les_accents() -> None:
    """« Lefèvre Rémi » et « LEFEVRE remi » du même club désignent le même archer (E02US002)."""
    assert cle_identite("Lefèvre", "Rémi", 2) == cle_identite("  LEFEVRE ", "remi", 2)


def test_cle_identite_distingue_deux_clubs() -> None:
    """Deux homonymes de clubs différents sont deux archers distincts, pas un doublon."""
    assert cle_identite("Dupont", "Jean", 1) != cle_identite("Dupont", "Jean", 2)


def test_cle_identite_ne_confond_pas_deux_archers_sans_club() -> None:
    """Sans club, la clé reste discriminante sur le nom et le prénom (E02US002)."""
    assert cle_identite("Dupont", "Jean", None) == cle_identite("dupont", "jean", None)
    assert cle_identite("Dupont", "Jean", None) != cle_identite("Dupont", "Paul", None)


def test_cle_identite_separe_club_connu_et_club_inconnu() -> None:
    """Un archer **sans club** n'est pas l'homonyme d'un archer rattaché (`NULL` = inconnu).

    Le rapprochement des deux (« c'est sans doute le même, complété depuis ») relève de
    E02US005 (détecter et fusionner les doublons), pas du refus à la saisie.
    """
    assert cle_identite("Dupont", "Jean", None) != cle_identite("Dupont", "Jean", 1)


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
