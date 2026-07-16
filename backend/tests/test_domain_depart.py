"""Tests unitaires de l'agrégat Depart (E02US004, ADR-0017) — domaine pur.

Le départ est un **créneau du tournoi** : il porte un `tournoi_id`, un `numero` (attribué par le
service, le domaine vérifie seulement qu'il est ≥ 1), un `horaire` facultatif et un `tarif_centimes`
**obligatoire** (`[0, 1 000 €]`, `0` = gratuit). Le lien archer↔départ est E02US009, hors de cet
agrégat.
"""

from __future__ import annotations

import pytest

from domain.depart import TARIF_DEPART_MAX_CENTIMES, Depart
from domain.erreurs import NumeroDepartInvalide, TarifDepartInvalide


def test_creer_un_depart_valide() -> None:
    """tournoi + numéro + tarif suffisent : horaire à None, id à None."""
    depart = Depart.creer(tournoi_id=1, numero=1, tarif_centimes=810)
    assert depart == Depart(
        tournoi_id=1,
        numero=1,
        tarif_centimes=810,
        horaire=None,
        id=None,
    )


def test_creer_avec_un_horaire() -> None:
    """L'horaire est un libellé de créneau, conservé tel quel (après normalisation)."""
    depart = Depart.creer(tournoi_id=1, numero=2, tarif_centimes=810, horaire="14h00")
    assert depart.horaire == "14h00"


def test_creer_normalise_l_horaire() -> None:
    """L'horaire est normalisé (espaces de bord retirés)."""
    depart = Depart.creer(tournoi_id=1, numero=1, tarif_centimes=810, horaire="  9h00  ")
    assert depart.horaire == "9h00"


def test_creer_horaire_vide_devient_none() -> None:
    """Un horaire vide ou blanc est facultatif → normalisé à None."""
    assert Depart.creer(tournoi_id=1, numero=1, tarif_centimes=810, horaire="   ").horaire is None


@pytest.mark.parametrize("numero", [0, -1, -3])
def test_creer_refuse_un_numero_non_positif(numero: int) -> None:
    """Le numéro d'un créneau est un entier ≥ 1 (le service attribue 1, 2, 3…)."""
    with pytest.raises(NumeroDepartInvalide):
        Depart.creer(tournoi_id=1, numero=numero, tarif_centimes=810)


# --- Tarif du créneau (ADR-0017) : centimes entiers, **obligatoire**, `0` = gratuit ---


def test_creer_avec_un_tarif() -> None:
    """Le tarif est stocké tel quel, en centimes (8,10 € = 810)."""
    assert Depart.creer(tournoi_id=1, numero=1, tarif_centimes=810).tarif_centimes == 810


def test_un_tarif_nul_est_admis_gratuit() -> None:
    """`0` = **gratuit**, un choix licite. Contrairement au tarif du tournoi d'avant, il n'y a plus
    d'état « non défini » : on ne crée pas un créneau sans prix."""
    assert Depart.creer(tournoi_id=1, numero=1, tarif_centimes=0).tarif_centimes == 0


@pytest.mark.parametrize("tarif", [-1, -810])
def test_creer_refuse_un_tarif_negatif(tarif: int) -> None:
    with pytest.raises(TarifDepartInvalide):
        Depart.creer(tournoi_id=1, numero=1, tarif_centimes=tarif)


def test_creer_refuse_un_tarif_au_dela_du_plafond() -> None:
    """Au-delà de 1 000 € le départ, c'est une faute de frappe — pas un tarif."""
    with pytest.raises(TarifDepartInvalide):
        Depart.creer(tournoi_id=1, numero=1, tarif_centimes=TARIF_DEPART_MAX_CENTIMES + 1)


def test_le_plafond_lui_meme_est_admis() -> None:
    """Cas limite : le plafond est inclus."""
    depart = Depart.creer(tournoi_id=1, numero=1, tarif_centimes=TARIF_DEPART_MAX_CENTIMES)
    assert depart.tarif_centimes == TARIF_DEPART_MAX_CENTIMES


def test_creer_refuse_un_tarif_absurde_plutot_que_de_deborder() -> None:
    """Un entier gigantesque est refusé **par le domaine** (422), et n'atteint jamais SQLite —
    qui déborderait en erreur non typée (500) au-delà de sa capacité."""
    with pytest.raises(TarifDepartInvalide):
        Depart.creer(tournoi_id=1, numero=1, tarif_centimes=10**20)


# --- Édition (créer/éditer/supprimer, CA) : `modifier` remplace tarif et horaire ---


def test_modifier_met_a_jour_tarif_et_horaire_et_preserve_l_identite() -> None:
    """`modifier` change tarif/horaire mais conserve `id`, `tournoi_id` et surtout `numero`
    (attribué par le système, non éditable)."""
    depart = Depart(tournoi_id=3, numero=2, tarif_centimes=810, horaire="9h00", id=7)
    modifie = depart.modifier(tarif_centimes=1250, horaire="14h00")
    assert modifie == Depart(
        tournoi_id=3,
        numero=2,
        tarif_centimes=1250,
        horaire="14h00",
        id=7,
    )


def test_modifier_est_immuable() -> None:
    """L'agrégat est gelé : `modifier` renvoie une copie, l'original n'est pas muté."""
    depart = Depart.creer(tournoi_id=1, numero=1, tarif_centimes=810)
    depart.modifier(tarif_centimes=1250, horaire=None)
    assert depart.tarif_centimes == 810


def test_modifier_normalise_l_horaire_et_valide_le_tarif() -> None:
    """`modifier` applique les mêmes règles que `creer`."""
    depart = Depart.creer(tournoi_id=1, numero=1, tarif_centimes=810, horaire="9h00")
    assert depart.modifier(tarif_centimes=900, horaire="  16h30  ").horaire == "16h30"
    with pytest.raises(TarifDepartInvalide):
        depart.modifier(tarif_centimes=-1, horaire=None)
