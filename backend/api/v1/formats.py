"""Endpoints REST des formats de tournoi (`/api/v1`) — la brique « déroulé » (E01US023).

ADR-0060 §5. Suit le patron de bout en bout (E00US009) : DTO Pydantic distincts des agrégats,
écriture routée par la **file** (writer unique, ADR-0005) et protégée par `exiger_admin`, lecture
directe **hors boucle** (threadpool), erreurs typées traduites à la frontière.

Deux familles de routes, calquées sur `/gabarits` (E01US007/E01US008) :

- **bibliothèque** de formats réutilisables, à plat sous `/formats` ;
- **déroulé d'un tournoi**, sous `/tournois/{id}/format` : appliquer un format (crée les phases) et
  promouvoir le déroulé courant en format de bibliothèque.

Noter l'asymétrie avec les autres briques : un format appliqué ne produit **pas** un format
rattaché au tournoi, mais des **phases** — il n'y a donc pas de `GET /tournois/{id}/format`, la
lecture du déroulé restant `GET /tournois/{id}/phases` (E05US001). Exposer une route qui laisserait
croire qu'un tournoi « a » un format entretiendrait exactement la confusion que l'ADR écarte.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from api.v1.phases import EtapeReponse
from application.formats import ServiceFormats
from application.simulation_format import (
    EFFECTIF_MAX,
    GRAINE_DEFAUT,
    ResultatSimulationFormat,
    ServiceSimulationFormat,
)
from domain.anomalie import Anomalie, Gravite
from domain.bareme import BaremeQualification
from domain.big_shoot_off import ConfigurationBigShootOff
from domain.deroule import BlocDeroule, Flux, ProjectionDeroule, TourBraquet
from domain.format_tournoi import FormatTournoi, ModelePhase
from domain.grain_validation import GrainValidation, TypeGrain
from domain.patrimoine import OrigineBrique
from domain.phase import IssueTour, NatureSource, SourcePhase, TypePhase
from domain.politiques import NomProfondeur, ProfondeurClassement
from domain.poule import BaremePoule, ReglageDePoules
from domain.suisse import ConfigurationSuisse
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["formats"])


class BaremeDTO(BaseModel):
    """Barème d'une étape : `nb_volees` volées de `nb_fleches_par_volee` flèches, au cumul."""

    nb_volees: int
    nb_fleches_par_volee: int


class GrainDTO(BaseModel):
    """Grain de validation d'une étape ; `n_volees` n'a de sens que pour « toutes les N volées »."""

    type: TypeGrain
    n_volees: int | None = None


class SourceDTO(BaseModel):
    """Un **prélèvement** d'une étape de format (E05US010) — mêmes natures que sur une phase réelle.

    Jumeau assumé de `api/v1/phases.SourceDTO` : les deux routeurs exposent la même notion mais des
    ressources distinctes (une phase de tournoi / une étape de brique de bibliothèque), et un DTO
    partagé les coupleraient — la duplication à la frontière est le prix de leur indépendance
    (déjà tranché à E01US023). Le **domaine**, lui, n'a qu'un seul `SourcePhase` : c'est là que la
    règle vit, ici il n'y a que du transport.
    """

    ordre_source: int
    nature: NatureSource = NatureSource.RANGS
    rang_debut: int = 1
    rang_fin: int | None = None
    tour: int | None = None
    issue: IssueTour | None = None

    def vers_agregat(self) -> SourcePhase:
        return SourcePhase(
            ordre_source=self.ordre_source,
            nature=self.nature,
            rang_debut=self.rang_debut,
            rang_fin=self.rang_fin,
            tour=self.tour,
            issue=self.issue,
        )

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


