"""Adapters repository SQLAlchemy (E00US009) — implémentent les ports du domaine.

`TournoiRepositorySQL` réalise `domain.ports.TournoiRepository` (conformité structurelle,
vérifiée au câblage). Chaque opération ouvre une **session courte** (une par opération,
ADR-0005) et traduit les lignes ORM en agrégats de domaine. Les pannes SQLAlchemy sont
**enveloppées** en `InfrastructureError` — le domaine ne voit jamais d'exception brute.

**Paquet depuis l'action 2 de l'audit de maintenabilité** (03/08/2026) : les 21 adapters
vivaient dans un **fichier unique de 3 378 lignes**, l'un des onze « passages obligés »
mesurés. Ils sont répartis par **thème métier** et ce module les **ré-exporte tous** : aucun
import existant n'a changé.

Les 45 fonctions de mapping ont suivi **le thème qui les appelle**, calculé sur le code et non
réparti à vue ; une seule était réellement partagée (`_mapping.py`).
"""

from __future__ import annotations

from infrastructure.db.repositories.exploitation import (
    AuditRepositorySQL,
    PosteRepositorySQL,
    ScoreurRepositorySQL,
)
from infrastructure.db.repositories.moteur import (
    DerouleEtapeRepositorySQL,
    FormatTournoiRepositorySQL,
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
    "GabaritSalleRepositorySQL",
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
