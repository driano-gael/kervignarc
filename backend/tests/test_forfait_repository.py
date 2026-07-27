"""Tests d'intégration du repository SQL des forfaits (E04US015, ADR-0050).

Exerce `ForfaitRepositorySQL` sur une **vraie base** migrée (`alembic upgrade head`) : aller-retour
d'un forfait (la nature revient en `NatureForfait`, `declare_le` *aware* UTC après SQLite, le motif
nullable), lectures `par_phase` / `par_tournoi` / `par_archer_et_phase`, la **couture d'atomicité**
acte↔trace (ADR-0035 : le forfait ET sa trace, ou ni l'un ni l'autre), et l'**annulation** (la ligne
disparaît, une trace d'annulation reste). Un forfait référence tournoi + archer + phase (FK) :
chaque contexte les crée d'abord.

Écrits **après** l'implémentation (règle 9 : repository/câblage, pas d'oracle en jeu).
"""

from __future__ import annotations

import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config

from domain.archer import Archer
from domain.categorie import Categorie
from domain.entree_audit import ActionAuditee, EntreeAudit
from domain.forfait import Forfait, NatureForfait
from domain.phase import Phase, TypePhase
from domain.tournoi import Tournoi
from infrastructure.db import (
    ArcherRepositorySQL,
    AuditRepositorySQL,
    CategorieRepositorySQL,
    Database,
    ForfaitRepositorySQL,
    PhaseRepositorySQL,
    TournoiRepositorySQL,
)

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)
_QUAND = datetime.datetime(2026, 3, 14, 10, 42, tzinfo=datetime.UTC)


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


class _Contexte:
    """Base jetable migrée + tournoi / catégorie / archer / phase prêts pour un forfait."""

    def __init__(self, tmp_path: Path) -> None:
        url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
        _migrer(url)
        self.db = Database(url)
        tournoi = TournoiRepositorySQL(self.db.session_factory).ajouter(
            Tournoi.creer("Salle 18m", _DATE)
        )
        assert tournoi.id is not None
        self.tournoi_id = tournoi.id
        categorie = CategorieRepositorySQL(self.db.session_factory).ajouter(
            Categorie.creer(tournoi.id, "Senior 1 H")
        )
        assert categorie.id is not None
        archer = ArcherRepositorySQL(self.db.session_factory).ajouter(
            Archer.creer("DURAND", "Jean", tournoi.id, categorie.id)
        )
        assert archer.id is not None
        self.archer_id = archer.id
        phase = PhaseRepositorySQL(self.db.session_factory).ajouter(
            Phase.creer(tournoi.id, 2, TypePhase.ELIMINATION_DIRECTE)
        )
        assert phase.id is not None
        self.phase_id = phase.id
        self.repository = ForfaitRepositorySQL(
            self.db.session_factory, AuditRepositorySQL(self.db.session_factory)
        )
        self.audit = AuditRepositorySQL(self.db.session_factory)

    def forfait(
        self, nature: NatureForfait = NatureForfait.ABANDON, motif: str | None = "blessure"
    ) -> Forfait:
        return Forfait.creer(
            tournoi_id=self.tournoi_id,
            archer_id=self.archer_id,
            phase_id=self.phase_id,
            nature=nature,
            declare_par="ROUX Sophie",
            declare_le=_QUAND,
            motif=motif,
        )

    def trace(self, avant: str | None = None, apres: str | None = None) -> EntreeAudit:
        return EntreeAudit.creer(
            tournoi_id=self.tournoi_id,
            action=ActionAuditee.FORFAIT,
            auteur="ROUX Sophie",
            horodatage=_QUAND,
            objet=f"forfait de l'archer {self.archer_id}",
            avant=avant,
            apres=apres,
        )


def test_declarer_puis_relire(tmp_path: Path) -> None:
    ctx = _Contexte(tmp_path)
    try:
        declare = ctx.repository.declarer_avec_trace(ctx.forfait(), ctx.trace(apres="abandon"))
        assert declare.id is not None
        (relu,) = ctx.repository.par_phase(ctx.phase_id)
        assert relu.nature is NatureForfait.ABANDON
        assert relu.motif == "blessure"
        assert relu.declare_le == _QUAND
        assert relu.declare_le.tzinfo is not None  # UTC réattaché
        # La trace a bien été co-écrite dans la même transaction.
        (trace,) = ctx.audit.par_tournoi(ctx.tournoi_id)
        assert trace.action is ActionAuditee.FORFAIT
    finally:
        ctx.db.engine.dispose()


def test_motif_nullable(tmp_path: Path) -> None:
    ctx = _Contexte(tmp_path)
    try:
        ctx.repository.declarer_avec_trace(ctx.forfait(motif=None), ctx.trace())
        (relu,) = ctx.repository.par_phase(ctx.phase_id)
        assert relu.motif is None
    finally:
        ctx.db.engine.dispose()


def test_par_archer_et_phase(tmp_path: Path) -> None:
    ctx = _Contexte(tmp_path)
    try:
        assert (
            ctx.repository.par_archer_et_phase(ctx.tournoi_id, ctx.archer_id, ctx.phase_id) is None
        )
        ctx.repository.declarer_avec_trace(ctx.forfait(), ctx.trace())
        trouve = ctx.repository.par_archer_et_phase(ctx.tournoi_id, ctx.archer_id, ctx.phase_id)
        assert trouve is not None and trouve.nature is NatureForfait.ABANDON
    finally:
        ctx.db.engine.dispose()


def test_annuler_supprime_le_forfait_et_trace(tmp_path: Path) -> None:
    ctx = _Contexte(tmp_path)
    try:
        declare = ctx.repository.declarer_avec_trace(ctx.forfait(), ctx.trace(apres="abandon"))
        ctx.repository.annuler_avec_trace(declare, ctx.trace(avant="abandon"))
        assert ctx.repository.par_phase(ctx.phase_id) == []
        # Deux traces : la déclaration puis l'annulation (le journal est en ajout seul).
        assert len(ctx.audit.par_tournoi(ctx.tournoi_id)) == 2
    finally:
        ctx.db.engine.dispose()
