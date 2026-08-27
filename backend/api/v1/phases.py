"""Phases — ressource rattachée au **départ**, pas au tournoi : c'est le créneau qui porte une
séquence (ADR-0075).

⚠️ **La cohérence de la séquence est une règle du DOMAINE** (422) ; les conflits d'état — transition
illégale, suppression d'une source référencée — sont applicatifs (409). Lecture ouverte, composition
et cycle de vie réservés à l'admin.
"""

from __future__ import annotations

import asyncio
import datetime
from enum import Enum

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.arrets_programmes import ServiceArretsProgrammes
from application.phases import ServicePhases
from domain.arret_programme import (
    ArretDeCirconstance,
    ArretProgramme,
    FranchissementArret,
    PorteeArret,
)
from domain.big_shoot_off import ConfigurationBigShootOff
from domain.colline import ConfigurationColline
from domain.deroule_etape import EtapeDeroule
from domain.phase import (
    IssueTour,
    NatureSource,
    Phase,
    SourcePhase,
    StatutPhase,
    TypePhase,
)
from domain.politiques import NomProfondeur, ProfondeurClassement
from domain.poule import BaremePoule, ModeDeComposition, ReglageDePoules
from domain.qualification import DecoupageEnTours
from domain.suisse import ConfigurationSuisse
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["phases"])


class SourceDTO(BaseModel):
    """Un **prélèvement** de participants dans une phase antérieure (E05US010).

    Trois natures, dont les champs diffèrent — `rangs` (le défaut historique, `rang_fin=null` pour
    « et suivants »), `issue_de_tour` (`tour` + `issue`) et `reste`. Le DTO les accepte tous en
    optionnel et **délègue la validation au domaine** (`SourcePhase.__post_init__`, qui lève
    `SourceMalFormee` → 422) : la règle « chaque nature porte ses champs » n'a pas à être écrite
    deux fois, et la frontière API ne doit pas devenir un second lieu d'invariants (règle 6).
    """

    ordre_source: int
    nature: NatureSource = NatureSource.RANGS
    rang_debut: int = 1
    rang_fin: int | None = None
    tour: int | None = None
    issue: IssueTour | None = None

    @staticmethod
    def de_agregat(source: SourcePhase) -> SourceDTO:
        return SourceDTO(
            ordre_source=source.ordre_source,
            nature=source.nature,
            rang_debut=source.rang_debut,
            rang_fin=source.rang_fin,
            tour=source.tour,
            issue=source.issue,
        )

    def vers_agregat(self) -> SourcePhase:
        return SourcePhase(
            ordre_source=self.ordre_source,
            nature=self.nature,
            rang_debut=self.rang_debut,
            rang_fin=self.rang_fin,
            tour=self.tour,
            issue=self.issue,
        )


class ProfondeurDTO(BaseModel):
    """La **profondeur de classement** d'une phase (E06US006, ADR-0070).

    Deux modes seulement, ceux qu'un organisateur choisit : `un_vers_n` et `top_n`. Le catalogue
    `depth` en compte un troisième — `aucun` — délibérément **absent** de la façade : c'est le
    contenu du type échauffement, pas un réglage de tableau (ADR-0045 §2).

    Jumeau assumé de `api/v1/formats.ProfondeurDTO` — cf. `DETTE-054`.
    """

    nom: NomProfondeur
    jusqu_au: int | None = None
    """Obligatoire pour `top_n`, interdit pour `un_vers_n`.

    ⚠️ **Aucune borne Pydantic ici, délibérément** : un `ge=1` recopiait à moitié l'invariant du
    `ProfondeurClassement`, avec pour effet **deux codes d'erreur pour une seule faute** (400
    `requete_invalide` contre 422 `profondeur_invalide`). Une seule source, un seul code : le
    domaine (règle 6). `barrage_jusqu_au` garde le sien — entier nu sans value object pour le
    porter, la frontière y est le seul lieu possible (ADR-0070, « à surveiller »).
    """

    def vers_agregat(self) -> ProfondeurClassement:
        return ProfondeurClassement(nom=self.nom, jusqu_au=self.jusqu_au)

    @staticmethod
    def de_agregat(profondeur: ProfondeurClassement) -> ProfondeurDTO:
        return ProfondeurDTO(nom=profondeur.nom, jusqu_au=profondeur.jusqu_au)


class BaremePouleDTO(BaseModel):
    """Ce que rapporte une rencontre de poule — victoire / nul / défaite (E05US023).

    Défaut **3 / 1 / 0**, arbitré le 31/07/2026. Aucune borne Pydantic : l'invariant
    « victoire ≥ nul ≥ défaite ≥ 0 » est porté par `BaremePoule`, et le recopier ici rendrait deux
    codes d'erreur pour une même faute — la leçon déjà tirée sur `ProfondeurDTO.jusqu_au`.
    """

    victoire: int = 3
    nul: int = 1
    defaite: int = 0

    def vers_agregat(self) -> BaremePoule:
        return BaremePoule(victoire=self.victoire, nul=self.nul, defaite=self.defaite)

    @staticmethod
    def de_agregat(bareme: BaremePoule) -> BaremePouleDTO:
        return BaremePouleDTO(victoire=bareme.victoire, nul=bareme.nul, defaite=bareme.defaite)


