"""Service applicatif Archers (E00US011, complété par E02US002) — inscrire, placer, marquer.

Orchestre le domaine derrière les ports repository. Ne connaît ni HTTP, ni SQL, ni la file
d'écriture (sérialisation assurée en amont, côté API). Chaque cas d'usage vérifie l'existence
des ressources amont (tournoi, archer, club, catégorie) et fait remonter des erreurs typées.
"""

from __future__ import annotations

from application.erreurs import (
    ArcherIntrouvable,
    CategorieHorsTournoi,
    ClubIntrouvable,
    HomonymeArcher,
    TournoiIntrouvable,
)
from domain.archer import Archer, ArcherId, CleIdentite
from domain.categorie import CategorieId
from domain.club import ClubId
from domain.ports import (
    ArcherRepository,
    CategorieRepository,
    ClubRepository,
    ScoreRepository,
    TournoiRepository,
)
from domain.score import Score
from domain.tournoi import TournoiId


class ServiceArchers:
    """Cas d'usage des archers : inscrire à un tournoi, placer sur une cible, marquer un score."""

    def __init__(
        self,
        tournois: TournoiRepository,
        archers: ArcherRepository,
        scores: ScoreRepository,
        clubs: ClubRepository,
        categories: CategorieRepository,
    ) -> None:
        self._tournois = tournois
        self._archers = archers
        self._scores = scores
        self._clubs = clubs
        self._categories = categories

    def ajouter(
        self,
        tournoi_id: TournoiId,
        nom: str,
        prenom: str,
        categorie_id: CategorieId,
        club_id: ClubId | None = None,
        autoriser_homonyme: bool = False,
    ) -> Archer:
        """Inscrit un archer à un tournoi (E02US002).

        La **catégorie est obligatoire** et doit appartenir au tournoi ; le **club est facultatif**
        (`None` = club encore inconnu, cf. `domain.archer` et ADR-0014) mais doit exister s'il est
        fourni.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas, `CategorieHorsTournoi` si la catégorie
        est inexistante ou étrangère au tournoi, `ClubIntrouvable` si un `club_id` est fourni sans
        correspondre à un club du référentiel, et `HomonymeArcher` si un archer de même identité
        (`domain.archer.cle_identite`) est déjà inscrit — sauf `autoriser_homonyme=True`, par lequel
        l'admin confirme qu'il s'agit bien de deux personnes distinctes.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        self._verifier_categorie_du_tournoi(tournoi_id, categorie_id)
        if club_id is not None and self._clubs.par_id(club_id) is None:
            raise ClubIntrouvable(f"Aucun club d'identifiant {club_id}.")
        # L'agrégat est construit **avant** le contrôle d'homonymie : la clé dérive ainsi du nom
        # réellement stocké (normalisé par `Archer.creer`) et non de l'entrée brute. Sans cela, la
        # justesse reposerait sur une coïncidence entre deux normalisations indépendantes — celle
        # de `cle_nom` et celle de `_texte_obligatoire` — qu'une évolution de l'une romprait en
        # silence. Effet de bord voulu : une saisie invalide rend 422 avant 409, ce qui est l'ordre
        # juste (une entrée invalide n'est pas un conflit).
        archer = Archer.creer(nom, prenom, tournoi_id, categorie_id, club_id)
        if not autoriser_homonyme:
            self._signaler_homonyme(tournoi_id, archer.cle_identite())
        return self._archers.ajouter(archer)

    def placer(self, archer_id: ArcherId, cible: int) -> Archer:
        """Place un archer sur une cible. Lève `ArcherIntrouvable` s'il n'existe pas."""
        archer = self._archer_existant(archer_id)
        return self._archers.enregistrer(archer.placer(cible))

    def saisir_score(self, archer_id: ArcherId, points: int) -> Score:
        """Enregistre une flèche d'un archer. Lève `ArcherIntrouvable` s'il n'existe pas."""
        self._archer_existant(archer_id)
        return self._scores.ajouter(Score.creer(archer_id, points))

    def _archer_existant(self, archer_id: ArcherId) -> Archer:
        archer = self._archers.par_id(archer_id)
        if archer is None:
            raise ArcherIntrouvable(f"Aucun archer d'identifiant {archer_id}.")
        return archer

    def _verifier_categorie_du_tournoi(
        self, tournoi_id: TournoiId, categorie_id: CategorieId
    ) -> None:
        """Exige une catégorie **du tournoi** (patron `ServiceCategories._verifier_blason_...`)."""
        categorie = self._categories.par_id(categorie_id)
        if categorie is None or categorie.tournoi_id != tournoi_id:
            raise CategorieHorsTournoi(
                f"La catégorie {categorie_id} n'appartient pas au tournoi {tournoi_id}."
            )

    def _signaler_homonyme(self, tournoi_id: TournoiId, cle: CleIdentite) -> None:
        """Lève `HomonymeArcher` si un archer de même identité est déjà inscrit au tournoi.

        Balayage linéaire des inscrits plutôt qu'un port de recherche dédié : quelques centaines
        d'archers par tournoi, sur une inscription — la simplicité prime hors du domaine (règle 12),
        et un index serait à maintenir cohérent avec `cle_identite` pour rien.
        """
        for inscrit in self._archers.par_tournoi(tournoi_id):
            if inscrit.cle_identite() == cle:
                raise HomonymeArcher(
                    f"« {inscrit.prenom} {inscrit.nom} » est déjà inscrit à ce tournoi. "
                    "S'il s'agit d'un homonyme (un père et son fils, par exemple), confirmez "
                    "l'inscription ; sinon, il s'agit d'un doublon."
                )
