"""Agrégat **Phase** et séquence — cycle de vie, typage, prélèvements (ADR-0045, ADR-0061).
L'agrégat porte la valeur et des transitions **pures** ; le service arbitre l'enchaînement.

⚠️ **Une source désigne sa phase amont par son `ordre`, pas par son identité** : tout
réordonnancement ou suppression oblige donc à **remapper** les références
(`ServicePhases._remapper`). Écart assumé et tracé — `DETTE-026`.
"""

# Forme persistée de `config` (ADR-0046) : les politiques sous `config.policies`, le barème sous
# `config.policies.scoring`, le grain de `validation` **à la racine**. La sérialisation elle-même
# est une affaire de repository — `infrastructure/db/repositories/moteur.py`.

from __future__ import annotations

import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, replace
from enum import Enum
from typing import Protocol

from domain.anomalie import Anomalie
from domain.bareme import BaremeQualification
from domain.big_shoot_off import ConfigurationBigShootOff
from domain.colline import ConfigurationColline
from domain.contrat_phase import TYPES_EN_TABLEAU as TYPES_EN_TABLEAU
from domain.contrat_phase import TYPES_SANS_CLASSEMENT as TYPES_SANS_CLASSEMENT
from domain.contrat_phase import TypePhase as TypePhase
from domain.contrat_phase import produit_un_classement as produit_un_classement
from domain.depart import DepartId
from domain.erreurs import (
    CadenceValidationSuperieureAuBareme,
    ConfigurationBigShootOffInvalide,
    ConfigurationCollineInvalide,
    ConfigurationSuisseInvalide,
    EffectifIncompatible,
    EffectifPhaseInvalide,
    GrainIncompatibleAvecTypePhase,
    PhaseQualificationIncomplete,
    PhaseSansClassementPrelevee,
    PlageSourceVide,
    ProfondeurInvalide,
    RangSourceInvalide,
    RangsSourceInexistants,
    ReglageDePoulesInvalide,
    SequenceOrdreInvalide,
    SeuilDeBarrageInvalide,
    SourceApresPhase,
    SourceIntrouvable,
    SourceMalFormee,
    SourcesQuiSeRecoupent,
)
from domain.grain_validation import GrainValidation, TypeGrain
from domain.politiques import RANGS_DU_PODIUM, ProfondeurClassement
from domain.poule import ReglageDePoules
from domain.qualification import DecoupageEnTours, verifier_decoupage_applicable
from domain.suisse import ConfigurationSuisse

PhaseId = int
"""Identifiant technique d'une phase, attribué par la persistance."""


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


# Grains admis par type de phase (`D-11`). La qualification se tire en séries et ne comporte pas
# de duels ; l'élimination directe se valide **en fin de duel** (FFTA B.6.1.1, ADR-0049 §5).
#
# **E05US015** range les six types neufs selon ce qu'ils *font tirer* : ce qui s'y joue en duels
# (barrage, poules, suisse, colline) se valide en fin de duel, le **Big Shoot Off** fait tirer des
# volées en parallèle donc se valide comme une série. L'**échauffement** n'a **aucun** grain admis
# — il n'attribue rien : un grain déclaré dessus est une `GrainIncompatibleAvecTypePhase`.
_GRAINS_ADMIS: dict[TypePhase, frozenset[TypeGrain]] = {
    TypePhase.QUALIFICATION: frozenset({TypeGrain.FIN_DE_SERIE, TypeGrain.TOUTES_LES_N_VOLEES}),
    TypePhase.ELIMINATION_DIRECTE: frozenset({TypeGrain.FIN_DE_DUEL}),
    TypePhase.BARRAGE: frozenset({TypeGrain.FIN_DE_DUEL}),
    TypePhase.POULES: frozenset({TypeGrain.FIN_DE_DUEL}),
    TypePhase.SUISSE: frozenset({TypeGrain.FIN_DE_DUEL}),
    TypePhase.COLLINE: frozenset({TypeGrain.FIN_DE_DUEL}),
    TypePhase.BIG_SHOOT_OFF: frozenset({TypeGrain.FIN_DE_SERIE, TypeGrain.TOUTES_LES_N_VOLEES}),
}

