"""Tests unitaires de l'agrégat `Forfait` (E04US015) — abandon / disqualification.

Dérivés du **CA** de `stories/E04-saisie-scores.md` (E04US015) et d'ADR-0016/0050, **avant**
implémentation :

- un forfait est **daté**, **attribué** (déclarant non vide) et porte un **motif optionnel** ;
- il **préserve** les flèches (rien n'est détruit ici — l'agrégat ne touche pas la série) ;
- sa **nature** décide de l'effet au classement : **abandon** relègue (reste classé), **DSQ** sort
  du classement (Q2/Q3 du cadrage, reversées dans `stories/`) — testé via `exclu_du_classement` ;
- le « quand » est un instant **UTC aware** (même contrat que l'audit).
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from domain.erreurs import DeclarantForfaitInvalide, HorodatageForfaitInvalide
from domain.forfait import Forfait, NatureForfait

UTC = datetime.UTC
_QUAND = datetime.datetime(2026, 7, 27, 9, 30, tzinfo=UTC)


def _forfait(
    nature: NatureForfait = NatureForfait.ABANDON,
    declare_par: str = "Scoreur",
    motif: str | None = None,
    quand: datetime.datetime = _QUAND,
) -> Forfait:
    return Forfait.creer(
        tournoi_id=1,
        archer_id=42,
        phase_id=7,
        nature=nature,
        declare_par=declare_par,
        declare_le=quand,
        motif=motif,
    )


def test_forfait_valide_porte_qui_quand_et_phase() -> None:
    """CA : le forfait est daté, attribué et rattaché à une phase (qualif ou tableau)."""
    forfait = _forfait()
    assert (forfait.archer_id, forfait.phase_id, forfait.declare_par) == (42, 7, "Scoreur")
    assert forfait.declare_le == _QUAND
    assert forfait.id is None  # non persisté


def test_motif_optionnel_normalise_le_vide_en_none() -> None:
    """Le motif est facultatif ; un motif vide (après normalisation) vaut « non renseigné »."""
    assert _forfait(motif=None).motif is None
    assert _forfait(motif="   ").motif is None
    assert _forfait(motif="  blessure  ").motif == "blessure"


def test_declarant_vide_est_refuse() -> None:
    """CA : le forfait est **attribué** — un déclarant vide n'a pas de sens (qui a décidé ?)."""
    with pytest.raises(DeclarantForfaitInvalide):
        _forfait(declare_par="   ")


def test_horodatage_doit_etre_utc_aware() -> None:
    """Le « quand » doit être UTC aware, comme l'audit : un instant naïf ou non-UTC est refusé."""
    naif = datetime.datetime(2026, 7, 27, 9, 30)
    paris = datetime.datetime(
        2026, 7, 27, 9, 30, tzinfo=datetime.timezone(datetime.timedelta(hours=2))
    )
    with pytest.raises(HorodatageForfaitInvalide):
        _forfait(quand=naif)
    with pytest.raises(HorodatageForfaitInvalide):
        _forfait(quand=paris)


def test_abandon_reste_classe_dsq_sort_du_classement() -> None:
    """CA Q2/Q3 : l'abandon **relègue** (n'exclut pas), la DSQ **exclut** du classement."""
    assert _forfait(nature=NatureForfait.ABANDON).exclu_du_classement is False
    assert _forfait(nature=NatureForfait.DISQUALIFICATION).exclu_du_classement is True


def test_forfait_est_immuable() -> None:
    """Agrégat `frozen` : une déclaration ne se mute pas par mégarde (trace fiable)."""
    forfait = _forfait()
    with pytest.raises(dataclasses.FrozenInstanceError):
        forfait.nature = NatureForfait.DISQUALIFICATION  # type: ignore[misc]
