"""Service du **déroulé horaire imprimable** — PDF seul (E09US007).

Les heures viennent de `ServicePhases.horaires_prevus`, la lecture que sert l'écran (ADR-0118) :
le papier ne recalcule rien.
"""

from __future__ import annotations

from application.erreurs import DepartIntrouvable, TournoiIntrouvable, TournoiSansDepart
from application.exports import FormatExport, RegistreDeFormats
from application.phases import HorairesDuDepart, ServicePhases
from domain.depart import DepartId
from domain.deroule_imprime import BlocDeroule, DerouleImprime, lignes_du_deroule
from domain.ports import GenerateurDerouleHoraire, TournoiRepository
from domain.tournoi import TournoiId


class ServiceDerouleImprime:
    """Cas d'usage : sortir le déroulé horaire d'un tournoi, un bloc par créneau."""

    def __init__(
        self,
        *,
        tournois: TournoiRepository,
        phases: ServicePhases,
        generateurs: RegistreDeFormats[GenerateurDerouleHoraire],
    ) -> None:
        self._tournois = tournois
        self._phases = phases
        self._generateurs = generateurs

    @property
    def formats_disponibles(self) -> tuple[FormatExport, ...]:
        """Formats que ce service sait produire — ce que le catalogue publie (ADR-0101 §3)."""
        return self._generateurs.formats

    def document(self, tournoi_id: TournoiId, depart_id: DepartId | None = None) -> DerouleImprime:
        """Tous les créneaux du tournoi, ou le seul `depart_id`.

        Lève `TournoiIntrouvable`, `TournoiSansDepart`, et `DepartIntrouvable` pour un départ
        inconnu **ou d'un autre tournoi**.
        """
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        etapes = self._phases.lister(tournoi_id)
        return DerouleImprime(
            tournoi=tournoi.nom,
            blocs=tuple(
                BlocDeroule(
                    libelle=creneau.depart.libelle_creneau(),
                    lignes=lignes_du_deroule(etapes, creneau.horaires),
                )
                for creneau in self._creneaux_retenus(tournoi_id, depart_id)
            ),
        )

    def imprimer(
        self,
        tournoi_id: TournoiId,
        depart_id: DepartId | None = None,
        format_: FormatExport = FormatExport.PDF,
    ) -> bytes:
        """Rend le document au format demandé ; `FormatExportIndisponible` s'il n'est pas câblé."""
        generateur = self._generateurs.pour(format_)
        return generateur.deroule_horaire(self.document(tournoi_id, depart_id))

    def _creneaux_retenus(
        self, tournoi_id: TournoiId, depart_id: DepartId | None
    ) -> list[HorairesDuDepart]:
        # L'ordre des départs est celui du port (`DepartRepository.par_tournoi`, par numéro).
        creneaux = list(self._phases.horaires_prevus(tournoi_id))
        if depart_id is not None:
            retenus = [c for c in creneaux if c.depart.id == depart_id]
            if not retenus:
                raise DepartIntrouvable(f"Aucun départ {depart_id} dans le tournoi {tournoi_id}.")
            return retenus
        if not creneaux:
            raise TournoiSansDepart(
                "Ce tournoi n'a aucun créneau : il n'y a pas de déroulé à imprimer."
            )
        return creneaux
