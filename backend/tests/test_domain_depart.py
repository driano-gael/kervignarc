"""Tests unitaires de l'agrégat Depart (E02US004, ADR-0017 ; E02US010) — domaine pur.

Le départ est un **créneau du tournoi** : il porte un `tournoi_id`, un `numero` (attribué par le
service, le domaine vérifie seulement qu'il est ≥ 1), un `horaire` `HH:MM` **obligatoire** (24 h)
et un `tarif_centimes` **obligatoire** (`[0, 1 000 €]`, `0` = gratuit). Le lien archer↔départ
est E02US009, hors de cet agrégat.
"""

from __future__ import annotations

import pytest

from domain.depart import QUOTA_DEPART_MAX, TARIF_DEPART_MAX_CENTIMES, Depart
from domain.erreurs import (
    HoraireDepartInvalide,
    NumeroDepartInvalide,
    QuotaDepartInvalide,
    TarifDepartInvalide,
)

_HORAIRE = "09:00"
"""Horaire valide neutre pour les tests où l'horaire n'est pas le sujet (obligatoire depuis
E02US010, il doit être fourni partout)."""


def test_creer_un_depart_valide() -> None:
    """tournoi + numéro + tarif + horaire suffisent : quota à None, id à None."""
    depart = Depart.creer(tournoi_id=1, numero=1, tarif_centimes=810, horaire="09:00")
    assert depart == Depart(
        tournoi_id=1,
        numero=1,
        tarif_centimes=810,
        horaire="09:00",
        quota=None,
        id=None,
    )


# --- Horaire du créneau (E02US010) : un `HH:MM` du jour (24 h), **obligatoire** ---


def test_creer_avec_un_horaire_hhmm() -> None:
    """L'horaire est un horaire du jour `HH:MM`, conservé tel quel (24 h)."""
    depart = Depart.creer(tournoi_id=1, numero=2, tarif_centimes=810, horaire="14:00")
    assert depart.horaire == "14:00"


def test_creer_normalise_les_espaces_de_l_horaire() -> None:
    """Les espaces de bord sont retirés ; le reste doit être un `HH:MM` valide."""
    depart = Depart.creer(tournoi_id=1, numero=1, tarif_centimes=810, horaire="  09:00  ")
    assert depart.horaire == "09:00"


@pytest.mark.parametrize("horaire", ["", "   "])
def test_creer_refuse_un_horaire_vide(horaire: str) -> None:
    """L'horaire est **obligatoire** (E02US010) : vide ou blanc est refusé au domaine."""
    with pytest.raises(HoraireDepartInvalide):
        Depart.creer(tournoi_id=1, numero=1, tarif_centimes=810, horaire=horaire)


@pytest.mark.parametrize("horaire", ["9h00", "14h30", "matin", "9hzc", "9:00", "0900", "09h00"])
def test_creer_refuse_un_libelle_libre(horaire: str) -> None:
    """L'ancien libellé libre d'E02US004 (« 9h00 », « matin »…) et tout format non `HH:MM` sont
    refusés — y compris l'heure à un chiffre (« 9:00 ») : le format canonique en a deux."""
    with pytest.raises(HoraireDepartInvalide):
        Depart.creer(tournoi_id=1, numero=1, tarif_centimes=810, horaire=horaire)


@pytest.mark.parametrize("horaire", ["24:00", "25:30", "23:60", "12:99", "-1:00"])
def test_creer_refuse_une_heure_hors_du_jour(horaire: str) -> None:
    """Un `HH:MM` bien formé mais hors du jour (heure ≥ 24, minute ≥ 60) est refusé (24 h)."""
    with pytest.raises(HoraireDepartInvalide):
        Depart.creer(tournoi_id=1, numero=1, tarif_centimes=810, horaire=horaire)


@pytest.mark.parametrize("horaire", ["00:00", "23:59", "09:05", "18:45"])
def test_creer_accepte_les_horaires_valides(horaire: str) -> None:
    """Cas limites inclus : minuit `00:00` et la dernière minute `23:59`."""
    assert (
        Depart.creer(tournoi_id=1, numero=1, tarif_centimes=810, horaire=horaire).horaire == horaire
    )


