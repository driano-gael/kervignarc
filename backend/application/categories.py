"""Service applicatif Catégories — CRUD des catégories d'un tournoi (E01US003).

Orchestre le domaine derrière les ports repository. Ne connaît ni HTTP, ni SQL, ni la file
d'écriture (sérialisation assurée en amont, côté API) ; il reste synchrone et pur
d'infrastructure. Il vérifie l'existence des ressources amont (tournoi, catégorie) et fait
remonter des erreurs typées (`TournoiIntrouvable`, `CategorieIntrouvable`).
"""

from __future__ import annotations

from application.erreurs import CategorieIntrouvable, TournoiIntrouvable
from domain.categorie import Categorie, CategorieId, SexeCategorie
from domain.ports import CategorieRepository, TournoiRepository
from domain.tournoi import TournoiId


class ServiceCategories:
    """Cas d'usage des catégories : créer, lister, éditer, supprimer."""

    def __init__(self, tournois: TournoiRepository, categories: CategorieRepository) -> None:
        self._tournois = tournois
        self._categories = categories

    def creer(
        self,
        tournoi_id: TournoiId,
        libelle: str,
        arme: str | None = None,
        tranche_age: str | None = None,
        sexe: SexeCategorie | None = None,
    ) -> Categorie:
        """Crée une catégorie rattachée à un tournoi.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas, `DomainError` si le libellé est vide.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        categorie = Categorie.creer(tournoi_id, libelle, arme, tranche_age, sexe)
        return self._categories.ajouter(categorie)

    def lister(self, tournoi_id: TournoiId) -> list[Categorie]:
        """Renvoie les catégories d'un tournoi. Lève `TournoiIntrouvable` s'il n'existe pas."""
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        return self._categories.par_tournoi(tournoi_id)

    def modifier(
        self,
        categorie_id: CategorieId,
        libelle: str,
        arme: str | None = None,
        tranche_age: str | None = None,
        sexe: SexeCategorie | None = None,
    ) -> Categorie:
        """Édite une catégorie (libellé, arme, âge, sexe).

        Lève `CategorieIntrouvable` si l'identifiant est inconnu, `DomainError` si le libellé
        est vide.
        """
        categorie = self._categorie_existante(categorie_id)
        modifiee = categorie.modifier(libelle, arme, tranche_age, sexe)
        return self._categories.enregistrer(modifiee)

    def supprimer(self, categorie_id: CategorieId) -> None:
        """Supprime une catégorie. Lève `CategorieIntrouvable` si l'identifiant est inconnu."""
        self._categorie_existante(categorie_id)
        self._categories.supprimer(categorie_id)

    def _categorie_existante(self, categorie_id: CategorieId) -> Categorie:
        categorie = self._categories.par_id(categorie_id)
        if categorie is None:
            raise CategorieIntrouvable(f"Aucune catégorie d'identifiant {categorie_id}.")
        return categorie
