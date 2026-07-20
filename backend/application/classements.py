"""Service applicatif Classement (E06US001) — lecture du classement de qualification.

Cas d'usage de **lecture** : charge les archers, leurs **séries** de saisie (E04US002) et les
catégories d'un tournoi via les ports, puis délègue le calcul (cumul, départage FFTA, deux rangs)
à la fonction pure du domaine (`calculer_classement`). Sans écriture, il s'exécute hors de la file
d'écriture (lecture concurrente, mode WAL).

Le classement se calcule **toujours en entier** (rang scratch global + rang par catégorie) ; le
paramètre `categorie_id` ne fait que **filtrer l'affichage** à une catégorie, sans recalculer : un
archer filtré garde donc son vrai rang scratch (sa place réelle dans le tournoi) et son rang de
catégorie. C'est le sens du CA « filtrage/segmentation par catégorie » — voir une catégorie sans
perdre la position d'ensemble.
"""

from __future__ import annotations

from application.erreurs import TournoiIntrouvable
from domain.categorie import CategorieId
from domain.classement import Classement, calculer_classement
from domain.ports import (
    ArcherRepository,
    CategorieRepository,
    SerieRepository,
    TournoiRepository,
)
from domain.tournoi import TournoiId


class ServiceClassement:
    """Cas d'usage du classement : consulter le classement de qualification d'un tournoi."""

    def __init__(
        self,
        tournois: TournoiRepository,
        archers: ArcherRepository,
        series: SerieRepository,
        categories: CategorieRepository,
    ) -> None:
        self._tournois = tournois
        self._archers = archers
        self._series = series
        self._categories = categories

    def pour_tournoi(
        self, tournoi_id: TournoiId, categorie_id: CategorieId | None = None
    ) -> Classement:
        """Renvoie le classement d'un tournoi, éventuellement **filtré** à une catégorie.

        Lève `TournoiIntrouvable` si le tournoi manque. `categorie_id=None` → toutes catégories
        (ordre scratch) ; sinon, seules les lignes de cette catégorie sont conservées, leurs rangs
        (scratch **et** catégorie) restant ceux du classement complet.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        archers = self._archers.par_tournoi(tournoi_id)
        series = self._series.par_tournoi(tournoi_id)
        categories = self._categories.par_tournoi(tournoi_id)
        classement = calculer_classement(archers, series, categories)
        if categorie_id is not None:
            classement = Classement(
                lignes=tuple(
                    ligne for ligne in classement.lignes if ligne.categorie_id == categorie_id
                )
            )
        return classement
