"""Agrégat `Phase` et `SequencePhases` — les étapes d'un tournoi et leur enchaînement.

**Historique.** E01US009/ADR-0011 a introduit la `Phase` de façon **minimale et passive** : un seul
type (`qualification`), un `ordre` et un `statut` conformes au modèle de données mais qu'aucun code
n'exploitait. E01US015 a ajouté la 2ᵉ politique de qualification (le grain de validation).

**E05US001 / [ADR-0045] rend la séquence active** — c'est le socle du moteur de phases (jalon J2) :

- **Cycle de vie** : quatre statuts `a_venir → en_cours → terminee`, avec `en_cours ⇄ en_pause`
  réversible. `en_pause` **gèle une phase** pendant que le reste du tournoi vit (distinct du
  `en_pause` **de tournoi**, ADR-0026 §3). L'agrégat porte la **valeur** et des transitions
  **pures** ; le service arbitre l'enchaînement (patron `ServiceTournois`).
- **Typage ouvert** : `elimination_directe` et `placement` rejoignent `qualification`. Déclarer un
  type ne présuppose pas son moteur ; leurs politiques propres viendront en E05US003. En
  conséquence, `bareme`/`validation` deviennent **facultatifs** (obligatoires pour `qualification`
  seulement).
- **Peuplement minimal** : une phase peut être alimentée par une `SourcePhase` (« rangs [a..b] de la
  phase d'ordre k »). Amorce **provisoire** (une source, une plage — pas de routing ni de
  gagnants/perdants ; modèle complet = E05US010) inscrite en DETTE-015. Elle suffit à décider les
  trois contrôles de cohérence du CA (source vide / rangs inexistants / effectif incompatible),
  portés par l'agrégat pur `SequencePhases`.

La **forme JSON** de la config est une préoccupation du **repository** (l'agrégat pur ci-dessous ne
sérialise rien) : depuis E05US003/ADR-0046, les politiques du moteur y vivent sous `config.policies`
(le barème sous `config.policies.scoring`), le grain de `validation` restant à la racine. Agrégats
de domaine **purs** (immuables, sans dépendance framework).

[ADR-0045]: ../../docs/adr/0045-sequence-de-phases-cycle-de-vie-typage-source.md
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from domain.bareme import BaremeQualification
from domain.erreurs import (
    CadenceValidationSuperieureAuBareme,
    EffectifIncompatible,
    EffectifPhaseInvalide,
    GrainIncompatibleAvecTypePhase,
    PhaseQualificationIncomplete,
    PlageSourceVide,
    RangSourceInvalide,
    RangsSourceInexistants,
    SequenceOrdreInvalide,
    SourceApresPhase,
    SourceIntrouvable,
)
from domain.grain_validation import GrainValidation, TypeGrain
from domain.tournoi import TournoiId

PhaseId = int
"""Identifiant technique d'une phase, attribué par la persistance."""


class TypePhase(str, Enum):
    """Type d'une phase. E05US001 ouvre le typage aux formats dont la **règle est écrite** ; les
    autres (barrage, finale, big_shoot_off, poules…) s'ajouteront avec l'US qui les implémente —
    on n'offre pas en façade un type qu'aucun moteur ne sait dérouler (ADR-0045 §2)."""

    QUALIFICATION = "qualification"
    ELIMINATION_DIRECTE = "elimination_directe"
    PLACEMENT = "placement"


class StatutPhase(str, Enum):
    """Cycle de vie d'une phase (E05US001, ADR-0045 §1).

    `a_venir` → **démarrer** → `en_cours` → **terminer** → `terminee`, avec
    `en_cours` ⇄ `en_pause` réversible (**mettre en pause** / **reprendre**). `en_pause` **gèle**
    la phase (aucune validation de score) — distinct du `en_pause` du **tournoi** (ADR-0026 §3),
    même intention à une autre maille. Comme le tournoi, l'agrégat ne porte que la **valeur** :
    l'enchaînement (qui passe de quoi à quoi) est arbitré par le service (409 si illégal).
    """

    A_VENIR = "a_venir"
    EN_COURS = "en_cours"
    EN_PAUSE = "en_pause"
    TERMINEE = "terminee"


