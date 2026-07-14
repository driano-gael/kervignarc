"""Ports du domaine — interfaces implémentées par des adapters d'infrastructure (ADR-0003).

Le domaine définit *ce dont il a besoin* (persister, relire) sans savoir *comment*.
`Protocol` : conformité **structurelle**, sans imposer d'héritage aux adapters — le
domaine reste pur (aucune dépendance vers l'infrastructure).
"""

from __future__ import annotations

from typing import Protocol

from domain.archer import Archer, ArcherId
from domain.blason import Blason, BlasonId
from domain.categorie import Categorie, CategorieId
from domain.gabarit_salle import GabaritSalle, GabaritSalleId
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

    def lister(self) -> list[Tournoi]:
        """Renvoie tous les tournois (liste éventuellement vide).

        L'ordre n'est **pas** garanti par le port (détail de l'adapter) : un consommateur
        qui a besoin d'un ordre précis doit le trier lui-même.
        """
        ...

    def enregistrer(self, tournoi: Tournoi) -> Tournoi:
        """Met à jour un tournoi déjà persisté (édition, transition de statut) et le renvoie."""
        ...

    def supprimer(self, tournoi_id: TournoiId) -> None:
        """Supprime le tournoi d'identifiant donné (existence garantie par l'appelant)."""
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


class CategorieRepository(Protocol):
    """Port de persistance des catégories (adapter fourni par l'infrastructure)."""

    def ajouter(self, categorie: Categorie) -> Categorie:
        """Persiste une catégorie et la renvoie avec son identifiant attribué."""
        ...

    def par_id(self, categorie_id: CategorieId) -> Categorie | None:
        """Renvoie la catégorie d'identifiant donné, ou `None` si elle n'existe pas."""
        ...

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Categorie]:
        """Renvoie toutes les catégories d'un tournoi (liste éventuellement vide)."""
        ...

    def par_blason(self, blason_id: BlasonId) -> list[Categorie]:
        """Renvoie les catégories dont le blason par défaut est `blason_id` (E01US006).

        Sert à refuser la suppression d'un blason encore référencé (liste non vide).
        """
        ...

    def enregistrer(self, categorie: Categorie) -> Categorie:
        """Met à jour une catégorie déjà persistée (édition) et la renvoie."""
        ...

    def supprimer(self, categorie_id: CategorieId) -> None:
        """Supprime la catégorie d'identifiant donné (existence garantie par l'appelant)."""
        ...


class BlasonRepository(Protocol):
    """Port de persistance des blasons (adapter fourni par l'infrastructure)."""

    def ajouter(self, blason: Blason) -> Blason:
        """Persiste un blason et le renvoie avec son identifiant attribué."""
        ...

    def par_id(self, blason_id: BlasonId) -> Blason | None:
        """Renvoie le blason d'identifiant donné, ou `None` s'il n'existe pas."""
        ...

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Blason]:
        """Renvoie tous les blasons d'un tournoi (liste éventuellement vide)."""
        ...

    def enregistrer(self, blason: Blason) -> Blason:
        """Met à jour un blason déjà persisté (édition) et le renvoie."""
        ...

    def supprimer(self, blason_id: BlasonId) -> None:
        """Supprime le blason d'identifiant donné (existence garantie par l'appelant)."""
        ...


class GabaritSalleRepository(Protocol):
    """Port de persistance des gabarits de salle (adapter fourni par l'infrastructure).

    Deux natures cohabitent : les **modèles** de bibliothèque (`tournoi_id is None`),
    réutilisables (E01US007), et les **instances** appliquées à un tournoi (E01US008), copies
    ajustables. `lister` ne renvoie que les modèles ; `par_tournoi` récupère l'instance d'un
    tournoi.
    """

    def ajouter(self, gabarit: GabaritSalle) -> GabaritSalle:
        """Persiste un gabarit (modèle ou instance) et le renvoie avec son identifiant attribué."""
        ...

    def par_id(self, gabarit_id: GabaritSalleId) -> GabaritSalle | None:
        """Renvoie le gabarit d'identifiant donné, ou `None` s'il n'existe pas."""
        ...

    def lister(self) -> list[GabaritSalle]:
        """Renvoie les gabarits **modèles** (bibliothèque, `tournoi_id is None`)."""
        ...

    def par_tournoi(self, tournoi_id: TournoiId) -> GabaritSalle | None:
        """Renvoie l'instance de gabarit appliquée à un tournoi, ou `None` s'il n'y en a pas.

        Un tournoi porte **au plus une** instance (son plan de salle courant).
        """
        ...

    def enregistrer(self, gabarit: GabaritSalle) -> GabaritSalle:
        """Met à jour un gabarit déjà persisté (édition, ajustement) et le renvoie."""
        ...

    def supprimer(self, gabarit_id: GabaritSalleId) -> None:
        """Supprime le gabarit d'identifiant donné (existence garantie par l'appelant)."""
        ...


class ScoreRepository(Protocol):
    """Port de persistance des scores (adapter fourni par l'infrastructure)."""

    def ajouter(self, score: Score) -> Score:
        """Persiste un score et le renvoie avec son identifiant attribué."""
        ...

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Score]:
        """Renvoie tous les scores des archers d'un tournoi (liste éventuellement vide)."""
        ...