class ProfondeurDTO(BaseModel):
    """La **profondeur de classement** d'une étape de format (E06US006, ADR-0070).

    Jumeau assumé de `api/v1/phases.ProfondeurDTO`, pour la raison déjà tranchée sur `SourceDTO` :
    même notion, deux ressources distinctes.

    ⚠️ **Les deux jumeaux sont strictement identiques**, et c'est ce que le régime brouillon
    d'ADR-0063 laisse ici. Un premier jet affirmait le contraire (« celui-ci ne valide rien de plus
    que la forme ») — c'était faux, et doublement : `vers_agregat()` construit un
    `ProfondeurClassement`, dont le `__post_init__` **refuse** un `top_n` sans seuil comme un
    `un_vers_n` avec seuil. Ce qui échappe au brouillon, ce n'est pas l'incohérence **interne** du
    descripteur (refusée des deux côtés, en 422), c'est sa **compatibilité avec le type** de
    l'étape : une profondeur posée sur une qualification s'enregistre, et n'est refusée qu'à
    `pour_tournoi`. ⚠️ Elle n'est pas non plus **diagnostiquée** — `projeter` ne lit pas la
    profondeur — donc l'organisateur ne l'apprend qu'à l'application. Inatteignable depuis l'écran
    (le front force `profondeur: null` hors tableau) ; cf. ADR-0070 §2.
    """

    nom: NomProfondeur
    jusqu_au: int | None = None

    def vers_agregat(self) -> ProfondeurClassement:
        return ProfondeurClassement(nom=self.nom, jusqu_au=self.jusqu_au)

    @staticmethod
    def de_agregat(profondeur: ProfondeurClassement) -> ProfondeurDTO:
        return ProfondeurDTO(nom=profondeur.nom, jusqu_au=profondeur.jusqu_au)


class BaremePouleDTO(BaseModel):
    """Ce que rapporte une rencontre de poule — victoire / nul / défaite, défaut 3 / 1 / 0.

    Jumeau de `api/v1/phases.BaremePouleDTO` (cf. `ReglagePoulesDTO` ci-dessus). Aucune borne
    Pydantic : `BaremePoule` porte l'invariant, un second lieu rendrait deux codes pour une faute.
    """

    victoire: int = 3
    nul: int = 1
    defaite: int = 0

    def vers_agregat(self) -> BaremePoule:
        return BaremePoule(victoire=self.victoire, nul=self.nul, defaite=self.defaite)

    @staticmethod
    def de_agregat(bareme: BaremePoule) -> BaremePouleDTO:
        return BaremePouleDTO(victoire=bareme.victoire, nul=bareme.nul, defaite=bareme.defaite)