# Grains admis par type de phase (`D-11`). La qualification se tire en séries et ne comporte
# **pas** de duels : « fin de duel » n'y a pas de sens. Les phases à duels (elimination_directe…)
# n'ont pas encore de grain déclaré ici : leur politique de scoring vient en E05US003 (leur
# `validation` reste `None` en E05US001).
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

    Lève `GrainIncompatibleAvecTypePhase` si le type n'a pas de preset déclaré (les types à duels,
    dont le preset viendra avec E05US003) : explicite plutôt qu'un `KeyError` que `_vers_phase`
    diagnostiquerait « configuration illisible ».
    """
    preset = _GRAIN_PAR_DEFAUT.get(type_phase)
    if preset is None:
        raise GrainIncompatibleAvecTypePhase(
            f"Aucun grain de validation par défaut n'est déclaré pour une phase de type "
            f"« {type_phase.value} »."
        )
    return preset


@dataclass(frozen=True)
class SourcePhase:
    """Peuplement d'une phase par une autre — **amorce minimale** (E05US001, ADR-0045 §3).

    Une phase est alimentée par « les rangs `[rang_debut..rang_fin]` du classement de la phase
    d'ordre `ordre_source` ». C'est un value object **pur**, validé à la construction sur ce qui ne
    dépend **pas** de la séquence (rang de début ≥ 1, plage non vide) ; les contrôles inter-phases
    (la source existe, est antérieure, tient dans son effectif) vivent dans `SequencePhases`.

    # DETTE-015 — modèle **provisoire** : une seule source, une plage de rangs, **pas** de routing
    ni de distinction gagnants/perdants. Le modèle complet (sources multiples, cascade, division
    récursive) est le cœur d'E05US010 ; celui-ci en est le sous-cas le plus simple.
    """

    ordre_source: int
    rang_debut: int
    rang_fin: int

    def __post_init__(self) -> None:
        if self.rang_debut < 1:
            raise RangSourceInvalide(
                f"Une source prélève à partir du rang 1 : « {self.rang_debut} » n'existe pas."
            )
        if self.rang_fin < self.rang_debut:
            raise PlageSourceVide(
                f"La plage de rangs [{self.rang_debut}..{self.rang_fin}] est vide : "
                "elle ne prélève aucun participant."
            )

    @property
    def effectif_selectionne(self) -> int:
        """Nombre de participants que la plage prélève (bornes incluses)."""
        return self.rang_fin - self.rang_debut + 1


@dataclass(frozen=True)
class Phase:
    """Une phase d'un tournoi. `id` vaut `None` tant qu'elle n'est pas persistée.

    `bareme` et `validation` ne concernent que la **qualification** (barème de cumul + grain,
    `D-11`) : ils sont `None` pour les autres types, dont les politiques propres viendront en
    E05US003 (ADR-0045 §2). `source` décrit d'où la phase tire ses participants (`None` = première
    de la séquence, alimentée par les inscriptions). `effectif` (facultatif) déclare combien de
    participants la phase classe/produit — il borne les rangs prélevables et sert au contrôle
    « effectif incompatible ».

    **Invariants** (vérifiés à chaque construction, `replace()` compris) : effectif ≥ 1 s'il est
    déclaré ; une phase de `qualification` porte barème **et** grain ; le grain — s'il y en a un —
    est admis par le type et sa cadence ne dépasse pas le barème.
    """

    tournoi_id: TournoiId
    ordre: int
    type: TypePhase
    bareme: BaremeQualification | None = None
    validation: GrainValidation | None = None
    source: SourcePhase | None = None
    effectif: int | None = None
    statut: StatutPhase = StatutPhase.A_VENIR
    id: PhaseId | None = None

    def __post_init__(self) -> None:
        """Fait respecter la cohérence quelle que soit la porte d'entrée (fabriques **et**
        `replace()`, qui repasse par ici)."""
        if self.effectif is not None and self.effectif < 1:
            raise EffectifPhaseInvalide(
                "L'effectif d'une phase, s'il est déclaré, compte au moins un participant."
            )
        if self.type is TypePhase.QUALIFICATION and (
            self.bareme is None or self.validation is None
        ):
            raise PhaseQualificationIncomplete(
                "Une phase de qualification porte un barème et un grain de validation."
            )
        if self.validation is not None:
            _verifier_grain_admis(self.type, self.validation)
            if self.bareme is not None:
                _verifier_cadence_couverte(self.validation, self.bareme)

    @staticmethod
    def qualification(
        tournoi_id: TournoiId,
        bareme: BaremeQualification,
        validation: GrainValidation | None = None,
    ) -> Phase:
        """Crée la phase de **qualification** d'un tournoi (première de la séquence, `ordre=1`).

        Sans grain explicite, applique le preset du type (`fin de série`, `D-11`) : une phase de
        qualification existe toujours **avec** un grain, jamais sans.
        """
        return Phase(
            tournoi_id=tournoi_id,
            ordre=1,
            type=TypePhase.QUALIFICATION,
            bareme=bareme,
            validation=validation or grain_par_defaut(TypePhase.QUALIFICATION),
            statut=StatutPhase.A_VENIR,
        )

    @staticmethod
    def creer(
        tournoi_id: TournoiId,
        ordre: int,
        type: TypePhase,
        source: SourcePhase | None = None,
        effectif: int | None = None,
    ) -> Phase:
        """Crée une phase **générique** (E05US001) à un rang donné de la séquence, statut `a venir`.

        Pour une phase de `qualification`, préférer `Phase.qualification` (qui exige le barème) —
        appelée ici, elle lèverait `PhaseQualificationIncomplete` faute de barème.
        """
        return Phase(
            tournoi_id=tournoi_id,
            ordre=ordre,
            type=type,
            source=source,
            effectif=effectif,
            statut=StatutPhase.A_VENIR,
        )

    def avec_bareme(self, bareme: BaremeQualification) -> Phase:
        """Renvoie une copie au barème mis à jour ; le reste est préservé.

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

    def avec_ordre(self, ordre: int) -> Phase:
        """Renvoie une copie à un nouveau rang dans la séquence (réordonnancement)."""
        return replace(self, ordre=ordre)

    def avec_type(self, type: TypePhase) -> Phase:
        """Renvoie une copie d'un autre type. La cohérence type/grain/barème est revérifiée.

        Retyper une qualification en un type à duels sans purger barème/grain lèverait
        `GrainIncompatibleAvecTypePhase` : le service décide quoi faire du barème (le retyper
        en profondeur relève de l'édition métier, hors amorce E05US001).
        """
        return replace(self, type=type)

    def avec_source(self, source: SourcePhase | None) -> Phase:
        """Renvoie une copie à la source (peuplement) mise à jour ; `None` = alimentée par les
        inscriptions (première de la séquence)."""
        return replace(self, source=source)

    def avec_effectif(self, effectif: int | None) -> Phase:
        """Renvoie une copie à l'effectif déclaré mis à jour ; `None` = non déclaré."""
        return replace(self, effectif=effectif)

    def demarrer(self) -> Phase:
        """Copie passée `en_cours` (précondition `a_venir` garantie par le service)."""
        return replace(self, statut=StatutPhase.EN_COURS)

    def mettre_en_pause(self) -> Phase:
        """Copie passée `en_pause` (précondition `en_cours` garantie par le service)."""
        return replace(self, statut=StatutPhase.EN_PAUSE)

    def reprendre(self) -> Phase:
        """Copie repassée `en_cours` (précondition `en_pause` garantie par le service)."""
        return replace(self, statut=StatutPhase.EN_COURS)

    def terminer(self) -> Phase:
        """Copie passée `terminee` (précondition `en_cours` garantie par le service)."""
        return replace(self, statut=StatutPhase.TERMINEE)


