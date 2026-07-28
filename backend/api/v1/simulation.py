"""Endpoints REST du pilotage de simulation (`/api/v1`) — bot + cockpit (E15US003, ADR-0055).

Outil **admin** de démo/QA : piloter une **session vivante** de simulation (ADR-0055). Toutes les
routes sont **lecture pure côté vraie base** — elles ne mutent qu'un état **en mémoire** (le harnais
in-memory de la session), jamais SQLite : elles n'empruntent donc **pas** la file d'écriture (règle
7) et s'exécutent via `run_in_threadpool`, contrairement aux écritures réelles du jeu d'essai
(E15US001).

Le cockpit pilote la session par ces routes : démarrer, avancer (le ticker du pilote automatique),
pause / reprendre, saisir une volée ou désigner un vainqueur (reprise en main), lire l'état (les
vues cible/archer/scoreur/public en dérivent), arrêter. La diffusion isolée (`/ws/simulation`)
signale les changements ; le front recharge l'état par `GET`.

DTO Pydantic distincts des agrégats (règle 6). On **réutilise** les DTO de lecture du classement
(`ClassementReponse`) et des tableaux (`TableauReponse`) : un même objet se rend partout pareil,
sans mapping dupliqué. Erreurs typées traduites à la frontière (`SessionSimulationIntrouvable` →
404, `PilotageSimulationInvalide` / `UniteSimulationInvalide` → 409).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from api.v1.competition import ClassementReponse
from api.v1.saisie_duels import DuellisteReponse, TableauReponse
from application.pilotage_simulation import (
    DetailArcher,
    EtatSession,
    ProchaineDuel,
    ProchaineVolee,
    ServicePilotageSimulation,
)
from domain.blason import ZoneScore
from domain.duel import Cote

router = APIRouter(prefix="/api/v1", tags=["simulation"], dependencies=[Depends(exiger_admin)])

_GRAINE_DEFAUT = 0
"""Graine par défaut si l'appelant n'en fournit pas : un déroulé **stable et rejouable** (règle
9)."""


# --- DTO de sortie ------------------------------------------------------------------------------


class ProgressionReponse(BaseModel):
    """Compteurs d'avancement (approximatifs en qualif : les tours de duels se révèlent au fil)."""

    volees_faites: int
    volees_total: int
    duels_faits: int
    duels_total: int


class ProchaineVoleeReponse(BaseModel):
    """L'unité de qualif à jouer (peuple le formulaire de reprise en main « cible »)."""

    archer_id: int
    archer_nom: str
    archer_prenom: str
    numero_volee: int
    nb_fleches: int
    zones: list[ZoneScore]


class ProchaineDuelReponse(BaseModel):
    """L'unité de duels à jouer (peuple le formulaire de reprise en main « scoreur »)."""

    phase_id: int
    match_numero: int
    tour: int
    haut: DuellisteReponse | None
    bas: DuellisteReponse | None
    mode: str


class ProchaineUniteReponse(BaseModel):
    """La prochaine unité (union étiquetée par `genre` : `volee` ou `duel`)."""

    genre: str
    volee: ProchaineVoleeReponse | None = None
    duel: ProchaineDuelReponse | None = None

    @staticmethod
    def de_unite(unite: ProchaineVolee | ProchaineDuel | None) -> ProchaineUniteReponse | None:
        if isinstance(unite, ProchaineVolee):
            return ProchaineUniteReponse(
                genre="volee",
                volee=ProchaineVoleeReponse(
                    archer_id=unite.archer_id,
                    archer_nom=unite.archer_nom,
                    archer_prenom=unite.archer_prenom,
                    numero_volee=unite.numero_volee,
                    nb_fleches=unite.nb_fleches,
                    zones=list(unite.zones),
                ),
            )
        if isinstance(unite, ProchaineDuel):
            return ProchaineUniteReponse(
                genre="duel",
                duel=ProchaineDuelReponse(
                    phase_id=unite.phase_id,
                    match_numero=unite.match_numero,
                    tour=unite.tour,
                    haut=DuellisteReponse.de_duelliste(unite.haut),
                    bas=DuellisteReponse.de_duelliste(unite.bas),
                    mode=unite.mode,
                ),
            )
        return None