class ReglageBigShootOffDTO(BaseModel):
    """Le réglage d'un **Big Shoot Off** (E05US028) — combien sortent, manche par manche.

    `eliminations` est une **liste écrite par l'organisateur**, une case par manche : `[4, 2, 1]`
    veut dire « quatre sortent au 1ᵉʳ tour, deux au 2ᵉ, un au 3ᵉ ». Rien n'impose qu'elle décroisse
    ni qu'elle soit régulière — ce n'est pas une progression, et le mot « suite » a été écarté au
    cadrage pour cette raison.

    ⚠️ **Il n'y a pas de champ « restants » (K)**, et c'est le cœur de l'élargissement du
    14/08/2026 : K se **déduit** de ce que la liste n'élimine pas. Deux champs pour la même
    information pouvaient se contredire ; il n'en reste qu'un.

    Aucune borne haute n'est posée sur la longueur de la liste : le format est réutilisé sur des
    effectifs qu'il ignore, et « on joue tant que la manche est possible ». L'écran montre la
    projection (`/api/v1/big-shoot-off/projection/…`) avant que l'organisateur compose.

    ⚠️ **Jumeau assumé de `api/v1/phases.ReglageBigShootOffDTO`** — 4ᵉ paire, `DETTE-054`.

    ⚠️ **Régime brouillon** (ADR-0063), comme `profondeur` et `poules` : un réglage posé sur une
    étape d'un autre type est un modèle **licite** ici, qui refusera de s'appliquer à la promotion
    (`ConfigurationBigShootOffInvalide` à la construction de la `Phase`).
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


class ReglageSuisseDTO(BaseModel):
    """Le réglage d'une étape au **système suisse** dans un format (E05US026) — le nombre de rondes.

    Jumeau assumé de `api/v1/phases.ReglageSuisseDTO` — **5ᵉ** paire, `DETTE-054`.

    ⚠️ **Régime brouillon** (ADR-0063), et il porte ici tout son sens : un format de bibliothèque
    s'écrit sans connaître l'effectif, or c'est l'effectif qui borne le nombre de rondes
    appariables sans ré-affrontement. « 5 rondes » est donc un modèle **licite** qui refusera de
    s'appliquer à un tournoi de 5 archers — le refus tombe à l'étape, jamais sur la brique.
    """

    model_config = ConfigDict(extra="forbid")

    nb_rondes: int = Field(default=5, ge=1, le=64)

    def vers_agregat(self) -> ConfigurationSuisse:
        return ConfigurationSuisse(nb_rondes=self.nb_rondes)

    @staticmethod
    def de_agregat(reglage: ConfigurationSuisse) -> ReglageSuisseDTO:
        return ReglageSuisseDTO(nb_rondes=reglage.nb_rondes)


class ReglagePoulesDTO(BaseModel):
    """Le réglage d'une étape de **poules** dans un format (E05US023, ADR-0083 §4).

    Jumeau assumé de `api/v1/phases.ReglagePoulesDTO` — même notion, deux ressources distinctes,
    pour la raison déjà tranchée sur `SourceDTO` et `ProfondeurDTO`. C'est la **3ᵉ** paire de
    jumeaux entre ces deux routeurs : le seuil du « remède structurel » de `CLAUDE.md` est atteint,
    et l'extraction est inscrite à `DETTE-054` plutôt que faite ici, où elle noierait le diff.

    ⚠️ **Régime brouillon** (ADR-0063), comme `profondeur` : un réglage de poules posé sur une
    élimination directe s'enregistre dans un format et n'est refusé qu'à `pour_tournoi`
    (`ReglageDePoulesInvalide`). Les incohérences **internes** du réglage (taille < 2, plus de
    qualifiés que de membres), elles, sont refusées ici même en 422 — `ReglageDePoules` les porte.
    """

    taille_visee: int
    bareme: BaremePouleDTO | None = None
    nb_qualifies: int | None = None
    rencontres_par_archer: int | None = None
    departage_inter_poules: bool = False

    def vers_agregat(self) -> ReglageDePoules:
        return ReglageDePoules(
            taille_visee=self.taille_visee,
            bareme=BaremePoule() if self.bareme is None else self.bareme.vers_agregat(),
            nb_qualifies=self.nb_qualifies,
            rencontres_par_archer=self.rencontres_par_archer,
            departage_inter_poules=self.departage_inter_poules,
        )

    @staticmethod
    def de_agregat(reglage: ReglageDePoules) -> ReglagePoulesDTO:
        return ReglagePoulesDTO(
            taille_visee=reglage.taille_visee,
            bareme=BaremePouleDTO.de_agregat(reglage.bareme),
            nb_qualifies=reglage.nb_qualifies,
            rencontres_par_archer=reglage.rencontres_par_archer,
            departage_inter_poules=reglage.departage_inter_poules,
        )


class EtapeDTO(BaseModel):
    """Un modèle de phase dans un format — **ni statut, ni tournoi** (ADR-0060 §5).

    L'absence de ces deux champs n'est pas un oubli du DTO : ils n'existent pas sur le modèle, et
    naissent à l'application. Les exposer ici inviterait un client à les fournir, donc à croire
    qu'un format porte un avancement.
    """

    model_config = ConfigDict(extra="forbid")
    """⚠️ **Seul régime strict du projet, et c'est délibéré** (E05US010, ADR-0061).

    Les 31 autres routeurs laissent Pydantic **ignorer** les champs inconnus. Ici, le champ d'entrée
    a été **renommé** (`source` → `sources`) : sans cette garde, un client resté sur l'ancienne
    forme
    verrait sa clé silencieusement ignorée. Et comme le `PUT` est une édition **totale**, il ne
    perdrait pas seulement sa saisie — il **écraserait** la composition existante par une liste
    vide,
    en 200. Le déploiement rend le cas réel : une trentaine de tablettes personnelles, une SPA
    servie
    depuis leur cache, aucun versionnage de bundle qui garantisse qu'elles rechargent le jour J.
    Mieux vaut un 422 explicite qu'une destruction muette."""

    ordre: int
    type: TypePhase
    bareme: BaremeDTO | None = None
    validation: GrainDTO | None = None
    sources: list[SourceDTO] = Field(default_factory=list, max_length=16)
    effectif: int | None = None
    profondeur: ProfondeurDTO | None = None
    """Jusqu'où cette étape départage (E06US006). `null` = non réglée → preset du type."""

    poules: ReglagePoulesDTO | None = None
    big_shoot_off: ReglageBigShootOffDTO | None = None
    suisse: ReglageSuisseDTO | None = None
    """Le réglage d'une phase au **système suisse** (E05US026) — `null` = non réglée."""

    """Le réglage d'une étape de poules (E05US023). `null` = non réglée.

    ⚠️ Le `extra="forbid"` ci-dessus rend ce champ **inaccessible aux clients d'avant l'US** — ce
    qui est voulu dans les deux sens : ils ne peuvent pas l'envoyer par erreur, et le PUT étant une
    édition **totale**, un client à jour qui l'omet **efface** le réglage."""

    def vers_modele(self) -> ModelePhase:
        """Traduit le DTO en agrégat de domaine.

        ⚠️ **Aucun invariant d'étape n'est revérifié ici depuis E01US024** (ADR-0063). Cette
        docstring promettait l'inverse — « une étape incohérente lève une `DomainError` → 422 » —
        et c'est précisément la garde que l'US a **déplacée** : `ModelePhase.__post_init__` n'existe
        plus. Un brouillon incohérent s'enregistre, `GET /formats/{id}/diagnostic` dit ce qui cloche
        et `PUT /tournois/{id}/format` refuse. Les **value objects** conservent, eux, leurs
        invariants (`BaremeQualification.creer`, `GrainValidation.creer`, `SourcePhase`) : une
        donnée **malformée** reste un 422, seule la **composition** est tolérée incomplète.
        """
        return ModelePhase(
            ordre=self.ordre,
            type=self.type,
            bareme=(
                None
                if self.bareme is None
                else BaremeQualification.creer(
                    self.bareme.nb_volees, self.bareme.nb_fleches_par_volee
                )
            ),
            validation=(
                None
                if self.validation is None
                else GrainValidation.creer(self.validation.type, self.validation.n_volees)
            ),
            sources=tuple(source.vers_agregat() for source in self.sources),
            effectif=self.effectif,
            profondeur=None if self.profondeur is None else self.profondeur.vers_agregat(),
            poules=None if self.poules is None else self.poules.vers_agregat(),
            big_shoot_off=(
                None if self.big_shoot_off is None else self.big_shoot_off.vers_agregat()
            ),
            suisse=(None if self.suisse is None else self.suisse.vers_agregat()),
        )

    @staticmethod
    def de_modele(etape: ModelePhase) -> EtapeDTO:
        return EtapeDTO(
            ordre=etape.ordre,
            type=etape.type,
            bareme=(
                None
                if etape.bareme is None
                else BaremeDTO(
                    nb_volees=etape.bareme.nb_volees,
                    nb_fleches_par_volee=etape.bareme.nb_fleches_par_volee,
                )
            ),
            validation=(
                None
                if etape.validation is None
                else GrainDTO(type=etape.validation.type, n_volees=etape.validation.n_volees)
            ),
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
        )


