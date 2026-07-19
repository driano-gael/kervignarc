"""Tests de l'agrégat `EntreeAudit` (E10US005) — écrits **depuis le CA** (règle 9).

CA : « `AuditLog` des corrections de score, validations, forfaits (**qui / quand / avant-après**) ».
On y vérifie ce qui est propre à l'agrégat : les trois natures d'action du CA, les invariants
« qui » (`auteur`) et « objet » non vides, le caractère **optionnel** de « avant-après » (une
validation n'en a pas), et l'immuabilité (une trace ne se retouche pas).

L'horodatage (« quand ») est **fourni** à l'agrégat (le domaine ne lit pas l'horloge : port
`Horloge`, testé côté service/infra) : ici on l'injecte, figé.
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from domain.entree_audit import ActionAuditee, EntreeAudit
from domain.erreurs import AuteurAuditInvalide, ObjetAuditInvalide

_QUAND = datetime.datetime(2026, 3, 14, 10, 42, tzinfo=datetime.UTC)


def test_actions_auditees_sont_les_trois_du_ca() -> None:
    """Le CA énumère un ensemble **fermé** : corrections de score, validations, forfaits."""
    assert {a.value for a in ActionAuditee} == {"validation", "correction_score", "forfait"}


def test_creer_une_validation_sans_avant_apres() -> None:
    """Une **validation** est un évènement : elle n'a ni « avant » ni « après » (défaut `None`)."""
    entree = EntreeAudit.creer(
        tournoi_id=1,
        action=ActionAuditee.VALIDATION,
        auteur="DURAND Jean",
        horodatage=_QUAND,
        objet="Série 3 — cible 4A — MARTIN Claire",
    )

    assert entree.id is None
    assert entree.tournoi_id == 1
    assert entree.action is ActionAuditee.VALIDATION
    assert entree.auteur == "DURAND Jean"
    assert entree.horodatage == _QUAND
    assert entree.objet == "Série 3 — cible 4A — MARTIN Claire"
    assert entree.avant is None
    assert entree.apres is None


def test_creer_une_correction_porte_avant_et_apres() -> None:
    """Une **correction** renseigne l'ancienne et la nouvelle valeur (« avant / après »)."""
    entree = EntreeAudit.creer(
        tournoi_id=1,
        action=ActionAuditee.CORRECTION_SCORE,
        auteur="ROUX Sophie",
        horodatage=_QUAND,
        objet="Série 3, flèche 2 — cible 4A — MARTIN Claire",
        avant="8",
        apres="9",
    )

    assert entree.action is ActionAuditee.CORRECTION_SCORE
    assert entree.avant == "8"
    assert entree.apres == "9"


def test_creer_normalise_auteur_et_objet() -> None:
    """Espaces de bord retirés sur « qui » et « objet »."""
    entree = EntreeAudit.creer(
        tournoi_id=1,
        action=ActionAuditee.VALIDATION,
        auteur="  DURAND Jean  ",
        horodatage=_QUAND,
        objet="  Série 3  ",
    )

    assert entree.auteur == "DURAND Jean"
    assert entree.objet == "Série 3"


@pytest.mark.parametrize("auteur", ["", "   "])
def test_creer_refuse_un_auteur_vide(auteur: str) -> None:
    """Sans « qui », la trace manque sa raison d'être en litige → `AuteurAuditInvalide`."""
    with pytest.raises(AuteurAuditInvalide):
        EntreeAudit.creer(
            tournoi_id=1,
            action=ActionAuditee.VALIDATION,
            auteur=auteur,
            horodatage=_QUAND,
            objet="Série 3",
        )


@pytest.mark.parametrize("objet", ["", "   "])
def test_creer_refuse_un_objet_vide(objet: str) -> None:
    """Sans « objet », une validation (ni avant ni après) ne se rattache à rien → refus."""
    with pytest.raises(ObjetAuditInvalide):
        EntreeAudit.creer(
            tournoi_id=1,
            action=ActionAuditee.VALIDATION,
            auteur="DURAND Jean",
            horodatage=_QUAND,
            objet=objet,
        )


def test_entree_est_immuable() -> None:
    """Une trace en **ajout seul** ne se retouche pas : l'agrégat est `frozen`."""
    entree = EntreeAudit.creer(
        tournoi_id=1,
        action=ActionAuditee.VALIDATION,
        auteur="DURAND Jean",
        horodatage=_QUAND,
        objet="Série 3",
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        entree.auteur = "AUTRE"  # type: ignore[misc]
