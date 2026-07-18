"""Tests d'intégration du repository SQL du plan de cibles matérialisé (E03US004, ADR-0024).

Exerce l'adapter sur une **vraie base** migrée (`alembic upgrade head`) : aller-retour d'un plan,
remplacement intégral (régénérer), upsert atomique (déplacement/échange), mise en réserve, et le
**`ON DELETE CASCADE`** vers l'inscription — la marque d'ADR-0024 (donnée dérivée qui suit
l'inscription). Une affectation référence une inscription (FK) : chaque test crée d'abord
tournoi → catégorie → départ → archer → inscription. Tests **après** l'implémentation (adapter, pas
d'oracle métier — règle 9).
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
from domain.placement import Affectation
from domain.tournoi import Tournoi
from infrastructure.db import (
    ArcherRepositorySQL,
    CategorieRepositorySQL,
    Database,
    DepartRepositorySQL,
    InscriptionRepositorySQL,
    PlacementRepositorySQL,
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
    """Base jetable migrée + tournoi/catégorie/départ prêts, avec de quoi inscrire des archers."""

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

    @property
    def placements(self) -> PlacementRepositorySQL:
        return PlacementRepositorySQL(self.db.session_factory)

    def inscrire(self) -> int:
        """Crée un archer et son inscription au départ ; renvoie l'id d'inscription."""
        archer = ArcherRepositorySQL(self.db.session_factory).ajouter(
            Archer(nom="N", prenom="P", tournoi_id=self.tournoi_id, categorie_id=self.categorie_id)
        )
        assert archer.id is not None
        inscription = InscriptionRepositorySQL(self.db.session_factory).ajouter(
            Inscription(archer_id=archer.id, depart_id=self.depart_id)
        )
        assert inscription.id is not None
        return inscription.id


def test_definir_plan_puis_relire(tmp_path: Path) -> None:
    """`definir_plan` matérialise le plan ; `par_depart` le relit (trié cible puis position)."""
    decor = _Decor(tmp_path)
    i1, i2 = decor.inscrire(), decor.inscrire()
    try:
        decor.placements.definir_plan(
            decor.depart_id,
            [
                Affectation(inscription_id=i2, cible_index=1, position="B"),
                Affectation(inscription_id=i1, cible_index=1, position="A"),
            ],
        )
        assert decor.placements.par_depart(decor.depart_id) == [
            Affectation(inscription_id=i1, cible_index=1, position="A"),
            Affectation(inscription_id=i2, cible_index=1, position="B"),
        ]
    finally:
        decor.db.engine.dispose()


def test_definir_plan_remplace_tout(tmp_path: Path) -> None:
    """Régénérer : `definir_plan` purge l'ancien plan avant d'écrire le nouveau (pas de cumul)."""
    decor = _Decor(tmp_path)
    i1 = decor.inscrire()
    try:
        decor.placements.definir_plan(
            decor.depart_id, [Affectation(inscription_id=i1, cible_index=1, position="A")]
        )
        decor.placements.definir_plan(
            decor.depart_id, [Affectation(inscription_id=i1, cible_index=2, position="C")]
        )
        assert decor.placements.par_depart(decor.depart_id) == [
            Affectation(inscription_id=i1, cible_index=2, position="C")
        ]
    finally:
        decor.db.engine.dispose()


def test_poser_plusieurs_insere_puis_met_a_jour(tmp_path: Path) -> None:
    """Upsert : `poser_plusieurs` insère une affectation absente et met à jour une existante.

    C'est le cœur du **déplacement** (une pose) et de l'**échange** (deux poses dans la même
    transaction) : appelé deux fois sur la même inscription, la seconde écrase la première."""
    decor = _Decor(tmp_path)
    i1 = decor.inscrire()
    try:
        decor.placements.poser_plusieurs(
            decor.depart_id, [Affectation(inscription_id=i1, cible_index=1, position="A")]
        )
        decor.placements.poser_plusieurs(
            decor.depart_id, [Affectation(inscription_id=i1, cible_index=3, position="B")]
        )
        assert decor.placements.par_depart(decor.depart_id) == [
            Affectation(inscription_id=i1, cible_index=3, position="B")
        ]
    finally:
        decor.db.engine.dispose()


def test_retirer_met_en_reserve(tmp_path: Path) -> None:
    """`retirer` supprime l'affectation (mise en réserve) ; idempotent si déjà absente."""
    decor = _Decor(tmp_path)
    i1 = decor.inscrire()
    try:
        decor.placements.poser_plusieurs(
            decor.depart_id, [Affectation(inscription_id=i1, cible_index=1, position="A")]
        )
        decor.placements.retirer(i1)
        assert decor.placements.par_depart(decor.depart_id) == []
        decor.placements.retirer(i1)  # sans effet, pas d'erreur
    finally:
        decor.db.engine.dispose()


def test_supprimer_l_inscription_efface_l_affectation(tmp_path: Path) -> None:
    """ADR-0024 : `ON DELETE CASCADE` — supprimer l'inscription retire son affectation (dérivée)."""
    decor = _Decor(tmp_path)
    i1 = decor.inscrire()
    try:
        decor.placements.poser_plusieurs(
            decor.depart_id, [Affectation(inscription_id=i1, cible_index=1, position="A")]
        )
        InscriptionRepositorySQL(decor.db.session_factory).supprimer(i1)
        assert decor.placements.par_depart(decor.depart_id) == []
    finally:
        decor.db.engine.dispose()