class FormatRequete(BaseModel):
    """Corps de création ou d'édition d'un format (nom + séquence d'étapes)."""

    nom: str
    # Borné pour la même raison que l'import de clubs : l'écriture passe par le writer unique. Un
    # format réel compte quelques étapes ; 64 est déjà hors de tout usage.
    etapes: list[EtapeDTO] = Field(default_factory=list, max_length=64)
    # E05US021 : « pas de tournoi de ce type sous 40 archers ». Facultatif — `None` = aucune
    # exigence propre, le plancher déduit des prélèvements fait seul la règle. Borné par le haut au
    # même plafond que la simulation : au-delà, c'est une saisie erronée, pas une règle de club.
    effectif_minimum_exige: int | None = Field(default=None, ge=1, le=EFFECTIF_MAX)


class RenommerRequete(BaseModel):
    """Corps d'une duplication ou d'une promotion : le nom sous lequel ranger le format."""

    nom: str


class AppliquerFormatRequete(BaseModel):
    """Corps d'application d'un format à un tournoi : l'identifiant du format de bibliothèque."""

    format_id: int


class FormatReponse(BaseModel):
    """Représentation d'un format de tournoi renvoyée au client."""

    id: int
    nom: str
    # Provenance de la brique (E01US023) : sert les **deux listes séparées** de l'atelier. Ne dit
    # **pas** la conformité au règlement (ADR-0060 §4).
    origine: OrigineBrique
    etapes: list[EtapeDTO]
    # E05US021 : ce que le club exige **en plus** du plancher déduit (`None` = rien). Le minimum
    # *effectif* ne se lit pas ici mais au diagnostic (`DiagnosticReponse.effectif_minimum`), qui
    # seul connaît les deux termes du `max`. **Sans défaut** : cf. `DiagnosticReponse`.
    effectif_minimum_exige: int | None

    @staticmethod
    def de_agregat(format_tournoi: FormatTournoi) -> FormatReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert format_tournoi.id is not None, "Un format persisté a toujours un identifiant."
        return FormatReponse(
            id=format_tournoi.id,
            nom=format_tournoi.nom,
            origine=format_tournoi.origine,
            etapes=[EtapeDTO.de_modele(etape) for etape in format_tournoi.etapes],
            effectif_minimum_exige=format_tournoi.effectif_minimum_exige,
        )