# Grain par défaut de chaque type de phase (« presets cohérents par type de phase », `D-11`).
_GRAIN_PAR_DEFAUT: dict[TypePhase, GrainValidation] = {
    TypePhase.QUALIFICATION: GrainValidation.fin_de_serie(),
    TypePhase.ELIMINATION_DIRECTE: GrainValidation.fin_de_duel(),
    TypePhase.BARRAGE: GrainValidation.fin_de_duel(),
    TypePhase.POULES: GrainValidation.fin_de_duel(),
    TypePhase.SUISSE: GrainValidation.fin_de_duel(),
    TypePhase.COLLINE: GrainValidation.fin_de_duel(),
    TypePhase.BIG_SHOOT_OFF: GrainValidation.fin_de_serie(),
}

# ⚠️ `TYPES_SANS_CLASSEMENT` et `TYPES_EN_TABLEAU` **vivaient ici** jusqu'à E05US023 ; ce sont
# désormais des dérivées du registre de contrat (`domain/contrat_phase.py`, ADR-0083), ré-exportées
# en tête de module pour que les ~30 sites qui les importent d'ici restent valides. Le commentaire
# qu'elles portaient — « une copie de plus divergerait au premier type ajouté » — est resté vrai un
# cran plus haut : trois copies de `TYPES_EN_TABLEAU` avaient été consolidées en deux, un
# commentaire affirmant l'unicité pendant qu'une troisième vivait dans `suivi_deroule`. Le registre
# rend la divergence **impossible** au lieu d'improbable, ce qu'aucun commentaire ne sait faire.

# Profondeur preset de chaque type en tableau (« politique sans migration », ADR-0011).
#
# ⚠️ **Deux presets différents, et l'asymétrie est le sujet** : le podium pour l'élimination
# directe, le classement **intégral** pour le placement (raison notée sur l'entrée elle-même).
#
# ⚠️ Le **podium** pour l'élimination directe, malgré le « 1→N (défaut) » du CA — ADR-0070. Le
# défaut du *catalogue* n'est pas le preset d'une *phase déjà en base* : faire de 1→N le preset
# aurait converti tous les tournois existants (un tableau de 120 passant de 128 duels à 436).
_PROFONDEUR_PAR_DEFAUT: dict[TypePhase, ProfondeurClassement] = {
    TypePhase.ELIMINATION_DIRECTE: ProfondeurClassement.top(RANGS_DU_PODIUM),
    # ⚠️ **Le placement, lui, va jusqu'au bout** — asymétrie voulue. L'argument de
    # rétro-compatibilité ci-dessus ne vaut que pour l'élimination directe : aucun service ne monte
    # de tableau pour une phase de type `placement` (`# DETTE-028`), donc il n'y a rien à préserver
    # — et le catalogue promet « du 1ᵉʳ au dernier ». La fenêtre est **maintenant** : plus tard,
    # corriger le preset exigerait la conversion silencieuse qu'ADR-0070 §3 refuse.
    TypePhase.PLACEMENT: ProfondeurClassement.integrale(),
}


def profondeur_par_defaut(type_phase: TypePhase) -> ProfondeurClassement:
    """La profondeur preset d'un type de phase — le podium pour un tableau (E06US006).

    Sert à la création **et** à la relecture d'une phase antérieure à E06US006, dont la `config` ne
    porte pas de clé `depth` — même mécanisme que `grain_par_defaut`. ⚠️ Le preset **dépend du
    type** : podium pour une élimination directe, classement intégral pour un placement (ADR-0070
    §3). Lève `ProfondeurInvalide` si le type ne monte aucun tableau, explicite plutôt qu'un
    `KeyError` que le repository diagnostiquerait « configuration illisible ».
    """
    preset = _PROFONDEUR_PAR_DEFAUT.get(type_phase)
    if preset is None:
        raise ProfondeurInvalide(
            f"Une phase de type « {type_phase.value} » ne monte aucun tableau : elle n'a pas de "
            "profondeur de classement à régler."
        )
    return preset


