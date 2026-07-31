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
- **Peuplement** : une phase est alimentée par des `SourcePhase`. E05US001 n'en admettait
  qu'**une**,
  « rangs [a..b] de la phase d'ordre k » (amorce inscrite en DETTE-015) ; **E05US010 / [ADR-0061] a
  livré le modèle complet et résorbé cette dette** : `Phase.sources` est une **liste** de
  prélèvements de natures mêlées (`rangs`, `issue_de_tour`, `reste`), dont les **plages relatives**
  (fin ouverte, « le reste ») rendent un format indépendant de l'effectif réel. Les contrôles
  collectifs — source existante et antérieure, rangs dans l'effectif, sources qui ne se recoupent
  pas, somme compatible — sont portés par l'agrégat pur `SequencePhases`.
  ⚠️ **Ce qui reste ancré par `ordre`** (et non par identité) : une source désigne sa phase amont
  par
  son rang dans la séquence, ce qui oblige à **remapper** les références à chaque réordonnancement
  ou suppression (`ServicePhases._remapper`, `ServiceBaremeQualification._decaler_dun_cran`).
  E05US010 n'a pas changé cet ancrage — elle l'a seulement généralisé à N sources. C'est un écart
  **assumé et tracé** : cf. [DETTE-026](../../docs/dette.md).

La **forme JSON** de la config est une préoccupation du **repository** (l'agrégat pur ci-dessous ne
sérialise rien) : depuis E05US003/ADR-0046, les politiques du moteur y vivent sous `config.policies`
(le barème sous `config.policies.scoring`), le grain de `validation` restant à la racine. Agrégats
de domaine **purs** (immuables, sans dépendance framework).

[ADR-0045]: ../../docs/adr/0045-sequence-de-phases-cycle-de-vie-typage-source.md
[ADR-0061]: ../../docs/adr/0061-routing-generique-et-placement-en-cascade.md
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import Enum
from typing import Protocol

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
    SourceMalFormee,
    SourcesQuiSeRecoupent,
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


# Grains admis par type de phase (`D-11`). La qualification se tire en séries (fin de série / toutes
# les N volées) et ne comporte **pas** de duels. L'élimination directe, elle, se valide **en fin de
# duel** (la feuille de marque se signe « à la fin du duel », FFTA B.6.1.1) : E04US013 ouvre
# `FIN_DE_DUEL` pour ce type (ADR-0049 §5). L'agrégat `Duel` valide toujours d'un bloc en fin de
# duel ; ce grain rend le **modèle de phase** cohérent (une phase à duels peut le déclarer).
_GRAINS_ADMIS: dict[TypePhase, frozenset[TypeGrain]] = {
    TypePhase.QUALIFICATION: frozenset({TypeGrain.FIN_DE_SERIE, TypeGrain.TOUTES_LES_N_VOLEES}),
    TypePhase.ELIMINATION_DIRECTE: frozenset({TypeGrain.FIN_DE_DUEL}),
}