class AnomalieDTO(BaseModel):
    """Un défaut du déroulé, tel que l'écran doit le montrer (E01US024).

    `ordre` colle l'anomalie au **bloc** du schéma qu'elle concerne (`null` = la séquence entière) :
    c'est ce que le CA exige — « un trou visible dans le dessin, pas un message d'erreur abstrait ».
    `code` et `message` sont ceux de l'erreur typée du domaine, inchangés.
    """

    code: str
    message: str
    ordre: int | None
    gravite: Gravite

    @staticmethod
    def de_agregat(anomalie: Anomalie) -> AnomalieDTO:
        return AnomalieDTO(
            code=anomalie.code,
            message=anomalie.message,
            ordre=anomalie.ordre,
            gravite=anomalie.gravite,
        )


class FluxDTO(BaseModel):
    """Une flèche du schéma : qui passe d'une phase à l'autre, et combien."""

    ordre_source: int
    ordre_cible: int
    nature: NatureSource
    effectif: int | None
    rang_debut: int | None
    rang_fin: int | None
    tour: int | None
    issue: IssueTour | None

    @staticmethod
    def de_agregat(flux: Flux) -> FluxDTO:
        return FluxDTO(
            ordre_source=flux.ordre_source,
            ordre_cible=flux.ordre_cible,
            nature=flux.nature,
            effectif=flux.effectif,
            rang_debut=flux.rang_debut,
            rang_fin=flux.rang_fin,
            tour=flux.tour,
            issue=flux.issue,
        )


class TourDTO(BaseModel):
    """Un tour d'un tableau et son **braquet** : les rangs que se partagent gagnants et perdants."""

    tour: int
    duels: int
    plage_gagnants: tuple[int, int]
    plage_perdants: tuple[int, int]

    @staticmethod
    def de_agregat(tour: TourBraquet) -> TourDTO:
        return TourDTO(
            tour=tour.tour,
            duels=tour.duels,
            plage_gagnants=tour.plage_gagnants,
            plage_perdants=tour.plage_perdants,
        )


class BlocDTO(BaseModel):
    """Un bloc du schéma à braquets — les quatre questions du CA pour une phase."""

    ordre: int
    type: TypePhase
    effectif: int | None
    tranche: tuple[int, int] | None
    nb_volees: int | None
    nb_fleches_par_volee: int | None
    tours: list[TourDTO]
    entrees: list[FluxDTO]
    sorties: list[FluxDTO]
    sans_suite: int | None
    anomalies: list[AnomalieDTO]

    @staticmethod
    def de_agregat(bloc: BlocDeroule) -> BlocDTO:
        return BlocDTO(
            ordre=bloc.ordre,
            type=bloc.type,
            effectif=bloc.effectif,
            tranche=bloc.tranche,
            nb_volees=bloc.nb_volees,
            nb_fleches_par_volee=bloc.nb_fleches_par_volee,
            tours=[TourDTO.de_agregat(tour) for tour in bloc.tours],
            entrees=[FluxDTO.de_agregat(flux) for flux in bloc.entrees],
            sorties=[FluxDTO.de_agregat(flux) for flux in bloc.sorties],
            sans_suite=bloc.sans_suite,
            anomalies=[AnomalieDTO.de_agregat(a) for a in bloc.anomalies],
        )


