"""Tests du service applicatif `ServiceSaisie` (E04US002) — orchestration, contre des faux ports.

Dérivés des **CA** (règle 9) : le pavé se déduit du **blason** de l'archer (ex-003), la validation
**trace** au nom du scoreur (ex-007 + E10US005), la correction **trace avant/après** (ex-012).
On vérifie la **résolution** (zones du blason, barème/grain de la phase, nom de l'auteur) et la
construction des entrées d'audit — pas la logique du domaine, prouvée dans `test_domain_serie`.
"""

from __future__ import annotations

import dataclasses
import datetime

import pytest

from application.erreurs import (
    ArcherIntrouvable,
    BlasonIntrouvable,
    PhaseQualificationAbsente,
)
from application.saisie import ServiceSaisie
from domain.archer import Archer, ArcherId
from domain.bareme import BaremeQualification
from domain.blason import Blason, BlasonId, ZoneScore
from domain.categorie import Categorie
from domain.entree_audit import ActionAuditee, EntreeAudit
from domain.erreurs import ValeurHorsBlason
from domain.grain_validation import GrainValidation
from domain.phase import Phase, PhaseId, TypePhase
from domain.serie import Serie
from domain.tournoi import TournoiId
from tests.conftest import FauxArcherRepository, FauxCategorieRepository

_QUAND = datetime.datetime(2026, 7, 19, 10, 42, tzinfo=datetime.UTC)
ZONES_SIMPLE = tuple(ZoneScore)
ZONES_TRIPLE = (
    ZoneScore.DIX,
    ZoneScore.NEUF,
    ZoneScore.HUIT,
    ZoneScore.SEPT,
    ZoneScore.SIX,
    ZoneScore.MANQUE,
)


def _v(*valeurs: str) -> tuple[ZoneScore, ...]:
    return tuple(ZoneScore(v) for v in valeurs)


class FauxSerieRepository:
    """Repository de séries en mémoire conforme au port `SerieRepository`.

    `enregistrer_avec_trace` **retient** l'entrée d'audit reçue (`traces`) : c'est ce que les tests
    inspectent pour vérifier que l'acte laisse bien sa trace, dans la même opération que l'écriture.
    """

    def __init__(self) -> None:
        self._series: dict[tuple[int, int], Serie] = {}
        self.traces: list[EntreeAudit] = []
        self._sequence = 0

    def par_archer(self, tournoi_id: TournoiId, archer_id: ArcherId) -> Serie | None:
        return self._series.get((tournoi_id, archer_id))

    def enregistrer(self, serie: Serie) -> Serie:
        if serie.id is None:
            self._sequence += 1
            serie = dataclasses.replace(serie, id=self._sequence)
        self._series[(serie.tournoi_id, serie.archer_id)] = serie
        return serie

    def enregistrer_avec_trace(self, serie: Serie, entree: EntreeAudit) -> Serie:
        self.traces.append(entree)
        return self.enregistrer(serie)


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
        return next(
            (
                p
                for p in self._phases.values()
                if p.tournoi_id == tournoi_id and p.type is type_phase
            ),
            None,
        )

    def enregistrer(self, phase: Phase) -> Phase:
        assert phase.id in self._phases
        self._phases[phase.id] = phase
        return phase


class FauxBlasonRepository:
    """Repository de blasons en mémoire conforme au port `BlasonRepository`."""

    def __init__(self) -> None:
        self._blasons: dict[int, Blason] = {}
        self._sequence = 0

    def ajouter(self, blason: Blason) -> Blason:
        self._sequence += 1
        persiste = dataclasses.replace(blason, id=self._sequence)
        self._blasons[self._sequence] = persiste
        return persiste

    def par_id(self, blason_id: BlasonId) -> Blason | None:
        return self._blasons.get(blason_id)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Blason]:
        return [b for b in self._blasons.values() if b.tournoi_id == tournoi_id]

    def enregistrer(self, blason: Blason) -> Blason:
        assert blason.id in self._blasons
        self._blasons[blason.id] = blason
        return blason

    def supprimer(self, blason_id: BlasonId) -> None:
        del self._blasons[blason_id]


class HorlogeFigee:
    """Horloge déterministe conforme au port `Horloge` : renvoie toujours le même instant."""

    def __init__(self, instant: datetime.datetime) -> None:
        self._instant = instant

    def maintenant(self) -> datetime.datetime:
        return self._instant