# Grain par défaut de chaque type de phase (« presets cohérents par type de phase », `D-11`).
_GRAIN_PAR_DEFAUT: dict[TypePhase, GrainValidation] = {
    TypePhase.QUALIFICATION: GrainValidation.fin_de_serie(),
    TypePhase.ELIMINATION_DIRECTE: GrainValidation.fin_de_duel(),
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


class NatureSource(str, Enum):
    """Comment une source prélève ses participants dans la phase amont (E05US010).

    Le catalogue vient d'**EF-3.3** du cahier des charges, qui énumérait déjà les provenances
    attendues : tous les inscrits, rangs N→M, gagnants d'un tour, perdants d'un tour, exempts.
    """

    RANGS = "rangs"
    """« Les rangs 1 à 32 du classement » — le prélèvement d'origine (E05US001)."""

    ISSUE_DE_TOUR = "issue_de_tour"
    """« Les gagnants (ou les perdants) du tour X » — indispensable dès qu'une phase succède à un
    tableau plutôt qu'à un classement."""

    RESTE = "reste"
    """« Tout ce qu'aucune autre source n'a prélevé » — le complément, qui rend un format
    indépendant de l'effectif réel."""


class IssueTour(str, Enum):
    """Le côté d'un tour dont on prélève : ceux qui l'ont gagné, ou ceux qui l'ont perdu."""

    GAGNANTS = "gagnants"
    PERDANTS = "perdants"


@dataclass(frozen=True)
class SourcePhase:
    """Un **prélèvement** de participants dans une phase antérieure (E05US010, ADR-0061).

    Une phase peut en porter **plusieurs**, de natures différentes — le CA cite l'exemple du
    commanditaire : « les demi-finalistes du tableau principal, **et** le gagnant du tableau
    secondaire ». Value object **pur**, validé à la construction sur ce qui ne dépend **pas** de la
    séquence ; les contrôles inter-phases (la source existe, est antérieure, tient dans son
    effectif, ne recoupe pas ses voisines) vivent dans `verifier_sequence`.

    **Un seul type, discriminé par `nature`, plutôt qu'une union de trois classes.** L'union serait
    plus étanche — chaque nature ne porterait que ses champs — mais `SourcePhase(ordre_source=…,
    rang_debut=…, rang_fin=…)` est construit dans une trentaine d'endroits (tests, DTO, repository,
    format de bibliothèque) et le prélèvement par rangs reste, de loin, le cas courant. On garde
    donc cette construction **valide telle quelle** (`nature` vaut `RANGS` par défaut) et l'on
    défend l'étanchéité par `__post_init__` : un champ étranger à la nature est une
    `SourceMalFormee`, pas une donnée ignorée en silence. Le compromis est assumé dans l'ADR.

    **Plages relatives** : `rang_fin=None` signifie « et suivants » — la fin dépend de l'effectif
    réel de la phase source, pas du format. C'est ce qui permet à un déroulé composé pour 120
    archers d'en accueillir 82 (CA « plages relatives »).
    """

    ordre_source: int
    rang_debut: int = 1
    rang_fin: int | None = None
    nature: NatureSource = NatureSource.RANGS
    tour: int | None = None
    issue: IssueTour | None = None

    def __post_init__(self) -> None:
        if self.nature is NatureSource.RANGS:
            self._verifier_rangs()
        elif self.nature is NatureSource.ISSUE_DE_TOUR:
            self._verifier_issue_de_tour()
        else:
            self._verifier_reste()
        if self.nature is not NatureSource.ISSUE_DE_TOUR and (
            self.tour is not None or self.issue is not None
        ):
            raise SourceMalFormee(
                f"Un prélèvement « {self.nature.value} » ne désigne pas de tour : "
                "seul « issue_de_tour » en porte un."
            )

    def _verifier_rangs(self) -> None:
        if self.rang_debut < 1:
            raise RangSourceInvalide(
                f"Une source prélève à partir du rang 1 : « {self.rang_debut} » n'existe pas."
            )
        if self.rang_fin is not None and self.rang_fin < self.rang_debut:
            raise PlageSourceVide(
                f"La plage de rangs [{self.rang_debut}..{self.rang_fin}] est vide : "
                "elle ne prélève aucun participant."
            )

    def _verifier_issue_de_tour(self) -> None:
        if self.tour is None or self.issue is None:
            raise SourceMalFormee(
                "Un prélèvement par issue de tour désigne un tour **et** un côté "
                "(gagnants ou perdants) : « les gagnants » sans tour ne désigne personne."
            )
        if self.tour < 1:
            raise SourceMalFormee(f"Le tour d'un prélèvement commence à 1 (reçu {self.tour}).")
        self._refuser_les_rangs("Un prélèvement par issue de tour ne se lit pas en rangs")

    def _verifier_reste(self) -> None:
        self._refuser_les_rangs("« Le reste » se définit par complément")

    def _refuser_les_rangs(self, motif: str) -> None:
        """Interdit `rang_debut`/`rang_fin` sur une nature qui ne se lit pas en rangs.

        ⚠️ `rang_debut` a pour **défaut** `1` : un test `is not None` ne dirait rien, il faut
        comparer à ce défaut. C'est précisément le trou qu'un premier jet de cette US a laissé —
        un `rang_fin` parasite sur une source « issue de tour » était **accepté** puis **jamais
        sérialisé** (`_source_json` n'écrit que les champs de la nature) : le POST répondait 201
        avec la valeur, le GET suivant la rendait à `null`. C'est exactement le « champ avalé en
        silence » que l'ADR déclarait écarter, et c'est le prix du type unique discriminé : ce que
        l'union de trois classes aurait rendu impossible par construction, il faut ici l'interdire
        à la main.
        """
        if self.rang_fin is not None or self.rang_debut != 1:
            raise SourceMalFormee(f"{motif} : « rang_debut » et « rang_fin » n'y ont aucun sens.")

    @property
    def effectif_selectionne(self) -> int | None:
        """Combien de participants ce prélèvement compte — `None` s'il est **indéterminable**.

        Indéterminable dès que le compte dépend de l'effectif réel (fin ouverte, « le reste ») ou
        du déroulé (issue de tour, dont le nombre de gagnants dépend des byes). Le `None` n'est pas
        un manque d'information à combler : c'est l'énoncé même des plages relatives, et c'est ce
        qui dispense du contrôle de somme exacte (cf. `_verifier_sources`).
        """
        if self.nature is not NatureSource.RANGS or self.rang_fin is None:
            return None
        return self.rang_fin - self.rang_debut + 1

    def resoudre(self, effectif_source: int) -> int | None:
        """Le compte **réel** de ce prélèvement une fois l'effectif de la phase source connu.

        C'est ici que « les rangs 33 et suivants » devient 88 à 120 inscrits et 50 à 82. Rend
        `None` pour les natures dont le compte ne se déduit pas de l'effectif seul (« le reste »
        dépend des autres sources, une issue de tour du déroulé).
        """
        if self.nature is not NatureSource.RANGS:
            return None
        fin = self.rang_fin if self.rang_fin is not None else effectif_source
        return max(0, fin - self.rang_debut + 1)

    def intervalle(self, effectif_source: int | None) -> tuple[int, int] | None:
        """Les **bornes** que ce prélèvement occupe dans la phase source, ou `None` s'il ne se lit
        pas en rangs (« le reste », une issue de tour : leur recoupement éventuel ne se décide qu'au
        déroulé — E01US024).

        ⚠️ Rend un **intervalle**, jamais l'ensemble des rangs. Deux intervalles se comparent en
        O(1) ; matérialiser `frozenset(range(debut, fin))` ferait dépendre l'allocation mémoire d'un
        entier fourni par le client (`effectif` n'est borné que par le bas), et ce calcul tourne sur
        le **thread du writer unique** — un effectif absurde y gèlerait toutes les écritures du jour
        J. Défaut relevé par trois axes de la revue d'E05US010.

        Une **fin ouverte** sans effectif source déclaré s'étend jusqu'à l'infini : c'est
        littéralement « et tous les suivants », donc elle recoupe tout ce qui commence après son
        début — le contrôle reste décidable sans connaître l'effectif.
        """
        if self.nature is not NatureSource.RANGS:
            return None
        if self.rang_fin is not None:
            return (self.rang_debut, self.rang_fin)
        return (self.rang_debut, effectif_source if effectif_source is not None else sys.maxsize)

    @staticmethod
    def par_rangs(
        ordre_source: int, rang_debut: int = 1, rang_fin: int | None = None
    ) -> SourcePhase:
        """« Les rangs `debut`..`fin` » — `fin=None` pour « et suivants »."""
        return SourcePhase(ordre_source=ordre_source, rang_debut=rang_debut, rang_fin=rang_fin)

    @staticmethod
    def par_issue_de_tour(ordre_source: int, tour: int, issue: IssueTour) -> SourcePhase:
        """« Les gagnants / les perdants du tour `tour` » de la phase `ordre_source`."""
        return SourcePhase(
            ordre_source=ordre_source,
            nature=NatureSource.ISSUE_DE_TOUR,
            tour=tour,
            issue=issue,
        )

    @staticmethod
    def le_reste(ordre_source: int) -> SourcePhase:
        """« Tout ce qu'aucune autre source n'a prélevé » dans la phase `ordre_source`."""
        return SourcePhase(ordre_source=ordre_source, nature=NatureSource.RESTE)


@dataclass(frozen=True)
class Phase:
    """Une phase d'un tournoi. `id` vaut `None` tant qu'elle n'est pas persistée.

    `bareme` et `validation` ne concernent que la **qualification** (barème de cumul + grain,
    `D-11`) : ils sont `None` pour les autres types, dont les politiques propres viendront en
    E05US003 (ADR-0045 §2). `sources` décrit d'où la phase tire ses participants — **plusieurs**
    prélèvements possibles depuis E05US010 (`()` = première de la séquence, alimentée par les
    inscriptions). `effectif` (facultatif) déclare combien de participants la phase classe/produit —
    il borne les rangs prélevables et sert au contrôle « effectif incompatible ».

    **Invariants** (vérifiés à chaque construction, `replace()` compris) : effectif ≥ 1 s'il est
    déclaré ; une phase de `qualification` porte barème **et** grain ; le grain — s'il y en a un —
    est admis par le type et sa cadence ne dépasse pas le barème.
    """

    tournoi_id: TournoiId
    ordre: int
    type: TypePhase
    bareme: BaremeQualification | None = None
    validation: GrainValidation | None = None
    sources: tuple[SourcePhase, ...] = ()
    effectif: int | None = None
    statut: StatutPhase = StatutPhase.A_VENIR
    id: PhaseId | None = None

    def __post_init__(self) -> None:
        """Fait respecter la cohérence quelle que soit la porte d'entrée (fabriques **et**
        `replace()`, qui repasse par ici)."""
        verifier_coherence_etape(self.type, self.bareme, self.validation, self.effectif)

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
        sources: tuple[SourcePhase, ...] = (),
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
            sources=sources,
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

    def avec_sources(self, sources: tuple[SourcePhase, ...]) -> Phase:
        """Renvoie une copie aux prélèvements mis à jour ; `()` = alimentée par les inscriptions
        (première de la séquence)."""
        return replace(self, sources=sources)

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
        verifier_sequence(self.phases)


class EtapeSequencee(Protocol):
    """Ce dont les contrôles de séquence ont besoin d'une étape — **rien de plus**.

    Deux agrégats satisfont ce contrat : la `Phase` d'un tournoi (ci-dessus) et le `ModelePhase`
    d'un `FormatTournoi` (E01US023, ADR-0060 §5). Les contrôles d'ordre et de source ne regardent
    que `ordre`, `sources` et `effectif` — ni le statut, ni le tournoi, qui n'existent que sur une
    phase réelle. Le protocole rend cette frontière explicite au lieu de la laisser deviner.

    Membres déclarés en **propriétés** (lecture seule) : les deux implémentations sont des
    dataclasses `frozen`, et un protocole à attributs *variables* exigerait qu'ils soient
    assignables (règle 4 — l'immutabilité est la norme dans le domaine).
    """

    @property
    def ordre(self) -> int: ...

    @property
    def sources(self) -> tuple[SourcePhase, ...]: ...

    @property
    def effectif(self) -> int | None: ...


def verifier_sequence(etapes: Sequence[EtapeSequencee]) -> None:
    """Vérifie les invariants **collectifs** d'une séquence d'étapes (ADR-0045 §3).

    Les ordres forment la suite contiguë 1..N, et chaque source désigne une étape **antérieure**
    existante dont l'effectif couvre les rangs prélevés, avec un compte compatible.

    **Publique et partagée** entre `SequencePhases` (les phases d'un tournoi) et `FormatTournoi`
    (les modèles de phases d'une brique de bibliothèque) : c'est le **même** invariant, et le
    recopier serait la duplication d'invariant que le registre de dette proscrit. Ce n'est pas
    l'introduction d'un patron — juste une fonction appelée à deux endroits.
    """
    _verifier_ordres(etapes)
    _verifier_sources(etapes)


def verifier_coherence_etape(
    type_phase: TypePhase,
    bareme: BaremeQualification | None,
    validation: GrainValidation | None,
    effectif: int | None,
) -> None:
    """Vérifie les invariants **d'une seule** étape — indépendamment de la séquence qui la porte.

    Effectif ≥ 1 s'il est déclaré ; une `qualification` porte barème **et** grain ; le grain — s'il
    y en a un — est admis par le type et sa cadence ne dépasse pas le barème.

    Partagée pour la même raison que `verifier_sequence` : une phase de tournoi et un modèle de
    phase d'un format obéissent aux **mêmes** règles de cohérence interne ; seul le contexte
    (statut, tournoi) les distingue.
    """
    if effectif is not None and effectif < 1:
        raise EffectifPhaseInvalide(
            "L'effectif d'une phase, s'il est déclaré, compte au moins un participant."
        )
    if type_phase is TypePhase.QUALIFICATION and (bareme is None or validation is None):
        raise PhaseQualificationIncomplete(
            "Une phase de qualification porte un barème et un grain de validation."
        )
    if validation is not None:
        _verifier_grain_admis(type_phase, validation)
        if bareme is not None:
            _verifier_cadence_couverte(validation, bareme)


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


def _verifier_ordres(phases: Sequence[EtapeSequencee]) -> None:
    """Les ordres doivent former la suite contiguë 1..N (ni trou, ni doublon, ni départ décalé)."""
    ordres = sorted(phase.ordre for phase in phases)
    if ordres != list(range(1, len(phases) + 1)):
        raise SequenceOrdreInvalide(
            "Les phases d'une séquence sont numérotées 1, 2, 3… sans trou ni doublon : "
            f"ordres reçus {ordres}."
        )


def _verifier_sources(phases: Sequence[EtapeSequencee]) -> None:
    """Les invariants **collectifs** du peuplement d'une phase (E05US001, étendus par E05US010).

    Cinq contrôles : chaque source désigne une phase **existante** et **antérieure** ; ses rangs
    tiennent dans l'effectif de cette phase ; deux sources d'une même phase ne **recoupent** pas
    leurs rangs ; et la somme des prélèvements **couvre** l'effectif déclaré.

    ⚠️ Le contrôle de somme ne s'applique que si **tous** les prélèvements sont dénombrables au
    format (`effectif_selectionne is not None`). Dès qu'une source est relative — fin ouverte, « le
    reste », issue de tour —, le compte ne se connaît qu'à l'exécution : l'exiger ici rendrait les
    plages relatives inutilisables, alors qu'elles sont précisément ce que le CA demande. Le CA le
    dit d'ailleurs pour l'autre bout du problème : un format devenu infaisable à effectif réduit
    n'est **pas** une erreur à corriger dans le format : c'est une **anomalie à afficher**
    (E01US024).
    """
    par_ordre = {phase.ordre: phase for phase in phases}
    for phase in phases:
        for source in phase.sources:
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
            if (
                phase_source.effectif is not None
                and source.rang_fin is not None
                and source.rang_fin > phase_source.effectif
            ):
                raise RangsSourceInexistants(
                    f"La source prélève jusqu'au rang {source.rang_fin}, mais la phase "
                    f"{source.ordre_source} n'en classe que {phase_source.effectif}."
                )
        _verifier_recoupements(phase, par_ordre)
        _verifier_somme(phase)


def _verifier_recoupements(phase: EtapeSequencee, par_ordre: dict[int, EtapeSequencee]) -> None:
    """Deux sources d'une même phase ne prélèvent pas le même participant (CA « cohérence »).

    Le recoupement se juge **par phase source** : « les rangs 1-2 de la phase 1 » et « les rangs 1-2
    de la phase 2 » désignent quatre participants distincts, pas deux. Seuls les prélèvements **par
    rangs** se comparent en rangs — mais deux sources **strictement identiques** sont refusées,
    quelle que soit leur nature : « le reste » deux fois, ou deux fois les mêmes gagnants d'un tour,
    sont
    des non-sens qui se voient sans dérouler le tournoi. Un recoupement *partiel* entre natures
    différentes, lui, reste une anomalie d'exécution (E01US024).

    ⚠️ Le contrôle **ne dépend pas** de l'effectif déclaré de la phase source. Un premier jet de
    cette US sautait tout le contrôle quand cet effectif valait `None` — or `Phase.effectif` est
    facultatif, donc le cas par défaut : deux plages pourtant **entièrement bornées** ([1..10] et
    [5..15]) passaient sans examen. Une fin ouverte sans effectif connu s'étend jusqu'à l'infini,
    ce qui la rend comparable elle aussi (cf. `SourcePhase.intervalle`).
    """
    doublons = [s for s in phase.sources if phase.sources.count(s) > 1]
    if doublons:
        raise SourcesQuiSeRecoupent(
            f"La phase {phase.ordre} porte deux fois le même prélèvement : un participant ne peut "
            "pas entrer deux fois dans la même phase."
        )
    for ordre_source in {source.ordre_source for source in phase.sources}:
        etape_source = par_ordre.get(ordre_source)
        effectif_source = None if etape_source is None else etape_source.effectif
        intervalles: list[tuple[int, int]] = []
        for source in phase.sources:
            if source.ordre_source != ordre_source:
                continue
            intervalle = source.intervalle(effectif_source)
            if intervalle is None:
                continue
            debut, fin = intervalle
            for autre_debut, autre_fin in intervalles:
                if debut <= autre_fin and autre_debut <= fin:
                    raise SourcesQuiSeRecoupent(
                        f"Deux sources de la phase {phase.ordre} prélèvent le même rang "
                        f"{max(debut, autre_debut)} de la phase {ordre_source} : un participant ne "
                        "peut pas entrer deux fois dans la même phase."
                    )
            intervalles.append(intervalle)


def _verifier_somme(phase: EtapeSequencee) -> None:
    """Les prélèvements doivent tenir dans l'effectif déclaré de la phase (CA « cohérence »).

    Deux régimes, et c'est la distinction qui compte :

    - **tous les prélèvements dénombrables** → la somme doit **égaler** l'effectif déclaré ;
    - **au moins un prélèvement relatif** (fin ouverte, « le reste », issue de tour) → l'**égalité**
      devient indécidable au format, puisque le compte ne se ferme qu'à l'exécution. Mais
      l'**inégalité**, elle, reste décidable : un prélèvement relatif ajoute un nombre ≥ 0 de
      participants, donc si les seuls dénombrables dépassent déjà l'effectif, la composition est
      fausse quoi qu'il arrive.

    Un premier jet de cette US désactivait **tout** le contrôle dès qu'un prélèvement était
    relatif :
    « les rangs 1 à 64, puis le reste » pour une phase déclarant 32 participants passait alors sans
    broncher, alors qu'il était refusé avant l'US. Relevé par la revue — et son test l'évitait en
    choisissant 8 prélevés pour 32 déclarés.
    """
    if phase.effectif is None or not phase.sources:
        return
    comptes = [source.effectif_selectionne for source in phase.sources]
    total = sum(compte for compte in comptes if compte is not None)
    if any(compte is None for compte in comptes):
        if total > phase.effectif:
            raise EffectifIncompatible(
                f"La phase {phase.ordre} attend {phase.effectif} participants, mais ses seuls "
                f"prélèvements dénombrables en prennent déjà {total}."
            )
        return
    if total != phase.effectif:
        raise EffectifIncompatible(
            f"La phase {phase.ordre} attend {phase.effectif} participants, mais ses sources en "
            f"prélèvent {total}."
        )
