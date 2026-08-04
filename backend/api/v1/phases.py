"""Endpoints REST de la séquence de phases (`/api/v1`) — composition d'un tournoi (E05US001).

Suit le patron de bout en bout (E00US009) : **DTO Pydantic** distincts des agrégats, **écritures**
routées par la file (writer unique, ADR-0005) et protégées par `exiger_admin`, **lectures** hors
boucle (threadpool), **erreurs typées** traduites à la frontière (`api/erreurs.py`).

Ressource rattachée au tournoi : `/tournois/{tournoi_id}/phases`. Lecture ouverte (comme les autres
consultations, E10US001) ; composition et cycle de vie réservés à l'admin. La **cohérence** de la
séquence (source vide / rangs inexistants / effectif incompatible) est une règle du domaine → elle
remonte en 422 ; les conflits d'état (transition illégale, suppression d'une source référencée) en
409 (ADR-0045).
"""

from __future__ import annotations

import asyncio
from enum import Enum

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.phases import ServicePhases
from domain.phase import (
    IssueTour,
    NatureSource,
    Phase,
    SourcePhase,
    StatutPhase,
    TypePhase,
)
from domain.politiques import NomProfondeur, ProfondeurClassement
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

    Deux modes seulement, ceux qu'un organisateur choisit : `un_vers_n` (tous les rangs se jouent)
    et `podium` (on ne départage que les `jusqu_au` premiers, le reste reste groupé). Le catalogue
    `depth` en compte un troisième — `aucun` — délibérément **absent** de la façade : c'est le
    contenu du type échauffement, pas un réglage de tableau (règle « on n'offre pas en façade ce
    qu'aucun moteur ne sait dérouler », ADR-0045 §2).

    Jumeau assumé de `api/v1/formats.ProfondeurDTO`, pour la raison déjà tranchée sur `SourceDTO`.
    """

    nom: NomProfondeur
    jusqu_au: int | None = None
    """Obligatoire pour `top_n`, interdit pour `un_vers_n`.

    ⚠️ **Aucune borne Pydantic ici, délibérément** (corrigé en revue). Un `ge=1` y figurait, et il
    contredisait la phrase qui l'accompagnait : il **recopiait** à moitié l'invariant que le
    `ProfondeurClassement` porte déjà, avec pour effet observable **deux codes d'erreur pour une
    seule faute** — `{"nom":"top_n","jusqu_au":0}` rendait 400 `requete_invalide`, alors que
    `{"nom":"top_n"}` rend 422 `profondeur_invalide`. Une seule source, un seul code : le domaine
    (règle 6 — la frontière API ne doit pas devenir un second lieu d'invariants).

    *(`barrage_jusqu_au`, plus bas, garde son `ge=1` : il est un entier nu sans value object pour le
    porter, donc la frontière y est bien le seul lieu possible. La divergence est assumée, pas une
    incohérence — cf. ADR-0070 « Négatives / à surveiller ».)*"""

    def vers_agregat(self) -> ProfondeurClassement:
        return ProfondeurClassement(nom=self.nom, jusqu_au=self.jusqu_au)

    @staticmethod
    def de_agregat(profondeur: ProfondeurClassement) -> ProfondeurDTO:
        return ProfondeurDTO(nom=profondeur.nom, jusqu_au=profondeur.jusqu_au)


class ConfigPhaseRequete(BaseModel):
    """Config de séquence d'une phase : son type, ses sources (facultatives, **plusieurs** possibles
    depuis E05US010) et son effectif attendu (facultatif). Sert à l'ajout comme à l'édition.

    `sources` est borné à 16 : une phase alimentée par plus d'une dizaine de provenances n'est
    pas un format, c'est une saisie qui a dérapé — et une liste non bornée à la frontière est une
    porte ouverte au déni de service (même garde que `FormatRequete.etapes`).
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

    type: TypePhase
    sources: list[SourceDTO] = Field(default_factory=list, max_length=16)
    effectif: int | None = None
    profondeur: ProfondeurDTO | None = None
    """Jusqu'où cette phase départage (E06US006, ADR-0070).

    `null` (défaut) = **non réglée**, donc le preset du type — le podium pour un tableau, soit ce
    qui se jouait avant cette US. ⚠️ Même régime d'édition **totale** que `sources` : omettre le
    champ au `PUT` **efface** le réglage et fait retomber la phase sur son preset.
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
    tournoi_id: int
    ordre: int
    type: TypePhase
    statut: StatutPhase
    sources: list[SourceDTO]
    effectif: int | None
    profondeur: ProfondeurDTO | None = None
    barrage_jusqu_au: int | None = None

    @staticmethod
    def de_agregat(phase: Phase) -> PhaseReponse:
        assert phase.id is not None, "Une phase renvoyée par le service est persistée."
        return PhaseReponse(
            id=phase.id,
            tournoi_id=phase.tournoi_id,
            ordre=phase.ordre,
            type=phase.type,
            statut=phase.statut,
            sources=[SourceDTO.de_agregat(source) for source in phase.sources],
            effectif=phase.effectif,
            profondeur=(
                None if phase.profondeur is None else ProfondeurDTO.de_agregat(phase.profondeur)
            ),
            barrage_jusqu_au=phase.barrage_jusqu_au,
        )


@router.get("/tournois/{tournoi_id}/phases", response_model=list[PhaseReponse])
async def lister_phases(tournoi_id: int, request: Request) -> list[PhaseReponse]:
    """Renvoie les phases du tournoi, ordonnées. Lève `TournoiIntrouvable` (404) si inconnu."""
    service: ServicePhases = request.app.state.service_phases
    phases = await run_in_threadpool(service.lister, tournoi_id)
    return [PhaseReponse.de_agregat(phase) for phase in phases]


@router.post(
    "/tournois/{tournoi_id}/phases",
    response_model=PhaseReponse,
    status_code=201,
    dependencies=[Depends(exiger_admin)],
)
async def ajouter_phase(
    tournoi_id: int, requete: ConfigPhaseRequete, request: Request
) -> PhaseReponse:
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
            )
        )
    )
    return PhaseReponse.de_agregat(phase)


@router.put(
    "/tournois/{tournoi_id}/phases/{phase_id}",
    response_model=PhaseReponse,
    dependencies=[Depends(exiger_admin)],
)
async def modifier_phase(
    tournoi_id: int, phase_id: int, requete: ConfigPhaseRequete, request: Request
) -> PhaseReponse:
    """Édite (totalement) la config de séquence d'une phase (**action admin**)."""
    service: ServicePhases = request.app.state.service_phases
    write_queue: WriteQueue = request.app.state.write_queue
    sources = tuple(source.vers_agregat() for source in requete.sources)
    phase = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.modifier(
                tournoi_id,
                phase_id,
                requete.type,
                sources,
                requete.effectif,
                requete.barrage_jusqu_au,
                None if requete.profondeur is None else requete.profondeur.vers_agregat(),
            )
        )
    )
    return PhaseReponse.de_agregat(phase)


