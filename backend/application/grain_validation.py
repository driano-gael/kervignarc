"""Service applicatif Grain de validation (E01US015 / `D-11`).

Orchestre le domaine derrière les ports repository. Ne connaît ni HTTP, ni SQL, ni la file
d'écriture (sérialisation assurée en amont, côté API) ; il reste synchrone et pur
d'infrastructure.

Le grain de validation d'un tournoi est une **politique de sa phase** de qualification (ADR-0011),
sérialisée dans `config.validation` à côté du barème. Contrairement au barème, `definir` **ne crée
pas** la phase : régler le grain d'une qualification dont le barème n'est pas encore défini
supposerait d'inventer un barème que l'organisateur n'a pas choisi. Le cas remonte donc en
`PhaseQualificationAbsente` (404) — le barème d'abord, le grain ensuite.

⚠️ **Le grain vit sur l'étape du déroulé** depuis ADR-0076, pas sur la phase de chaque créneau : il
se définit **une fois** pour le tournoi. Avant, ce service écrivait « en éventail » — une fois par
départ — et la seule chose qui empêchait deux créneaux de valider à des rythmes différents était
que personne n'avait édité l'un sans l'autre.
"""

from __future__ import annotations

from dataclasses import replace

from application.erreurs import PhaseQualificationAbsente, TournoiIntrouvable
from domain.deroule_etape import EtapeDeroule
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

    def grain_du_tournoi(self, tournoi_id: TournoiId) -> GrainValidation | None:
        """Renvoie le grain de validation de la qualification, ou `None` si la phase n'existe pas
        encore (barème non défini).

        Lève `TournoiIntrouvable` si le tournoi n'existe pas.
        """
        self._tournoi_existant(tournoi_id)
        etape = self._qualification_ou_none(tournoi_id)
        return None if etape is None else etape.validation

    def definir(
        self, tournoi_id: TournoiId, type_grain: TypeGrain, n_volees: int | None
    ) -> GrainValidation:
        """Définit le grain de validation de la qualification d'un tournoi.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas, `PhaseQualificationAbsente` si son
        barème n'est pas encore défini, et `DomainError` si le grain est invalide (cadence `< 1` ou
        manquante) ou incohérent avec la phase (grain hors du type, cadence au-delà du barème).

        La cohérence grain ↔ barème est éprouvée par la construction de l'`EtapeDeroule` remplacée
        (`__post_init__`), donc **avant** toute écriture : un grain plus fin que le barème est
        refusé sans que la base ait bougé.
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
