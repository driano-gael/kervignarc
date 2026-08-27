"""Barème de qualification — ressource rattachée au tournoi.

Lecture publique, définition réservée à l'admin ; le barème est porté par la phase de qualification,
de façon transparente pour le client.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.bareme_qualification import ServiceBaremeQualification
from domain.bareme import BaremeQualification
from domain.deroule_etape import EtapeDeroule
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["bareme-qualification"])


class DefinirBaremeRequete(BaseModel):
    """Corps de définition du barème : nombre de volées et nombre de flèches par volée."""

    nb_volees: int
    nb_fleches_par_volee: int


class BaremeReponse(BaseModel):
    """Représentation du barème de qualification renvoyée au client (total et max dérivés)."""

    nb_volees: int
    nb_fleches_par_volee: int
    nb_fleches_total: int
    score_max: int

    @staticmethod
    def de_agregat(bareme: BaremeQualification) -> BaremeReponse:
        """Traduit le value object de domaine en DTO de réponse."""
        return BaremeReponse(
            nb_volees=bareme.nb_volees,
            nb_fleches_par_volee=bareme.nb_fleches_par_volee,
            nb_fleches_total=bareme.nb_fleches_total,
            score_max=bareme.score_max,
        )


@router.get(
    "/tournois/{tournoi_id}/bareme-qualification",
    response_model=BaremeReponse | None,
)
async def bareme_du_tournoi(tournoi_id: int, request: Request) -> BaremeReponse | None:
    """Renvoie le barème de qualification du tournoi, ou `null` s'il n'est pas encore défini.

    Lève `TournoiIntrouvable` (404) si le tournoi n'existe pas.
    """
    service: ServiceBaremeQualification = request.app.state.service_bareme_qualification
    bareme = await run_in_threadpool(service.bareme_du_tournoi, tournoi_id)
    return None if bareme is None else BaremeReponse.de_agregat(bareme)


@router.put(
    "/tournois/{tournoi_id}/bareme-qualification",
    response_model=BaremeReponse,
    dependencies=[Depends(exiger_admin)],
)
async def definir_bareme(
    tournoi_id: int, requete: DefinirBaremeRequete, request: Request
) -> BaremeReponse:
    """Définit le barème de qualification (**action admin**) : écriture via la file (ADR-0005).

    Upsert : crée le barème s'il n'existe pas, sinon met à jour ses valeurs. Le preset FFTA 18 m
    (20 volées de 3) est fourni par le client, qui reste libre de saisir d'autres valeurs.
    """
    service: ServiceBaremeQualification = request.app.state.service_bareme_qualification
    write_queue: WriteQueue = request.app.state.write_queue
    bareme = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.definir(tournoi_id, requete.nb_volees, requete.nb_fleches_par_volee)
        )
    )
    return BaremeReponse.de_agregat(bareme)


class QualificationReponse(BaseModel):
    """Une qualification du déroulé, avec ses réglages (E05US025, ADR-0082).

    Ce que l'écran « Barème & validation » liste depuis qu'un déroulé peut en porter plusieurs.
    `libelle` est dérivé de l'ordre **côté serveur** — le front n'a pas à réinventer une
    numérotation. ⚠️ `bareme` et `grain` sont **facultatifs par prudence, pas par usage** : aucun
    chemin de composition ne laisse aujourd'hui une qualification sans réglage ; l'optionalité vaut
    pour une base reprise d'une version antérieure, pas pour le geste d'aujourd'hui.
    """

    etape_id: int
    ordre: int
    libelle: str
    bareme: BaremeReponse | None = None
    grain: str | None = None
    grain_n_volees: int | None = None

    @staticmethod
    def de_agregat(etape: EtapeDeroule, rang: int) -> QualificationReponse:
        """Traduit une étape de déroulé en DTO.

        `rang` est la position **parmi les qualifications** (1, 2, 3…), pas l'ordre dans la
        séquence : sur le déroulé de référence la *basse* est l'étape d'ordre 3 mais la 3ᵉ
        qualification, et l'écran parle de qualifications, pas d'étapes.
        """
        assert etape.id is not None, "Une étape relue du dépôt porte toujours son identifiant."
        return QualificationReponse(
            etape_id=etape.id,
            ordre=etape.ordre,
            libelle=f"Qualification {rang}",
            bareme=None if etape.bareme is None else BaremeReponse.de_agregat(etape.bareme),
            grain=None if etape.validation is None else etape.validation.type.value,
            grain_n_volees=None if etape.validation is None else etape.validation.n_volees,
        )


@router.get(
    "/tournois/{tournoi_id}/qualifications",
    response_model=list[QualificationReponse],
)
async def lister_qualifications(tournoi_id: int, request: Request) -> list[QualificationReponse]:
    """Les qualifications du déroulé et leurs réglages (E05US025).

    Remplace, pour l'écran, la lecture `GET .../bareme-qualification` qui ne pouvait en rendre
    qu'une. Celle-ci reste en place — elle sert les clients qui n'ont pas besoin de choisir.

    Lève `TournoiIntrouvable` (404) si le tournoi n'existe pas ; liste vide si le déroulé n'a
    aucune qualification.
    """
    service: ServiceBaremeQualification = request.app.state.service_bareme_qualification
    etapes = await run_in_threadpool(service.qualifications, tournoi_id)
    return [QualificationReponse.de_agregat(etape, rang) for rang, etape in enumerate(etapes, 1)]


@router.put(
    "/tournois/{tournoi_id}/qualifications/{etape_id}/bareme",
    response_model=BaremeReponse,
    dependencies=[Depends(exiger_admin)],
)
async def definir_bareme_d_etape(
    tournoi_id: int, etape_id: int, requete: DefinirBaremeRequete, request: Request
) -> BaremeReponse:
    """Règle le barème d'une qualification **désignée** (**action admin**, E05US025).

    Ne crée rien : l'étape est composée à l'atelier. `PhaseIntrouvable` (404) si elle n'appartient
    pas à ce tournoi, `PhasePasUneQualification` (409) si elle n'en est pas une, et
    `CadenceValidationSuperieureAuBareme` (409) si le barème passe sous la cadence du grain.
    """
    service: ServiceBaremeQualification = request.app.state.service_bareme_qualification
    write_queue: WriteQueue = request.app.state.write_queue
    bareme = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.definir_pour_etape(
                tournoi_id, etape_id, requete.nb_volees, requete.nb_fleches_par_volee
            )
        )
    )
    return BaremeReponse.de_agregat(bareme)