class DiagnosticReponse(BaseModel):
    """Le déroulé projeté : de quoi dessiner le schéma **et** rendre le verdict d'applicabilité."""

    effectif: int | None
    applicable: bool
    blocs: list[BlocDTO]
    anomalies: list[AnomalieDTO]
    # E05US021 : le nombre d'inscrits en dessous duquel ce format ne peut pas se dérouler. Une
    # **donnée** du diagnostic, pas une anomalie : l'écran l'annonce en permanence, qu'un effectif
    # soit simulé ou non. **Sans défaut** : sur une réponse, un défaut masquerait un oubli de
    # mapping au lieu de le faire échouer.
    effectif_minimum: int

    @staticmethod
    def de_agregat(projection: ProjectionDeroule) -> DiagnosticReponse:
        return DiagnosticReponse(
            effectif=projection.effectif,
            applicable=projection.est_applicable,
            blocs=[BlocDTO.de_agregat(bloc) for bloc in projection.blocs],
            anomalies=[AnomalieDTO.de_agregat(a) for a in projection.anomalies],
            effectif_minimum=projection.effectif_minimum,
        )


class SimulerFormatRequete(BaseModel):
    """Corps de simulation d'un format : combien d'archers fictifs, et avec quelle graine."""

    effectif: int
    graine: int = GRAINE_DEFAUT


class LigneClassementDTO(BaseModel):
    """Une ligne du classement 1→N effectivement produit par la simulation."""

    rang: int | None
    nom: str
    prenom: str
    total: int


class PhaseSimuleeDTO(BaseModel):
    """Ce qu'une phase a réellement coûté : tours joués et duels tranchés.

    `effectif_projete` et `ecart` disent si le moteur a joué ce que le schéma annonçait. Aujourd'hui
    il peut diverger (`# DETTE-028` : les duels ensemencent tous les archers en lice, sans lire le
    prélèvement déclaré) — l'écran l'affiche plutôt que de servir un chiffre faux et muet.
    """

    ordre: int
    type: TypePhase
    effectif: int
    effectif_projete: int | None
    ecart: bool
    joue: bool
    tours: int
    tours_projetes: int | None
    duels: int
    duels_projetes: int | None


class SimulationFormatReponse(BaseModel):
    """Ce que le format a produit à cet effectif — la réponse au CA « simuler le format »."""

    format_id: int
    nom: str
    effectif: int
    graine: int
    duels_total: int
    volees_total: int
    phases: list[PhaseSimuleeDTO]
    classement: list[LigneClassementDTO]
    diagnostic: DiagnosticReponse

    @staticmethod
    def de_agregat(resultat: ResultatSimulationFormat) -> SimulationFormatReponse:
        return SimulationFormatReponse(
            format_id=resultat.format_id,
            nom=resultat.nom,
            effectif=resultat.effectif,
            graine=resultat.graine,
            duels_total=resultat.duels_total,
            volees_total=resultat.volees_total,
            phases=[
                PhaseSimuleeDTO(
                    ordre=phase.ordre,
                    type=phase.type,
                    effectif=phase.effectif,
                    effectif_projete=phase.effectif_projete,
                    ecart=phase.ecart,
                    joue=phase.joue,
                    tours=phase.tours,
                    tours_projetes=phase.tours_projetes,
                    duels=phase.duels,
                    duels_projetes=phase.duels_projetes,
                )
                for phase in resultat.phases
            ],
            classement=[
                LigneClassementDTO(
                    rang=ligne.rang_scratch,
                    nom=ligne.nom,
                    prenom=ligne.prenom,
                    total=ligne.total,
                )
                for ligne in resultat.classement.lignes
            ],
            diagnostic=DiagnosticReponse.de_agregat(resultat.projection),
        )


# --- Bibliothèque de formats --------------------------------------------------------------------


@router.get("/formats", response_model=list[FormatReponse])
async def lister_formats(request: Request) -> list[FormatReponse]:
    """Liste la bibliothèque de formats : lecture directe exécutée hors de la boucle."""
    service: ServiceFormats = request.app.state.service_formats
    formats = await run_in_threadpool(service.lister)
    return [FormatReponse.de_agregat(format_tournoi) for format_tournoi in formats]


