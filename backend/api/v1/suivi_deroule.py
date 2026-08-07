"""Endpoint REST du **suivi du déroulé** (E07US004, ADR-0064) — le plan rempli par la réalité.

`GET /api/v1/departs/{depart_id}/suivi-deroule` — **lecture publique**, comme le classement, le
plan de cibles et le tableau de duels.

⚠️ **La route est celle d'un créneau** depuis E01US025 (ADR-0075,
`docs/adr/0075-le-depart-est-la-portee-sportive.md`) : elle était
`/tournois/{id}/suivi-deroule` et fusionnait les créneaux — même chemin que
`/departs/{id}/classement` et `/departs/{id}/phases`, et pour la même raison (un départ rejoue le
tournoi en entier, avec son effectif et son avancement propres).

Deux consommateurs, et c'est le CA lui-même qui l'exige :
l'**écran de salle** (projeté, sans authentification possible — c'est un poste public) et le
**pilotage** (écran PC de l'organisateur). Un endpoint et non deux : la donnée est la même, seul
l'habillage change (« un seul composant de dessin, trois surfaces »).

**Rien de sensible n'y transite** : des types de phase, des comptes de duels, des tranches de rangs.
Ni nom d'archer, ni code de poste, ni donnée de paiement — la règle 6 est tenue par construction,
puisque la projection ne connaît que des structures.

Le DTO **reprend** la forme de `GET /api/v1/formats/{id}/diagnostic` (E01US024) pour ses blocs, et
lui **ajoute** un calque `avancement`. C'est délibéré : le composant de dessin du front reçoit la
même structure à l'atelier et ici, il ne diffère que par ce qu'il superpose.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from application.suivi_deroule import ServiceSuiviDeroule, SuiviDeroule
from domain.deroule import BlocDeroule, Flux, TourBraquet
from domain.suivi_deroule import AvancementBloc, AvancementTour

router = APIRouter(prefix="/api/v1/departs/{depart_id}", tags=["suivi"])


class FluxReponse(BaseModel):
    """Une flèche du schéma : d'où viennent des archers, où ils vont, et combien."""

    ordre_source: int
    ordre_cible: int
    nature: str
    effectif: int | None
    rang_debut: int | None
    rang_fin: int | None
    tour: int | None
    issue: str | None

    @staticmethod
    def de_flux(flux: Flux) -> FluxReponse:
        return FluxReponse(
            ordre_source=flux.ordre_source,
            ordre_cible=flux.ordre_cible,
            nature=flux.nature.value,
            effectif=flux.effectif,
            rang_debut=flux.rang_debut,
            rang_fin=flux.rang_fin,
            tour=flux.tour,
            issue=None if flux.issue is None else flux.issue.value,
        )


class TourReponse(BaseModel):
    """Un braquet : le tour, ses duels **attendus**, et les tranches de rangs qu'il départage."""

    tour: int
    duels: int
    plage_gagnants: tuple[int, int]
    plage_perdants: tuple[int, int]

    @staticmethod
    def de_braquet(braquet: TourBraquet) -> TourReponse:
        return TourReponse(
            tour=braquet.tour,
            duels=braquet.duels,
            plage_gagnants=braquet.plage_gagnants,
            plage_perdants=braquet.plage_perdants,
        )


class BlocReponse(BaseModel):
    """Un bloc du schéma — la **projection**, identique à celle de l'atelier."""

    ordre: int
    type: str
    effectif: int | None
    tranche: tuple[int, int] | None
    nb_volees: int | None
    nb_fleches_par_volee: int | None
    tours: list[TourReponse]
    entrees: list[FluxReponse]
    sorties: list[FluxReponse]
    sans_suite: int | None

    @staticmethod
    def de_bloc(bloc: BlocDeroule) -> BlocReponse:
        return BlocReponse(
            ordre=bloc.ordre,
            type=bloc.type.value,
            effectif=bloc.effectif,
            tranche=bloc.tranche,
            nb_volees=bloc.nb_volees,
            nb_fleches_par_volee=bloc.nb_fleches_par_volee,
            tours=[TourReponse.de_braquet(t) for t in bloc.tours],
            entrees=[FluxReponse.de_flux(f) for f in bloc.entrees],
            sorties=[FluxReponse.de_flux(f) for f in bloc.sorties],
            sans_suite=bloc.sans_suite,
        )


class AvancementTourReponse(BaseModel):
    """Le remplissage d'un braquet : duels joués sur duels attendus."""

    tour: int
    duels_attendus: int
    duels_joues: int

    @staticmethod
    def de_tour(tour: AvancementTour) -> AvancementTourReponse:
        return AvancementTourReponse(
            tour=tour.tour,
            duels_attendus=tour.duels_attendus,
            duels_joues=tour.duels_joues,
        )


class AvancementBlocReponse(BaseModel):
    """Le calque de réalité d'un bloc : statut, braquets remplis, tour en cours.

    `statut` ∈ `a_venir` · `en_cours` · `en_pause` · `terminee`. `tour_courant` est `null` quand
    rien ne tourne — phase pas encore démarrée, déjà close, ou tous ses duels tranchés.
    """

    ordre: int
    statut: str
    tour_courant: int | None
    duels_joues: int
    duels_attendus: int
    tours: list[AvancementTourReponse]

    @staticmethod
    def de_bloc(bloc: AvancementBloc) -> AvancementBlocReponse:
        return AvancementBlocReponse(
            ordre=bloc.ordre,
            statut=bloc.statut.value,
            tour_courant=bloc.tour_courant,
            duels_joues=bloc.duels_joues,
            duels_attendus=bloc.duels_attendus,
            tours=[AvancementTourReponse.de_tour(t) for t in bloc.tours],
        )


class SuiviDerouleReponse(BaseModel):
    """Le déroulé d'une édition : le dessin **et** son remplissage, appariés par `ordre`.

    Deux listes plutôt qu'une structure fusionnée : le front dessine avec `blocs` — exactement comme
    à l'atelier — et **superpose** `avancement`. C'est ce qui garantit qu'un seul composant sert les
    trois surfaces sans qu'aucune ne reçoive une forme particulière.
    """

    effectif: int
    ordre_courant: int | None
    blocs: list[BlocReponse]
    avancement: list[AvancementBlocReponse]

    @staticmethod
    def de_suivi(suivi: SuiviDeroule) -> SuiviDerouleReponse:
        return SuiviDerouleReponse(
            effectif=suivi.effectif,
            ordre_courant=suivi.avancement.ordre_courant,
            blocs=[BlocReponse.de_bloc(bloc) for bloc in suivi.projection.blocs],
            avancement=[AvancementBlocReponse.de_bloc(bloc) for bloc in suivi.avancement.blocs],
        )


@router.get("/suivi-deroule", response_model=SuiviDerouleReponse)
async def suivi_deroule(depart_id: int, request: Request) -> SuiviDerouleReponse:
    """Où en est ce créneau : phases, braquets et duels joués (**lecture publique**).

    `404 depart_introuvable` si le créneau n'existe pas. Un créneau sans phase rend des listes
    vides — avant qu'un format soit appliqué, il n'y a rien à suivre, ce n'est pas une erreur.
    Lecture (phases + tableaux reconstruits) : hors file, dans le threadpool.
    """
    service: ServiceSuiviDeroule = request.app.state.service_suivi_deroule
    suivi = await run_in_threadpool(service.pour_depart, depart_id)
    return SuiviDerouleReponse.de_suivi(suivi)