class ReglagePoulesDTO(BaseModel):
    """Le réglage d'une phase de **poules** (E05US023, ADR-0083 §4).

    Porte la **taille visée**, pas le nombre de groupes : le déroulé se compose avant le tournoi,
    inscriptions ouvertes. La conversion se fait le jour J (`ReglageDePoules.pour_effectif`).
    `nb_qualifies` porte aussi le **régime d'ex æquo** (§5) : vide, la poule *classe* ; renseigné,
    elle *qualifie*. Pas un champ de plus — le même, rendu explicite. ⚠️ Jumeau assumé de son
    homonyme dans l'autre routeur de composition, 3ᵉ paire — `DETTE-054`.
    """

    taille_visee: int
    bareme: BaremePouleDTO | None = None
    """`null` = le barème par défaut 3 / 1 / 0. Le service, lui, l'écrit **toujours** en base."""

    nb_qualifies: int | None = None
    rencontres_par_archer: int | None = None
    departage_inter_poules: bool = False
    """Départager les archers d'un même rang de poule par leur décompte (§10.1, ADR-0083 §6)."""

    mode: ModeDeComposition = ModeDeComposition.SERPENT
    """Comment composer les groupes : `serpent` (défaut) ou `par_niveau` (E05US029)."""

    serpent_assume: bool = False
    """La dérogation qui lève le refus « 2ᵉ phase de poules au serpent » (E05US029)."""

    def vers_agregat(self) -> ReglageDePoules:
        return ReglageDePoules(
            taille_visee=self.taille_visee,
            bareme=BaremePoule() if self.bareme is None else self.bareme.vers_agregat(),
            nb_qualifies=self.nb_qualifies,
            rencontres_par_archer=self.rencontres_par_archer,
            departage_inter_poules=self.departage_inter_poules,
            mode=self.mode,
            serpent_assume=self.serpent_assume,
        )

    @staticmethod
    def de_agregat(reglage: ReglageDePoules) -> ReglagePoulesDTO:
        return ReglagePoulesDTO(
            taille_visee=reglage.taille_visee,
            bareme=BaremePouleDTO.de_agregat(reglage.bareme),
            nb_qualifies=reglage.nb_qualifies,
            rencontres_par_archer=reglage.rencontres_par_archer,
            departage_inter_poules=reglage.departage_inter_poules,
            mode=reglage.mode,
            serpent_assume=reglage.serpent_assume,
        )


class ReglageBigShootOffDTO(BaseModel):
    """Le réglage d'un **Big Shoot Off** (E05US028) — combien sortent, manche par manche.

    `eliminations` est une **liste écrite par l'organisateur**, une case par manche : `[4, 2, 1]`
    = quatre sortent au 1ᵉʳ tour, deux au 2ᵉ, un au 3ᵉ. Rien n'impose qu'elle décroisse.
    ⚠️ **Pas de champ « restants »** : K se **déduit** de ce que la liste n'élimine pas — deux
    champs pour la même information pouvaient se contredire. Aucune borne haute de longueur : le
    format est réutilisé sur des effectifs qu'il ignore. Jumeau, 4ᵉ paire — `DETTE-054`.
    """

    # ⚠️ Bornes ajoutées à la revue d'E05US028. Les **valeurs** restent libres (`paliers_pour`
    # s'ajuste à l'effectif, c'est ce qui rend un format réutilisable), mais la **longueur** et les
    # entiers du format du tir ne le sont pas : le produit `len(eliminations)` par `volees` devient
    # le barème d'une `Serie`, et le réglage est réémis dans chaque projection. Le voisin
    # `ConfigPhaseRequete.sources` portait déjà ce plafond avec le motif « une liste non bornée à la
    # frontière est une saisie qui a dérapé » — l'asymétrie était gratuite.
    eliminations: list[int] = Field(max_length=64)
    volees: int = Field(default=1, ge=1)
    fleches_par_volee: int = Field(default=3, ge=1)
    cumul_des_manches: bool = False
    """Cumuler les manches plutôt que repartir de zéro. Défaut : remise à zéro — c'est ce qui garde
    l'enjeu jusqu'à la dernière flèche (arbitrage du 31/07/2026)."""

    departage_les_sortants: bool = False
    """Faire tirer un barrage entre **éliminés** à égalité, pour leur donner des rangs distincts.

    Défaut : non. Leur égalité ne change rien à qui continue — elle ne décide que d'un numéro de
    rang —, et un barrage immobilise le pas de tir et le juge (arbitrage du 14/08/2026)."""

    def vers_agregat(self) -> ConfigurationBigShootOff:
        return ConfigurationBigShootOff(
            eliminations=tuple(self.eliminations),
            volees=self.volees,
            fleches_par_volee=self.fleches_par_volee,
            cumul_des_manches=self.cumul_des_manches,
            departage_les_sortants=self.departage_les_sortants,
        )

    @staticmethod
    def de_agregat(reglage: ConfigurationBigShootOff) -> ReglageBigShootOffDTO:
        return ReglageBigShootOffDTO(
            eliminations=list(reglage.eliminations),
            volees=reglage.volees,
            fleches_par_volee=reglage.fleches_par_volee,
            cumul_des_manches=reglage.cumul_des_manches,
            departage_les_sortants=reglage.departage_les_sortants,
        )


