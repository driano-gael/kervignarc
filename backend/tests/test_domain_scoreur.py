"""Tests de l'agrégat `Scoreur` (E10US003) — règles portées par le domaine, sans infrastructure.

Écrits **depuis le CA** (règle 9) : nom non vide, code normalisé et préservé à l'édition. L'unicité
du code et sa **génération** ne sont **pas** ici : le domaine ne voit qu'un scoreur à la fois, ces
règles d'ensemble vivent dans `ServiceScoreurs` (cf. `test_service_scoreurs`).
"""

from __future__ import annotations

import pytest

from domain.erreurs import CodeScoreurInvalide, NomScoreurInvalide
from domain.scoreur import Scoreur, normaliser_code


def test_creer_un_scoreur_valide() -> None:
    scoreur = Scoreur.creer(tournoi_id=1, nom="Camille Dubois", code="AB12CD")

    assert scoreur.id is None
    assert scoreur.tournoi_id == 1
    assert scoreur.nom == "Camille Dubois"
    assert scoreur.code == "AB12CD"


def test_creer_normalise_le_nom() -> None:
    scoreur = Scoreur.creer(tournoi_id=1, nom="  Camille Dubois  ", code="AB12CD")

    assert scoreur.nom == "Camille Dubois"


def test_creer_refuse_un_nom_vide() -> None:
    with pytest.raises(NomScoreurInvalide):
        Scoreur.creer(tournoi_id=1, nom="   ", code="AB12CD")


def test_creer_normalise_le_code_en_majuscules() -> None:
    """Le code stocké est canonique : c'est ce qui rend la saisie tolérante à la casse."""
    scoreur = Scoreur.creer(tournoi_id=1, nom="Camille", code="  ab12cd  ")

    assert scoreur.code == "AB12CD"


def test_creer_refuse_un_code_vide() -> None:
    with pytest.raises(CodeScoreurInvalide):
        Scoreur.creer(tournoi_id=1, nom="Camille", code="   ")


def test_modifier_renomme_en_preservant_le_code_et_le_tournoi() -> None:
    """Le code est imprimé et distribué : l'édition ne touche que le nom (comme `Depart.numero`)."""
    scoreur = Scoreur(tournoi_id=1, nom="Camile", code="AB12CD", id=7)

    corrige = scoreur.modifier(nom="Camille Dubois")

    assert corrige.id == 7
    assert corrige.tournoi_id == 1
    assert corrige.code == "AB12CD"
    assert corrige.nom == "Camille Dubois"


def test_modifier_refuse_un_nom_vide() -> None:
    scoreur = Scoreur(tournoi_id=1, nom="Camille", code="AB12CD", id=7)

    with pytest.raises(NomScoreurInvalide):
        scoreur.modifier(nom="  ")


def test_scoreur_est_immuable() -> None:
    """Agrégat `frozen` : une affectation d'attribut lève, l'édition passe par une copie."""
    scoreur = Scoreur.creer(tournoi_id=1, nom="Camille", code="AB12CD")

    with pytest.raises(AttributeError):
        scoreur.nom = "Autre"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("saisie", "attendu"),
    [
        ("ab12cd", "AB12CD"),
        ("  AB12CD  ", "AB12CD"),
        ("Ab12Cd", "AB12CD"),
    ],
)
def test_normaliser_code_replie_casse_et_espaces(saisie: str, attendu: str) -> None:
    """La forme canonique d'un code : deux saisies de même forme ouvrent la même session."""
    assert normaliser_code(saisie) == attendu
