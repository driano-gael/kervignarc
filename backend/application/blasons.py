"""Service applicatif Blasons — CRUD des blasons d'un tournoi (E01US005).

Orchestre le domaine derrière les ports repository. Ne connaît ni HTTP, ni SQL, ni la file
d'écriture (sérialisation assurée en amont, côté API) ; il reste synchrone et pur
d'infrastructure. Il vérifie l'existence des ressources amont (tournoi, blason) et fait
remonter des erreurs typées (`TournoiIntrouvable`, `BlasonIntrouvable`).
"""

from __future__ import annotations

from application.erreurs import BlasonIntrouvable, TournoiIntrouvable
from domain.blason import Blason, BlasonId
from domain.ports import BlasonRepository, TournoiRepository
from domain.tournoi import TournoiId


class ServiceBlasons:
    """Cas d'usage des blasons : créer, lister, éditer, supprimer."""

    def __init__(self, tournois: TournoiRepository, blasons: BlasonRepository) -> None:
        self._tournois = tournois
        self._blasons = blasons

    def creer(self, tournoi_id: TournoiId, nom: str, taille: float, capacite: int) -> Blason:
        """Crée un blason rattaché à un tournoi.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas, `DomainError` si un attribut
        (nom, taille, capacité) est invalide.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        blason = Blason.creer(tournoi_id, nom, taille, capacite)
        return self._blasons.ajouter(blason)

    def lister(self, tournoi_id: TournoiId) -> list[Blason]:
        """Renvoie les blasons d'un tournoi. Lève `TournoiIntrouvable` s'il n'existe pas."""
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        return self._blasons.par_tournoi(tournoi_id)

    def modifier(self, blason_id: BlasonId, nom: str, taille: float, capacite: int) -> Blason:
        """Édite un blason (nom, taille, capacité).

        Lève `BlasonIntrouvable` si l'identifiant est inconnu, `DomainError` si un attribut
        est invalide.
        """
        blason = self._blason_existant(blason_id)
        modifie = blason.modifier(nom, taille, capacite)
        return self._blasons.enregistrer(modifie)

    def supprimer(self, blason_id: BlasonId) -> None:
        """Supprime un blason. Lève `BlasonIntrouvable` si l'identifiant est inconnu."""
        self._blason_existant(blason_id)
        self._blasons.supprimer(blason_id)

    def _blason_existant(self, blason_id: BlasonId) -> Blason:
        blason = self._blasons.par_id(blason_id)
        if blason is None:
            raise BlasonIntrouvable(f"Aucun blason d'identifiant {blason_id}.")
        return blason
