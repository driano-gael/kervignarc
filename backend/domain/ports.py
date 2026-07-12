"""Ports du domaine — interfaces implémentées par des adapters d'infrastructure (ADR-0003).

Le domaine définit *ce dont il a besoin* (persister, relire) sans savoir *comment*.
`Protocol` : conformité **structurelle**, sans imposer d'héritage aux adapters — le
domaine reste pur (aucune dépendance vers l'infrastructure).
"""

from __future__ import annotations

from typing import Protocol

from domain.archer import Archer, ArcherId
from domain.score import Score
from domain.tournoi import Tournoi, TournoiId


class TournoiRepository(Protocol):
    """Port de persistance des tournois (adapter fourni par l'infrastructure)."""

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        """Persiste un tournoi et le renvoie avec son identifiant attribué."""
        ...

    def par_id(self, tournoi_id: TournoiId) -> Tournoi | None:
        """Renvoie le tournoi d'identifiant donné, ou `None` s'il n'existe pas."""
        ...


class ArcherRepository(Protocol):
    """Port de persistance des archers (adapter fourni par l'infrastructure)."""

    def ajouter(self, archer: Archer) -> Archer:
        """Persiste un archer et le renvoie avec son identifiant attribué."""
        ...

    def par_id(self, archer_id: ArcherId) -> Archer | None:
        """Renvoie l'archer d'identifiant donné, ou `None` s'il n'existe pas."""
        ...

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Archer]:
        """Renvoie tous les archers d'un tournoi (liste éventuellement vide)."""
        ...

    def enregistrer(self, archer: Archer) -> Archer:
        """Met à jour un archer déjà persisté (ex. après placement) et le renvoie."""
        ...


class ScoreRepository(Protocol):
    """Port de persistance des scores (adapter fourni par l'infrastructure)."""

    def ajouter(self, score: Score) -> Score:
        """Persiste un score et le renvoie avec son identifiant attribué."""
        ...

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Score]:
        """Renvoie tous les scores des archers d'un tournoi (liste éventuellement vide)."""
        ...
