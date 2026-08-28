"""Adapters SQL — traduisent les lignes ORM en agrégats et **enveloppent** les pannes SQLAlchemy
en `InfrastructureError` : le domaine ne voit jamais d'exception brute.

⚠️ **Paquet réparti par thème métier, qui RÉ-EXPORTE tout** : aucun import existant n'a changé
quand les 21 adapters ont quitté leur fichier unique de 3 378 lignes. Une seule fonction de mapping
était réellement partagée — `_mapping.py`. ADR-0005
"""

from __future__ import annotations

from infrastructure.db.repositories.exploitation import (
    AuditRepositorySQL,
    PosteRepositorySQL,
    ScoreurRepositorySQL,
)
from infrastructure.db.repositories.moteur import (
    ArretDeCirconstanceRepositorySQL,
    DerouleEtapeRepositorySQL,
    FormatTournoiRepositorySQL,
    FranchissementArretRepositorySQL,
    PhaseRepositorySQL,
    PlacementParBlocRepositorySQL,
    PlacementRepositorySQL,
    PlacementTableauRepositorySQL,
)
from infrastructure.db.repositories.referentiel import (
    ArcherRepositorySQL,
    BlasonRepositorySQL,
    CategorieRepositorySQL,
    ClubRepositorySQL,
    DepartRepositorySQL,
    GabaritSalleRepositorySQL,
    IdentiteVisuelleRepositorySQL,
    InscriptionRepositorySQL,
    RemboursementRepositorySQL,
    TournoiRepositorySQL,
)
from infrastructure.db.repositories.tir import (
    BarrageRepositorySQL,
    DuelRepositorySQL,
    ForfaitRepositorySQL,
    ScoreRepositorySQL,
    SerieRepositorySQL,
)

__all__ = [
    "ArcherRepositorySQL",
    "ArretDeCirconstanceRepositorySQL",
    "AuditRepositorySQL",
    "BarrageRepositorySQL",
    "BlasonRepositorySQL",
    "CategorieRepositorySQL",
    "ClubRepositorySQL",
    "DepartRepositorySQL",
    "DerouleEtapeRepositorySQL",
    "DuelRepositorySQL",
    "ForfaitRepositorySQL",
    "FormatTournoiRepositorySQL",
    "FranchissementArretRepositorySQL",
    "GabaritSalleRepositorySQL",
    "IdentiteVisuelleRepositorySQL",
    "InscriptionRepositorySQL",
    "PhaseRepositorySQL",
    "PlacementParBlocRepositorySQL",
    "PlacementRepositorySQL",
    "PlacementTableauRepositorySQL",
    "PosteRepositorySQL",
    "RemboursementRepositorySQL",
    "ScoreRepositorySQL",
    "ScoreurRepositorySQL",
    "SerieRepositorySQL",
    "TournoiRepositorySQL",
]
