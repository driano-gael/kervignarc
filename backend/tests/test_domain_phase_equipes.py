"""Une phase oppose des équipes par un réglage d'étape (E13US004, CA 1, 4 et 8 ; ADR-0120).

Écrits **depuis le CA** (règle 9), avant le code.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from domain.bareme import BaremeQualification
from domain.deroule_etape import EtapeDeroule
from domain.duel import BaremeDuel, ModeDuel, ResolveurBaremeDuelFfta
from domain.equipe import TypeEquipe
from domain.erreurs import EquipesNonPrisesEnCharge
from domain.format_tournoi import ModelePhase
from domain.phase import (
    Phase,
    SourcePhase,
    TypePhase,
    anomalies_sequence,
    grain_par_defaut,
    vues_par_rangs,
)
from tests.conftest import identite_d_etape


def _elimination(
    ordre: int = 2,
    equipes: TypeEquipe | None = None,
    sources: tuple[SourcePhase, ...] = (),
) -> Phase:
    phase = Phase.creer(
        depart_id=1,
        ordre=ordre,
        type=TypePhase.ELIMINATION_DIRECTE,
        sources=sources,
        etape_id=identite_d_etape(ordre),
    )
    return replace(phase, equipes=equipes)


# --- CA 1 : un réglage d'étape, accepté par la seule élimination directe ---------------------


def test_une_elimination_directe_se_regle_par_equipes() -> None:
    phase = _elimination(equipes=TypeEquipe.MIXTE)

    assert phase.equipes is TypeEquipe.MIXTE


def test_sans_reglage_une_phase_reste_individuelle() -> None:
    assert _elimination().equipes is None


@pytest.mark.parametrize(
    "type_phase", [t for t in TypePhase if t is not TypePhase.ELIMINATION_DIRECTE]
)
def test_tout_autre_type_de_phase_refuse_le_reglage(type_phase: TypePhase) -> None:
    # Via l'étape, qui sait construire chaque type (barème de la qualification compris).
    qualif = type_phase is TypePhase.QUALIFICATION
    etape = EtapeDeroule(
        tournoi_id=1,
        ordre=2,
        type=type_phase,
        bareme=BaremeQualification.preset_ffta_18m() if qualif else None,
        validation=grain_par_defaut(type_phase) if qualif else None,
        equipes=TypeEquipe.STANDARD,
    )

    with pytest.raises(EquipesNonPrisesEnCharge):
        etape.verifier_instanciable()


def test_l_etape_transmet_le_reglage_a_la_phase_qu_elle_instancie() -> None:
    etape = EtapeDeroule(
        tournoi_id=1, ordre=2, type=TypePhase.ELIMINATION_DIRECTE, equipes=TypeEquipe.STANDARD
    )

    assert etape.instancier(depart_id=4).equipes is TypeEquipe.STANDARD


def test_une_etape_d_un_autre_type_n_est_pas_instanciable_par_equipes() -> None:
    etape = EtapeDeroule(tournoi_id=1, ordre=2, type=TypePhase.POULES, equipes=TypeEquipe.STANDARD)

    with pytest.raises(EquipesNonPrisesEnCharge):
        etape.verifier_instanciable()


# --- CA 8 : une phase d'équipes est un îlot (DETTE-120) --------------------------------------


def test_une_phase_d_equipes_qui_preleve_par_rangs_est_une_anomalie() -> None:
    qualification = Phase.creer(
        1, ordre=1, type=TypePhase.ELIMINATION_DIRECTE, etape_id=identite_d_etape(1)
    )
    equipes = _elimination(
        equipes=TypeEquipe.STANDARD,
        sources=(SourcePhase.par_rangs(identite_d_etape(1), 1, 16),),
    )

    anomalies = list(anomalies_sequence(vues_par_rangs([qualification, equipes])))

    assert any(isinstance(a.erreur, EquipesNonPrisesEnCharge) for a in anomalies)


def test_une_phase_qui_preleve_dans_une_phase_d_equipes_est_une_anomalie() -> None:
    equipes = _elimination(ordre=1, equipes=TypeEquipe.STANDARD)
    consolante = _elimination(ordre=2, sources=(SourcePhase.par_rangs(identite_d_etape(1), 5, 8),))

    anomalies = list(anomalies_sequence(vues_par_rangs([equipes, consolante])))

    assert [a.ordre for a in anomalies if isinstance(a.erreur, EquipesNonPrisesEnCharge)] == [2]


def test_une_phase_d_equipes_sans_source_n_est_pas_une_anomalie() -> None:
    equipes = _elimination(equipes=TypeEquipe.STANDARD)

    assert not any(
        isinstance(a.erreur, EquipesNonPrisesEnCharge)
        for a in anomalies_sequence(vues_par_rangs([equipes]))
    )


# --- CA 4 : le barème par défaut d'un duel d'équipes est le preset FFTA du type ---------------


@pytest.mark.parametrize(
    ("type_equipe", "arme", "attendu"),
    [
        (TypeEquipe.STANDARD, "Classique", BaremeDuel(ModeDuel.SETS, 4, 6, 5, 3)),
        (TypeEquipe.STANDARD, "Arc à poulies", BaremeDuel(ModeDuel.CUMUL, 4, 6, 0, 3)),
        (TypeEquipe.MIXTE, "Classique", BaremeDuel(ModeDuel.SETS, 4, 4, 5, 2)),
        (TypeEquipe.MIXTE, "Compound", BaremeDuel(ModeDuel.CUMUL, 4, 4, 0, 2)),
        (TypeEquipe.STANDARD, None, BaremeDuel(ModeDuel.SETS, 4, 6, 5, 3)),
    ],
)
def test_le_resolveur_ffta_rend_le_preset_du_type_d_equipe(
    type_equipe: TypeEquipe, arme: str | None, attendu: BaremeDuel
) -> None:
    assert ResolveurBaremeDuelFfta().bareme_equipe_pour(type_equipe, arme) == attendu


def test_le_format_transmet_le_reglage_a_l_etape_et_le_relit() -> None:
    """CA 1, versant bibliothèque : `ModelePhase` → `EtapeDeroule` → `ModelePhase`."""
    modele = ModelePhase(ordre=1, type=TypePhase.ELIMINATION_DIRECTE, equipes=TypeEquipe.MIXTE)

    etape = modele.pour_tournoi(tournoi_id=1)

    assert etape.equipes is TypeEquipe.MIXTE
    assert ModelePhase.d_etape(etape).equipes is TypeEquipe.MIXTE