class DecoupageDTO(BaseModel):
    """Le découpage d'une **qualification** en tours (E05US035, ADR-0093) — « 20 volées en 2 ».

    Un seul champ : l'organisateur saisit un **nombre de tours**. Le découpage ne change rien au
    score (`avancer ≠ classer`, ADR-0090) ; il n'existe que pour donner à une pause une frontière.
    ⚠️ **La divisibilité n'est pas ici** : « 2 tours » est licite sur 20 volées et pas sur 15 —
    elle dépend du **barème**, que ce DTO ne connaît pas. `EtapeDeroule` la vérifie. Le `le=64` est
    la garde de frontière habituelle, pas la règle du format. Jumeau, 7ᵉ paire — `DETTE-054`.
    """

    model_config = ConfigDict(extra="forbid")

    nb_tours: int = Field(default=1, ge=1, le=64)

    def vers_agregat(self) -> DecoupageEnTours:
        return DecoupageEnTours(nb_tours=self.nb_tours)

    @staticmethod
    def de_agregat(decoupage: DecoupageEnTours) -> DecoupageDTO:
        return DecoupageDTO(nb_tours=decoupage.nb_tours)


class ReglageSuisseDTO(BaseModel):
    """Le réglage d'une phase au **système suisse** (E05US026) — le nombre de rondes.

    Un seul champ : tout le reste du format est écrit dans le moteur (appariement, évitement des
    revanches, byes, Buchholz).
    ⚠️ **La borne haute n'est pas ici** : à N participants on ne peut apparier que N-1 rondes sans
    ré-affrontement, donc elle dépend de l'**effectif**, que ce DTO ne connaît pas. `EtapeDeroule`
    la vérifie. Le `le=64` est la garde de frontière habituelle. Jumeau, 5ᵉ paire — `DETTE-054`.
    """

    model_config = ConfigDict(extra="forbid")

    nb_rondes: int = Field(default=5, ge=1, le=64)

    def vers_agregat(self) -> ConfigurationSuisse:
        return ConfigurationSuisse(nb_rondes=self.nb_rondes)

    @staticmethod
    def de_agregat(reglage: ConfigurationSuisse) -> ReglageSuisseDTO:
        return ReglageSuisseDTO(nb_rondes=reglage.nb_rondes)


class ReglageCollineDTO(BaseModel):
    """Le réglage d'une phase de **colline** (E05US027) — manches et portée de défi.

    **Deux champs là où ses voisins n'en ont qu'un** : `portee_de_defi` distingue le **King of the
    Hill** (1) du **Ladder** (2+). Le référentiel §10.1 les donne comme deux formats ; ce sont deux
    réglages d'un même format (règle 2), d'où un seul `TypePhase.COLLINE`.
    ⚠️ **La borne haute de la portée n'est pas ici** — elle dépend de l'effectif, vérifié par
    `EtapeDeroule`. Le `le=64` est la garde de frontière. Jumeau, 8ᵉ paire — `DETTE-054`.
    """

    model_config = ConfigDict(extra="forbid")

    nb_manches: int = Field(default=5, ge=1, le=64)
    portee_de_defi: int = Field(default=1, ge=1, le=64)

    def vers_agregat(self) -> ConfigurationColline:
        return ConfigurationColline(nb_manches=self.nb_manches, portee_de_defi=self.portee_de_defi)

    @staticmethod
    def de_agregat(reglage: ConfigurationColline) -> ReglageCollineDTO:
        return ReglageCollineDTO(
            nb_manches=reglage.nb_manches, portee_de_defi=reglage.portee_de_defi
        )


class ArretProgrammeDTO(BaseModel):
    """Une **pause programmée** : après quel tour la salle s'arrête (E05US033, ADR-0091).

    `portee` vaut `phase` (défaut, le moins intrusif) ou `depart` — toutes les phases du créneau,
    chacune **finissant son tour en cours**.
    ⚠️ **Ce DTO ne porte aucun état de franchissement** : il décrit une *définition*, rejouée par
    chaque créneau (ADR-0076) ; mêler les deux laisserait un client réécrire un état d'exploitation
    en éditant un déroulé. La borne d'`apres_tour` dépend du nombre de tours — `EtapeDeroule`.
    """

    model_config = ConfigDict(extra="forbid")

    apres_tour: int = Field(ge=1, le=64)
    portee: PorteeArret = PorteeArret.PHASE

    def vers_agregat(self) -> ArretProgramme:
        return ArretProgramme(apres_tour=self.apres_tour, portee=self.portee)

    @staticmethod
    def de_agregat(arret: ArretProgramme) -> ArretProgrammeDTO:
        return ArretProgrammeDTO(apres_tour=arret.apres_tour, portee=arret.portee)


