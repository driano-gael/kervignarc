"""Service applicatif Tournois (E00US009) — orchestre le domaine derrière le port repository.

Gabarit de use case : il ne connaît ni HTTP, ni SQL, ni la file d'écriture. Il reçoit un
`TournoiRepository` (port) par **injection** depuis la composition root. Les écritures
sont sérialisées en amont (file d'écriture, côté API) ; ce service reste synchrone et pur
d'infrastructure.
"""

from __future__ import annotations

from application.erreurs import TournoiIntrouvable
from domain.ports import TournoiRepository
from domain.tournoi import Tournoi, TournoiId


class ServiceTournois:
    """Cas d'usage des tournois : créer, consulter."""

    def __init__(self, repository: TournoiRepository) -> None:
        self._repository = repository

    def creer(self, nom: str) -> Tournoi:
        """Crée et persiste un tournoi. Lève `DomainError` si le nom est invalide."""
        tournoi = Tournoi.creer(nom)
        return self._repository.ajouter(tournoi)

    def consulter(self, tournoi_id: TournoiId) -> Tournoi:
        """Relit un tournoi. Lève `TournoiIntrouvable` s'il n'existe pas."""
        tournoi = self._repository.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        return tournoi
