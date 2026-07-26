"""Tests du service applicatif Phases (E05US001) — repositories factices en mémoire.

Le service est testé **en isolation** : de faux repositories conformes aux ports
`TournoiRepository` / `PhaseRepository` suffisent (ni base ni serveur). Les assertions dérivent du
CA d'E05US001 (composer / éditer / ordonner / supprimer, cycle de vie, cohérence) et d'ADR-0045.
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.erreurs import (
    PhaseIntrouvable,
    PhaseSourceReferencee,
    ReordonnancementPhasesInvalide,
    TournoiIntrouvable,
    TransitionStatutInvalide,
)
from application.phases import ServicePhases
from domain.erreurs import EffectifIncompatible, SourceApresPhase
from domain.phase import Phase, PhaseId, SourcePhase, StatutPhase, TypePhase
from domain.tournoi import Tournoi, TournoiId, TypeTournoi

_DATE = datetime.date(2026, 3, 14)


class FauxTournoiRepository:
    def __init__(self) -> None:
        self._tournois: dict[int, Tournoi] = {}
        self._sequence = 0

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        self._sequence += 1
        persiste = dataclasses.replace(tournoi, id=self._sequence)
        self._tournois[self._sequence] = persiste
        return persiste

    def par_id(self, tournoi_id: TournoiId) -> Tournoi | None:
        return self._tournois.get(tournoi_id)

    def lister(self) -> list[Tournoi]:
        return list(self._tournois.values())

    def enregistrer(self, tournoi: Tournoi) -> Tournoi:
        assert tournoi.id is not None
        self._tournois[tournoi.id] = tournoi
        return tournoi

    def supprimer(self, tournoi_id: TournoiId) -> None:
        del self._tournois[tournoi_id]


class FauxPhaseRepository:
    def __init__(self) -> None:
        self._phases: dict[int, Phase] = {}
        self._sequence = 0

    def ajouter(self, phase: Phase) -> Phase:
        self._sequence += 1
        persiste = dataclasses.replace(phase, id=self._sequence)
        self._phases[self._sequence] = persiste
        return persiste

    def par_id(self, phase_id: PhaseId) -> Phase | None:
        return self._phases.get(phase_id)

    def par_tournoi_et_type(self, tournoi_id: TournoiId, type_phase: TypePhase) -> Phase | None:
        trouvees = [
            p for p in self._phases.values() if p.tournoi_id == tournoi_id and p.type is type_phase
        ]
        return trouvees[-1] if trouvees else None

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Phase]:
        phases = [p for p in self._phases.values() if p.tournoi_id == tournoi_id]
        return sorted(phases, key=lambda p: p.ordre)

    def enregistrer(self, phase: Phase) -> Phase:
        assert phase.id in self._phases
        self._phases[phase.id] = phase
        return phase

    def supprimer(self, phase_id: PhaseId) -> None:
        del self._phases[phase_id]


def _service() -> tuple[ServicePhases, int]:
    tournois = FauxTournoiRepository()
    tournoi = tournois.ajouter(
        Tournoi(nom="Kervignarc", date=_DATE, lieu=None, type_tournoi=TypeTournoi.NON_OFFICIEL)
    )
    assert tournoi.id is not None
    return ServicePhases(tournois, FauxPhaseRepository()), tournoi.id


# --- Lister / ajouter --------------------------------------------------------------------------


def test_un_tournoi_neuf_n_a_aucune_phase() -> None:
    service, tournoi_id = _service()
    assert service.lister(tournoi_id) == []


def test_lister_leve_si_tournoi_inconnu() -> None:
    service, _ = _service()
    with pytest.raises(TournoiIntrouvable):
        service.lister(404)


def test_ajouter_empile_les_phases_en_ordre() -> None:
    """Chaque ajout prend le rang suivant (1, 2, 3…)."""
    service, tournoi_id = _service()
    p1 = service.ajouter(tournoi_id, TypePhase.ELIMINATION_DIRECTE)
    p2 = service.ajouter(tournoi_id, TypePhase.PLACEMENT)

    assert (p1.ordre, p2.ordre) == (1, 2)
    assert [p.id for p in service.lister(tournoi_id)] == [p1.id, p2.id]


def test_ajouter_leve_si_tournoi_inconnu() -> None:
    service, _ = _service()
    with pytest.raises(TournoiIntrouvable):
        service.ajouter(404, TypePhase.ELIMINATION_DIRECTE)


def test_ajouter_une_phase_avec_source_incoherente_ne_persiste_rien() -> None:
    """Une source qui vise une phase postérieure est rejetée (cohérence de séquence, 422)."""
    service, tournoi_id = _service()
    service.ajouter(tournoi_id, TypePhase.ELIMINATION_DIRECTE)  # ordre 1
    with pytest.raises(SourceApresPhase):
        service.ajouter(
            tournoi_id,
            TypePhase.PLACEMENT,
            source=SourcePhase(ordre_source=2, rang_debut=1, rang_fin=8),  # se référence lui-même
        )
    assert len(service.lister(tournoi_id)) == 1  # rien ajouté


# --- Modifier ----------------------------------------------------------------------------------


def test_modifier_change_type_source_effectif() -> None:
    service, tournoi_id = _service()
    p1 = service.ajouter(tournoi_id, TypePhase.PLACEMENT, effectif=40)
    p2 = service.ajouter(tournoi_id, TypePhase.PLACEMENT)
    assert p2.id is not None

    modifiee = service.modifier(
        tournoi_id,
        p2.id,
        type=TypePhase.ELIMINATION_DIRECTE,
        source=SourcePhase(ordre_source=1, rang_debut=1, rang_fin=16),
        effectif=16,
    )

    assert modifiee.type is TypePhase.ELIMINATION_DIRECTE
    assert modifiee.effectif == 16
    assert modifiee.source == SourcePhase(ordre_source=1, rang_debut=1, rang_fin=16)
    assert modifiee.ordre == 2  # préservé
    _ = p1


def test_modifier_effectif_incompatible_est_refuse() -> None:
    service, tournoi_id = _service()
    service.ajouter(tournoi_id, TypePhase.PLACEMENT, effectif=40)
    p2 = service.ajouter(tournoi_id, TypePhase.ELIMINATION_DIRECTE)
    assert p2.id is not None

    with pytest.raises(EffectifIncompatible):
        service.modifier(
            tournoi_id,
            p2.id,
            type=TypePhase.ELIMINATION_DIRECTE,
            source=SourcePhase(ordre_source=1, rang_debut=1, rang_fin=8),  # 8 prélevés
            effectif=16,  # mais 16 attendus
        )


def test_modifier_leve_si_phase_d_un_autre_tournoi() -> None:
    service, tournoi_id = _service()
    with pytest.raises(PhaseIntrouvable):
        service.modifier(tournoi_id, 999, type=TypePhase.PLACEMENT, source=None, effectif=None)


# --- Réordonner --------------------------------------------------------------------------------


def test_reordonner_reassigne_les_ordres() -> None:
    service, tournoi_id = _service()
    p1 = service.ajouter(tournoi_id, TypePhase.ELIMINATION_DIRECTE)
    p2 = service.ajouter(tournoi_id, TypePhase.PLACEMENT)
    assert p1.id is not None and p2.id is not None

    reordonnees = service.reordonner(tournoi_id, [p2.id, p1.id])

    ordres = {p.id: p.ordre for p in reordonnees}
    assert ordres == {p2.id: 1, p1.id: 2}


def test_reordonner_remappe_les_sources() -> None:
    """La source suit la phase qu'elle désignait, même après permutation (DETTE-015)."""
    service, tournoi_id = _service()
    a = service.ajouter(tournoi_id, TypePhase.PLACEMENT, effectif=40)  # ordre 1
    b = service.ajouter(tournoi_id, TypePhase.PLACEMENT)  # ordre 2
    assert b.id is not None
    # b tire des 16 premiers de a.
    service.modifier(
        tournoi_id,
        b.id,
        type=TypePhase.ELIMINATION_DIRECTE,
        source=SourcePhase(ordre_source=1, rang_debut=1, rang_fin=16),
        effectif=16,
    )
    assert a.id is not None
    # On insère une nouvelle phase, puis on réordonne a, b, c → c, a, b : a passe en 2, b en 3.
    c = service.ajouter(tournoi_id, TypePhase.PLACEMENT)
    assert c.id is not None

    reordonnees = service.reordonner(tournoi_id, [c.id, a.id, b.id])

    par_id = {p.id: p for p in reordonnees}
    assert par_id[a.id].ordre == 2
    assert par_id[b.id].ordre == 3
    # La source de b désigne toujours a — désormais en ordre 2.
    assert par_id[b.id].source == SourcePhase(ordre_source=2, rang_debut=1, rang_fin=16)


