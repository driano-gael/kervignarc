"""Grain de validation — une politique de la phase de qualification (ADR-0011).

⚠️ **`definir` ne CRÉE pas la phase**, contrairement au barème : régler le grain d'une
qualification sans barème supposerait d'en inventer un que l'organisateur n'a pas choisi. Le barème
d'abord, le grain ensuite (404 sinon). ⚠️ Le grain vit sur l'**étape** du déroulé (ADR-0076), donc
se définit **une fois** pour le tournoi — l'écriture en éventail laissait deux créneaux diverger.
"""

from __future__ import annotations

from dataclasses import replace

from application.erreurs import (
    PhaseIntrouvable,
    PhasePasUneQualification,
    PhaseQualificationAbsente,
    TournoiIntrouvable,
)
from domain.deroule_etape import EtapeDeroule, EtapeDerouleId
from domain.grain_validation import GrainValidation, TypeGrain
from domain.phase import TypePhase
from domain.ports import DerouleRepository, TournoiRepository
from domain.tournoi import TournoiId


class ServiceGrainValidation:
    """Cas d'usage du grain de validation : lire, définir (preset du type ou cadence libre)."""

    def __init__(self, tournois: TournoiRepository, deroules: DerouleRepository) -> None:
        self._tournois = tournois
        # Le **déroulé**, et non les phases : le grain est une donnée de définition (ADR-0076).
        # Passer par `PhaseRepository.enregistrer` serait pire qu'inutile — le port ne déplace que
        # l'avancement, si bien que l'écriture *paraîtrait* réussir sans rien changer.
        self._deroules = deroules

    # DETTE-053 : le nom promet un réglage de tournoi, le code rend celui de la première phase.
    def grain_du_tournoi(self, tournoi_id: TournoiId) -> GrainValidation | None:
        """Le grain de la **première** qualification, ou `None` si le barème n'est pas défini.

        ⚠️ **Le nom ment depuis E05US025**, comme celui de `bareme_du_tournoi` — et lui le disait
        (relevé de revue). Un déroulé peut porter plusieurs qualifications, chacune avec **son**
        grain : cette lecture rend celui de la première, conservée parce que la route historique la
        sert (`DETTE-053`). Lève `TournoiIntrouvable`.
        """
        self._tournoi_existant(tournoi_id)
        etape = self._qualification_ou_none(tournoi_id)
        return None if etape is None else etape.validation

    def definir(
        self, tournoi_id: TournoiId, type_grain: TypeGrain, n_volees: int | None
    ) -> GrainValidation:
        """Définit le grain de validation de la qualification d'un tournoi.

        Lève `TournoiIntrouvable`, `PhaseQualificationAbsente` si le barème n'est pas défini, et
        `DomainError` si le grain est invalide (cadence `< 1`) ou incohérent avec la phase. ⚠️ La
        cohérence grain ↔ barème est éprouvée par la construction de l'`EtapeDeroule` remplacée
        (`__post_init__`), donc **avant** toute écriture : refus sans que la base ait bougé.
        """
        self._tournoi_existant(tournoi_id)
        grain = GrainValidation.creer(type_grain, n_volees)
        # **Une seule écriture** (ADR-0076) : le déroulé est défini une fois, tous les créneaux le
        # rejouent. Un scoreur ne peut donc plus voir sa tablette valider à un autre rythme selon
        # l'heure de son départ — la divergence n'est pas improbable, elle est impossible.
        etape = self._qualification(tournoi_id)
        self._deroules.enregistrer(replace(etape, validation=grain))
        # Le grain persisté est celui qu'on vient d'écrire ; le renvoyer directement évite de
        # re-narrower `validation` (optionnel depuis E05US001, toujours présent sur une
        # qualification — ADR-0045 §2).
        return grain

    def definir_pour_etape(
        self,
        tournoi_id: TournoiId,
        etape_id: EtapeDerouleId,
        type_grain: TypeGrain,
        n_volees: int | None,
    ) -> GrainValidation:
        """Règle le grain d'une **étape désignée** (E05US025, ADR-0082).

        Pendant de `ServiceBaremeQualification.definir_pour_etape` : rien n'oblige la *haute* à
        valider au même rythme que le premier tour, et le CA le demande explicitement. Lève
        `TournoiIntrouvable`, `PhaseIntrouvable` (étape hors de ce tournoi),
        `PhasePasUneQualification`, ou `DomainError` — éprouvée **avant** toute écriture.
        """
        self._tournoi_existant(tournoi_id)
        grain = GrainValidation.creer(type_grain, n_volees)
        etape = next((e for e in self._deroules.par_tournoi(tournoi_id) if e.id == etape_id), None)
        if etape is None:
            raise PhaseIntrouvable(
                f"Aucune étape d'identifiant {etape_id} dans le déroulé du tournoi {tournoi_id}."
            )
        if etape.type is not TypePhase.QUALIFICATION:
            raise PhasePasUneQualification(
                f"L'étape {etape_id} est de type « {etape.type.value} » : un grain de "
                "validation de série ne se règle que sur une qualification."
            )
        self._deroules.enregistrer(replace(etape, validation=grain))
        return grain

    def _tournoi_existant(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")

    def _qualification_ou_none(self, tournoi_id: TournoiId) -> EtapeDeroule | None:
        return next(
            (
                etape
                for etape in self._deroules.par_tournoi(tournoi_id)
                if etape.type is TypePhase.QUALIFICATION
            ),
            None,
        )

    def _qualification(self, tournoi_id: TournoiId) -> EtapeDeroule:
        """L'étape de qualification du déroulé ; lève si le tournoi n'en a pas."""
        etape = self._qualification_ou_none(tournoi_id)
        if etape is None:
            raise PhaseQualificationAbsente(
                "Le grain de validation se règle sur la qualification du tournoi : "
                "définissez d'abord son barème."
            )
        return etape
