"""Tests unitaires de l'entité de domaine `Inscription` (E02US009, ADR-0017).

L'agrégat est **mince** : il ne porte que les deux clés et `paye`. Les règles inter-agrégats
(même tournoi, unicité du couple) vivent dans le service et sont testées là-bas. Ici on vérifie
seulement le contrat de l'entité : création non payée, bascule de `paye`, immutabilité (règle 4).
"""

from __future__ import annotations

import dataclasses

import pytest

from domain.inscription import Inscription


def test_creer_produit_une_inscription_non_payee_et_non_persistee() -> None:
    """`creer` fixe les deux clés, `paye=False` et un `id` encore vide (posé à la persistance)."""
    inscription = Inscription.creer(archer_id=7, depart_id=3)
    assert (inscription.archer_id, inscription.depart_id) == (7, 3)
    assert inscription.paye is False
    assert inscription.id is None


def test_marquer_paye_bascule_le_statut_sans_toucher_au_reste() -> None:
    """`marquer_paye(True)` renvoie une copie payée ; les clés et l'`id` sont préservés."""
    persistee = dataclasses.replace(Inscription.creer(7, 3), id=42)
    paye = persistee.marquer_paye(True)
    assert paye.paye is True
    assert (paye.archer_id, paye.depart_id, paye.id) == (7, 3, 42)


def test_marquer_paye_peut_repasser_a_non_paye() -> None:
    """La bascule est réversible : repasser à non payé une inscription payée (erreur de saisie)."""
    inscription = Inscription.creer(7, 3).marquer_paye(True)
    assert inscription.marquer_paye(False).paye is False


def test_inscription_est_immuable() -> None:
    """L'entité est `frozen` (règle 4) : on n'édite pas en place, on remplace."""
    inscription = Inscription.creer(7, 3)
    with pytest.raises(dataclasses.FrozenInstanceError):
        inscription.paye = True  # type: ignore[misc]
