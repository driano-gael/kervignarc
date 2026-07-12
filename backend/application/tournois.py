"""Service applicatif Tournois — orchestre le domaine derrière le port repository.

Use cases de configuration d'un tournoi (E01US001) : créer, consulter, lister. Il ne
connaît ni HTTP, ni SQL, ni la file d'écriture (sérialisation assurée en amont, côté API) ;
il reste synchrone et pur d'infrastructure.
"""

from __future__ import annotations

import datetime

from application.erreurs import TournoiIntrouvable
from domain.ports import TournoiRepository
from domain.tournoi import Tournoi, TournoiId, TypeTournoi


class ServiceTournois:
    """Cas d'usage des tournois : créer, consulter, lister."""

    def __init__(self, repository: TournoiRepository) -> None:
        self._repository = repository

    def creer(
        self,
        nom: str,
        date: datetime.date,
        lieu: str | None = None,
        type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL,
    ) -> Tournoi:
        """Crée et persiste un tournoi. Lève `DomainError` si les champs sont invalides."""
        tournoi = Tournoi.creer(nom, date, lieu, type_tournoi)
        return self._repository.ajouter(tournoi)

    def consulter(self, tournoi_id: TournoiId) -> Tournoi:
        """Relit un tournoi. Lève `TournoiIntrouvable` s'il n'existe pas."""
        tournoi = self._repository.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        return tournoi

    def lister(self) -> list[Tournoi]:
        """Renvoie tous les tournois (liste éventuellement vide)."""
        return self._repository.lister()