class EtatSessionReponse(BaseModel):
    """Instantané complet d'une session, servi au cockpit (les quatre vues en dérivent)."""

    session_id: int
    tournoi_id: int
    tournoi_nom: str
    graine: int
    etat_pilote: str
    etape: str
    progression: ProgressionReponse
    classement: ClassementReponse
    tableaux: list[TableauReponse]
    prochaine_unite: ProchaineUniteReponse | None

    @staticmethod
    def de_etat(etat: EtatSession) -> EtatSessionReponse:
        return EtatSessionReponse(
            session_id=etat.session_id,
            tournoi_id=etat.tournoi_id,
            tournoi_nom=etat.tournoi_nom,
            graine=etat.graine,
            etat_pilote=etat.etat_pilote.value,
            etape=etat.etape.value,
            progression=ProgressionReponse(
                volees_faites=etat.progression.volees_faites,
                volees_total=etat.progression.volees_total,
                duels_faits=etat.progression.duels_faits,
                duels_total=etat.progression.duels_total,
            ),
            classement=ClassementReponse.de_agregat(etat.tournoi_id, etat.classement),
            tableaux=[TableauReponse.de_etat(t) for t in etat.tableaux],
            prochaine_unite=ProchaineUniteReponse.de_unite(etat.prochaine_unite),
        )


class VoleeReponse(BaseModel):
    """Une volée d'un archer simulé (vue archer)."""

    numero: int
    valeurs: list[ZoneScore]
    saisie_par: str | None
    validee_par: str | None
    points: int


class DetailArcherReponse(BaseModel):
    """La « journée » d'un archer simulé (vue archer) : ses volées et son cumul courant."""

    archer_id: int
    nom: str
    prenom: str
    cumul: int
    volees: list[VoleeReponse]

    @staticmethod
    def de_detail(detail: DetailArcher) -> DetailArcherReponse:
        return DetailArcherReponse(
            archer_id=detail.archer_id,
            nom=detail.nom,
            prenom=detail.prenom,
            cumul=detail.cumul,
            volees=[
                VoleeReponse(
                    numero=v.numero,
                    valeurs=list(v.valeurs),
                    saisie_par=v.saisie_par,
                    validee_par=v.validee_par,
                    points=v.points,
                )
                for v in detail.volees
            ],
        )


# --- DTO d'entrée -------------------------------------------------------------------------------


class DemarrerRequete(BaseModel):
    """Corps du démarrage : le tournoi à simuler et la graine (déterminisme, règle 9)."""

    tournoi_id: int
    graine: int | None = None


class AvancerRequete(BaseModel):
    """Corps d'un pas de bot : combien d'unités avancer (le ticker envoie 1 ; le QA plus)."""

    nb_pas: int = Field(default=1, ge=1, le=5000)


class SaisirVoleeRequete(BaseModel):
    """Corps d'une saisie manuelle de volée (reprise en main « cible »).

    `valeurs` sont des `ZoneScore` : Pydantic valide l'appartenance à l'énuméré (422 sur code
    inconnu), comme la saisie de qualification (E04US002) — cohérence de la frontière API.
    """

    archer_id: int
    numero_volee: int
    valeurs: list[ZoneScore]


class DesignerVainqueurRequete(BaseModel):
    """Corps d'une désignation de vainqueur (reprise en main « scoreur »)."""

    phase_id: int
    match_numero: int
    cote: Cote


# --- Routes -------------------------------------------------------------------------------------


def _service(request: Request) -> ServicePilotageSimulation:
    service: ServicePilotageSimulation = request.app.state.service_pilotage_simulation
    return service


@router.post("/simulations", status_code=201, response_model=EtatSessionReponse)
async def demarrer(requete: DemarrerRequete, request: Request) -> EtatSessionReponse:
    """Ouvre une session de simulation sur un tournoi **avant démarrage** (bot prêt à avancer).

    404 si le tournoi (ou sa phase de qualification) est absent ; 409 s'il est déjà démarré/figé.
    """
    service = _service(request)
    graine = _GRAINE_DEFAUT if requete.graine is None else requete.graine
    etat = await run_in_threadpool(service.demarrer, requete.tournoi_id, graine)
    return EtatSessionReponse.de_etat(etat)