class Montage:
    """Attelage d'un test : service, faux repos, un archer prêt à tirer, une phase de qualif."""

    def __init__(
        self,
        *,
        zones: tuple[ZoneScore, ...] = ZONES_SIMPLE,
        avec_phase: bool = True,
        avec_blason: bool = True,
    ) -> None:
        self.series = FauxSerieRepository()
        self.phases = FauxPhaseRepository()
        self.archers = FauxArcherRepository()
        self.categories = FauxCategorieRepository()
        self.blasons = FauxBlasonRepository()
        self.horloge = HorlogeFigee(_QUAND)
        self.tournoi_id: TournoiId = 1
        blason_id: BlasonId | None = None
        if avec_blason:
            blason = self.blasons.ajouter(
                Blason(tournoi_id=1, nom="Simple", taille=1.0, capacite=1, zones=zones)
            )
            blason_id = blason.id
        categorie = self.categories.ajouter(
            Categorie(tournoi_id=1, libelle="Senior Homme", blason_id=blason_id)
        )
        assert categorie.id is not None
        archer = self.archers.ajouter(
            Archer(nom="DUPONT", prenom="Jean", tournoi_id=1, categorie_id=categorie.id)
        )
        assert archer.id is not None
        self.archer_id: ArcherId = archer.id
        if avec_phase:
            self.phases.ajouter(
                Phase.qualification(
                    tournoi_id=1,
                    bareme=BaremeQualification.creer(2, 3),
                    validation=GrainValidation.fin_de_serie(),
                )
            )
        self.service = ServiceSaisie(
            self.series, self.phases, self.archers, self.categories, self.blasons, self.horloge
        )

    def saisir_serie_complete(self) -> None:
        """Saisit les deux volées du barème (préalable à une validation de fin de série)."""
        self.service.saisir_volee(self.tournoi_id, self.archer_id, 1, _v("10", "9", "8"), "DURAND")
        self.service.saisir_volee(self.tournoi_id, self.archer_id, 2, _v("9", "9", "9"), "DURAND")


def test_saisir_volee_persiste_avec_le_marqueur() -> None:
    """ex-005/017 : la volée saisie est persistée, avec le nom du marqueur."""
    m = Montage()
    m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "8"), saisie_par="DURAND")
    serie = m.series.par_archer(m.tournoi_id, m.archer_id)
    assert serie is not None
    volee = serie.volee(1)
    assert volee is not None
    assert volee.valeurs == _v("10", "9", "8")
    assert volee.saisie_par == "DURAND"


def test_le_pave_vient_du_blason_de_l_archer() -> None:
    """ex-003 : les zones admises se déduisent du blason — un « 5 » sur un triple 40 est refusé."""
    m = Montage(zones=ZONES_TRIPLE)
    with pytest.raises(ValeurHorsBlason):
        m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "5"))


def test_valider_trace_une_entree_au_nom_du_scoreur() -> None:
    """ex-007 : valider verrouille la série et trace une VALIDATION au nom du scoreur, datée."""
    m = Montage()
    m.saisir_serie_complete()
    m.service.valider(m.tournoi_id, m.archer_id, scoreur="MARTIN")
    serie = m.series.par_archer(m.tournoi_id, m.archer_id)
    assert serie is not None
    assert all(v.verrouillee for v in serie.volees)
    assert len(m.series.traces) == 1
    trace = m.series.traces[0]
    assert trace.action is ActionAuditee.VALIDATION
    assert trace.auteur == "MARTIN"
    assert trace.horodatage == _QUAND
    assert (trace.avant, trace.apres) == (None, None)


def test_corriger_trace_l_avant_et_l_apres() -> None:
    """ex-012 : corriger une volée verrouillée laisse une trace CORRECTION_SCORE avant/après."""
    m = Montage()
    m.saisir_serie_complete()
    m.service.valider(m.tournoi_id, m.archer_id, scoreur="MARTIN")
    m.service.corriger_volee(m.tournoi_id, m.archer_id, 1, _v("9", "9", "9"), auteur="ARBITRE")
    trace = m.series.traces[-1]
    assert trace.action is ActionAuditee.CORRECTION_SCORE
    assert trace.auteur == "ARBITRE"
    assert trace.avant == "10, 9, 8"
    assert trace.apres == "9, 9, 9"


def test_saisir_pour_un_archer_inconnu_est_refuse() -> None:
    """Un archer inconnu rend `ArcherIntrouvable` (traduit en 404)."""
    m = Montage()
    with pytest.raises(ArcherIntrouvable):
        m.service.saisir_volee(m.tournoi_id, 999, 1, _v("10", "9", "8"))


def test_saisir_pour_un_archer_d_un_autre_tournoi_est_refuse() -> None:
    """Un archer d'un autre tournoi n'existe pas pour ce tournoi (`ArcherIntrouvable`)."""
    m = Montage()
    with pytest.raises(ArcherIntrouvable):
        m.service.saisir_volee(2, m.archer_id, 1, _v("10", "9", "8"))


def test_saisir_sans_phase_de_qualification_est_refuse() -> None:
    """Sans phase de qualification configurée, la saisie rend `PhaseQualificationAbsente`."""
    m = Montage(avec_phase=False)
    with pytest.raises(PhaseQualificationAbsente):
        m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "8"))


def test_saisir_pour_un_archer_sans_blason_est_refuse() -> None:
    """Sans blason par défaut, le pavé est indéterminable : `BlasonIntrouvable`."""
    m = Montage(avec_blason=False)
    with pytest.raises(BlasonIntrouvable):
        m.service.saisir_volee(m.tournoi_id, m.archer_id, 1, _v("10", "9", "8"))
