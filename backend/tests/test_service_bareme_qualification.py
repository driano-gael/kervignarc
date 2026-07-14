"""Tests du service applicatif Barème de qualification (E01US009) — repositories factices.

Le service est testé **en isolation** : de faux repositories en mémoire (conformes aux ports
`TournoiRepository` / `PhaseRepository`) suffisent — ni base ni serveur.
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.bareme_qualification import ServiceBaremeQualification
from application.erreurs import TournoiIntrouvable
from domain.erreurs import NombreFlechesParVoleeInvalide, NombreVoleesInvalide
from domain.phase import Phase, PhaseId, TypePhase
from domain.tournoi import Tournoi, TournoiId, TypeTournoi

_DATE = datetime.date(2026, 3, 14)


class FauxTournoiRepository:
    """Repository de tournois minimal (seul `par_id` est exercé par ce service)."""

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
    """Repository de phases en mémoire conforme au port `PhaseRepository`."""

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

    def enregistrer(self, phase: Phase) -> Phase:
        assert phase.id in self._phases
        self._phases[phase.id] = phase
        return phase


def _service_avec_tournoi() -> tuple[ServiceBaremeQualification, int]:
    tournois = FauxTournoiRepository()
    tournoi = tournois.ajouter(
        Tournoi(nom="Kervignarc", date=_DATE, lieu=None, type_tournoi=TypeTournoi.NON_OFFICIEL)
    )
    assert tournoi.id is not None
    return ServiceBaremeQualification(tournois, FauxPhaseRepository()), tournoi.id


def test_bareme_absent_par_defaut() -> None:
    """Un tournoi neuf n'a pas encore de barème de qualification."""
    service, tournoi_id = _service_avec_tournoi()
    assert service.bareme_du_tournoi(tournoi_id) is None


def test_bareme_du_tournoi_leve_si_tournoi_inconnu() -> None:
    """Lire le barème d'un tournoi inexistant lève `TournoiIntrouvable`."""
    service = ServiceBaremeQualification(FauxTournoiRepository(), FauxPhaseRepository())
    with pytest.raises(TournoiIntrouvable):
        service.bareme_du_tournoi(404)


def test_definir_cree_le_bareme() -> None:
    """`definir` crée le barème (via une phase qualification) puis le rend lisible."""
    service, tournoi_id = _service_avec_tournoi()
    bareme = service.definir(tournoi_id, 20, 3)
    assert (bareme.nb_volees, bareme.nb_fleches_par_volee) == (20, 3)
    assert bareme.score_max == 600
    assert service.bareme_du_tournoi(tournoi_id) == bareme


def test_definir_met_a_jour_sans_creer_de_seconde_phase() -> None:
    """Redéfinir remplace les valeurs (upsert) sans empiler de phases."""
    service, tournoi_id = _service_avec_tournoi()
    service.definir(tournoi_id, 20, 3)
    maj = service.definir(tournoi_id, 10, 6)
    assert (maj.nb_volees, maj.nb_fleches_par_volee) == (10, 6)
    # Toujours lisible comme le barème courant (une seule phase qualification).
    assert service.bareme_du_tournoi(tournoi_id) == maj


def test_definir_leve_si_tournoi_inconnu() -> None:
    """Définir sur un tournoi inexistant lève `TournoiIntrouvable`."""
    service = ServiceBaremeQualification(FauxTournoiRepository(), FauxPhaseRepository())
    with pytest.raises(TournoiIntrouvable):
        service.definir(404, 20, 3)


def test_definir_valeurs_invalides_leve_domaine() -> None:
    """Des grandeurs `< 1` font remonter l'erreur du domaine (rien n'est persisté)."""
    service, tournoi_id = _service_avec_tournoi()
    with pytest.raises(NombreVoleesInvalide):
        service.definir(tournoi_id, 0, 3)
    with pytest.raises(NombreFlechesParVoleeInvalide):
        service.definir(tournoi_id, 20, 0)
    assert service.bareme_du_tournoi(tournoi_id) is None