def test_reordonner_qui_place_la_source_apres_la_consommatrice_est_refuse() -> None:
    service, tournoi_id = _service()
    a = service.ajouter(tournoi_id, TypePhase.PLACEMENT, effectif=40)
    b = service.ajouter(tournoi_id, TypePhase.PLACEMENT)
    assert a.id is not None and b.id is not None
    service.modifier(
        tournoi_id,
        b.id,
        type=TypePhase.ELIMINATION_DIRECTE,
        source=SourcePhase(ordre_source=1, rang_debut=1, rang_fin=16),
        effectif=16,
    )

    # Inverser met la source (a) après la consommatrice (b) → incohérent.
    with pytest.raises(SourceApresPhase):
        service.reordonner(tournoi_id, [b.id, a.id])


def test_reordonner_liste_incomplete_est_refuse() -> None:
    service, tournoi_id = _service()
    p1 = service.ajouter(tournoi_id, TypePhase.ELIMINATION_DIRECTE)
    service.ajouter(tournoi_id, TypePhase.PLACEMENT)
    assert p1.id is not None

    with pytest.raises(ReordonnancementPhasesInvalide):
        service.reordonner(tournoi_id, [p1.id])  # une seule sur deux


# --- Supprimer ---------------------------------------------------------------------------------


def test_supprimer_retire_et_recompacte_les_ordres() -> None:
    service, tournoi_id = _service()
    p1 = service.ajouter(tournoi_id, TypePhase.ELIMINATION_DIRECTE)
    p2 = service.ajouter(tournoi_id, TypePhase.PLACEMENT)
    p3 = service.ajouter(tournoi_id, TypePhase.PLACEMENT)
    assert p1.id is not None

    service.supprimer(tournoi_id, p1.id)

    restantes = service.lister(tournoi_id)
    assert [p.id for p in restantes] == [p2.id, p3.id]
    assert [p.ordre for p in restantes] == [1, 2]  # recompacté


