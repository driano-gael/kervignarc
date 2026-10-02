"""Équipes d'un tournoi — CRUD admin et composition membre par membre (E13US002)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.equipes import EquipeVue, ServiceEquipes
from domain.equipe import TypeEquipe
from infrastructure.db import WriteQueue

router = APIRouter(
    prefix="/api/v1/tournois/{tournoi_id}/equipes",
    tags=["equipes"],
    dependencies=[Depends(exiger_admin)],
)


class EquipeRequete(BaseModel):
    """`effectif_attendu` absent ou `null` : le défaut FFTA du type (CA 1) ; 0 est refusé."""

    nom: str
    type: TypeEquipe
    effectif_attendu: int | None = None


class AjouterMembreRequete(BaseModel):
    archer_id: int


class MembreReponse(BaseModel):
    archer_id: int
    nom: str
    prenom: str
    categorie: str


class EquipeReponse(BaseModel):
    """`ecarts` : les valeurs d'`EcartComposition`, dans l'ordre du domaine."""

    id: int
    tournoi_id: int
    nom: str
    type: TypeEquipe
    effectif_attendu: int
    membres: list[MembreReponse]
    conforme: bool
    ecarts: list[str]

    @staticmethod
    def de_vue(vue: EquipeVue) -> EquipeReponse:
        equipe = vue.equipe
        assert equipe.id is not None, "Une équipe persistée a toujours un identifiant."
        return EquipeReponse(
            id=equipe.id,
            tournoi_id=equipe.tournoi_id,
            nom=equipe.nom,
            type=equipe.type,
            effectif_attendu=equipe.effectif_attendu,
            membres=[
                MembreReponse(
                    archer_id=m.archer_id, nom=m.nom, prenom=m.prenom, categorie=m.categorie
                )
                for m in vue.membres
            ],
            conforme=vue.conforme,
            ecarts=[ecart.value for ecart in vue.ecarts],
        )


def _service(request: Request) -> ServiceEquipes:
    service: ServiceEquipes = request.app.state.service_equipes
    return service


def _file(request: Request) -> WriteQueue:
    write_queue: WriteQueue = request.app.state.write_queue
    return write_queue


@router.get("", response_model=list[EquipeReponse])
async def lister_equipes(tournoi_id: int, request: Request) -> list[EquipeReponse]:
    vues = await run_in_threadpool(_service(request).lister, tournoi_id)
    return [EquipeReponse.de_vue(vue) for vue in vues]


@router.post("", status_code=201, response_model=EquipeReponse)
async def creer_equipe(tournoi_id: int, requete: EquipeRequete, request: Request) -> EquipeReponse:
    service = _service(request)
    vue = await asyncio.wrap_future(
        _file(request).submit(
            lambda: service.creer(tournoi_id, requete.nom, requete.type, requete.effectif_attendu)
        )
    )
    return EquipeReponse.de_vue(vue)


@router.put("/{equipe_id}", response_model=EquipeReponse)
async def modifier_equipe(
    tournoi_id: int, equipe_id: int, requete: EquipeRequete, request: Request
) -> EquipeReponse:
    service = _service(request)
    vue = await asyncio.wrap_future(
        _file(request).submit(
            lambda: service.modifier(
                tournoi_id, equipe_id, requete.nom, requete.type, requete.effectif_attendu
            )
        )
    )
    return EquipeReponse.de_vue(vue)


@router.delete("/{equipe_id}", status_code=204)
async def supprimer_equipe(tournoi_id: int, equipe_id: int, request: Request) -> Response:
    service = _service(request)
    await asyncio.wrap_future(
        _file(request).submit(lambda: service.supprimer(tournoi_id, equipe_id))
    )
    return Response(status_code=204)


@router.post("/{equipe_id}/membres", response_model=EquipeReponse)
async def ajouter_membre(
    tournoi_id: int, equipe_id: int, requete: AjouterMembreRequete, request: Request
) -> EquipeReponse:
    service = _service(request)
    vue = await asyncio.wrap_future(
        _file(request).submit(
            lambda: service.ajouter_membre(tournoi_id, equipe_id, requete.archer_id)
        )
    )
    return EquipeReponse.de_vue(vue)


@router.delete("/{equipe_id}/membres/{archer_id}", response_model=EquipeReponse)
async def retirer_membre(
    tournoi_id: int, equipe_id: int, archer_id: int, request: Request
) -> EquipeReponse:
    service = _service(request)
    vue = await asyncio.wrap_future(
        _file(request).submit(lambda: service.retirer_membre(tournoi_id, equipe_id, archer_id))
    )
    return EquipeReponse.de_vue(vue)
