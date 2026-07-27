"""Tests d'intégration du repository SQL du plan de duels matérialisé (E03US009, ADR-0048).

Exerce l'adapter sur une **vraie base** migrée (`alembic upgrade head`) : aller-retour d'un plan,
remplacement intégral (régénérer), upsert atomique (déplacement/échange), mise en réserve, et le
**`ON DELETE CASCADE`** vers la phase **et** l'inscription (donnée dérivée, feuille). La clé étant
**composite** `(phase_id, inscription_id)`, chaque test crée tournoi → catégorie → départ → phase
d'élimination → archer → inscription. Tests **après** l'implémentation (adapter, pas d'oracle métier
— règle 9).
"""

from __future__ import annotations

import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config

from domain.archer import Archer
from domain.categorie import Categorie
from domain.depart import Depart
from domain.inscription import Inscription
from domain.phase import Phase, TypePhase
from domain.placement import Affectation
from domain.tournoi import Tournoi
from infrastructure.db import (
    ArcherRepositorySQL,
    AuditRepositorySQL,
    CategorieRepositorySQL,
    Database,
    DepartRepositorySQL,
    InscriptionRepositorySQL,
    PhaseRepositorySQL,
    PlacementTableauRepositorySQL,
    TournoiRepositorySQL,
)

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


class _Decor:
    """Base jetable migrée + tournoi/catégorie/départ/phase d'élimination prêts pour inscrire."""

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
            Categorie.creer(self.tournoi_id, "Cat", hauteur_cm=130)
        )
        assert categorie.id is not None
        self.categorie_id = categorie.id
        depart = DepartRepositorySQL(self.db.session_factory).ajouter(
            Depart.creer(self.tournoi_id, 1, 0)
        )
        assert depart.id is not None
        self.depart_id = depart.id
        phase = PhaseRepositorySQL(self.db.session_factory).ajouter(
            Phase.creer(self.tournoi_id, 2, TypePhase.ELIMINATION_DIRECTE)
        )
        assert phase.id is not None
        self.phase_id = phase.id

    @property
    def placements(self) -> PlacementTableauRepositorySQL:
        return PlacementTableauRepositorySQL(self.db.session_factory)

    def inscrire(self) -> int:
        """Crée un archer et son inscription au départ ; renvoie l'id d'inscription."""
        archer = ArcherRepositorySQL(self.db.session_factory).ajouter(
            Archer(nom="N", prenom="P", tournoi_id=self.tournoi_id, categorie_id=self.categorie_id)
        )
        assert archer.id is not None
        inscription = InscriptionRepositorySQL(
            self.db.session_factory, AuditRepositorySQL(self.db.session_factory)
        ).ajouter(Inscription(archer_id=archer.id, depart_id=self.depart_id))
        assert inscription.id is not None
        return inscription.id


def test_definir_plan_puis_relire(tmp_path: Path) -> None:
    """`definir_plan` matérialise le plan de duels ; `par_phase` le relit (trié cible, position)."""
    decor = _Decor(tmp_path)
    i1, i2 = decor.inscrire(), decor.inscrire()
    try:
        decor.placements.definir_plan(
            decor.phase_id,
            [
                Affectation(inscription_id=i2, cible_index=1, position="B"),
                Affectation(inscription_id=i1, cible_index=1, position="A"),
            ],
        )
        assert decor.placements.par_phase(decor.phase_id) == [
            Affectation(inscription_id=i1, cible_index=1, position="A"),
            Affectation(inscription_id=i2, cible_index=1, position="B"),
        ]
    finally:
        decor.db.engine.dispose()


def test_definir_plan_remplace_tout(tmp_path: Path) -> None:
    """Régénérer : `definir_plan` purge l'ancien plan de la phase avant d'écrire le nouveau."""
    decor = _Decor(tmp_path)
    i1 = decor.inscrire()
    try:
        decor.placements.definir_plan(
            decor.phase_id, [Affectation(inscription_id=i1, cible_index=1, position="A")]
        )
        decor.placements.definir_plan(
            decor.phase_id, [Affectation(inscription_id=i1, cible_index=2, position="C")]
        )
        assert decor.placements.par_phase(decor.phase_id) == [
            Affectation(inscription_id=i1, cible_index=2, position="C")
        ]
    finally:
        decor.db.engine.dispose()


def test_poser_plusieurs_insere_puis_met_a_jour(tmp_path: Path) -> None:
    """Upsert (clé phase+inscription) : insère une affectation absente, met à jour une existante."""
    decor = _Decor(tmp_path)
    i1 = decor.inscrire()
    try:
        decor.placements.poser_plusieurs(
            decor.phase_id, [Affectation(inscription_id=i1, cible_index=1, position="A")]
        )
        decor.placements.poser_plusieurs(
            decor.phase_id, [Affectation(inscription_id=i1, cible_index=3, position="B")]
        )
        assert decor.placements.par_phase(decor.phase_id) == [
            Affectation(inscription_id=i1, cible_index=3, position="B")
        ]
    finally:
        decor.db.engine.dispose()


def test_retirer_met_en_reserve(tmp_path: Path) -> None:
    """`retirer` supprime l'affectation de la phase (réserve) ; idempotent si déjà absente."""
    decor = _Decor(tmp_path)
    i1 = decor.inscrire()
    try:
        decor.placements.poser_plusieurs(
            decor.phase_id, [Affectation(inscription_id=i1, cible_index=1, position="A")]
        )
        decor.placements.retirer(decor.phase_id, i1)
        assert decor.placements.par_phase(decor.phase_id) == []
        decor.placements.retirer(decor.phase_id, i1)  # sans effet, pas d'erreur
    finally:
        decor.db.engine.dispose()


def test_supprimer_l_inscription_efface_la_pose(tmp_path: Path) -> None:
    """ADR-0048 : `ON DELETE CASCADE` — supprimer l'inscription retire sa pose (dérivée)."""
    decor = _Decor(tmp_path)
    i1 = decor.inscrire()
    try:
        decor.placements.poser_plusieurs(
            decor.phase_id, [Affectation(inscription_id=i1, cible_index=1, position="A")]
        )
        InscriptionRepositorySQL(
            decor.db.session_factory, AuditRepositorySQL(decor.db.session_factory)
        ).supprimer(i1)
        assert decor.placements.par_phase(decor.phase_id) == []
    finally:
        decor.db.engine.dispose()