def test_supprimer_une_phase_source_d_une_autre_est_refuse() -> None:
    service, tournoi_id = _service()
    a = service.ajouter(tournoi_id, TypePhase.PLACEMENT, effectif=40)
    b = service.ajouter(tournoi_id, TypePhase.PLACEMENT)
    assert a.id is not None and b.id is not None
    service.modifier(
        tournoi_id,
        b.id,
        type=TypePhase.ELIMINATION_DIRECTE,
        source=SourcePhase(ordre_source=1, rang_debut=1, rang_fin=16),
        effectif=16,
    )

    with pytest.raises(PhaseSourceReferencee):
        service.supprimer(tournoi_id, a.id)  # a alimente b


def test_supprimer_recompacte_et_remappe_la_source_restante() -> None:
    """Retirer une phase avant une source décale l'ancre de celle-ci d'un cran (DETTE-015)."""
    service, tournoi_id = _service()
    filler = service.ajouter(tournoi_id, TypePhase.PLACEMENT)  # ordre 1, sans source
    a = service.ajouter(tournoi_id, TypePhase.PLACEMENT, effectif=40)  # ordre 2
    b = service.ajouter(tournoi_id, TypePhase.PLACEMENT)  # ordre 3
    assert filler.id is not None and a.id is not None and b.id is not None
    service.modifier(
        tournoi_id,
        b.id,
        type=TypePhase.ELIMINATION_DIRECTE,
        source=SourcePhase(ordre_source=2, rang_debut=1, rang_fin=16),  # b ← a (ordre 2)
        effectif=16,
    )

    service.supprimer(tournoi_id, filler.id)  # tout remonte d'un cran

    par_id = {p.id: p for p in service.lister(tournoi_id)}
    assert par_id[a.id].ordre == 1
    assert par_id[b.id].ordre == 2
    assert par_id[b.id].source == SourcePhase(ordre_source=1, rang_debut=1, rang_fin=16)


def test_supprimer_leve_si_phase_inconnue() -> None:
    service, tournoi_id = _service()
    with pytest.raises(PhaseIntrouvable):
        service.supprimer(tournoi_id, 999)


# --- Cycle de vie ------------------------------------------------------------------------------


def test_cycle_de_vie_nominal() -> None:
    service, tournoi_id = _service()
    phase = service.ajouter(tournoi_id, TypePhase.ELIMINATION_DIRECTE)
    assert phase.id is not None

    assert service.demarrer(tournoi_id, phase.id).statut is StatutPhase.EN_COURS
    assert service.mettre_en_pause(tournoi_id, phase.id).statut is StatutPhase.EN_PAUSE
    assert service.reprendre(tournoi_id, phase.id).statut is StatutPhase.EN_COURS
    assert service.terminer(tournoi_id, phase.id).statut is StatutPhase.TERMINEE


def test_demarrer_une_phase_deja_en_cours_est_refuse() -> None:
    service, tournoi_id = _service()
    phase = service.ajouter(tournoi_id, TypePhase.ELIMINATION_DIRECTE)
    assert phase.id is not None
    service.demarrer(tournoi_id, phase.id)

    with pytest.raises(TransitionStatutInvalide):
        service.demarrer(tournoi_id, phase.id)


def test_mettre_en_pause_une_phase_a_venir_est_refuse() -> None:
    service, tournoi_id = _service()
    phase = service.ajouter(tournoi_id, TypePhase.ELIMINATION_DIRECTE)
    assert phase.id is not None

    with pytest.raises(TransitionStatutInvalide):
        service.mettre_en_pause(tournoi_id, phase.id)


def test_terminer_une_phase_non_en_cours_est_refuse() -> None:
    service, tournoi_id = _service()
    phase = service.ajouter(tournoi_id, TypePhase.ELIMINATION_DIRECTE)
    assert phase.id is not None

    with pytest.raises(TransitionStatutInvalide):
        service.terminer(tournoi_id, phase.id)


def test_transition_leve_si_phase_d_un_autre_tournoi() -> None:
    service, tournoi_id = _service()
    with pytest.raises(PhaseIntrouvable):
        service.demarrer(tournoi_id, 999)