@router.post(
    "/formats",
    status_code=201,
    response_model=FormatReponse,
    dependencies=[Depends(exiger_admin)],
)
async def creer_format(requete: FormatRequete, request: Request) -> FormatReponse:
    """Crée un format (**action admin**) : écriture via la file (ADR-0005).

    **Accepte un brouillon** (E01US024, ADR-0063) : un format sans étape ou à la séquence
    incohérente est créé en **201** — c'est `PUT /tournois/{id}/format` qui protège le tournoi, et
    `GET /formats/{id}/diagnostic` qui dit ce qui manque. Renvoie 409 (`nom_format_deja_pris`) si le
    nom est déjà porté, 422 si le **nom** est vide ou une valeur est malformée.
    """
    service: ServiceFormats = request.app.state.service_formats
    write_queue: WriteQueue = request.app.state.write_queue
    etapes = [etape.vers_modele() for etape in requete.etapes]
    format_tournoi = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.creer(requete.nom, etapes, requete.effectif_minimum_exige)
        )
    )
    return FormatReponse.de_agregat(format_tournoi)


@router.post(
    "/formats/precharger-presets",
    status_code=201,
    response_model=list[FormatReponse],
    dependencies=[Depends(exiger_admin)],
)
async def precharger_presets(request: Request) -> list[FormatReponse]:
    """Pré-charge les formats presets (**action admin**) : FFTA officiel et format club (E01US009).

    Idempotent sur le nom ; renvoie les formats effectivement **créés** (liste vide si tout était
    déjà présent).
    """
    service: ServiceFormats = request.app.state.service_formats
    write_queue: WriteQueue = request.app.state.write_queue
    crees = await asyncio.wrap_future(write_queue.submit(service.precharger_presets))
    return [FormatReponse.de_agregat(format_tournoi) for format_tournoi in crees]


@router.put(
    "/formats/{format_id}",
    response_model=FormatReponse,
    dependencies=[Depends(exiger_admin)],
)
async def modifier_format(
    format_id: int, requete: FormatRequete, request: Request
) -> FormatReponse:
    """Édite un format **sur place** (**action admin**) — l'origine est préservée.

    C'est l'issue « intégrer au FFTA officiel » du CA (le règlement évolue). Pour garder les deux
    modèles, passer par `/formats/{id}/duplication`.
    """
    service: ServiceFormats = request.app.state.service_formats
    write_queue: WriteQueue = request.app.state.write_queue
    etapes = [etape.vers_modele() for etape in requete.etapes]
    format_tournoi = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.modifier(format_id, requete.nom, etapes, requete.effectif_minimum_exige)
        )
    )
    return FormatReponse.de_agregat(format_tournoi)


@router.post(
    "/formats/{format_id}/duplication",
    status_code=201,
    response_model=FormatReponse,
    dependencies=[Depends(exiger_admin)],
)
async def dupliquer_format(
    format_id: int, requete: RenommerRequete, request: Request
) -> FormatReponse:
    """Détache une **copie** d'un format (**action admin**), marquée « création utilisateur ».

    L'issue « en faire une copie pour garder les deux modèles » du CA : l'original reste intact.
    """
    service: ServiceFormats = request.app.state.service_formats
    write_queue: WriteQueue = request.app.state.write_queue
    format_tournoi = await asyncio.wrap_future(
        write_queue.submit(lambda: service.dupliquer(format_id, requete.nom))
    )
    return FormatReponse.de_agregat(format_tournoi)


@router.delete(
    "/formats/{format_id}",
    status_code=204,
    dependencies=[Depends(exiger_admin)],
)
async def supprimer_format(format_id: int, request: Request) -> Response:
    """Supprime un format (**action admin**) ; les phases déjà appliquées survivent. Renvoie 204."""
    service: ServiceFormats = request.app.state.service_formats
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(write_queue.submit(lambda: service.supprimer(format_id)))
    return Response(status_code=204)


# --- Diagnostic & simulation d'un format --------------------------------------------------------


