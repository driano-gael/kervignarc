"""Service applicatif Catégories — CRUD des catégories d'un tournoi (E01US003).

Orchestre le domaine derrière les ports repository. Ne connaît ni HTTP, ni SQL, ni la file
d'écriture (sérialisation assurée en amont, côté API) ; il reste synchrone et pur
d'infrastructure. Il vérifie l'existence des ressources amont (tournoi, catégorie) et la
cohérence du **blason par défaut** (règle inter-agrégats : même tournoi), et fait remonter des
erreurs typées (`TournoiIntrouvable`, `CategorieIntrouvable`, `BlasonHorsTournoi`).
"""

from __future__ import annotations

from application.erreurs import BlasonHorsTournoi, CategorieIntrouvable, TournoiIntrouvable
from application.referentiel_ffta import categories_salle_18m
from domain.blason import BlasonId
from domain.categorie import Categorie, CategorieId, SexeCategorie
from domain.ports import BlasonRepository, CategorieRepository, TournoiRepository
from domain.tournoi import TournoiId


class ServiceCategories:
    """Cas d'usage des catégories : créer, lister, éditer, supprimer."""

    def __init__(
        self,
        tournois: TournoiRepository,
        categories: CategorieRepository,
        blasons: BlasonRepository,
    ) -> None:
        self._tournois = tournois
        self._categories = categories
        self._blasons = blasons

    def creer(
        self,
        tournoi_id: TournoiId,
        libelle: str,
        arme: str | None = None,
        tranche_age: str | None = None,
        sexe: SexeCategorie | None = None,
        blason_id: BlasonId | None = None,
    ) -> Categorie:
        """Crée une catégorie rattachée à un tournoi.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas, `BlasonHorsTournoi` si le blason par
        défaut n'appartient pas à ce tournoi, `DomainError` si le libellé est vide.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        self._verifier_blason_du_tournoi(tournoi_id, blason_id)
        categorie = Categorie.creer(tournoi_id, libelle, arme, tranche_age, sexe, blason_id)
        return self._categories.ajouter(categorie)

    def lister(self, tournoi_id: TournoiId) -> list[Categorie]:
        """Renvoie les catégories d'un tournoi. Lève `TournoiIntrouvable` s'il n'existe pas."""
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        return self._categories.par_tournoi(tournoi_id)

    def precharger_ffta(self, tournoi_id: TournoiId) -> list[Categorie]:
        """Pré-charge le jeu de catégories FFTA salle (18 m) dans un tournoi (E01US004).

        Crée les catégories du référentiel officiel (`application.referentiel_ffta`) absentes du
        tournoi ; celles dont le libellé existe déjà (comparaison insensible à la casse et aux
        espaces de bord) sont **ignorées** — l'action est ainsi rejouable sans doublonner. Les
        catégories créées sont ordinaires : **modifiables et supprimables** via le CRUD.

        Renvoie les catégories effectivement **créées**, dans l'ordre du référentiel (liste vide
        si tout était déjà présent). Lève `TournoiIntrouvable` si le tournoi n'existe pas.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        libelles_existants = {
            categorie.libelle.strip().casefold()
            for categorie in self._categories.par_tournoi(tournoi_id)
        }
        creees: list[Categorie] = []
        for modele in categories_salle_18m():
            cle = modele.libelle.strip().casefold()
            if cle in libelles_existants:
                continue
            categorie = Categorie.creer(
                tournoi_id, modele.libelle, modele.arme, modele.tranche_age, modele.sexe
            )
            creees.append(self._categories.ajouter(categorie))
            libelles_existants.add(cle)
        return creees

    def modifier(
        self,
        categorie_id: CategorieId,
        libelle: str,
        arme: str | None = None,
        tranche_age: str | None = None,
        sexe: SexeCategorie | None = None,
        blason_id: BlasonId | None = None,
    ) -> Categorie:
        """Édite une catégorie (libellé, arme, âge, sexe, blason par défaut).

        Lève `CategorieIntrouvable` si l'identifiant est inconnu, `BlasonHorsTournoi` si le blason
        par défaut n'appartient pas au tournoi de la catégorie, `DomainError` si le libellé est
        vide.
        """
        categorie = self._categorie_existante(categorie_id)
        self._verifier_blason_du_tournoi(categorie.tournoi_id, blason_id)
        modifiee = categorie.modifier(libelle, arme, tranche_age, sexe, blason_id)
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

    def _verifier_blason_du_tournoi(
        self, tournoi_id: TournoiId, blason_id: BlasonId | None
    ) -> None:
        """Vérifie qu'un blason par défaut (facultatif) appartient bien au tournoi.

        Sans blason (`None`), rien à vérifier. Sinon, le blason doit exister **et** être rattaché
        au même tournoi, sans quoi le lien serait incohérent → `BlasonHorsTournoi`.
        """
        if blason_id is None:
            return
        blason = self._blasons.par_id(blason_id)
        if blason is None or blason.tournoi_id != tournoi_id:
            raise BlasonHorsTournoi(
                f"Le blason {blason_id} n'appartient pas au tournoi {tournoi_id}."
            )
