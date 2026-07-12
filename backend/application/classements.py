"""Service applicatif Classement (tranche verticale E00US011) — lecture d'un classement.

Cas d'usage de **lecture** : charge les archers et scores d'un tournoi via les ports, puis
délègue le calcul à la fonction pure du domaine (`calculer_classement`). Sans écriture, il
s'exécute hors de la file d'écriture (lecture concurrente, mode WAL).
"""

from __future__ import annotations

from application.erreurs import TournoiIntrouvable
from domain.classement import Classement, calculer_classement
from domain.ports import ArcherRepository, ScoreRepository, TournoiRepository
from domain.tournoi import TournoiId


class ServiceClassement:
    """Cas d'usage du classement : consulter le classement courant d'un tournoi."""

    def __init__(
        self,
        tournois: TournoiRepository,
        archers: ArcherRepository,
        scores: ScoreRepository,
    ) -> None:
        self._tournois = tournois
        self._archers = archers
        self._scores = scores

    def pour_tournoi(self, tournoi_id: TournoiId) -> Classement:
        """Renvoie le classement d'un tournoi. Lève `TournoiIntrouvable` s'il n'existe pas."""
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        archers = self._archers.par_tournoi(tournoi_id)
        scores = self._scores.par_tournoi(tournoi_id)
        return calculer_classement(archers, scores)