class ConfigPhaseRequete(BaseModel):
    """Config de séquence d'une phase : son type, ses sources (facultatives, **plusieurs** possibles
    depuis E05US010) et son effectif attendu (facultatif). Sert à l'ajout comme à l'édition.

    `sources` est borné à 16 : une phase alimentée par plus d'une dizaine de provenances n'est
    pas un format, c'est une saisie qui a dérapé — et une liste non bornée à la frontière est une
    porte ouverte au déni de service (même garde que `FormatRequete.etapes`).
    """

    model_config = ConfigDict(extra="forbid")
    """⚠️ **Seul régime strict du projet, et c'est délibéré** (E05US010, ADR-0061).

    Les 31 autres routeurs laissent Pydantic **ignorer** les champs inconnus. Ici le champ d'entrée
    a été renommé (`source` → `sources`) : sans cette garde, un client resté sur l'ancienne forme
    verrait sa clé ignorée — et comme le `PUT` est une édition **totale**, il **écraserait** la
    composition existante par une liste vide, en 200. Une trentaine de tablettes personnelles
    servent une SPA depuis leur cache : mieux vaut un 422 explicite qu'une destruction muette.
    """

    type: TypePhase
    sources: list[SourceDTO] = Field(default_factory=list, max_length=16)
    effectif: int | None = None
    profondeur: ProfondeurDTO | None = None
    """Jusqu'où cette phase départage (E06US006, ADR-0070).

    `null` (défaut) = **non réglée**, donc le preset du type : le **podium** pour une élimination
    directe, le **classement intégral** pour un placement (ADR-0070 §3). ⚠️ Même régime d'édition
    **totale** que `sources` : omettre le champ au `PUT` **efface** le réglage.
    """

    poules: ReglagePoulesDTO | None = None
    """Le réglage d'une phase de **poules** (E05US023, ADR-0083).

    `null` (défaut) = **non réglée**, ce qui est licite : c'est la composition du jour J qui exigera
    le réglage (`PhasePasReglee`, 409). ⚠️ Même régime d'édition **totale** que `sources`. Posé sur
    un type qui n'est pas `poules`, il lève `ReglageDePoulesInvalide` (422) — contrairement à
    `profondeur`, dont l'incompatibilité n'est refusée qu'à l'application.
    """

    big_shoot_off: ReglageBigShootOffDTO | None = None
    """Le réglage d'un **Big Shoot Off** (E05US028) — `null` = non réglé, même régime."""

    suisse: ReglageSuisseDTO | None = None
    """Le réglage d'une phase au **système suisse** (E05US026) — `null` = non réglée.

    ⚠️ Les trois docstrings sont désormais **rattachées à leur champ**. Elles ne l'étaient plus : en
    Python, un littéral documente l'attribut qui le **précède**, et le bloc « poules » avait glissé
    d'un cran à chaque réglage inséré — jusqu'à devenir une expression morte sous `suisse` (relevé
    en revue). C'est l'angle mort que `DETTE-054` désigne, vu de l'autre côté."""

    colline: ReglageCollineDTO | None = None
    """Le réglage d'une phase de **colline** (E05US027) — `null` = non réglée.

    Même régime d'édition **totale** que ses voisins : omettre le champ au `PUT` efface le réglage.
    Posé sur un type qui n'est pas `colline`, il lève `ConfigurationCollineInvalide` (422)."""

    decoupage: DecoupageDTO | None = None
    """Le découpage d'une **qualification** en tours (E05US035) — `null` = non découpée.

    Même régime d'édition **totale** que ses voisins : omettre le champ au `PUT` efface le réglage.
    Posé sur un type qui n'est pas `qualification`, il lève `DecoupageEnToursInvalide` (422)."""

    arrets: list[ArretProgrammeDTO] = Field(default_factory=list, max_length=64)
    """Les **pauses programmées** de cette étape (E05US033, ADR-0091) — liste vide = aucune.

    ⚠️ Une **liste**, parce que c'est la lettre du CA : l'organisateur prépare sa journée.
    ⚠️ Même régime d'édition **totale** : envoyer une liste vide au `PUT` **supprime** tous les
    arrêts — l'effacement porte ici sur du planning saisi ligne à ligne, donc l'écran doit toujours
    renvoyer la liste complète, jamais un delta. Deux arrêts après le même tour, ou un arrêt au-delà
    du dernier tour connu, lèvent `ArretProgrammeInvalide` (422) — le refus vit sur l'étape.
    """

    titre: str | None = Field(default=None, max_length=80)
    """Le **libellé** que l'organisateur donne à cette étape (E16US002) — `null` = aucun.

    ⚠️ Même régime d'édition **totale** : omettre le champ au `PUT` **efface** le titre et fait
    retomber l'écran sur le libellé du type. C'est le geste par lequel on *retire* un titre.

    **Borné à 80 caractères à la frontière, pas dans le domaine** : le domaine n'a aucune règle
    métier sur la longueur. Ce qu'il faut borner est l'**entrée** — même garde que `sources` (16).
    """

    barrage_jusqu_au: int | None = Field(default=None, ge=1)
    """Rang jusqu'auquel les ex æquo se départagent **au tir** (E06US003, ADR-0066).

    `null` (défaut) = **aucun barrage**, donc l'ex æquo partagé d'E06US001. ⚠️ Le `PUT` étant une
    édition **totale**, omettre ce champ **efface** le seuil : c'est le régime déjà annoncé plus
    haut pour `sources`, et la raison du `extra="forbid"`.
    """


class ReordonnerRequete(BaseModel):
    """Nouvel ordre de **l'ensemble** des phases : la liste complète de leurs identifiants."""

    phases: list[int]


class TransitionPhase(str, Enum):
    """Action de cycle de vie demandée sur une phase (ADR-0045 §1)."""

    DEMARRER = "demarrer"
    METTRE_EN_PAUSE = "mettre_en_pause"
    REPRENDRE = "reprendre"
    TERMINER = "terminer"


class TransitionRequete(BaseModel):
    """Transition de statut à appliquer à une phase."""

    transition: TransitionPhase