@router.post(
    "/tournois/{tournoi_id}/phases/reordonner",
    response_model=list[PhaseReponse],
    dependencies=[Depends(exiger_admin)],
)
async def reordonner_phases(
    tournoi_id: int, requete: ReordonnerRequete, request: Request
) -> list[PhaseReponse]:
    """Réordonne l'ensemble des phases du tournoi (**action admin**)."""
    service: ServicePhases = request.app.state.service_phases
    write_queue: WriteQueue = request.app.state.write_queue
    phases = await asyncio.wrap_future(
        write_queue.submit(lambda: service.reordonner(tournoi_id, requete.phases))
    )
    return [PhaseReponse.de_agregat(phase) for phase in phases]


@router.delete(
    "/tournois/{tournoi_id}/phases/{phase_id}",
    status_code=204,
    dependencies=[Depends(exiger_admin)],
)
async def supprimer_phase(tournoi_id: int, phase_id: int, request: Request) -> None:
    """Retire une phase de la séquence (**action admin**). Refuse (409) si elle en alimente une
    autre (`PhaseSourceReferencee`)."""
    service: ServicePhases = request.app.state.service_phases
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(write_queue.submit(lambda: service.supprimer(tournoi_id, phase_id)))


@router.post(
    "/tournois/{tournoi_id}/phases/{phase_id}/statut",
    response_model=PhaseReponse,
    dependencies=[Depends(exiger_admin)],
)
async def changer_statut(
    tournoi_id: int, phase_id: int, requete: TransitionRequete, request: Request
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
    phase = await asyncio.wrap_future(write_queue.submit(lambda: action(tournoi_id, phase_id)))
    return PhaseReponse.de_agregat(phase)
