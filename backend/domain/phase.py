"""Agrégat `Phase` — une étape d'un tournoi (introduction **minimale**, E01US009 / ADR-0011).

Le modèle cible (ADR-0004) fait de la phase le porteur des **politiques injectables** du moteur
(routage, barème, seeding, byes, départage, profondeur), stockées dans sa `config`. Ce moteur
relève d'EPIC-05 ; E01US009 n'introduit que ce qu'il faut pour héberger le **barème de
qualification** là où le modèle de données l'attend : une phase de type `qualification` par
tournoi, portant un `BaremeQualification` (sérialisé dans `config.scoring`).

E01US015 ajoute la deuxième politique annoncée par l'ADR-0011 (« les autres politiques y viendront
sans changement de schéma ») : le **grain de validation** (`GrainValidation`, sérialisé dans
`config.validation`, `D-11`). La phase porte donc désormais **deux** politiques, et devient le
gardien de leur **cohérence** : une cadence « toutes les N volées » qui dépasse le barème ne
validerait jamais.

Périmètre volontairement réduit (cf. ADR-0011) : `ordre` et `statut` sont conformes au modèle de
données mais **passifs** (aucune transition, aucune séquence) — le moteur les exploitera. Agrégat
de domaine **pur** (immuable, sans dépendance framework).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from domain.bareme import BaremeQualification
from domain.erreurs import CadenceValidationSuperieureAuBareme, GrainIncompatibleAvecTypePhase
from domain.grain_validation import GrainValidation, TypeGrain
from domain.tournoi import TournoiId

PhaseId = int
"""Identifiant technique d'une phase, attribué par la persistance."""


class TypePhase(str, Enum):
    """Type d'une phase. E01US009 n'utilise que `qualification` ; le moteur (EPIC-05) ajoutera
    les autres (barrage, tableau, placement, finale, big_shoot_off)."""

    QUALIFICATION = "qualification"


class StatutPhase(str, Enum):
    """Cycle de vie d'une phase (modèle de données). Passif en E01US009 : aucune transition n'est
    encore définie (elles viendront avec le moteur, EPIC-05)."""

    A_VENIR = "a_venir"
    EN_COURS = "en_cours"
    TERMINEE = "terminee"


# Grains admis par type de phase (`D-11`). La qualification se tire en séries et ne comporte
# **pas** de duels : « fin de duel » n'y a pas de sens. Le moteur (EPIC-05) étendra cette table
# aux phases à duels, dont le preset sera `FIN_DE_DUEL`.
_GRAINS_ADMIS: dict[TypePhase, frozenset[TypeGrain]] = {
    TypePhase.QUALIFICATION: frozenset({TypeGrain.FIN_DE_SERIE, TypeGrain.TOUTES_LES_N_VOLEES}),
}

# Grain par défaut de chaque type de phase (« presets cohérents par type de phase », `D-11`).
_GRAIN_PAR_DEFAUT: dict[TypePhase, GrainValidation] = {
    TypePhase.QUALIFICATION: GrainValidation.fin_de_serie(),
}


def grain_par_defaut(type_phase: TypePhase) -> GrainValidation:
    """Le grain preset d'un type de phase — `fin de série` pour la qualification (`D-11`).

    Sert à la création d'une phase **et** à la relecture d'une phase antérieure à E01US015, dont la
    `config` ne porte pas encore de clé `validation` (cf. `repositories._vers_phase`).
    """
    return _GRAIN_PAR_DEFAUT[type_phase]


@dataclass(frozen=True)
class Phase:
    """Une phase d'un tournoi. `id` vaut `None` tant qu'elle n'est pas persistée.

    En E01US009/E01US015, seules des phases `qualification` existent ; `bareme` porte alors le
    barème de qualification et `validation` le grain de validation (`D-11`). `ordre` (position dans
    la future séquence) et `statut` sont conformes au modèle cible mais non encore exploités
    (ADR-0011).

    **Invariants** (vérifiés à chaque construction) : le grain doit être admis par le type de phase,
    et sa cadence — s'il en a une — ne peut pas dépasser le nombre de volées du barème.
    """

    tournoi_id: TournoiId
    ordre: int
    type: TypePhase
    bareme: BaremeQualification
    validation: GrainValidation
    statut: StatutPhase = StatutPhase.A_VENIR
    id: PhaseId | None = None

    def __post_init__(self) -> None:
        """Fait respecter la cohérence (type, grain, barème) — quelle que soit la porte d'entrée.

        Placé ici plutôt que dans les fabriques : `replace()` reconstruit l'agrégat et repasse donc
        par cette vérification, ce qui garantit qu'`avec_bareme` comme `avec_validation` ne peuvent
        pas créer une phase incohérente.
        """
        _verifier_grain_admis(self.type, self.validation)
        _verifier_cadence_couverte(self.validation, self.bareme)

    @staticmethod
    def qualification(
        tournoi_id: TournoiId,
        bareme: BaremeQualification,
        validation: GrainValidation | None = None,
    ) -> Phase:
        """Crée la phase de **qualification** d'un tournoi (première de la séquence, `ordre=1`).

        Sans grain explicite, applique le preset du type (`fin de série`, `D-11`) : une phase existe
        toujours **avec** un grain, jamais sans.
        """
        return Phase(
            tournoi_id=tournoi_id,
            ordre=1,
            type=TypePhase.QUALIFICATION,
            bareme=bareme,
            validation=validation or grain_par_defaut(TypePhase.QUALIFICATION),
            statut=StatutPhase.A_VENIR,
        )

    def avec_bareme(self, bareme: BaremeQualification) -> Phase:
        """Renvoie une copie au barème mis à jour ; `id`, `tournoi_id`, `ordre` et `statut` sont
        préservés.

        Lève `CadenceValidationSuperieureAuBareme` si le nouveau barème compte moins de volées que
        la cadence du grain en place : il faut alors ajuster le grain d'abord.
        """
        return replace(self, bareme=bareme)

    def avec_validation(self, validation: GrainValidation) -> Phase:
        """Renvoie une copie au grain de validation mis à jour ; le reste est préservé.

        Lève `GrainIncompatibleAvecTypePhase` si le grain n'a pas de sens pour ce type de phase, et
        `CadenceValidationSuperieureAuBareme` si sa cadence dépasse le barème en place.
        """
        return replace(self, validation=validation)


def _verifier_grain_admis(type_phase: TypePhase, validation: GrainValidation) -> None:
    admis = _GRAINS_ADMIS[type_phase]
    if validation.type not in admis:
        raise GrainIncompatibleAvecTypePhase(
            f"Le grain « {validation.type.value} » ne s'applique pas à une phase "
            f"de type « {type_phase.value} »."
        )


def _verifier_cadence_couverte(validation: GrainValidation, bareme: BaremeQualification) -> None:
    if validation.n_volees is None:
        return
    if validation.n_volees > bareme.nb_volees:
        raise CadenceValidationSuperieureAuBareme(
            f"Valider toutes les {validation.n_volees} volées est impossible sur un barème qui "
            f"n'en compte que {bareme.nb_volees} : aucune validation n'aurait lieu."
        )
