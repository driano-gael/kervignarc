"""Tests unitaires de l'agrégat `Phase` (E01US009 / ADR-0011, E01US015) — domaine pur, sans base."""

from __future__ import annotations

import pytest

from domain.bareme import BaremeQualification
from domain.erreurs import CadenceValidationSuperieureAuBareme, GrainIncompatibleAvecTypePhase
from domain.grain_validation import GrainValidation, TypeGrain
from domain.phase import Phase, StatutPhase, TypePhase, grain_par_defaut


def _phase(
    bareme: BaremeQualification | None = None,
    validation: GrainValidation | None = None,
) -> Phase:
    """Une phase de qualification persistée (id=3), valeurs par défaut surchargeables."""
    return Phase(
        tournoi_id=7,
        ordre=1,
        type=TypePhase.QUALIFICATION,
        bareme=bareme or BaremeQualification.creer(20, 3),
        validation=validation or GrainValidation.fin_de_serie(),
        statut=StatutPhase.A_VENIR,
        id=3,
    )


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


def test_qualification_applique_le_preset_fin_de_serie_par_defaut() -> None:
    """Sans grain explicite, la qualification valide en fin de série (`D-11`)."""
    phase = Phase.qualification(tournoi_id=7, bareme=BaremeQualification.preset_ffta_18m())

    assert phase.validation == GrainValidation.fin_de_serie()


def test_qualification_accepte_un_grain_explicite() -> None:
    phase = Phase.qualification(
        tournoi_id=7,
        bareme=BaremeQualification.preset_ffta_18m(),
        validation=GrainValidation.toutes_les_n_volees(2),
    )

    assert phase.validation == GrainValidation.toutes_les_n_volees(2)


def test_grain_par_defaut_de_la_qualification_est_fin_de_serie() -> None:
    assert grain_par_defaut(TypePhase.QUALIFICATION) == GrainValidation.fin_de_serie()


def test_avec_bareme_remplace_le_bareme_et_preserve_le_reste() -> None:
    """`avec_bareme` met à jour le barème et conserve id/tournoi/ordre/statut/type/grain."""
    phase = _phase(bareme=BaremeQualification.creer(20, 3))
    modifiee = phase.avec_bareme(BaremeQualification.creer(10, 3))
    assert modifiee.id == 3
    assert modifiee.tournoi_id == 7
    assert modifiee.ordre == 1
    assert modifiee.type is TypePhase.QUALIFICATION
    assert modifiee.statut is StatutPhase.A_VENIR
    assert modifiee.validation == GrainValidation.fin_de_serie()
    assert modifiee.bareme.nb_volees == 10
    # L'agrégat est gelé : l'original n'est pas muté.
    assert phase.bareme.nb_volees == 20


def test_avec_validation_remplace_le_grain_et_preserve_le_reste() -> None:
    phase = _phase(validation=GrainValidation.fin_de_serie())

    modifiee = phase.avec_validation(GrainValidation.toutes_les_n_volees(4))

    assert modifiee.id == 3
    assert modifiee.tournoi_id == 7
    assert modifiee.ordre == 1
    assert modifiee.type is TypePhase.QUALIFICATION
    assert modifiee.statut is StatutPhase.A_VENIR
    assert modifiee.bareme == phase.bareme
    assert modifiee.validation == GrainValidation.toutes_les_n_volees(4)
    # L'agrégat est gelé : l'original n'est pas muté.
    assert phase.validation == GrainValidation.fin_de_serie()


def test_une_qualification_refuse_le_grain_fin_de_duel() -> None:
    """Une qualification se tire en séries : « fin de duel » n'y a pas de sens (`D-11`)."""
    with pytest.raises(GrainIncompatibleAvecTypePhase):
        Phase.qualification(
            tournoi_id=7,
            bareme=BaremeQualification.preset_ffta_18m(),
            validation=GrainValidation.fin_de_duel(),
        )


def test_avec_validation_refuse_un_grain_hors_du_type_de_phase() -> None:
    with pytest.raises(GrainIncompatibleAvecTypePhase):
        _phase().avec_validation(GrainValidation.fin_de_duel())


def test_une_cadence_superieure_au_bareme_est_refusee() -> None:
    """Valider toutes les 30 volées sur un barème de 20, c'est ne jamais valider."""
    with pytest.raises(CadenceValidationSuperieureAuBareme):
        _phase(
            bareme=BaremeQualification.creer(20, 3),
            validation=GrainValidation.toutes_les_n_volees(30),
        )


def test_une_cadence_egale_au_bareme_est_admise() -> None:
    """Cas limite : valider toutes les 20 volées d'un barème de 20 = une validation, à la fin."""
    phase = _phase(
        bareme=BaremeQualification.creer(20, 3),
        validation=GrainValidation.toutes_les_n_volees(20),
    )

    assert phase.validation.n_volees == 20


def test_reduire_le_bareme_sous_la_cadence_en_place_est_refuse() -> None:
    """Le barème et le grain vivent sur la même phase : leur cohérence se vérifie des deux côtés.

    Conséquence assumée (E01US015) : l'endpoint barème (E01US009) peut désormais refuser une
    réduction — l'admin doit d'abord élargir son grain.
    """
    phase = _phase(
        bareme=BaremeQualification.creer(20, 3),
        validation=GrainValidation.toutes_les_n_volees(10),
    )

    with pytest.raises(CadenceValidationSuperieureAuBareme):
        phase.avec_bareme(BaremeQualification.creer(5, 3))


def test_reduire_le_bareme_sous_un_grain_de_fin_reste_possible() -> None:
    """Un grain de fin n'a pas de cadence : aucun couplage avec le barème."""
    phase = _phase(
        bareme=BaremeQualification.creer(20, 3),
        validation=GrainValidation.fin_de_serie(),
    )

    modifiee = phase.avec_bareme(BaremeQualification.creer(5, 3))

    assert modifiee.bareme.nb_volees == 5


def test_le_grain_fin_de_duel_reste_declare_pour_le_moteur() -> None:
    """`FIN_DE_DUEL` existe dans le domaine (choix cible, `D-11`) même si aucune phase actuelle ne
    l'accepte : EPIC-05 introduira les phases à duels, dont il sera le preset."""
    assert TypeGrain.FIN_DE_DUEL.value == "fin_de_duel"
