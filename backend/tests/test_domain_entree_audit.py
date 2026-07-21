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
from domain.erreurs import AuteurAuditInvalide, HorodatageAuditInvalide, ObjetAuditInvalide

_QUAND = datetime.datetime(2026, 3, 14, 10, 42, tzinfo=datetime.UTC)


def test_actions_auditees_sont_l_ensemble_ferme_trace() -> None:
    """Ensemble **fermé** des actes tracés : les trois d'E10US005 + `replacement` (E12US007,
    ADR-0040) + `paiement` (E08US002).

    L'enum est étendue par chaque US qui trace un nouvel acte sensible ; ce test **est** l'oracle du
    vocabulaire courant (non-régression) : validation/correction/forfait (E10US005), replacement
    (régénération massive du plan), paiement (marquage d'un règlement, simple ou groupé)."""
    assert {a.value for a in ActionAuditee} == {
        "validation",
        "correction_score",
        "forfait",
        "replacement",
        "paiement",
    }


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


def test_creer_refuse_un_horodatage_naif() -> None:
    """Un datetime **naïf** (sans fuseau) serait stocké puis relu comme de l'UTC — refus."""
    naif = datetime.datetime(2026, 3, 14, 10, 42)  # cas fautif volontairement testé (datetime naïf)
    with pytest.raises(HorodatageAuditInvalide):
        EntreeAudit.creer(
            tournoi_id=1,
            action=ActionAuditee.VALIDATION,
            auteur="DURAND Jean",
            horodatage=naif,
            objet="Série 3",
        )


def test_creer_refuse_un_horodatage_aware_non_utc() -> None:
    """Un instant aware dans un **autre fuseau** ferait mentir le journal de 2 h (murale ≠ UTC)."""
    paris = datetime.datetime(
        2026, 3, 14, 12, 42, tzinfo=datetime.timezone(datetime.timedelta(hours=2))
    )
    with pytest.raises(HorodatageAuditInvalide):
        EntreeAudit.creer(
            tournoi_id=1,
            action=ActionAuditee.VALIDATION,
            auteur="DURAND Jean",
            horodatage=paris,
            objet="Série 3",
        )


def test_creer_accepte_un_offset_zero_non_singleton_utc() -> None:
    """Le contrat est « **offset nul** », pas « la tzinfo est le singleton `datetime.UTC` ».

    Une zone à offset 0 **distincte** du singleton (ici `timezone(timedelta(0), name="UTC")`, pour
    laquelle `is datetime.UTC` vaut False) reste un instant UTC valide. Ce test verrouille
    l'intention contre un futur refactor de la garde en `tzinfo is datetime.UTC`, qui rejetterait à
    tort une horloge renvoyant une telle zone tout en passant les autres tests.
    """
    utc_bis = datetime.datetime(
        2026, 3, 14, 10, 42, tzinfo=datetime.timezone(datetime.timedelta(0), name="UTC")
    )
    entree = EntreeAudit.creer(
        tournoi_id=1,
        action=ActionAuditee.VALIDATION,
        auteur="DURAND Jean",
        horodatage=utc_bis,
        objet="Série 3",
    )

    assert entree.horodatage == utc_bis


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
