"""Service applicatif Tournois — orchestre le domaine derrière le port repository.

Use cases de configuration d'un tournoi : créer, consulter, lister (E01US001) ; éditer,
démarrer, terminer, supprimer (E01US002). Il ne connaît ni HTTP, ni SQL, ni la file
d'écriture (sérialisation assurée en amont, côté API) ; il reste synchrone et pur
d'infrastructure. Il arbitre l'**existence** (`TournoiIntrouvable`) et les **conflits d'état**
du cycle de vie (`TransitionStatutInvalide`, `TournoiEnCoursNonSupprimable`) — l'agrégat, lui,
ne valide que les valeurs (ADR-0007).
"""

from __future__ import annotations

import datetime

from application.erreurs import (
    TournoiEnCoursNonSupprimable,
    TournoiIntrouvable,
    TransitionStatutInvalide,
)
from domain.ports import TournoiRepository
from domain.tournoi import StatutTournoi, Tournoi, TournoiId, TypeTournoi


class ServiceTournois:
    """Cas d'usage des tournois : créer, consulter, lister, éditer, cycle de vie, supprimer."""

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

    def modifier(
        self,
        tournoi_id: TournoiId,
        nom: str,
        date: datetime.date,
        lieu: str | None = None,
        type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL,
    ) -> Tournoi:
        """Édite les métadonnées d'un tournoi (nom, date, lieu, type), statut préservé.

        Lève `TournoiIntrouvable` si l'identifiant est inconnu, `DomainError` si le nom est
        vide. L'édition est autorisée quel que soit le statut.
        """
        tournoi = self.consulter(tournoi_id)
        modifie = tournoi.modifier(nom, date, lieu, type_tournoi)
        return self._repository.enregistrer(modifie)

    def demarrer(self, tournoi_id: TournoiId) -> Tournoi:
        """Passe un tournoi `brouillon` à `en_cours`.

        Lève `TournoiIntrouvable` si inconnu, `TransitionStatutInvalide` (→ 409) s'il n'est
        pas au statut `brouillon`.
        """
        tournoi = self.consulter(tournoi_id)
        if tournoi.statut is not StatutTournoi.BROUILLON:
            raise TransitionStatutInvalide("Seul un tournoi en brouillon peut être démarré.")
        return self._repository.enregistrer(tournoi.demarrer())

    def terminer(self, tournoi_id: TournoiId) -> Tournoi:
        """Passe un tournoi `en_cours` à `terminé`.

        Lève `TournoiIntrouvable` si inconnu, `TransitionStatutInvalide` (→ 409) s'il n'est
        pas au statut `en_cours`.
        """
        tournoi = self.consulter(tournoi_id)
        if tournoi.statut is not StatutTournoi.EN_COURS:
            raise TransitionStatutInvalide("Seul un tournoi en cours peut être terminé.")
        return self._repository.enregistrer(tournoi.terminer())

    def supprimer(self, tournoi_id: TournoiId) -> None:
        """Supprime un tournoi.

        Lève `TournoiIntrouvable` si inconnu, `TournoiEnCoursNonSupprimable` (→ 409) si le
        tournoi est `en_cours` (le terminer d'abord). Un `brouillon` ou un `terminé` est
        supprimable.
        """
        tournoi = self.consulter(tournoi_id)
        if tournoi.statut is StatutTournoi.EN_COURS:
            raise TournoiEnCoursNonSupprimable(
                "Un tournoi en cours ne peut pas être supprimé ; terminez-le d'abord."
            )
        assert tournoi.id is not None, "Un tournoi consulté est persisté."
        self._repository.supprimer(tournoi.id)