class PhaseReponse(BaseModel):
    """Représentation d'une phase renvoyée au client (config de séquence, sans les politiques de
    scoring — celles-ci ont leurs propres endpoints)."""

    id: int
    depart_id: int
    ordre: int
    type: TypePhase
    statut: StatutPhase
    sources: list[SourceDTO]
    effectif: int | None
    profondeur: ProfondeurDTO | None = None
    poules: ReglagePoulesDTO | None = None
    big_shoot_off: ReglageBigShootOffDTO | None = None
    suisse: ReglageSuisseDTO | None = None
    """Le réglage d'une phase au **système suisse** (E05US026) — `null` = non réglée."""

    colline: ReglageCollineDTO | None = None
    """Le réglage d'une phase de **colline** (E05US027) — `null` = non réglée.

    Même régime d'édition **totale** que ses voisins : omettre le champ au `PUT` efface le réglage.
    Posé sur un type qui n'est pas `colline`, il lève `ConfigurationCollineInvalide` (422)."""

    decoupage: DecoupageDTO | None = None
    """Le découpage d'une **qualification** en tours (E05US035) — `null` = non découpée.

    Même régime d'édition **totale** que ses voisins : omettre le champ au `PUT` efface le réglage.
    Posé sur un type qui n'est pas `qualification`, il lève `DecoupageEnToursInvalide` (422)."""

    barrage_jusqu_au: int | None = None

    @staticmethod
    def de_agregat(phase: Phase) -> PhaseReponse:
        assert phase.id is not None, "Une phase renvoyée par le service est persistée."
        return PhaseReponse(
            id=phase.id,
            depart_id=phase.depart_id,
            ordre=phase.ordre,
            type=phase.type,
            statut=phase.statut,
            sources=[SourceDTO.de_agregat(source) for source in phase.sources],
            effectif=phase.effectif,
            profondeur=(
                None if phase.profondeur is None else ProfondeurDTO.de_agregat(phase.profondeur)
            ),
            poules=None if phase.poules is None else ReglagePoulesDTO.de_agregat(phase.poules),
            big_shoot_off=(
                None
                if phase.big_shoot_off is None
                else ReglageBigShootOffDTO.de_agregat(phase.big_shoot_off)
            ),
            suisse=(None if phase.suisse is None else ReglageSuisseDTO.de_agregat(phase.suisse)),
            colline=(
                None if phase.colline is None else ReglageCollineDTO.de_agregat(phase.colline)
            ),
            decoupage=(
                None if phase.decoupage is None else DecoupageDTO.de_agregat(phase.decoupage)
            ),
            barrage_jusqu_au=phase.barrage_jusqu_au,
        )


class EtapeReponse(BaseModel):
    """Une **étape du déroulé** d'un tournoi — la définition, sans créneau ni avancement.

    Miroir de `EtapeDeroule` (ADR-0076). Distincte de `PhaseReponse`, qui décrit *où en est un
    créneau* de cette étape : les deux se ressemblent parce que l'une définit ce que l'autre joue,
    mais les confondre reviendrait à réintroduire le mélange que l'ADR sépare.
    """

    id: int
    tournoi_id: int
    ordre: int
    type: TypePhase
    sources: list[SourceDTO]
    effectif: int | None
    profondeur: ProfondeurDTO | None = None
    poules: ReglagePoulesDTO | None = None
    big_shoot_off: ReglageBigShootOffDTO | None = None
    suisse: ReglageSuisseDTO | None = None
    """Le réglage d'une phase au **système suisse** (E05US026) — `null` = non réglée."""

    colline: ReglageCollineDTO | None = None
    """Le réglage d'une phase de **colline** (E05US027) — `null` = non réglée.

    Même régime d'édition **totale** que ses voisins : omettre le champ au `PUT` efface le réglage.
    Posé sur un type qui n'est pas `colline`, il lève `ConfigurationCollineInvalide` (422)."""

    decoupage: DecoupageDTO | None = None
    """Le découpage d'une **qualification** en tours (E05US035) — `null` = non découpée.

    Même régime d'édition **totale** que ses voisins : omettre le champ au `PUT` efface le réglage.
    Posé sur un type qui n'est pas `qualification`, il lève `DecoupageEnToursInvalide` (422)."""

    nb_volees: int | None = None
    """Le nombre de volées du barème de cette étape — **lecture seule** (E05US035).

    ⚠️ **Ce n'est pas « le barème exposé »** : il se règle par sa propre ressource
    (`/bareme-qualification`), et l'y dupliquer en écriture ouvrirait deux chemins. Ce qui est servi
    ici est le seul chiffre dont l'atelier a besoin pour dire ce que le découpage donne (« 2 tours
    de 10 volées »). `null` sur tout type sans barème — donc partout sauf la qualification.
    """

    arrets: list[ArretProgrammeDTO] = Field(default_factory=list, max_length=64)
    """Les pauses programmées de cette étape (E05US033) — **rendues au complet**.

    L'édition étant totale, l'écran d'atelier doit renvoyer la liste entière au `PUT` : c'est
    pourquoi elle est servie ici sans pagination ni delta.
    """

    titre: str | None = None
    """Le **libellé** de cette étape (E16US002) — `null` = aucun, l'écran retombe sur le type.

    Servi **normalisé** par le domaine (espaces de bord retirés, blanc ramené à `null`) : le client
    n'a donc rien à nettoyer, et deux clients ne peuvent pas normaliser différemment."""

    barrage_jusqu_au: int | None = None

    @staticmethod
    def de_agregat(etape: EtapeDeroule) -> EtapeReponse:
        assert etape.id is not None, "Une étape renvoyée par le service est persistée."
        return EtapeReponse(
            id=etape.id,
            tournoi_id=etape.tournoi_id,
            ordre=etape.ordre,
            type=etape.type,
            sources=[SourceDTO.de_agregat(source) for source in etape.sources],
            effectif=etape.effectif,
            profondeur=(
                None if etape.profondeur is None else ProfondeurDTO.de_agregat(etape.profondeur)
            ),
            poules=None if etape.poules is None else ReglagePoulesDTO.de_agregat(etape.poules),
            big_shoot_off=(
                None
                if etape.big_shoot_off is None
                else ReglageBigShootOffDTO.de_agregat(etape.big_shoot_off)
            ),
            suisse=(None if etape.suisse is None else ReglageSuisseDTO.de_agregat(etape.suisse)),
            colline=(
                None if etape.colline is None else ReglageCollineDTO.de_agregat(etape.colline)
            ),
            decoupage=(
                None if etape.decoupage is None else DecoupageDTO.de_agregat(etape.decoupage)
            ),
            arrets=[ArretProgrammeDTO.de_agregat(arret) for arret in etape.arrets],
            titre=etape.titre,
            nb_volees=None if etape.bareme is None else etape.bareme.nb_volees,
            barrage_jusqu_au=etape.barrage_jusqu_au,
        )


