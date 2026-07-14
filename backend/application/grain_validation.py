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
from domain.grain_validation import GrainValidation, TypeGrain
from domain.phase import Phase, TypePhase
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
        phase = self._phases.par_tournoi_et_type(tournoi_id, TypePhase.QUALIFICATION)
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
        phase = self._phase_de_qualification(tournoi_id)
        modifiee = self._phases.enregistrer(phase.avec_validation(grain))
        return modifiee.validation

    def _tournoi_existant(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")

    def _phase_de_qualification(self, tournoi_id: TournoiId) -> Phase:
        phase = self._phases.par_tournoi_et_type(tournoi_id, TypePhase.QUALIFICATION)
        if phase is None:
            raise PhaseQualificationAbsente(
                "Le grain de validation se règle sur la qualification du tournoi : "
                "définissez d'abord son barème."
            )
        return phase
