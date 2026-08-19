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
from domain.phase import TypePhase
from domain.plage import Plage
from domain.suivi_deroule import AvancementBloc, AvancementTour
from domain.tour_de_phase import libelle_de_tour, unite_de_tour_effective

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
    rien ne tourne — phase pas encore démarrée, déjà close, ou tout son contenu tranché.

    ⚠️ **`tour_courant` n'est plus un numéro de braquet** (E05US032, [ADR-0090]) : c'est le numéro du
    tour de la phase, dans l'unité de son format — un tour d'arbre, un tour de poule, une **ronde**
    de système suisse, une **manche** de Big Shoot Off. `libelle_tour_courant` porte le mot que la
    salle emploie, **servi ici** et jamais redérivé côté client (`DETTE-020` compte déjà deux
    domiciles pour cette règle).

    ⚠️ **`nb_tours` n'est pas `len(tours)`** : `tours` porte les **braquets** — les tranches de rangs
    qu'un tableau attribue au fil de l'eau —, et une phase qui ne classe qu'à la fin en a zéro tout
    en comptant plusieurs tours. Il ne descend jamais sous 1.

    [ADR-0090]: ../../docs/adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md
    """

    ordre: int
    statut: str
    tour_courant: int | None
    nb_tours: int
    libelle_tour_courant: str | None
    duels_joues: int
    duels_attendus: int
    tours: list[AvancementTourReponse]

    @staticmethod
    def de_bloc(
        bloc: AvancementBloc, type_phase: TypePhase, tranche: tuple[int, int] | None
    ) -> AvancementBlocReponse:
        """⚠️ **Le libellé est servi, jamais recalculé à l'écran** (E05US032, [ADR-0090] §4).

        Le front pourrait dériver « Demi-finale » de `tour_courant` et `nb_tours` — c'est ce que
        `saisie-duels/duel.ts` fait déjà, et c'est précisément `DETTE-020` : deux domiciles pour une
        règle de vocabulaire. E07US005 a refermé la même tentation en servant le libellé du domaine
        au DTO ; on fait pareil, sinon l'US **aggrave** une dette qu'elle est censée contenir.

        `place_en_jeu` reste à `None` : on nomme ici le tour **de la phase**, pas un match — la
        petite finale se nomme au match, là où le routage et la vue publique la rendent déjà.

        ⚠️ **`plage`, en revanche, est indispensable** (correctif de revue, axe adversarial). Sans
        elle, `libelle_tour` nomme **par la distance au titre** un tour dont la tranche ne part pas
        du rang 1 : une phase de `placement` alimentée par les perdants du tour 1 s'annonçait
        « **Finale** » pour le match des places 7-8, et un tableau secondaire prélevant « les rangs
        33 et suivants » faisait de même. C'est nommément le défaut que `libelle_tour` porte dans
        ses propres encarts (« trois "Finale" simultanées sur le panneau de routage »), et l'écran
        disait « tour 2 » — neutre et **vrai** — avant cette US : une régression de véracité sur la
        surface même que l'US livre. Une plage qui commence au rang 1 est celle du titre et ne
        discrimine rien : on ne la passe pas, pour laisser jouer la branche « distance au titre ».

        [ADR-0090]: ../../docs/adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md
        """
        return AvancementBlocReponse(
            ordre=bloc.ordre,
            statut=bloc.statut.value,
            tour_courant=bloc.tour_courant,
            nb_tours=bloc.nb_tours,
            libelle_tour_courant=(
                libelle_de_tour(
                    unite_de_tour_effective(type_phase, bloc.nb_tours),
                    bloc.tour_courant,
                    bloc.nb_tours,
                    plage=Plage(*tranche) if tranche is not None and tranche[0] > 1 else None,
                )
                if bloc.tour_courant is not None
                else None
            ),
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
        # Le type de phase et la tranche d'entrée viennent de la **projection**, appariée à
        # l'avancement par `ordre` — le même appariement que le front fait pour superposer les deux
        # listes. Les porter dans `AvancementBloc` les aurait dupliqués dans les deux moitiés de la
        # réponse. L'appariement est sûr par construction (`pour_depart` itère sur
        # `projection.blocs`) ; `tranches.get(...)` tolère malgré tout l'absence, une tranche nulle
        # étant un cas **normal** (phase à plusieurs sources).
        types = {bloc.ordre: bloc.type for bloc in suivi.projection.blocs}
        tranches = {bloc.ordre: bloc.tranche for bloc in suivi.projection.blocs}
        return SuiviDerouleReponse(
            effectif=suivi.effectif,
            ordre_courant=suivi.avancement.ordre_courant,
            blocs=[BlocReponse.de_bloc(bloc) for bloc in suivi.projection.blocs],
            avancement=[
                AvancementBlocReponse.de_bloc(bloc, types[bloc.ordre], tranches.get(bloc.ordre))
                for bloc in suivi.avancement.blocs
            ],
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