@router.get("/formats/{format_id}/diagnostic", response_model=DiagnosticReponse)
async def diagnostiquer_format(
    format_id: int,
    request: Request,
    # Bornes **identiques** à celles de la simulation (source unique : `EFFECTIF_MAX`). Un premier
    # jet laissait `effectif` libre sur cette route, alors qu'elle est **publique en lecture** et
    # que le raisonnement d'ADR-0063 §6 — « l'effectif vient du client et rien d'autre ne le
    # borne » — s'y applique mot pour mot : un entier Python n'a pas de plafond, et la réponse
    # grossit en `log2(N)` **tours** dont les plages, elles, portent des entiers de la taille de N.
    # Mesuré en revue : 2 Ko de requête anonyme → 1,2 s de CPU et 27 Mo de réponse.
    effectif: int | None = Query(default=None, ge=1, le=EFFECTIF_MAX),
) -> DiagnosticReponse:
    """Projette le format sur `effectif` archers : le schéma à braquets et ses anomalies.

    **Lecture** (hors file, règle 7) et **sans refus** : c'est l'écran de composition qui l'appelle
    à chaque frappe, sur un brouillon par définition incomplet. Le verdict d'applicabilité est dans
    le corps (`applicable`), pas dans le code HTTP — un brouillon incohérent est une réponse 200
    parfaitement normale. 404 si le format n'existe pas.
    """
    service: ServiceFormats = request.app.state.service_formats
    projection = await run_in_threadpool(service.diagnostiquer, format_id, effectif)
    return DiagnosticReponse.de_agregat(projection)


@router.post(
    "/formats/{format_id}/simulation",
    response_model=SimulationFormatReponse,
    dependencies=[Depends(exiger_admin)],
)
async def simuler_format(
    format_id: int, requete: SimulerFormatRequete, request: Request
) -> SimulationFormatReponse:
    """Joue le format sur N archers fictifs et rend ce qu'il produit (**action admin**).

    **Hors de la file d'écriture**, délibérément (ADR-0063 §6) : la simulation n'écrit rien de
    persistant — elle tourne de bout en bout sur des adapters in-memory (ADR-0054), et rien n'y mène
    à SQLite. La faire passer par le writer unique bloquerait toutes les écritures du tournoi
    pendant plusieurs secondes, pour un calcul qui ne touche pas la base. Elle part donc au
    threadpool, comme une lecture.

    400 si l'effectif sort des bornes de service, 404 si le format n'existe pas, 422 s'il porte
    une anomalie bloquante (on ne simule pas un déroulé qu'aucun tournoi ne pourrait recevoir).
    """
    service: ServiceSimulationFormat = request.app.state.service_simulation_format
    resultat = await run_in_threadpool(service.simuler, format_id, requete.effectif, requete.graine)
    return SimulationFormatReponse.de_agregat(resultat)


# --- Déroulé d'un tournoi -----------------------------------------------------------------------


@router.put(
    "/tournois/{tournoi_id}/format",
    response_model=list[EtapeReponse],
    dependencies=[Depends(exiger_admin)],
)
async def appliquer_format(
    tournoi_id: int, requete: AppliquerFormatRequete, request: Request
) -> list[EtapeReponse]:
    """Applique un format au tournoi (**action admin**) : **crée son déroulé**, via la file.

    Rend les **étapes** créées (la définition, une par rang) et non les phases : celles-ci ne sont
    que l'avancement de chaque créneau, et il y en a autant que de départs (ADR-0076).

    **Remplace** la séquence existante. Renvoie 409 (`phases_engagees`) si une phase du tournoi
    n'est plus `à venir` : le remplacement jetterait un déroulé en cours.
    """
    service: ServiceFormats = request.app.state.service_formats
    write_queue: WriteQueue = request.app.state.write_queue
    etapes = await asyncio.wrap_future(
        write_queue.submit(lambda: service.appliquer(tournoi_id, requete.format_id))
    )
    return [EtapeReponse.de_agregat(etape) for etape in etapes]


@router.post(
    "/tournois/{tournoi_id}/format/promotion",
    status_code=201,
    response_model=FormatReponse,
    dependencies=[Depends(exiger_admin)],
)
async def promouvoir_format(
    tournoi_id: int, requete: RenommerRequete, request: Request
) -> FormatReponse:
    """Capture le déroulé du tournoi en format de bibliothèque (**action admin**, « permanent »).

    Idempotent par nom (met à jour plutôt que d'accumuler des homonymes) et sans rétroaction sur
    les éditions déjà assemblées. Renvoie 409 (`tournoi_sans_phase`) si le tournoi n'a rien à
    promouvoir.
    """
    service: ServiceFormats = request.app.state.service_formats
    write_queue: WriteQueue = request.app.state.write_queue
    format_tournoi = await asyncio.wrap_future(
        write_queue.submit(lambda: service.promouvoir(tournoi_id, requete.nom))
    )
    return FormatReponse.de_agregat(format_tournoi)