@router.get("/simulations/{session_id}", response_model=EtatSessionReponse)
async def etat(session_id: int, request: Request) -> EtatSessionReponse:
    """L'état courant de la session (le front recharge après un signal `/ws/simulation`)."""
    etat = await run_in_threadpool(_service(request).etat, session_id)
    return EtatSessionReponse.de_etat(etat)


@router.post("/simulations/{session_id}/avancer", response_model=EtatSessionReponse)
async def avancer(session_id: int, requete: AvancerRequete, request: Request) -> EtatSessionReponse:
    """Le pilote automatique : fait avancer le bot de `nb_pas` unités. 409 si la session n'est pas
    en cours (en pause/terminée)."""
    etat = await run_in_threadpool(_service(request).avancer, session_id, requete.nb_pas)
    return EtatSessionReponse.de_etat(etat)


@router.post("/simulations/{session_id}/terminer", response_model=EtatSessionReponse)
async def terminer(session_id: int, request: Request) -> EtatSessionReponse:
    """Déroule tout ce qui reste d'un coup (QA : « va jusqu'au classement »)."""
    etat = await run_in_threadpool(_service(request).terminer, session_id)
    return EtatSessionReponse.de_etat(etat)


@router.post("/simulations/{session_id}/pause", response_model=EtatSessionReponse)
async def pause(session_id: int, request: Request) -> EtatSessionReponse:
    """Suspend le bot (ouvre la reprise en main). 409 si la session n'est pas en cours."""
    etat = await run_in_threadpool(_service(request).pause, session_id)
    return EtatSessionReponse.de_etat(etat)


@router.post("/simulations/{session_id}/reprendre", response_model=EtatSessionReponse)
async def reprendre(session_id: int, request: Request) -> EtatSessionReponse:
    """Rend la main au bot. 409 si la session n'est pas en pause."""
    etat = await run_in_threadpool(_service(request).reprendre, session_id)
    return EtatSessionReponse.de_etat(etat)


@router.post("/simulations/{session_id}/saisir-volee", response_model=EtatSessionReponse)
async def saisir_volee(
    session_id: int, requete: SaisirVoleeRequete, request: Request
) -> EtatSessionReponse:
    """Reprise en main « cible » : saisir une volée à la place du bot (en pause seulement)."""
    etat = await run_in_threadpool(
        _service(request).saisir_volee,
        session_id,
        requete.archer_id,
        requete.numero_volee,
        tuple(requete.valeurs),
    )
    return EtatSessionReponse.de_etat(etat)


@router.post("/simulations/{session_id}/designer-vainqueur", response_model=EtatSessionReponse)
async def designer_vainqueur(
    session_id: int, requete: DesignerVainqueurRequete, request: Request
) -> EtatSessionReponse:
    """Reprise en main « scoreur » : désigner le vainqueur d'un duel (en pause seulement)."""
    etat = await run_in_threadpool(
        _service(request).designer_vainqueur,
        session_id,
        requete.phase_id,
        requete.match_numero,
        requete.cote,
    )
    return EtatSessionReponse.de_etat(etat)


@router.get("/simulations/{session_id}/archers/{archer_id}", response_model=DetailArcherReponse)
async def detail_archer(session_id: int, archer_id: int, request: Request) -> DetailArcherReponse:
    """La « journée » d'un archer simulé (vue archer). 404 si l'archer n'est pas dans la session."""
    detail = await run_in_threadpool(_service(request).detail_archer, session_id, archer_id)
    return DetailArcherReponse.de_detail(detail)


@router.delete("/simulations/{session_id}", status_code=204)
async def arreter(session_id: int, request: Request) -> Response:
    """Arrête la session (le harnais est libéré). Idempotent : 204 même si déjà partie."""
    await run_in_threadpool(_service(request).arreter, session_id)
    return Response(status_code=204)
