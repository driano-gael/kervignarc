"""Service du **classement de qualification imprimable** — PDF, CSV, Excel (E09US005).

Le classement vient de `ServiceClassement`, jamais d'un calcul à part : le document affiché au mur
doit dire ce que dit l'écran (CA « même calcul que l'écran »).
"""

from __future__ import annotations

from collections.abc import Sequence

from application.classements import ServiceClassement
from application.erreurs import DepartIntrouvable, TournoiIntrouvable, TournoiSansDepart
from application.exports import FormatExport, RegistreDeFormats
from domain.categorie import Categorie
from domain.classement_imprime import (
    ClassementQualificationImprime,
    SectionClassementQualification,
    blocs_par_categorie,
    qualification_provisoire,
)
from domain.depart import Depart, DepartId
from domain.ports import (
    CategorieRepository,
    ClubRepository,
    DepartRepository,
    GenerateurClassementQualification,
    SerieRepository,
    TournoiRepository,
)
from domain.serie import Serie
from domain.tournoi import TournoiId


class ServiceClassementImprime:
    """Cas d'usage : sortir le classement de qualification d'un tournoi, par créneau."""

    def __init__(
        self,
        *,
        tournois: TournoiRepository,
        departs: DepartRepository,
        categories: CategorieRepository,
        clubs: ClubRepository,
        series: SerieRepository,
        classements: ServiceClassement,
        generateurs: RegistreDeFormats[GenerateurClassementQualification],
    ) -> None:
        self._tournois = tournois
        self._departs = departs
        self._categories = categories
        self._clubs = clubs
        self._series = series
        self._classements = classements
        self._generateurs = generateurs

    @property
    def formats_disponibles(self) -> tuple[FormatExport, ...]:
        """Formats que ce service sait produire — ce que le catalogue publie (ADR-0101 §3)."""
        return self._generateurs.formats

    def document(
        self, tournoi_id: TournoiId, depart_id: DepartId | None = None
    ) -> ClassementQualificationImprime:
        """Le contenu : tous les créneaux du tournoi, ou le seul `depart_id`.

        Lève `TournoiIntrouvable`, `TournoiSansDepart`, et `DepartIntrouvable` pour un départ
        inconnu **ou d'un autre tournoi**.
        """
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        departs = self._departs_retenus(tournoi_id, depart_id)
        categories = self._categories.par_tournoi(tournoi_id)
        return ClassementQualificationImprime(
            tournoi=tournoi.nom,
            sections=tuple(self._section(depart, categories) for depart in departs),
            clubs={club.id: club.nom for club in self._clubs.lister() if club.id is not None},
        )

    def imprimer(
        self,
        tournoi_id: TournoiId,
        depart_id: DepartId | None = None,
        format_: FormatExport = FormatExport.PDF,
    ) -> bytes:
        """Rend le document au format demandé ; `FormatExportIndisponible` s'il n'est pas câblé."""
        generateur = self._generateurs.pour(format_)
        return generateur.classement_qualification(self.document(tournoi_id, depart_id))

    def _departs_retenus(self, tournoi_id: TournoiId, depart_id: DepartId | None) -> list[Depart]:
        if depart_id is not None:
            depart = self._departs.par_id(depart_id)
            if depart is None or depart.tournoi_id != tournoi_id:
                raise DepartIntrouvable(f"Aucun départ {depart_id} dans le tournoi {tournoi_id}.")
            return [depart]
        departs = self._departs.par_tournoi(tournoi_id)
        if not departs:
            raise TournoiSansDepart(
                "Ce tournoi n'a aucun créneau : il n'y a pas de classement à imprimer."
            )
        return departs

    def _section(
        self, depart: Depart, categories: Sequence[Categorie]
    ) -> SectionClassementQualification:
        assert depart.id is not None, "Un départ relu du dépôt porte toujours son identifiant."
        # ⚠️ **La phase est choisie par `ServiceClassement`**, pas ici : juger le provisoire sur
        # une autre qualification que celle qui est classée mentirait sur la feuille.
        phase = self._classements.premiere_qualification(depart.id)
        classement = self._classements.pour_phase(depart.id, phase)
        if phase is None or phase.id is None:
            series: list[Serie] = []
            nb_volees = 0
        else:
            series = self._series.par_phase(phase.id)
            nb_volees = phase.bareme.nb_volees if phase.bareme is not None else 0
        return SectionClassementQualification(
            libelle=depart.libelle_creneau(),
            provisoire=qualification_provisoire(classement, series, nb_volees),
            categories=blocs_par_categorie(classement, categories),
        )
