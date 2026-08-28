"""Endpoints REST du jeu d'essai (`/api/v1`) — peupler & instancier des scénarios (E15US001).

⚠️ C'est de la **donnée réelle persistée** dans le tournoi visé, à ne pas confondre avec la
simulation éphémère d'E15US002.
"""

from __future__ import annotations

import asyncio
import datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.jeu_essai import ResultatJeuEssai, Scenario, ServiceJeuEssai
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["jeu-essai"], dependencies=[Depends(exiger_admin)])

# Défaut de graine exposé au client : un jeu **stable et rejouable** quand l'appelant n'en fournit
# pas (miroir de `application.jeu_essai._GRAINE_DEFAUT`, gardé simple pour ne pas exposer un privé).
_GRAINE_DEFAUT = 0


class ScenarioReponse(BaseModel):
    """Un scénario du catalogue présenté à l'écran (le prédicat interne n'est pas exposé)."""

    id: str
    libelle: str
    description: str
    nombre_archers: int
    nombre_departs: int

    @staticmethod
    def de_scenario(scenario: Scenario) -> ScenarioReponse:
        return ScenarioReponse(
            id=scenario.id,
            libelle=scenario.libelle,
            description=scenario.description,
            nombre_archers=scenario.nombre_archers,
            nombre_departs=scenario.nombre_departs,
        )


class PeuplerRequete(BaseModel):
    """Corps du peuplement : combien d'archers, et la graine (déterminisme, règle 9).

    `nombre` est borné [1, 500] à la frontière (au-delà, 400 avant que le service ne voie la
    requête) — un tournoi de test n'a pas besoin de plus, et ça évite un peuplement massif par
    mégarde.
    `graine` est facultative : absente, une graine stable est utilisée (jeu rejouable)."""

    nombre: int = Field(ge=1, le=500)
    graine: int | None = None


class PeuplerReponse(BaseModel):
    """Bilan d'un peuplement : le tournoi visé et combien d'archers ont été créés."""

    tournoi_id: int
    nombre_archers_crees: int


class InstancierRequete(BaseModel):
    """Corps de l'instanciation d'un scénario : la graine seule (le reste vient du catalogue)."""

    graine: int | None = None


class InstancierReponse(BaseModel):
    """Ce que le scénario a instancié : le tournoi créé et ce qu'il porte."""

    tournoi_id: int
    nom: str
    nombre_archers: int
    nombre_departs: int

    @staticmethod
    def de_resultat(resultat: ResultatJeuEssai) -> InstancierReponse:
        return InstancierReponse(
            tournoi_id=resultat.tournoi_id,
            nom=resultat.nom,
            nombre_archers=resultat.nombre_archers,
            nombre_departs=resultat.nombre_departs,
        )


@router.get("/jeu-essai/scenarios", response_model=list[ScenarioReponse])
async def lister_scenarios(request: Request) -> list[ScenarioReponse]:
    """Le catalogue de scénarios rejouables (lecture ; le prédicat de catégories reste interne)."""
    service: ServiceJeuEssai = request.app.state.service_jeu_essai
    scenarios = await run_in_threadpool(service.scenarios)
    return [ScenarioReponse.de_scenario(scenario) for scenario in scenarios]


@router.post(
    "/tournois/{tournoi_id}/jeu-essai/peupler",
    status_code=201,
    response_model=PeuplerReponse,
)
async def peupler_tournoi(
    tournoi_id: int, requete: PeuplerRequete, request: Request
) -> PeuplerReponse:
    """Peuple un tournoi existant de N archers de test (**action admin**) : écriture via la file.

    Tout le peuplement tient dans **une** commande de file (ADR-0005), comme le pré-chargement FFTA.
    Lève `TournoiIntrouvable` (404) si le tournoi n'existe pas.
    """
    service: ServiceJeuEssai = request.app.state.service_jeu_essai
    write_queue: WriteQueue = request.app.state.write_queue
    graine = _GRAINE_DEFAUT if requete.graine is None else requete.graine
    archers = await asyncio.wrap_future(
        write_queue.submit(lambda: service.peupler(tournoi_id, requete.nombre, graine))
    )
    return PeuplerReponse(tournoi_id=tournoi_id, nombre_archers_crees=len(archers))


@router.post(
    "/jeu-essai/scenarios/{scenario_id}/instancier",
    status_code=201,
    response_model=InstancierReponse,
)
async def instancier_scenario(
    scenario_id: str, requete: InstancierRequete, request: Request
) -> InstancierReponse:
    """Instancie un scénario en un tournoi **complet, prêt à lancer** (**action admin**).

    La date du tournoi de test est celle du jour (lue à la frontière, couche infra) ; le service,
    lui, la reçoit en paramètre pour rester déterministe (règle 9). Lève `ScenarioInconnu` (404) si
    l'identifiant est hors catalogue. Tout tient dans **une** commande de file (ADR-0005).
    """
    service: ServiceJeuEssai = request.app.state.service_jeu_essai
    write_queue: WriteQueue = request.app.state.write_queue
    graine = _GRAINE_DEFAUT if requete.graine is None else requete.graine
    date = datetime.date.today()
    resultat = await asyncio.wrap_future(
        write_queue.submit(lambda: service.instancier(scenario_id, date, graine))
    )
    return InstancierReponse.de_resultat(resultat)
