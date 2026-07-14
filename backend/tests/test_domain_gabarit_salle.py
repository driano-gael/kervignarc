"""Tests unitaires de l'agrégat GabaritSalle (E01US007) — domaine pur, sans base."""

from __future__ import annotations

import pytest

from domain.erreurs import (
    CapaciteCibleInvalide,
    NombreCiblesInvalide,
    NomGabaritInvalide,
)
from domain.gabarit_salle import GabaritSalle


def test_creer_gabarit_uniforme_par_defaut() -> None:
    """Sans plafond précisé, toutes les cibles sont à 4 (positions A/B/C/D)."""
    gabarit = GabaritSalle.creer("Salle A", 3)
    assert gabarit.nom == "Salle A"
    assert gabarit.nb_cibles == 3
    assert gabarit.capacites == (4, 4, 4)
    assert gabarit.id is None


def test_cibles_sont_numerotees_et_portent_leurs_positions() -> None:
    """Les cibles sont numérotées à partir de 1 ; les positions dérivent du plafond."""
    cibles = GabaritSalle.creer("Salle", 2, 2).cibles
    assert [c.index for c in cibles] == [1, 2]
    assert cibles[0].capacite == 2
    assert cibles[0].positions == ("A", "B")


@pytest.mark.parametrize(
    ("capacite", "positions"),
    [(1, ("A",)), (2, ("A", "B")), (3, ("A", "B", "C")), (4, ("A", "B", "C", "D"))],
)
def test_positions_deduites_du_plafond(capacite: int, positions: tuple[str, ...]) -> None:
    """Le plafond détermine les positions occupables (les N premières lettres)."""
    cible = GabaritSalle.creer("Salle", 1, capacite).cibles[0]
    assert cible.positions == positions


def test_creer_normalise_le_nom() -> None:
    """Le nom est normalisé (espaces de bord retirés)."""
    assert GabaritSalle.creer("  Salle B  ", 1).nom == "Salle B"


@pytest.mark.parametrize("nom", ["", "   ", "\t\n"])
def test_creer_refuse_un_nom_vide(nom: str) -> None:
    """Un nom vide ou blanc lève une erreur de domaine typée."""
    with pytest.raises(NomGabaritInvalide):
        GabaritSalle.creer(nom, 1)


@pytest.mark.parametrize("nb_cibles", [0, -1])
def test_creer_refuse_moins_d_une_cible(nb_cibles: int) -> None:
    """Un gabarit doit compter au moins une cible."""
    with pytest.raises(NombreCiblesInvalide):
        GabaritSalle.creer("Salle", nb_cibles)


@pytest.mark.parametrize("capacite", [0, 5, -1])
def test_creer_refuse_un_plafond_hors_plage(capacite: int) -> None:
    """Le plafond d'archers d'une cible doit rester dans [1, 4]."""
    with pytest.raises(CapaciteCibleInvalide):
        GabaritSalle.creer("Salle", 1, capacite)


def test_modifier_change_les_attributs_et_preserve_id() -> None:
    """`modifier` met à jour nom/nb cibles/plafond mais conserve l'identifiant."""
    gabarit = GabaritSalle(nom="Ancien", capacites=(4, 4), id=7)
    modifie = gabarit.modifier("Nouveau", 3, 2)
    assert modifie.id == 7
    assert modifie.nom == "Nouveau"
    assert modifie.capacites == (2, 2, 2)


def test_modifier_valide_les_attributs() -> None:
    """`modifier` applique les mêmes règles que `creer`."""
    gabarit = GabaritSalle.creer("Salle", 1)
    with pytest.raises(CapaciteCibleInvalide):
        gabarit.modifier("Salle", 1, 9)