@pytest.mark.parametrize("numero", [0, -1, -3])
def test_creer_refuse_un_numero_non_positif(numero: int) -> None:
    """Le numéro d'un créneau est un entier ≥ 1 (le service attribue 1, 2, 3…)."""
    with pytest.raises(NumeroDepartInvalide):
        Depart.creer(tournoi_id=1, numero=numero, tarif_centimes=810, horaire=_HORAIRE)


# --- Tarif du créneau (ADR-0017) : centimes entiers, **obligatoire**, `0` = gratuit ---


def test_creer_avec_un_tarif() -> None:
    """Le tarif est stocké tel quel, en centimes (8,10 € = 810)."""
    assert (
        Depart.creer(tournoi_id=1, numero=1, tarif_centimes=810, horaire=_HORAIRE).tarif_centimes
        == 810
    )


def test_un_tarif_nul_est_admis_gratuit() -> None:
    """`0` = **gratuit**, un choix licite. Contrairement au tarif du tournoi d'avant, il n'y a plus
    d'état « non défini » : on ne crée pas un créneau sans prix."""
    assert (
        Depart.creer(tournoi_id=1, numero=1, tarif_centimes=0, horaire=_HORAIRE).tarif_centimes == 0
    )


@pytest.mark.parametrize("tarif", [-1, -810])
def test_creer_refuse_un_tarif_negatif(tarif: int) -> None:
    with pytest.raises(TarifDepartInvalide):
        Depart.creer(tournoi_id=1, numero=1, tarif_centimes=tarif, horaire=_HORAIRE)


def test_creer_refuse_un_tarif_au_dela_du_plafond() -> None:
    """Au-delà de 1 000 € le départ, c'est une faute de frappe — pas un tarif."""
    with pytest.raises(TarifDepartInvalide):
        Depart.creer(
            tournoi_id=1, numero=1, tarif_centimes=TARIF_DEPART_MAX_CENTIMES + 1, horaire=_HORAIRE
        )


def test_le_plafond_lui_meme_est_admis() -> None:
    """Cas limite : le plafond est inclus."""
    depart = Depart.creer(
        tournoi_id=1, numero=1, tarif_centimes=TARIF_DEPART_MAX_CENTIMES, horaire=_HORAIRE
    )
    assert depart.tarif_centimes == TARIF_DEPART_MAX_CENTIMES


def test_creer_refuse_un_tarif_absurde_plutot_que_de_deborder() -> None:
    """Un entier gigantesque est refusé **par le domaine** (422), et n'atteint jamais SQLite —
    qui déborderait en erreur non typée (500) au-delà de sa capacité."""
    with pytest.raises(TarifDepartInvalide):
        Depart.creer(tournoi_id=1, numero=1, tarif_centimes=10**20, horaire=_HORAIRE)


# --- Quota du créneau (E02US006) : facultatif, entier ≥ 1, plafonné ; `None` = illimité ---


def test_creer_sans_quota_donne_un_creneau_sans_plafond() -> None:
    """Le quota est **facultatif** : absent, le créneau n'a pas de plafond (`None`)."""
    assert Depart.creer(tournoi_id=1, numero=1, tarif_centimes=810, horaire=_HORAIRE).quota is None


def test_creer_avec_un_quota() -> None:
    """Un quota défini est un entier de places, stocké tel quel."""
    assert (
        Depart.creer(tournoi_id=1, numero=1, tarif_centimes=810, horaire=_HORAIRE, quota=20).quota
        == 20
    )


def test_creer_refuse_un_quota_nul() -> None:
    """`0` est refusé : un créneau plafonné à zéro serait fermé — on le supprime, on ne le crée pas.

    C'est la distinction que `is not None` protège dans le service : `0` n'est pas « absent »."""
    with pytest.raises(QuotaDepartInvalide):
        Depart.creer(tournoi_id=1, numero=1, tarif_centimes=810, horaire=_HORAIRE, quota=0)