@router.get("/tournois/{tournoi_id}/phases", response_model=list[EtapeReponse])
async def lister_phases(tournoi_id: int, request: Request) -> list[EtapeReponse]:
    """Renvoie les phases du tournoi, ordonnées. Lève `TournoiIntrouvable` (404) si inconnu."""
    service: ServicePhases = request.app.state.service_phases
    phases = await run_in_threadpool(service.lister, tournoi_id)
    return [EtapeReponse.de_agregat(phase) for phase in phases]


@router.get("/departs/{depart_id}/phases", response_model=list[PhaseReponse])
async def lister_avancement(depart_id: int, request: Request) -> list[PhaseReponse]:
    """Renvoie **où en est ce créneau** : ses phases ordonnées, avec leur statut.

    Pendant de `lister_phases` à l'autre maille (ADR-0076) : celle-ci rend le déroulé *prévu* du
    tournoi, celle-là ce qu'un créneau en a *joué*.
    `# DETTE-071` — ⚠️ **route ouverte servant `PhaseReponse` entière**, alors que ses consommateurs
    publics n'ont besoin que d'`id`, `ordre`, `type`, `statut`. Rien de secret, mais **tout champ
    ajouté à `PhaseReponse` part au public sans décision**. Résorption par un DTO étroit (E10US009).
    """
    service: ServicePhases = request.app.state.service_phases
    phases = await run_in_threadpool(service.avancement, depart_id)
    return [PhaseReponse.de_agregat(phase) for phase in phases]


@router.post(
    "/tournois/{tournoi_id}/phases",
    response_model=EtapeReponse,
    status_code=201,
    dependencies=[Depends(exiger_admin)],
)
async def ajouter_phase(
    tournoi_id: int, requete: ConfigPhaseRequete, request: Request
) -> EtapeReponse:
    """Ajoute une phase en fin de séquence (**action admin**), écriture via la file (ADR-0005)."""
    service: ServicePhases = request.app.state.service_phases
    write_queue: WriteQueue = request.app.state.write_queue
    sources = tuple(source.vers_agregat() for source in requete.sources)
    phase = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.ajouter(
                tournoi_id,
                requete.type,
                sources,
                requete.effectif,
                requete.barrage_jusqu_au,
                None if requete.profondeur is None else requete.profondeur.vers_agregat(),
                None if requete.poules is None else requete.poules.vers_agregat(),
                None if requete.big_shoot_off is None else requete.big_shoot_off.vers_agregat(),
                None if requete.suisse is None else requete.suisse.vers_agregat(),
                None if requete.colline is None else requete.colline.vers_agregat(),
                None if requete.decoupage is None else requete.decoupage.vers_agregat(),
                tuple(arret.vers_agregat() for arret in requete.arrets),
                titre=requete.titre,
            )
        )
    )
    return EtapeReponse.de_agregat(phase)


@router.put(
    "/tournois/{tournoi_id}/phases/{etape_id}",
    response_model=EtapeReponse,
    dependencies=[Depends(exiger_admin)],
)
async def modifier_phase(
    tournoi_id: int, etape_id: int, requete: ConfigPhaseRequete, request: Request
) -> EtapeReponse:
    """Édite (totalement) la config de séquence d'une phase (**action admin**)."""
    service: ServicePhases = request.app.state.service_phases
    write_queue: WriteQueue = request.app.state.write_queue
    sources = tuple(source.vers_agregat() for source in requete.sources)
    phase = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.modifier(
                tournoi_id,
                etape_id,
                requete.type,
                sources,
                requete.effectif,
                requete.barrage_jusqu_au,
                None if requete.profondeur is None else requete.profondeur.vers_agregat(),
                None if requete.poules is None else requete.poules.vers_agregat(),
                None if requete.big_shoot_off is None else requete.big_shoot_off.vers_agregat(),
                None if requete.suisse is None else requete.suisse.vers_agregat(),
                None if requete.colline is None else requete.colline.vers_agregat(),
                None if requete.decoupage is None else requete.decoupage.vers_agregat(),
                tuple(arret.vers_agregat() for arret in requete.arrets),
                titre=requete.titre,
            )
        )
    )
    return EtapeReponse.de_agregat(phase)


