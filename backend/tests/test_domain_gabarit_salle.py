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


# --- Application à un tournoi (E01US008) ---


def test_pour_tournoi_produit_une_copie_detachee() -> None:
    """`pour_tournoi` copie nom et plafonds, détache l'`id` et fixe le `tournoi_id`."""
    modele = GabaritSalle(nom="Salle municipale", capacites=(4, 4, 2), id=7)
    instance = modele.pour_tournoi(42)
    assert instance.id is None  # à persister comme une nouvelle ligne
    assert instance.tournoi_id == 42
    assert instance.nom == "Salle municipale"
    assert instance.capacites == (4, 4, 2)
    # Le modèle d'origine n'est pas muté (dataclass gelée).
    assert modele.tournoi_id is None
    assert modele.id == 7


def test_ajuster_regle_le_plafond_cible_par_cible() -> None:
    """`ajuster` fixe un plafond par cible et préserve `id`/`tournoi_id`."""
    instance = GabaritSalle(nom="Salle", capacites=(4, 4, 4, 4), id=3, tournoi_id=42)
    ajustee = instance.ajuster("Salle adaptée", (4, 2, 2, 1))
    assert ajustee.id == 3
    assert ajustee.tournoi_id == 42
    assert ajustee.nom == "Salle adaptée"
    assert ajustee.capacites == (4, 2, 2, 1)
    assert [c.positions for c in ajustee.cibles] == [
        ("A", "B", "C", "D"),
        ("A", "B"),
        ("A", "B"),
        ("A",),
    ]


def test_ajuster_peut_changer_le_nombre_de_cibles() -> None:
    """La longueur de `capacites` redéfinit le nombre de cibles."""
    instance = GabaritSalle(nom="Salle", capacites=(4, 4), id=3, tournoi_id=42)
    assert instance.ajuster("Salle", (4, 4, 4, 2, 2)).nb_cibles == 5
    assert instance.ajuster("Salle", (2,)).nb_cibles == 1


def test_ajuster_refuse_un_plafond_hors_plage() -> None:
    """Chaque plafond ajusté doit rester dans [1, 4]."""
    instance = GabaritSalle(nom="Salle", capacites=(4, 4), id=3, tournoi_id=42)
    with pytest.raises(CapaciteCibleInvalide):
        instance.ajuster("Salle", (4, 5))


def test_ajuster_refuse_zero_cible() -> None:
    """Un ajustement sans aucune cible est refusé."""
    instance = GabaritSalle(nom="Salle", capacites=(4,), id=3, tournoi_id=42)
    with pytest.raises(NombreCiblesInvalide):
        instance.ajuster("Salle", ())


def test_ajuster_normalise_le_nom() -> None:
    """Le nom est normalisé et ne peut pas être vide à l'ajustement."""
    instance = GabaritSalle(nom="Salle", capacites=(4,), id=3, tournoi_id=42)
    assert instance.ajuster("  Salle B  ", (4,)).nom == "Salle B"
    with pytest.raises(NomGabaritInvalide):
        instance.ajuster("   ", (4,))
