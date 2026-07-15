"""Service applicatif Archers (tranche verticale E00US011) — inscrire, placer, marquer.

Orchestre le domaine derrière les ports repository. Ne connaît ni HTTP, ni SQL, ni la file
d'écriture (sérialisation assurée en amont, côté API). Chaque cas d'usage vérifie l'existence
des ressources amont (tournoi, archer) et fait remonter des erreurs typées.
"""

from __future__ import annotations

from application.erreurs import ArcherIntrouvable, ClubIntrouvable, TournoiIntrouvable
from domain.archer import Archer, ArcherId
from domain.club import ClubId
from domain.ports import ArcherRepository, ClubRepository, ScoreRepository, TournoiRepository
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
    ) -> None:
        self._tournois = tournois
        self._archers = archers
        self._scores = scores
        self._clubs = clubs

    def ajouter(self, tournoi_id: TournoiId, nom: str, club_id: ClubId | None = None) -> Archer:
        """Inscrit un archer à un tournoi, éventuellement rattaché à un club (E02US001).

        Lève `TournoiIntrouvable` si le tournoi n'existe pas, `ClubIntrouvable` si un `club_id`
        est fourni sans correspondre à un club du référentiel. Le club reste **facultatif** ici ;
        E02US002 le rendra obligatoire.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        if club_id is not None and self._clubs.par_id(club_id) is None:
            raise ClubIntrouvable(f"Aucun club d'identifiant {club_id}.")
        return self._archers.ajouter(Archer.creer(nom, tournoi_id, club_id))

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
