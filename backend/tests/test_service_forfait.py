"""Tests du service applicatif `ServiceForfait` (E04US015, ADR-0050).

Le comportement de **classement** (relégation abandon / exclusion DSQ) et de **duels** (walkover)
est couvert là où il vit (`test_domain_classement.py`, `test_service_saisie_duels.py`). Ici on teste
ce que le **service** garantit, **depuis le CA** (règle 9, service = règle métier) :

- déclarer un forfait **préserve les flèches** (le service ne touche jamais la série) et **trace** ;
- un forfait par `(tournoi, archer, phase)` : re-déclarer lève `ForfaitDejaDeclare` ;
- **réversible tant que le tournoi n'est pas terminé** (`D-15`) : sinon `ForfaitTournoiTermine` ;
- annuler suppose une déclaration : sinon `ForfaitIntrouvable` ;
- gardes d'existence (archer, phase de qualif / phase de tableau).

Fakes en mémoire : le service n'orchestre que des ports.
"""

from __future__ import annotations

import datetime

import pytest

from application.erreurs import (
    ArcherIntrouvable,
    ForfaitDejaDeclare,
    ForfaitIntrouvable,
    ForfaitTournoiTermine,
    PhaseIntrouvable,
    PhaseQualificationAbsente,
    TournoiIntrouvable,
)
from application.forfaits import ServiceForfait
from domain.archer import Archer
from domain.bareme import BaremeQualification
from domain.categorie import Categorie
from domain.depart import Depart
from domain.forfait import NatureForfait
from domain.phase import Phase, TypePhase
from domain.tournoi import StatutTournoi, Tournoi, TournoiId
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxDepartRepository,
    FauxForfaitRepository,
    FauxPhaseRepository,
)

_QUAND = datetime.datetime(2026, 3, 14, 10, 42, tzinfo=datetime.UTC)


class HorlogeFigee:
    """Horloge de test conforme au port `Horloge` : renvoie un instant fixe (UTC aware)."""

    def maintenant(self) -> datetime.datetime:
        return _QUAND


class FauxTournoiRepository:
    """Double de `TournoiRepository` : un tournoi au **statut réglable** (pour la garde `D-15`)."""

    def __init__(self, statut: StatutTournoi = StatutTournoi.EN_COURS) -> None:
        self._statut = statut
        self._existe = True

    def par_id(self, tournoi_id: TournoiId) -> Tournoi | None:
        if not self._existe:
            return None
        from dataclasses import replace

        return replace(Tournoi.creer("Salle 18m", datetime.date(2026, 3, 14)), statut=self._statut)

    def sans_tournoi(self) -> None:
        self._existe = False

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        raise NotImplementedError

    def lister(self) -> list[Tournoi]:
        raise NotImplementedError

    def enregistrer(self, tournoi: Tournoi) -> Tournoi:
        raise NotImplementedError

    def supprimer(self, tournoi_id: TournoiId) -> None:
        raise NotImplementedError


class _Monde:
    """Un tournoi EN_COURS, un archer, une phase de qualif et une phase de tableau prêtes."""

    def __init__(self, statut: StatutTournoi = StatutTournoi.EN_COURS) -> None:
        self.tournoi_id = 1
        self.tournois = FauxTournoiRepository(statut)
        self.archers = FauxArcherRepository()
        self.categories = FauxCategorieRepository()
        self.departs = FauxDepartRepository()
        # Le créneau qui porte les phases : sans lui, la lecture transverse « la qualification de
        # ce tournoi » ne trouve rien (ADR-0075) et le service croit la phase absente.
        _d = self.departs.ajouter(
            Depart.creer(tournoi_id=self.tournoi_id, numero=1, tarif_centimes=800, horaire="09:00")
        )
        assert _d.id is not None
        self.depart_id = _d.id
        self.phases = FauxPhaseRepository(self.departs)
        self.forfaits = FauxForfaitRepository()
        cat = self.categories.ajouter(Categorie.creer(self.tournoi_id, "Senior 1 H"))
        assert cat.id is not None
        archer = self.archers.ajouter(Archer.creer("DURAND", "Jean", self.tournoi_id, cat.id))
        assert archer.id is not None
        self.archer_id = archer.id
        qualif = self.phases.ajouter(
            Phase.qualification(self.depart_id, BaremeQualification.creer(3, 3))
        )
        assert qualif.id is not None
        self.qualif_id = qualif.id
        tableau = self.phases.ajouter(Phase.creer(self.depart_id, 2, TypePhase.ELIMINATION_DIRECTE))
        assert tableau.id is not None
        self.tableau_id = tableau.id
        self.service = ServiceForfait(
            self.forfaits, self.tournois, self.archers, self.phases, HorlogeFigee()
        )


