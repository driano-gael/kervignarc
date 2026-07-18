"""Tests de l'agrégat `Poste` (E04US001) — écrits **depuis le CA/ADR-0029** (règle 9).

Le `Poste` est le **credential d'une cible** d'un tournoi : le couple `(tournoi_id, cible_index)`
plus un `code` distribuable. Le domaine ne garantit que ses **invariants de construction** — cible
strictement positive, code non vide, code sous forme canonique. L'unicité du code et sa génération
sont des règles d'**ensemble** (service + `UNIQUE` en base), testées ailleurs.
"""

from __future__ import annotations

import pytest

from domain.erreurs import CibleInvalide, CodePosteInvalide
from domain.poste import Poste, normaliser_code


def test_creer_construit_un_poste_valide() -> None:
    poste = Poste.creer(tournoi_id=7, cible_index=12, code="AB12CD")

    assert poste.id is None
    assert poste.tournoi_id == 7
    assert poste.cible_index == 12
    assert poste.code == "AB12CD"


def test_creer_normalise_le_code() -> None:
    """Le code est stocké sous forme canonique (majuscules, espaces de bord retirés)."""
    poste = Poste.creer(tournoi_id=1, cible_index=1, code="  ab12cd ")

    assert poste.code == "AB12CD"


def test_creer_refuse_une_cible_non_positive() -> None:
    with pytest.raises(CibleInvalide):
        Poste.creer(tournoi_id=1, cible_index=0, code="AB12CD")


def test_creer_refuse_un_code_vide() -> None:
    """Le code est **généré** (jamais saisi ici) : cette garde protège l'invariant de l'agrégat."""
    with pytest.raises(CodePosteInvalide):
        Poste.creer(tournoi_id=1, cible_index=1, code="   ")


def test_normaliser_code_replie_casse_et_espaces() -> None:
    assert normaliser_code("  ab12cd ") == "AB12CD"
    assert normaliser_code("AB12CD") == "AB12CD"
