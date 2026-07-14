"""Tests unitaires de l'agrégat `Phase` (E01US009 / ADR-0011) — domaine pur, sans base."""

from __future__ import annotations

from domain.bareme import BaremeQualification
from domain.phase import Phase, StatutPhase, TypePhase


def test_qualification_cree_la_premiere_phase() -> None:
    """`qualification` crée une phase qualification, ordre 1, statut à venir, non persistée."""
    bareme = BaremeQualification.preset_ffta_18m()
    phase = Phase.qualification(tournoi_id=7, bareme=bareme)
    assert phase.tournoi_id == 7
    assert phase.ordre == 1
    assert phase.type is TypePhase.QUALIFICATION
    assert phase.statut is StatutPhase.A_VENIR
    assert phase.bareme == bareme
    assert phase.id is None


def test_avec_bareme_remplace_le_bareme_et_preserve_le_reste() -> None:
    """`avec_bareme` met à jour le barème et conserve id/tournoi/ordre/statut/type."""
    phase = Phase(
        tournoi_id=7,
        ordre=1,
        type=TypePhase.QUALIFICATION,
        bareme=BaremeQualification.creer(20, 3),
        statut=StatutPhase.A_VENIR,
        id=3,
    )
    modifiee = phase.avec_bareme(BaremeQualification.creer(10, 3))
    assert modifiee.id == 3
    assert modifiee.tournoi_id == 7
    assert modifiee.ordre == 1
    assert modifiee.type is TypePhase.QUALIFICATION
    assert modifiee.statut is StatutPhase.A_VENIR
    assert modifiee.bareme.nb_volees == 10
    # L'agrégat est gelé : l'original n'est pas muté.
    assert phase.bareme.nb_volees == 20