def grain_par_defaut(type_phase: TypePhase) -> GrainValidation:
    """Le grain preset d'un type de phase — `fin de série` pour la qualification (`D-11`).

    Sert à la création **et** à la relecture d'une phase antérieure à E01US015, dont la `config` ne
    porte pas de clé `validation`. Lève `GrainIncompatibleAvecTypePhase` si le type n'a pas de
    preset déclaré : explicite plutôt qu'un `KeyError` diagnostiqué « configuration illisible ».
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

    Une phase peut en porter **plusieurs**, de natures différentes. Value object pur, validé sur ce
    qui ne dépend **pas** de la séquence ; les contrôles inter-phases vivent dans
    `verifier_sequence`. ⚠️ **Un seul type discriminé par `nature`**, et non trois classes : la
    construction par rangs est le cas courant et reste valide telle quelle, l'étanchéité étant
    défendue par `__post_init__` (`SourceMalFormee`). `rang_fin=None` = « et suivants ».
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
        comparer à ce défaut. C'est le trou d'un premier jet — un `rang_fin` parasite était accepté
        puis jamais sérialisé, le POST répondant 201 avec la valeur et le GET la rendant à `null`.
        C'est le prix du type unique discriminé : ce qu'une union rendrait impossible s'interdit
        ici à la main.
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
        pas en rangs.

        ⚠️ Rend un **intervalle**, jamais l'ensemble des rangs : matérialiser
        `frozenset(range(...))` ferait dépendre l'allocation d'un entier fourni par le client, et ce
        calcul tourne sur le **thread du writer unique**. Une **fin ouverte** sans effectif déclaré
        s'étend jusqu'à l'infini — le recoupement reste décidable sans connaître l'effectif.
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
    """Une phase **d'un départ**. `id` vaut `None` tant qu'elle n'est pas persistée.

    ⚠️ **D'un départ, pas d'un tournoi** (E01US025, ADR-0075) : un départ rejoue le tournoi en
    entier — sa séquence, ses classements, ses tableaux. Deux archers de départs différents ne sont
    jamais comparés, et un prélèvement ne traverse jamais un départ. `bareme` et `validation` ne
    concernent que la **qualification** (ADR-0045 §2) ; `sources` dit d'où la phase tire ses
    participants (`()` = première de la séquence) ; `effectif` borne les rangs prélevables.
    """

    depart_id: DepartId
    ordre: int
    type: TypePhase
    bareme: BaremeQualification | None = None
    validation: GrainValidation | None = None
    sources: tuple[SourcePhase, ...] = ()
    effectif: int | None = None
    barrage_jusqu_au: int | None = None
    profondeur: ProfondeurClassement | None = None
    """Jusqu'où cette phase départage ses participants (E06US006, ADR-0070).

    `None` = **non réglée**, et non « 1→N » : la phase retombe sur le preset de son type —
    `top_n(4)` pour une élimination directe, `un_vers_n` pour un placement (ADR-0070 §3). C'est ce
    qui rend l'US rétro-compatible : une phase écrite avant elle continue de jouer ce qu'elle
    jouait."""

    poules: ReglageDePoules | None = None
    """Le réglage d'une phase de **poules** (E05US023) — taille visée, barème, régime d'ex æquo.

    `None` sur tout autre type, et sur une phase de poules **pas encore réglée** : le type est
    choisi avant ses paramètres, et l'atelier doit pouvoir enregistrer un déroulé en cours de
    composition. C'est la composition du jour J qui exigera le réglage, pas l'agrégat."""

    big_shoot_off: ConfigurationBigShootOff | None = None
    """Le réglage d'une phase de **Big Shoot Off** (E05US028) — combien sortent, manche par manche.

    Même régime que `poules` : `None` sur tout autre type, et sur un Big Shoot Off pas encore réglé.
    ⚠️ **Une seule classe ici, là où les poules en ont deux** : celles-ci séparent une *taille
    visée* d'un *nombre de poules* parce que la conversion dépend de l'effectif. « 4 puis 2 puis 1 »
    se lit à l'identique sur 12 ou 20 inscrits — seule la projection (`paliers_pour`) varie, et elle
    se calcule à la lecture.
    """

    suisse: ConfigurationSuisse | None = None
    """Le réglage d'une phase au **système suisse** (E05US026) — le nombre de rondes.

    Même régime que les deux réglages ci-dessus, et **une seule classe** pour la même raison que le
    Big Shoot Off : un nombre de rondes ne dépend pas de l'effectif. Ce qui en dépend est la
    **borne** appariable sans ré-affrontement (`suisse.rondes_maximales`), affichée à l'atelier et
    vérifiée par `EtapeDeroule` là où l'effectif est déclaré — jamais figée ici."""

    colline: ConfigurationColline | None = None
    """Le réglage d'une phase de **colline** (E05US027) — nombre de manches et portée de défi.

    Une seule classe, comme ses voisins : ni le nombre de manches ni la portée ne dépendent de
    l'effectif — c'est la **borne** de portée qui en dépend, vérifiée par `EtapeDeroule`.
    ⚠️ **Deux champs pour un seul réglage** : la portée distingue le **King of the Hill** (défier
    son voisin) du **Ladder**. Le référentiel §10.1 les donne comme deux formats ; ce sont deux
    **réglages** d'un même format (règle 2), d'où un seul `TypePhase.COLLINE`.
    """

    decoupage: DecoupageEnTours | None = None
    """Le découpage d'une **qualification** en tours — « 20 volées en 2 tours de 10 » (E05US035).

    Même régime que ses voisins : porté par l'étape (ADR-0076), `None` sur une qualification non
    découpée — auquel cas la phase **est** son tour. ⚠️ **Ce n'est pas du barème** : un barème dit
    comment on **classe**, un découpage comment on **avance** (invariant *avancer ≠ classer*,
    ADR-0090) ; les mêler ferait croire qu'un tour produit un classement intermédiaire, qu'aucune
    règle FFTA ne prévoit. Seul usage : rendre la qualification **arrêtable** (ADR-0093).
    """

    statut: StatutPhase = StatutPhase.A_VENIR
    id: PhaseId | None = None

    def __post_init__(self) -> None:
        """Fait respecter la cohérence quelle que soit la porte d'entrée (fabriques **et**
        `replace()`, qui repasse par ici)."""
        verifier_coherence_etape(self.type, self.bareme, self.validation, self.effectif)
        verifier_decoupage_applicable(self.type, self.bareme, self.decoupage)
        if self.profondeur is not None and self.type not in TYPES_EN_TABLEAU:
            raise ProfondeurInvalide(
                f"Une phase de type « {self.type.value} » ne monte aucun tableau : elle n'a pas "
                "de profondeur de classement à régler."
            )
        if self.poules is not None and self.type is not TypePhase.POULES:
            # Même garde que `profondeur` ci-dessus, et pour la même raison : retyper une phase sans
            # nettoyer son réglage laisserait une élimination directe porter une taille de poule,
            # que rien ne lirait — un réglage fantôme, invisible et faux.
            raise ReglageDePoulesInvalide(
                f"Une phase de type « {self.type.value} » n'est pas une phase de poules : elle n'a "
                "pas de taille de poule à régler."
            )
        # DETTE-078
        # ⚠️ **Ces gardes-ci arrivent APRÈS la persistance de l'étape, et c'est la dette.** Elles
        # vivent sur `Phase`, donc à `instancier()`, or `ServicePhases.ajouter` fait rejoindre
        # l'étape au déroulé **avant** : une requête refusée en 422 laisse une étape orpheline qui
        # brûle un `ordre`. Seule `colline` est fermée (garde jumelle dans
        # `EtapeDeroule.__post_init__`) ; les quatre autres sont héritées, résorption en US dédiée.
        if self.big_shoot_off is not None and self.type is not TypePhase.BIG_SHOOT_OFF:
            # Même garde que `poules`, et le motif est le même : un réglage que rien ne lit est
            # invisible et faux. Il est d'autant plus dangereux ici qu'il décrit **qui sort** — le
            # retrouver actif après un retypage éliminerait des archers sur une consigne oubliée.
            raise ConfigurationBigShootOffInvalide(
                f"Une phase de type « {self.type.value} » n'est pas un Big Shoot Off : elle n'a "
                "pas de nombre de sortants à régler."
            )
        if self.suisse is not None and self.type is not TypePhase.SUISSE:
            # Même garde que les deux précédentes. Un nombre de rondes oublié sur une phase
            # retypée est moins dangereux qu'une liste de sortants — il ne décide de l'élimination
            # de personne — mais il reste un réglage que rien ne lit, donc invisible et faux.
            raise ConfigurationSuisseInvalide(
                f"Une phase de type « {self.type.value} » n'est pas un système suisse : elle n'a "
                "pas de nombre de rondes à régler."
            )
        if self.colline is not None and self.type is not TypePhase.COLLINE:
            # Même garde que les trois précédentes, cinquième et dernière de la famille. Un réglage
            # de colline oublié sur une phase retypée porte deux valeurs que rien ne lirait — dont
            # la portée de défi, qui décide **qui rencontre qui**. Invisible et faux.
            raise ConfigurationCollineInvalide(
                f"Une phase de type « {self.type.value} » n'est pas une colline : elle n'a pas de "
                "nombre de manches ni de portée de défi à régler."
            )
        if self.barrage_jusqu_au is not None and self.barrage_jusqu_au < 1:
            raise SeuilDeBarrageInvalide(
                "Le rang jusqu'auquel un barrage départage est un entier positif "
                f"(reçu {self.barrage_jusqu_au}) ; « aucun barrage » se dit en ne réglant rien."
            )

    @staticmethod
    def qualification(
        depart_id: DepartId,
        bareme: BaremeQualification,
        validation: GrainValidation | None = None,
    ) -> Phase:
        """Crée la phase de **qualification** d'un départ (première de sa séquence, `ordre=1`).

        Sans grain explicite, applique le preset du type (`fin de série`, `D-11`) : une phase de
        qualification existe toujours **avec** un grain, jamais sans.
        """
        return Phase(
            depart_id=depart_id,
            ordre=1,
            type=TypePhase.QUALIFICATION,
            bareme=bareme,
            validation=validation or grain_par_defaut(TypePhase.QUALIFICATION),
            statut=StatutPhase.A_VENIR,
        )

    @staticmethod
    def creer(
        depart_id: DepartId,
        ordre: int,
        type: TypePhase,
        sources: tuple[SourcePhase, ...] = (),
        effectif: int | None = None,
        barrage_jusqu_au: int | None = None,
        profondeur: ProfondeurClassement | None = None,
    ) -> Phase:
        """Crée une phase **générique** (E05US001) à un rang donné de la séquence, statut `a venir`.

        Pour une phase de `qualification`, préférer `Phase.qualification` (qui exige le barème) —
        appelée ici, elle lèverait `PhaseQualificationIncomplete` faute de barème.
        """
        return Phase(
            depart_id=depart_id,
            ordre=ordre,
            type=type,
            sources=sources,
            effectif=effectif,
            barrage_jusqu_au=barrage_jusqu_au,
            profondeur=profondeur,
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
    """La séquence **ordonnée** des phases **d'un départ**, gardienne de sa cohérence (E05US001).

    ⚠️ **D'un départ depuis E01US025** (ADR-0075) : les ordres forment la suite contiguë 1..N *dans
    un départ*. Assembler les phases de deux départs lève `SequenceOrdreInvalide` — c'est le
    garde-fou qui signale une lecture restée à la portée tournoi. Value object pur : chaque source
    désigne une phase **antérieure** existante dont l'effectif couvre les rangs prélevés (ADR-0045
    §3). Une séquence **vide** est licite (tournoi sans phase composée).
    """

    phases: tuple[Phase, ...]

    def __post_init__(self) -> None:
        verifier_sequence(self.phases)


class EtapeSequencee(Protocol):
    """Ce dont les contrôles de séquence ont besoin d'une étape — **rien de plus**.

    Deux agrégats satisfont ce contrat : la `Phase` d'un départ et le `ModelePhase` d'un
    `FormatTournoi` (ADR-0060 §5). Les contrôles ne regardent que `ordre`, `sources` et `effectif`
    — ni le statut ni le départ, qui n'existent que sur une phase réelle. Membres déclarés en
    **propriétés** : les deux implémentations sont `frozen`, et un protocole à attributs variables
    exigerait qu'ils soient assignables (règle 4).
    """

    @property
    def ordre(self) -> int: ...

    @property
    def type(self) -> TypePhase: ...

    @property
    def sources(self) -> tuple[SourcePhase, ...]: ...

    @property
    def effectif(self) -> int | None: ...


def verifier_sequence(etapes: Sequence[EtapeSequencee]) -> None:
    """Vérifie les invariants **collectifs** d'une séquence d'étapes (ADR-0045 §3).

    Ordres contigus 1..N, et chaque source désigne une étape **antérieure** existante dont
    l'effectif couvre les rangs prélevés, avec un compte compatible. **Publique et partagée** entre
    `SequencePhases` et `FormatTournoi` : c'est le **même** invariant, et le recopier serait la
    duplication que le registre proscrit. **Enveloppe levante** depuis E01US024 — la règle vit dans
    `anomalies_sequence`, celle-ci lève la première.
    """
    for anomalie in anomalies_sequence(etapes):
        raise anomalie.erreur


def anomalies_sequence(etapes: Sequence[EtapeSequencee]) -> Iterator[Anomalie]:
    """Énumère **tous** les défauts collectifs d'une séquence, au lieu de s'arrêter au premier.

    Source unique des règles de séquence (E01US024, ADR-0063) : `verifier_sequence` en est
    l'enveloppe levante, et la projection de déroulé la consomme telle quelle. Toutes les anomalies
    produites ici sont **bloquantes** — un ordre en doublon ou une source postérieure est faux quel
    que soit l'effectif ; les défauts qui ne valent qu'à un effectif donné naissent dans
    `domain.deroule`.
    """
    yield from _anomalies_ordres(etapes)
    yield from _anomalies_sources(etapes)


def verifier_coherence_etape(
    type_phase: TypePhase,
    bareme: BaremeQualification | None,
    validation: GrainValidation | None,
    effectif: int | None,
) -> None:
    """Vérifie les invariants **d'une seule** étape — indépendamment de la séquence qui la porte.

    Effectif ≥ 1 s'il est déclaré ; une `qualification` porte barème **et** grain ; le grain est
    admis par le type et sa cadence ne dépasse pas le barème.

    Partagée pour la même raison que `verifier_sequence` : une phase et un modèle de phase obéissent
    aux **mêmes** règles internes. **Enveloppe levante** depuis E01US024.
    """
    for anomalie in anomalies_etape(type_phase, bareme, validation, effectif):
        raise anomalie.erreur


def anomalies_etape(
    type_phase: TypePhase,
    bareme: BaremeQualification | None,
    validation: GrainValidation | None,
    effectif: int | None,
    ordre: int | None = None,
) -> Iterator[Anomalie]:
    """Énumère les défauts **internes** d'une étape ; `ordre` sert à les localiser sur le schéma.

    Toutes bloquantes : ces règles ne dépendent d'aucun effectif simulé — une qualification sans
    barème l'est à 12 archers comme à 120.
    """
    if effectif is not None and effectif < 1:
        yield Anomalie(
            EffectifPhaseInvalide(
                "L'effectif d'une phase, s'il est déclaré, compte au moins un participant."
            ),
            ordre,
        )
    if type_phase is TypePhase.QUALIFICATION and (bareme is None or validation is None):
        yield Anomalie(
            PhaseQualificationIncomplete(
                "Une phase de qualification porte un barème et un grain de validation."
            ),
            ordre,
        )
    if validation is not None:
        yield from _anomalies_grain_admis(type_phase, validation, ordre)
        if bareme is not None:
            yield from _anomalies_cadence_couverte(validation, bareme, ordre)


def _anomalies_grain_admis(
    type_phase: TypePhase, validation: GrainValidation, ordre: int | None
) -> Iterator[Anomalie]:
    # `.get` plutôt qu'une indexation : un type sans entrée n'admet aucun grain, ce qui donne un
    # `GrainIncompatibleAvecTypePhase` au message exact — pas un `KeyError` nu.
    admis = _GRAINS_ADMIS.get(type_phase, frozenset())
    if validation.type not in admis:
        yield Anomalie(
            GrainIncompatibleAvecTypePhase(
                f"Le grain « {validation.type.value} » ne s'applique pas à une phase "
                f"de type « {type_phase.value} »."
            ),
            ordre,
        )


def _anomalies_cadence_couverte(
    validation: GrainValidation, bareme: BaremeQualification, ordre: int | None
) -> Iterator[Anomalie]:
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
        yield Anomalie(
            CadenceValidationSuperieureAuBareme(
                f"Valider toutes les {validation.n_volees} volées est impossible sur un barème qui "
                f"n'en compte que {bareme.nb_volees} : aucune validation n'aurait lieu."
            ),
            ordre,
        )


def _anomalies_ordres(phases: Sequence[EtapeSequencee]) -> Iterator[Anomalie]:
    """Les ordres doivent former la suite contiguë 1..N (ni trou, ni doublon, ni départ décalé).

    Anomalie **non localisée** (`ordre=None`) : une suite `[1, 1, 3]` ne désigne aucune phase
    fautive en particulier — c'est la séquence entière qui l'est.
    """
    ordres = sorted(phase.ordre for phase in phases)
    if ordres != list(range(1, len(phases) + 1)):
        yield Anomalie(
            SequenceOrdreInvalide(
                "Les phases d'une séquence sont numérotées 1, 2, 3… sans trou ni doublon : "
                f"ordres reçus {ordres}."
            )
        )


# E05US025 — `_anomalies_unicite_qualification` a été **retiré** ici.
#
# E05US021 l'avait posé pour fermer un bug (neuf lecteurs de « la » qualification), mais ce n'était
# pas une règle du tir à l'arc : on avait interdit le cas au lieu de réparer les lecteurs. E05US025
# les répare — chacun sait désormais **de quelle** phase il parle — et rend le cas licite
# (ADR-0082). ⚠️ Ne pas le réintroduire « par prudence » : un lecteur qui aurait besoin de
# l'unicité pour être juste est un lecteur à corriger.


def _anomalies_sources(phases: Sequence[EtapeSequencee]) -> Iterator[Anomalie]:
    """Les invariants **collectifs** du peuplement d'une phase (E05US001, étendus par E05US010).

    Chaque source désigne une phase existante et antérieure ; elle ne prélève pas par rangs dans
    une phase qui n'en produit aucun ; ses rangs tiennent dans l'effectif ; deux sources ne se
    recoupent pas ; la somme couvre l'effectif déclaré. ⚠️ Ce dernier contrôle ne s'applique que si
    **tous** les prélèvements sont dénombrables — une source relative ne se compte qu'à l'exécution,
    et l'exiger ici rendrait les plages relatives inutilisables (anomalie à afficher, E01US024).
    """
    par_ordre = {phase.ordre: phase for phase in phases}
    for phase in phases:
        for source in phase.sources:
            phase_source = par_ordre.get(source.ordre_source)
            if phase_source is None:
                yield Anomalie(
                    SourceIntrouvable(
                        f"La phase {phase.ordre} est alimentée par une phase d'ordre "
                        f"{source.ordre_source}, qui n'existe pas dans la séquence."
                    ),
                    phase.ordre,
                )
                # Les contrôles suivants déréférencent la phase source : sans elle, ils n'ont pas
                # de sens. La version levante s'arrêtait ici de toute façon.
                continue
            if source.ordre_source >= phase.ordre:
                yield Anomalie(
                    SourceApresPhase(
                        f"La phase {phase.ordre} ne peut être alimentée que par une phase "
                        f"antérieure ; l'ordre {source.ordre_source} lui est égal ou postérieur."
                    ),
                    phase.ordre,
                )
                continue
            # ⚠️ **Toutes les natures sauf `RESTE`**, et non les seuls rangs. Le CA est catégorique :
            # « la seule façon licite de lui succéder est *les mêmes archers, sans ordre* ». Un
            # premier jet ne refusait que `RANGS` — or « les gagnants du tour 1 de l'échauffement »
            # est exactement aussi vide, un échauffement n'ayant ni tour ni duel. Le trou était
            # d'autant plus invisible que les deux tests encadrants couvraient `RANGS` (refusé) et
            # `RESTE` (accepté), laissant la troisième nature dans l'angle mort.
            if source.nature is not NatureSource.RESTE and not produit_un_classement(
                phase_source.type
            ):
                yield Anomalie(
                    PhaseSansClassementPrelevee(
                        f"La phase {phase.ordre} prélève « {source.nature.value} » dans la phase "
                        f"{source.ordre_source}, de type « {phase_source.type.value} », qui ne "
                        "produit ni classement ni rencontre : reprendre « le reste » de ses "
                        "participants est la seule succession possible."
                    ),
                    phase.ordre,
                )
            if (
                phase_source.effectif is not None
                and source.rang_fin is not None
                and source.rang_fin > phase_source.effectif
            ):
                yield Anomalie(
                    RangsSourceInexistants(
                        f"La source prélève jusqu'au rang {source.rang_fin}, mais la phase "
                        f"{source.ordre_source} n'en classe que {phase_source.effectif}."
                    ),
                    phase.ordre,
                )
        yield from _anomalies_recoupements(phase, par_ordre)
        yield from _anomalies_somme(phase)


def _anomalies_recoupements(
    phase: EtapeSequencee, par_ordre: dict[int, EtapeSequencee]
) -> Iterator[Anomalie]:
    """Deux sources d'une même phase ne prélèvent pas le même participant (CA « cohérence »).

    Le recoupement se juge **par phase source**. Seuls les prélèvements par rangs se comparent en
    rangs — mais deux sources **strictement identiques** sont refusées quelle que soit leur nature.
    ⚠️ Le contrôle **ne dépend pas** de l'effectif déclaré de la phase source : un premier jet le
    sautait quand cet effectif valait `None` — le cas par défaut —, si bien que deux plages
    entièrement bornées passaient sans examen (cf. `SourcePhase.intervalle`).
    """
    doublons = [s for s in phase.sources if phase.sources.count(s) > 1]
    if doublons:
        yield Anomalie(
            SourcesQuiSeRecoupent(
                f"La phase {phase.ordre} porte deux fois le même prélèvement : un participant ne "
                "peut pas entrer deux fois dans la même phase."
            ),
            phase.ordre,
        )
    for ordre_source in sorted({source.ordre_source for source in phase.sources}):
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
                    yield Anomalie(
                        SourcesQuiSeRecoupent(
                            f"Deux sources de la phase {phase.ordre} prélèvent le même rang "
                            f"{max(debut, autre_debut)} de la phase {ordre_source} : un "
                            "participant ne peut pas entrer deux fois dans la même phase."
                        ),
                        phase.ordre,
                    )
                    # Un recoupement par phase source suffit à le dire : énumérer chaque paire
                    # noierait le diagnostic sous des redites du même défaut.
                    return
            intervalles.append(intervalle)


def _anomalies_somme(phase: EtapeSequencee) -> Iterator[Anomalie]:
    """Les prélèvements doivent tenir dans l'effectif déclaré de la phase (CA « cohérence »).

    Deux régimes : **tous dénombrables** ⇒ la somme doit **égaler** l'effectif ; **au moins un
    relatif** ⇒ l'égalité devient indécidable au format, mais l'**inégalité** reste décidable — un
    prélèvement relatif ajoute ≥ 0 participants, donc des dénombrables qui dépassent déjà l'effectif
    sont faux quoi qu'il arrive. Un premier jet désactivait **tout** le contrôle dès qu'un
    prélèvement était relatif, et son test l'évitait en choisissant 8 prélevés pour 32 déclarés.
    """
    if phase.effectif is None or not phase.sources:
        return
    comptes = [source.effectif_selectionne for source in phase.sources]
    total = sum(compte for compte in comptes if compte is not None)
    if any(compte is None for compte in comptes):
        if total > phase.effectif:
            yield Anomalie(
                EffectifIncompatible(
                    f"La phase {phase.ordre} attend {phase.effectif} participants, mais ses seuls "
                    f"prélèvements dénombrables en prennent déjà {total}."
                ),
                phase.ordre,
            )
        return
    if total != phase.effectif:
        yield Anomalie(
            EffectifIncompatible(
                f"La phase {phase.ordre} attend {phase.effectif} participants, mais ses sources en "
                f"prélèvent {total}."
            ),
            phase.ordre,
        )