@router.post(
    "/tournois/{tournoi_id}/phases/reordonner",
    response_model=list[EtapeReponse],
    dependencies=[Depends(exiger_admin)],
)
async def reordonner_phases(
    tournoi_id: int, requete: ReordonnerRequete, request: Request
) -> list[EtapeReponse]:
    """Réordonne l'ensemble des phases du tournoi (**action admin**)."""
    service: ServicePhases = request.app.state.service_phases
    write_queue: WriteQueue = request.app.state.write_queue
    phases = await asyncio.wrap_future(
        write_queue.submit(lambda: service.reordonner(tournoi_id, requete.phases))
    )
    return [EtapeReponse.de_agregat(phase) for phase in phases]


@router.delete(
    "/tournois/{tournoi_id}/phases/{etape_id}",
    status_code=204,
    dependencies=[Depends(exiger_admin)],
)
async def supprimer_phase(tournoi_id: int, etape_id: int, request: Request) -> None:
    """Retire une phase de la séquence (**action admin**). Refuse (409) si elle en alimente une
    autre (`PhaseSourceReferencee`)."""
    service: ServicePhases = request.app.state.service_phases
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(write_queue.submit(lambda: service.supprimer(tournoi_id, etape_id)))


@router.post(
    "/departs/{depart_id}/phases/{phase_id}/statut",
    response_model=PhaseReponse,
    dependencies=[Depends(exiger_admin)],
)
async def changer_statut(
    depart_id: int, phase_id: int, requete: TransitionRequete, request: Request
) -> PhaseReponse:
    """Applique une transition de cycle de vie à une phase (**action admin**).

    Une transition illégale depuis l'état courant remonte en `TransitionStatutInvalide` (409).
    """
    service: ServicePhases = request.app.state.service_phases
    write_queue: WriteQueue = request.app.state.write_queue
    transitions = {
        TransitionPhase.DEMARRER: service.demarrer,
        TransitionPhase.METTRE_EN_PAUSE: service.mettre_en_pause,
        TransitionPhase.REPRENDRE: service.reprendre,
        TransitionPhase.TERMINER: service.terminer,
    }
    action = transitions[requete.transition]
    phase = await asyncio.wrap_future(write_queue.submit(lambda: action(depart_id, phase_id)))
    return PhaseReponse.de_agregat(phase)


# ─────────────────────── Arrêts programmés : la relance (E05US033) ───────────────────────


class ArretFranchiReponse(BaseModel):
    """Un arrêt **franchi** qui attend un geste de relance (E05US033, ADR-0091).

    Distinct d'`ArretProgrammeDTO`, qui décrit la *définition* : celui-ci décrit un **fait
    d'exploitation**. Les mêler laisserait un client réécrire un état d'exploitation en éditant un
    déroulé. `phases_arretees` porte **toutes** les phases que cet arrêt a coupées — c'est ce que la
    relance rendra d'un seul geste, d'où un bouton par arrêt et non par phase.
    """

    id: int
    phase_id: int
    """La phase **déclenchante** — celle dont le tour s'est achevé, pas nécessairement la seule
    arrêtée."""

    apres_tour: int
    portee: PorteeArret
    phases_arretees: list[int]

    arrete_depuis: datetime.datetime | None = None
    """L'instant où cet arrêt a éteint sa **première** phase (E05US034), en UTC — ou `None` s'il
    n'a encore rien éteint (arrêt de créneau armé, phase qui finit son tour).

    ⚠️ **Le serveur rend un instant, pas une durée.** Un « depuis 14 min » calculé ici serait périmé
    à l'affichage : la route est pollée toutes les 10 s, mais le rendu vit entre deux réponses. Le
    client soustrait de son horloge — l'écart de fuseau est nul (UTC des deux côtés) et l'écart de
    quelques secondes entre deux machines du réseau local est sans effet sur une durée affichée à la
    minute."""

    @staticmethod
    def de_agregat(franchissement: FranchissementArret) -> ArretFranchiReponse:
        assert (
            franchissement.id is not None
        ), "un franchissement relu du dépôt porte un identifiant."
        return ArretFranchiReponse(
            id=franchissement.id,
            phase_id=franchissement.phase_id,
            apres_tour=franchissement.apres_tour,
            # La portée se **déduit** de la forme du franchissement plutôt que d'être recopiée : un
            # arrêt de portée « départ » est le seul à prendre une photo des tours à finir. Stocker
            # la portée en double dans la table aurait ouvert une seconde source pour ce que la
            # définition dit déjà (`deroule_etape.config`), avec la divergence qui va avec.
            portee=PorteeArret.DEPART if franchissement.tours_a_finir else PorteeArret.PHASE,
            phases_arretees=list(franchissement.phases_arretees),
            arrete_depuis=franchissement.arrete_depuis,
        )