@dataclass(frozen=True)
class SequencePhases:
    """La séquence **ordonnée** des phases d'un tournoi, gardienne de sa cohérence (E05US001).

    Value object pur validé à la construction : les ordres forment la suite contiguë 1..N, et
    chaque source désigne une phase **antérieure** existante dont l'effectif couvre les rangs
    prélevés, avec un compte compatible (ADR-0045 §3). Le service assemble les phases relues du
    dépôt en `SequencePhases` — dont la construction **rejette** une séquence incohérente — avant
    de persister une édition. Une séquence **vide** est licite (tournoi sans phase composée).
    """

    phases: tuple[Phase, ...]

    def __post_init__(self) -> None:
        _verifier_ordres(self.phases)
        _verifier_sources(self.phases)


def _verifier_grain_admis(type_phase: TypePhase, validation: GrainValidation) -> None:
    # `.get` plutôt qu'une indexation : un type sans entrée n'admet aucun grain, ce qui donne un
    # `GrainIncompatibleAvecTypePhase` au message exact — pas un `KeyError` nu.
    admis = _GRAINS_ADMIS.get(type_phase, frozenset())
    if validation.type not in admis:
        raise GrainIncompatibleAvecTypePhase(
            f"Le grain « {validation.type.value} » ne s'applique pas à une phase "
            f"de type « {type_phase.value} »."
        )