def test_declarer_en_qualification_trace_et_preserve() -> None:
    """CA : déclarer un abandon crée un forfait daté/attribué sur la phase de qualif, sans toucher
    la série (le service n'a pas de port série — les flèches sont préservées par construction)."""
    m = _Monde()
    forfait = m.service.declarer_en_qualification(
        m.tournoi_id, m.archer_id, NatureForfait.ABANDON, "ROUX Sophie", "blessure"
    )
    assert forfait.id is not None
    assert forfait.phase_id == m.qualif_id
    assert forfait.declare_par == "ROUX Sophie"
    assert forfait.motif == "blessure"
    assert m.forfaits.par_phase(m.qualif_id)[0].nature is NatureForfait.ABANDON


def test_declarer_deux_fois_leve_deja_declare() -> None:
    """CA : un forfait par (tournoi, archer, phase) — re-déclarer est refusé (409)."""
    m = _Monde()
    m.service.declarer_en_qualification(m.tournoi_id, m.archer_id, NatureForfait.ABANDON, "S")
    with pytest.raises(ForfaitDejaDeclare):
        m.service.declarer_en_qualification(
            m.tournoi_id, m.archer_id, NatureForfait.DISQUALIFICATION, "S"
        )


def test_tournoi_termine_refuse_declaration_et_annulation() -> None:
    """CA `D-15` : sur un tournoi terminé, on ne déclare ni n'annule un forfait (figé)."""
    m = _Monde(statut=StatutTournoi.TERMINE)
    with pytest.raises(ForfaitTournoiTermine):
        m.service.declarer_en_qualification(m.tournoi_id, m.archer_id, NatureForfait.ABANDON, "S")
    with pytest.raises(ForfaitTournoiTermine):
        m.service.annuler_en_qualification(m.tournoi_id, m.archer_id, "S")


def test_tournoi_inconnu_leve_introuvable() -> None:
    m = _Monde()
    m.tournois.sans_tournoi()
    with pytest.raises(TournoiIntrouvable):
        m.service.declarer_en_qualification(m.tournoi_id, m.archer_id, NatureForfait.ABANDON, "S")


def test_archer_inconnu_leve_introuvable() -> None:
    m = _Monde()
    with pytest.raises(ArcherIntrouvable):
        m.service.declarer_en_qualification(m.tournoi_id, 999, NatureForfait.ABANDON, "S")


def test_qualif_absente_leve_erreur() -> None:
    """Sans phase de qualification configurée, on ne peut pas déclarer un abandon de qualif."""
    m = _Monde()
    m.phases = FauxPhaseRepository(m.departs)  # aucune phase
    m.service = ServiceForfait(m.forfaits, m.tournois, m.archers, m.phases, HorlogeFigee())
    with pytest.raises(PhaseQualificationAbsente):
        m.service.declarer_en_qualification(m.tournoi_id, m.archer_id, NatureForfait.ABANDON, "S")


def test_annuler_sans_declaration_leve_introuvable() -> None:
    """CA : annuler suppose une déclaration existante (404 sinon)."""
    m = _Monde()
    with pytest.raises(ForfaitIntrouvable):
        m.service.annuler_en_qualification(m.tournoi_id, m.archer_id, "S")


def test_declarer_puis_annuler_retire_le_forfait() -> None:
    """CA `D-15` : la réversibilité **supprime** la déclaration (les flèches n'ont jamais bougé)."""
    m = _Monde()
    m.service.declarer_en_qualification(m.tournoi_id, m.archer_id, NatureForfait.ABANDON, "S")
    m.service.annuler_en_qualification(m.tournoi_id, m.archer_id, "S")
    assert m.forfaits.par_phase(m.qualif_id) == []


def test_declarer_en_duel_utilise_la_phase_fournie() -> None:
    """En duels, le forfait est porté par la **phase de tableau** fournie (pas la qualif)."""
    m = _Monde()
    forfait = m.service.declarer_en_duel(
        m.tournoi_id, m.tableau_id, m.archer_id, NatureForfait.ABANDON, "S"
    )
    assert forfait.phase_id == m.tableau_id


def test_declarer_en_duel_phase_inconnue_leve_erreur() -> None:
    m = _Monde()
    with pytest.raises(PhaseIntrouvable):
        m.service.declarer_en_duel(m.tournoi_id, 999, m.archer_id, NatureForfait.ABANDON, "S")
