"""Service applicatif Grain de validation (E01US015 / `D-11`).

Orchestre le domaine derrière les ports repository. Ne connaît ni HTTP, ni SQL, ni la file
d'écriture (sérialisation assurée en amont, côté API) ; il reste synchrone et pur
d'infrastructure.

Le grain de validation d'un tournoi est une **politique de sa phase** de qualification (ADR-0011),
sérialisée dans `config.validation` à côté du barème. Contrairement au barème, `definir` **ne crée
pas** la phase : régler le grain d'une qualification dont le barème n'est pas encore défini
supposerait d'inventer un barème que l'organisateur n'a pas choisi. Le cas remonte donc en
`PhaseQualificationAbsente` (404) — le barème d'abord, le grain ensuite.
"""

from __future__ import annotations

from application.erreurs import PhaseQualificationAbsente, TournoiIntrouvable
from application.portee import (
    qualification_representative,
    qualifications_de_chaque_depart,
)
from domain.grain_validation import GrainValidation, TypeGrain
from domain.phase import Phase
from domain.ports import PhaseRepository, TournoiRepository
from domain.tournoi import TournoiId


class ServiceGrainValidation:
    """Cas d'usage du grain de validation : lire, définir (preset du type ou cadence libre)."""

    def __init__(self, tournois: TournoiRepository, phases: PhaseRepository) -> None:
        self._tournois = tournois
        self._phases = phases

    def grain_du_tournoi(self, tournoi_id: TournoiId) -> GrainValidation | None:
        """Renvoie le grain de validation de la qualification, ou `None` si la phase n'existe pas
        encore (barème non défini).

        Lève `TournoiIntrouvable` si le tournoi n'existe pas.
        """
        self._tournoi_existant(tournoi_id)
        phase = qualification_representative(self._phases, tournoi_id)
        return None if phase is None else phase.validation

    def definir(
        self, tournoi_id: TournoiId, type_grain: TypeGrain, n_volees: int | None
    ) -> GrainValidation:
        """Définit le grain de validation de la qualification d'un tournoi.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas, `PhaseQualificationAbsente` si son
        barème n'est pas encore défini, et `DomainError` si le grain est invalide (cadence `< 1` ou
        manquante) ou incohérent avec la phase (grain hors du type, cadence au-delà du barème).
        """
        self._tournoi_existant(tournoi_id)
        grain = GrainValidation.creer(type_grain, n_volees)
        # **Écriture en éventail** (E01US025, ADR-0075) : la qualification vit par départ, donc
        # régler « le grain du tournoi » l'écrit sur chacune. N'en servir qu'une laisserait les
        # autres créneaux valider à un autre rythme — un scoreur verrait sa tablette se comporter
        # différemment selon l'heure, sans que rien ne l'explique.
        for phase in self._qualifications(tournoi_id):
            self._phases.enregistrer(phase.avec_validation(grain))
        # Le grain persisté est celui qu'on vient d'écrire ; le renvoyer directement évite de
        # re-narrower `validation` (optionnel depuis E05US001, toujours présent sur une
        # qualification — ADR-0045 §2).
        return grain

    def _tournoi_existant(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")

    def _qualifications(self, tournoi_id: TournoiId) -> list[Phase]:
        """Les qualifications de **tous** les départs ; lève si le tournoi n'en a aucune."""
        phases = qualifications_de_chaque_depart(self._phases, tournoi_id)
        if not phases:
            raise PhaseQualificationAbsente(
                "Le grain de validation se règle sur la qualification du tournoi : "
                "définissez d'abord son barème."
            )
        return phases