@pytest.mark.parametrize("quota", [-1, -20])
def test_creer_refuse_un_quota_negatif(quota: int) -> None:
    with pytest.raises(QuotaDepartInvalide):
        Depart.creer(tournoi_id=1, numero=1, tarif_centimes=810, horaire=_HORAIRE, quota=quota)


def test_creer_refuse_un_quota_au_dela_du_plafond() -> None:
    """Au-delà de 1 000 places sur un seul créneau, c'est une faute de frappe — pas un quota."""
    with pytest.raises(QuotaDepartInvalide):
        Depart.creer(
            tournoi_id=1, numero=1, tarif_centimes=810, horaire=_HORAIRE, quota=QUOTA_DEPART_MAX + 1
        )


def test_les_bornes_du_quota_sont_admises() -> None:
    """Cas limites : 1 (le plus petit quota sensé) et le plafond sont inclus."""
    assert (
        Depart.creer(tournoi_id=1, numero=1, tarif_centimes=810, horaire=_HORAIRE, quota=1).quota
        == 1
    )
    assert (
        Depart.creer(
            tournoi_id=1, numero=1, tarif_centimes=810, horaire=_HORAIRE, quota=QUOTA_DEPART_MAX
        ).quota
        == QUOTA_DEPART_MAX
    )


# --- Édition (créer/éditer/supprimer, CA) : `modifier` remplace tarif, horaire et quota ---


def test_modifier_met_a_jour_tarif_horaire_quota_et_preserve_l_identite() -> None:
    """`modifier` change tarif/horaire/quota mais conserve `id`, `tournoi_id` et surtout `numero`
    (attribué par le système, non éditable)."""
    depart = Depart(tournoi_id=3, numero=2, tarif_centimes=810, horaire="09:00", quota=20, id=7)
    modifie = depart.modifier(tarif_centimes=1250, horaire="14:00", quota=30)
    assert modifie == Depart(
        tournoi_id=3,
        numero=2,
        tarif_centimes=1250,
        horaire="14:00",
        quota=30,
        id=7,
    )


def test_modifier_sans_quota_retire_le_plafond() -> None:
    """Remplacement complet : un `quota` omis efface le plafond existant (CA E02US006). L'horaire,
    lui, reste obligatoire — l'appelant renvoie la valeur courante s'il veut la conserver."""
    depart = Depart(tournoi_id=3, numero=2, tarif_centimes=810, horaire="09:00", quota=20, id=7)
    assert depart.modifier(tarif_centimes=810, horaire="09:00").quota is None


def test_modifier_valide_le_quota() -> None:
    """`modifier` applique les mêmes bornes que `creer` au quota."""
    depart = Depart.creer(tournoi_id=1, numero=1, tarif_centimes=810, horaire=_HORAIRE, quota=20)
    with pytest.raises(QuotaDepartInvalide):
        depart.modifier(tarif_centimes=810, horaire=_HORAIRE, quota=0)


def test_modifier_est_immuable() -> None:
    """L'agrégat est gelé : `modifier` renvoie une copie, l'original n'est pas muté."""
    depart = Depart.creer(tournoi_id=1, numero=1, tarif_centimes=810, horaire=_HORAIRE)
    depart.modifier(tarif_centimes=1250, horaire="10:00")
    assert depart.tarif_centimes == 810


def test_modifier_valide_l_horaire_et_le_tarif() -> None:
    """`modifier` applique les mêmes règles que `creer` : horaire `HH:MM` et tarif dans la plage."""
    depart = Depart.creer(tournoi_id=1, numero=1, tarif_centimes=810, horaire="09:00")
    assert depart.modifier(tarif_centimes=900, horaire="  16:30  ").horaire == "16:30"
    with pytest.raises(HoraireDepartInvalide):
        depart.modifier(tarif_centimes=900, horaire="9h00")
    with pytest.raises(TarifDepartInvalide):
        depart.modifier(tarif_centimes=-1, horaire="09:00")