@router.get(
    "/departs/{depart_id}/arrets/en-attente",
    response_model=list[ArretFranchiReponse],
    dependencies=[Depends(exiger_admin)],
)
async def lister_arrets_en_attente(depart_id: int, request: Request) -> list[ArretFranchiReponse]:
    """Les arrêts qui **attendent une relance** dans ce créneau (**lecture admin**).

    Ni les arrêts armés — la coupe est décidée mais une phase finit son tour, il n'y a rien à
    relancer — ni les arrêts déjà levés.
    """
    service: ServiceArretsProgrammes = request.app.state.service_arrets_programmes
    # ⚠️ **`run_in_threadpool`, comme les deux `GET` voisins de ce fichier** (règle 7 : lectures
    # synchrones **hors** boucle événementielle). La première rédaction appelait le service
    # directement dans la coroutine, alors qu'il fait un `SELECT` avec jointure — et que le pilotage
    # polle cette route toutes les 10 s, par client. Relevé en revue (axe A).
    franchissements = await run_in_threadpool(service.en_attente_de_relance, depart_id)
    return [ArretFranchiReponse.de_agregat(f) for f in franchissements]


@router.post(
    "/departs/{depart_id}/arrets/{arret_id}/relancer",
    response_model=list[int],
    dependencies=[Depends(exiger_admin)],
)
async def relancer_arret(depart_id: int, arret_id: int, request: Request) -> list[int]:
    """Relance la salle : **toutes** les phases coupées par cet arrêt repartent (**action admin**).

    Rend la liste des phases relancées. `ArretIntrouvable` (404) si l'identifiant est inconnu,
    relève d'un autre créneau, est encore armé, ou a **déjà été levé** — un double-clic ne relance
    pas deux fois. ⚠️ **Un seul geste pour tout l'arrêt** (CA : « quatre boutons pour un seul arrêt
    créerait le piège qu'on cherche à éviter »), d'où une route adressée par **arrêt**.
    """
    service: ServiceArretsProgrammes = request.app.state.service_arrets_programmes
    write_queue: WriteQueue = request.app.state.write_queue
    relancees = await asyncio.wrap_future(
        write_queue.submit(lambda: service.lever(depart_id, arret_id))
    )
    return list(relancees)


# ─────────────────── Arrêts : la pause posée le jour J (E05US034) ───────────────────


class PoserArretRelatifRequete(BaseModel):
    """« Bloque-moi dans x tours » — la pause décidée pendant que la salle tire (E05US034).

    ⚠️ **Trois DTO d'arrêt, et ce n'est pas une redondance** : `ArretProgrammeDTO` est une
    *définition*, `ArretFranchiReponse` un *fait d'exploitation*, celui-ci une *commande*. Les deux
    premiers portent `apres_tour` (absolu), celui-ci `dans_x_tours` (relatif) : l'organisateur lit
    « tour 3 sur 5 » et pense « encore deux ». La conversion est faite par le **domaine** — un
    client qui la calculerait couperait au mauvais endroit dès dix secondes de retard.
    """

    dans_x_tours: int = Field(ge=1, le=64)
    """Combien de tours se jouent encore, **celui en cours compris**. `ge=1` : le mécanisme coupe à
    la fin d'un tour, jamais au milieu (ADR-0091). `le=64` borne l'entrée, comme `arrets` borne sa
    liste — aucun format du catalogue n'approche cet ordre de grandeur."""

    portee: PorteeArret = PorteeArret.PHASE
    """Cette phase seule, ou tout ce qui tire dans le créneau. Défaut le plus étroit : un arrêt de
    créneau posé par mégarde éteindrait la salle entière."""


class ArretDeCirconstanceReponse(BaseModel):
    """La pause qui vient d'être posée, telle que le pilotage doit la relire (E05US034).

    Rend `apres_tour` **résolu** et non le relatif reçu : c'est ce que l'organisateur doit pouvoir
    vérifier (« j'ai demandé dans 2 tours, ça coupe après le tour 4 »), et c'est aussi ce qui rend
    la réponse comparable aux arrêts programmés affichés à côté.
    """

    id: int
    phase_id: int
    apres_tour: int
    portee: PorteeArret

    @staticmethod
    def de_agregat(arret: ArretDeCirconstance) -> ArretDeCirconstanceReponse:
        assert arret.id is not None, "un arrêt relu du dépôt porte un identifiant."
        return ArretDeCirconstanceReponse(
            id=arret.id,
            phase_id=arret.phase_id,
            apres_tour=arret.apres_tour,
            portee=arret.portee,
        )


@router.post(
    "/departs/{depart_id}/phases/{phase_id}/arrets",
    response_model=ArretDeCirconstanceReponse,
    status_code=201,
    dependencies=[Depends(exiger_admin)],
)
async def poser_arret_relatif(
    depart_id: int, phase_id: int, requete: PoserArretRelatifRequete, request: Request
) -> ArretDeCirconstanceReponse:
    """Pose une pause **dans ce créneau seul**, à partir du tour en cours (**action admin**).

    ⚠️ **Adressée par créneau et par phase, et pas par étape** — la route *dit* ce que décide
    l'ADR : poser un arrêt à l'atelier se fait sur le déroulé, et tous les créneaux le rejouent
    (ADR-0076 §4) ; ici on agit sur ce qui tire **maintenant** (§5). Refus : `ArretIntrouvable`
    (404) hors créneau, `ArretProgrammeInvalide` (422) si le tour n'est pas lisible ou déjà occupé.
    """
    service: ServiceArretsProgrammes = request.app.state.service_arrets_programmes
    write_queue: WriteQueue = request.app.state.write_queue
    arret = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.poser_arret_relatif(
                depart_id, phase_id, requete.dans_x_tours, requete.portee
            )
        )
    )
    return ArretDeCirconstanceReponse.de_agregat(arret)
