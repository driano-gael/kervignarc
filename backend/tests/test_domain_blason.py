"""Tests unitaires de l'agrégat Blason (E01US005, zones : E01US014) — domaine pur, sans base."""

from __future__ import annotations

import pytest

from domain.blason import ZONES_DEFAUT, Blason
from domain.erreurs import (
    CapaciteBlasonInvalide,
    NomBlasonInvalide,
    TailleBlasonInvalide,
    ZonesBlasonInvalides,
)


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


# --- Zones : valeurs de score admises (E01US014) --------------------------------------------
#
# Tests dérivés du CA d'E01US014 (`stories/E01-configuration.md`) et du référentiel FFTA
# (§4.2 vocabulaire des zones, §4.4 le triple 40 s'arrête à 6), écrits avant l'implémentation.


def test_creer_sans_zones_applique_le_blason_simple_complet() -> None:
    """CA « valeur par défaut cohérente » : le jeu FFTA complet d'un blason simple (§4.2).

    Le domaine ne peut pas déduire le type de blason : `taille` est une **fraction de place**,
    pas un diamètre. Le défaut est donc le sur-ensemble, que l'admin restreint pour un triple.
    """
    assert ZONES_DEFAUT == ("10", "9", "8", "7", "6", "5", "4", "3", "2", "1", "M")
    assert Blason.creer(1, "Monospot 60", 1.0, 1).zones == ZONES_DEFAUT


def test_creer_accepte_les_zones_d_un_triple_40() -> None:
    """Le cas qui motive l'US : un triple 40 n'a pas les zones 5 → 1, son minimum est 6 (§4.4)."""
    blason = Blason.creer(1, "Trispot 40", 0.5, 3, zones=["10", "9", "8", "7", "6", "M"])
    assert blason.zones == ("10", "9", "8", "7", "6", "M")


def test_les_zones_sont_immuables() -> None:
    """Agrégat `frozen` (règle 4) : les zones sont un tuple, pas une liste partagée."""
    saisie = ["10", "9", "M"]
    blason = Blason.creer(1, "Blason", 0.5, 1, zones=saisie)
    saisie.append("8")
    assert blason.zones == ("10", "9", "M")


def test_creer_normalise_l_ordre_des_zones() -> None:
    """L'ordre saisi ne porte pas d'information : seul l'ensemble compte, l'ordre est canonique."""
    blason = Blason.creer(1, "Trispot 40", 0.5, 3, zones=["M", "6", "9", "10", "7", "8"])
    assert blason.zones == ("10", "9", "8", "7", "6", "M")


@pytest.mark.parametrize(
    "zones", [["10", "9", "X", "M"], ["11", "10", "M"], ["dix", "M"], ["10", "", "M"]]
)
def test_creer_refuse_une_zone_hors_vocabulaire(zones: list[str]) -> None:
    """Le vocabulaire est celui du référentiel §4.2 : 10 → 1 et M.

    Ce n'est pas une vérification de conformité FFTA (RG-8 l'interdit) : c'est une contrainte
    d'intégrité aval — EPIC-04 doit **sommer** ces valeurs, un jeton inconnu n'a pas de sens.
    """
    with pytest.raises(ZonesBlasonInvalides):
        Blason.creer(1, "Blason", 0.5, 1, zones=zones)


def test_creer_refuse_un_doublon() -> None:
    """Une même zone ne peut pas être admise deux fois."""
    with pytest.raises(ZonesBlasonInvalides):
        Blason.creer(1, "Blason", 0.5, 1, zones=["10", "9", "9", "M"])


def test_creer_refuse_des_zones_sans_manque() -> None:
    """`M` est obligatoire : un manqué est toujours possible, le scoreur doit pouvoir le saisir."""
    with pytest.raises(ZonesBlasonInvalides):
        Blason.creer(1, "Blason", 0.5, 1, zones=["10", "9", "8"])


@pytest.mark.parametrize("zones", [[], ["M"]])
def test_creer_refuse_des_zones_sans_valeur_marquante(zones: list[str]) -> None:
    """Un blason sans aucune zone marquante n'existe pas."""
    with pytest.raises(ZonesBlasonInvalides):
        Blason.creer(1, "Blason", 0.5, 1, zones=zones)


def test_creer_admet_un_jeu_non_contigu() -> None:
    """RG-8 : l'app **n'impose pas** la conformité au règlement.

    Un jeu troué n'existe sur aucun blason FFTA, mais l'interdire reviendrait à vérifier la
    conformité — ce que RG-8 exclut. Le CA veut restreindre la saisie, pas normer le carton.
    """
    blason = Blason.creer(1, "Exotique", 0.5, 1, zones=["10", "8", "M"])
    assert blason.zones == ("10", "8", "M")


def test_modifier_met_a_jour_les_zones() -> None:
    """CA « modifiable comme le reste du blason » (RG-8) : les zones s'éditent comme le nom."""
    blason = Blason.creer(1, "Trispot 40", 0.5, 3)
    modifie = blason.modifier("Trispot 40", 0.5, 3, zones=["10", "9", "8", "7", "6", "M"])
    assert modifie.zones == ("10", "9", "8", "7", "6", "M")


def test_modifier_valide_les_zones() -> None:
    """`modifier` applique les mêmes règles de zones que `creer`."""
    blason = Blason.creer(1, "Blason", 0.5, 2)
    with pytest.raises(ZonesBlasonInvalides):
        blason.modifier("Blason", 0.5, 2, zones=["10", "9"])
