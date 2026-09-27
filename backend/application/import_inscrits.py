"""Service d'import des inscrits (E02US007) — aperçu, puis confirmation. ADR-0115.

⚠️ `importer` doit s'exécuter **dans une seule commande** de la file d'écriture (règle 7) : le plan
y est recalculé sur l'état du moment, et c'est ce qui dispense l'écrivain de tout revérifier. La
**lecture** du fichier, elle, se fait avant (`lire`), hors de la file : elle ne dépend d'aucun état.
"""

from __future__ import annotations

from application.erreurs import TournoiIntrouvable
from domain.import_inscrits import (
    FichierInscrits,
    InstantaneDuTournoi,
    PlanImport,
    planifier_import,
)
from domain.ports import (
    ArcherRepository,
    CategorieRepository,
    ClubRepository,
    DepartRepository,
    Horloge,
    ImportInscritsRepository,
    InscriptionRepository,
    LecteurFichierInscrits,
    TournoiRepository,
)
from domain.tournoi import TournoiId


class ServiceImportInscrits:
    def __init__(
        self,
        tournois: TournoiRepository,
        categories: CategorieRepository,
        departs: DepartRepository,
        archers: ArcherRepository,
        clubs: ClubRepository,
        inscriptions: InscriptionRepository,
        lecteur: LecteurFichierInscrits,
        ecrivain: ImportInscritsRepository,
        horloge: Horloge,
    ) -> None:
        self._tournois = tournois
        self._categories = categories
        self._departs = departs
        self._archers = archers
        self._clubs = clubs
        self._inscriptions = inscriptions
        self._lecteur = lecteur
        self._ecrivain = ecrivain
        self._horloge = horloge

    def lire(self, contenu: bytes) -> FichierInscrits:
        return self._lecteur.lire(contenu)

    def apercu(self, tournoi_id: TournoiId, contenu: bytes) -> PlanImport:
        """Le rapport de ce que ferait l'import, homonymes non cochés ; n'écrit rien."""
        return self._planifier(tournoi_id, self.lire(contenu), frozenset())

    def importer(
        self, tournoi_id: TournoiId, fichier: FichierInscrits, homonymes_acceptes: frozenset[int]
    ) -> PlanImport:
        """Écrit toutes les lignes importables en une transaction ; rend le rapport final."""
        plan = self._planifier(tournoi_id, fichier, homonymes_acceptes)
        if plan.importables:
            # Daté comme au guichet (E17US012) : non daté, l'import passerait pour la plus
            # ancienne dette du tournoi.
            self._ecrivain.appliquer(tournoi_id, plan, self._horloge.maintenant())
        return plan

    def _planifier(
        self, tournoi_id: TournoiId, fichier: FichierInscrits, homonymes_acceptes: frozenset[int]
    ) -> PlanImport:
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        departs = tuple(self._departs.par_tournoi(tournoi_id))
        instantane = InstantaneDuTournoi(
            date_tournoi=tournoi.date,
            categories=tuple(self._categories.par_tournoi(tournoi_id)),
            departs=departs,
            archers=tuple(self._archers.par_tournoi(tournoi_id)),
            clubs=tuple(self._clubs.lister()),
            inscriptions=tuple(
                inscription
                for depart in departs
                if depart.id is not None
                for inscription in self._inscriptions.par_depart(depart.id)
            ),
        )
        return planifier_import(fichier, instantane, homonymes_acceptes)
