"""Tests unitaires de l'entité de domaine `Inscription` (E02US009, ADR-0017).

L'agrégat est **mince** : il ne porte que les deux clés et `paye`. Les règles inter-agrégats
(même tournoi, unicité du couple) vivent dans le service et sont testées là-bas. Ici on vérifie
seulement le contrat de l'entité : création non payée, bascule de `paye`, immutabilité (règle 4).
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from domain.inscription import Inscription, date_fusionnee


def test_creer_produit_une_inscription_non_payee_et_non_persistee() -> None:
    """`creer` fixe les deux clés, `paye=False` et un `id` encore vide (posé à la persistance)."""
    inscription = Inscription.creer(archer_id=7, depart_id=3, cree_le=None)
    assert (inscription.archer_id, inscription.depart_id) == (7, 3)
    assert inscription.paye is False
    assert inscription.id is None


def test_marquer_paye_bascule_le_statut_sans_toucher_au_reste() -> None:
    """`marquer_paye(True)` renvoie une copie payée ; les clés et l'`id` sont préservés."""
    persistee = dataclasses.replace(Inscription.creer(7, 3, cree_le=None), id=42)
    paye = persistee.marquer_paye(True)
    assert paye.paye is True
    assert (paye.archer_id, paye.depart_id, paye.id) == (7, 3, 42)


def test_marquer_paye_peut_repasser_a_non_paye() -> None:
    """La bascule est réversible : repasser à non payé une inscription payée (erreur de saisie)."""
    inscription = Inscription.creer(7, 3, cree_le=None).marquer_paye(True)
    assert inscription.marquer_paye(False).paye is False


def test_inscription_est_immuable() -> None:
    """L'entité est `frozen` (règle 4) : on n'édite pas en place, on remplace."""
    inscription = Inscription.creer(7, 3, cree_le=None)
    with pytest.raises(dataclasses.FrozenInstanceError):
        inscription.paye = True  # type: ignore[misc]


def test_creer_porte_la_date_d_inscription() -> None:
    """E17US012 (A17) : l'inscription est datée à la création — c'est d'elle que la dette date."""
    quand = datetime.datetime(2026, 11, 2, 18, 0, tzinfo=datetime.UTC)
    assert Inscription.creer(7, 3, cree_le=quand).cree_le == quand


def test_une_inscription_anterieure_a_la_date_n_en_a_pas() -> None:
    """Une inscription d'avant E17US012 se relit **sans** date — jamais une date inventée."""
    assert Inscription(archer_id=7, depart_id=3).cree_le is None


def test_marquer_paye_preserve_la_date_d_inscription() -> None:
    quand = datetime.datetime(2026, 11, 2, 18, 0, tzinfo=datetime.UTC)
    assert Inscription.creer(7, 3, cree_le=quand).marquer_paye(True).cree_le == quand


# --- Fusion de deux inscriptions sur un même départ (E17US012, revue axe D) --------------------
# Une fusion d'archers ne doit pas RAJEUNIR une dette : même règle que `dater_la_dette`.

_LE_02_11 = datetime.datetime(2026, 11, 2, 18, 0, tzinfo=datetime.UTC)
_LE_20_11 = datetime.datetime(2026, 11, 20, 18, 0, tzinfo=datetime.UTC)


def test_la_fusion_garde_la_plus_ancienne_date() -> None:
    assert date_fusionnee(_LE_20_11, _LE_02_11) == _LE_02_11
    assert date_fusionnee(_LE_02_11, _LE_20_11) == _LE_02_11


def test_une_date_inconnue_l_emporte_a_la_fusion() -> None:
    """Une inscription non datée est antérieure à toute date connue : la fusion reste inconnue."""
    assert date_fusionnee(_LE_02_11, None) is None
    assert date_fusionnee(None, _LE_02_11) is None