def _verifier_cadence_couverte(validation: GrainValidation, bareme: BaremeQualification) -> None:
    """Garantit qu'**au moins une** validation aura lieu — pas que la cadence divise le barème.

    Une cadence de 3 sur 20 volées donne 6 validations, la dernière à la volée 18 : les volées 19-20
    restent hors cadence. Ni les CA d'E01US015 ni le CDC n'exigent la divisibilité, et l'imposer
    interdirait des réglages légitimes (7 volées sur 20). **C'est E04US002 qui devra décider** si ce
    reliquat déclenche une validation de fin — la validation étant réglementairement un acte *de
    fin* (CDC UX §7.3), c'est probable ; ce n'est pas à la configuration de le préempter.
    """
    if validation.n_volees is None:
        return
    if validation.n_volees > bareme.nb_volees:
        raise CadenceValidationSuperieureAuBareme(
            f"Valider toutes les {validation.n_volees} volées est impossible sur un barème qui "
            f"n'en compte que {bareme.nb_volees} : aucune validation n'aurait lieu."
        )


def _verifier_ordres(phases: tuple[Phase, ...]) -> None:
    """Les ordres doivent former la suite contiguë 1..N (ni trou, ni doublon, ni départ décalé)."""
    ordres = sorted(phase.ordre for phase in phases)
    if ordres != list(range(1, len(phases) + 1)):
        raise SequenceOrdreInvalide(
            "Les phases d'une séquence sont numérotées 1, 2, 3… sans trou ni doublon : "
            f"ordres reçus {ordres}."
        )


def _verifier_sources(phases: tuple[Phase, ...]) -> None:
    """Chaque source désigne une phase antérieure existante, dont l'effectif couvre les rangs
    prélevés, avec un compte compatible avec l'effectif de la phase consommatrice."""
    par_ordre = {phase.ordre: phase for phase in phases}
    for phase in phases:
        source = phase.source
        if source is None:
            continue
        phase_source = par_ordre.get(source.ordre_source)
        if phase_source is None:
            raise SourceIntrouvable(
                f"La phase {phase.ordre} est alimentée par une phase d'ordre "
                f"{source.ordre_source}, qui n'existe pas dans la séquence."
            )
        if source.ordre_source >= phase.ordre:
            raise SourceApresPhase(
                f"La phase {phase.ordre} ne peut être alimentée que par une phase antérieure ; "
                f"l'ordre {source.ordre_source} lui est égal ou postérieur."
            )
        if phase_source.effectif is not None and source.rang_fin > phase_source.effectif:
            raise RangsSourceInexistants(
                f"La source prélève jusqu'au rang {source.rang_fin}, mais la phase "
                f"{source.ordre_source} n'en classe que {phase_source.effectif}."
            )
        if phase.effectif is not None and source.effectif_selectionne != phase.effectif:
            raise EffectifIncompatible(
                f"La phase {phase.ordre} attend {phase.effectif} participants, mais sa source en "
                f"prélève {source.effectif_selectionne}."
            )
