"""Endpoints REST des départs — créneaux d'un tournoi (`/api/v1/tournois/{tournoi_id}/departs`).

Configurer les départs d'un tournoi (E02US004, ADR-0017) : créer, lister, éditer (tarif/horaire),
supprimer. Les routes sont **imbriquées sous le tournoi** — un départ n'existe pas hors de lui.

Suit le patron de bout en bout (E00US009) : DTO Pydantic distincts des agrégats ; écritures routées
par la **file d'écriture** (writer unique, ADR-0005) et réservées à l'admin (`exiger_admin`) ;
lectures **hors boucle** (threadpool) ; erreurs typées traduites à la frontière (`api/erreurs.py`).
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.departs import ServiceDeparts
from domain.cycle_depart import EtatDepart
from domain.depart import Depart
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1/tournois/{tournoi_id}/departs", tags=["departs"])


class CreerDepartRequete(BaseModel):
    """Corps de création d'un départ : tarif et horaire requis, quota facultatif.

    Le **numéro** n'est pas dans le corps : il est attribué par le serveur (le plus grand + 1).
    L'`horaire` est **obligatoire** (E02US010) : le DTO ne contraint que le **type** (`str`) — un
    horaire **manquant** ou d'un mauvais type est une requête malformée (→ 400) ; le **format**
    `HH:MM` (24 h) est, lui, validé par le domaine (`HoraireDepartInvalide` → 422), comme la valeur
    du tarif ou du quota. Le `quota` reste **facultatif** — absent (`null`) = créneau sans plafond.
    """

    tarif_centimes: int
    horaire: str
    quota: int | None = None


class ModifierDepartRequete(BaseModel):
    """Corps d'édition d'un départ : tarif, horaire (`HH:MM`), quota ; le numéro est fixe.

    **Remplacement complet** : un `quota` absent (`null`) **retire** le plafond ; l'horaire est
    **obligatoire** (E02US010) — le client renvoie l'horaire courant s'il veut le conserver (le
    formulaire est pré-rempli pour ça). Mêmes règles de validation qu'à la création (type → 400,
    format `HH:MM` → 422).
    """

    tarif_centimes: int
    horaire: str
    quota: int | None = None


class DepartReponse(BaseModel):
    """Représentation d'un départ renvoyée au client.

    `tarif_centimes` est en **centimes entiers** (l'unité est dans le nom) : c'est le client qui met
    en forme des euros. `0` = gratuit. `quota` = nombre maximal d'inscrits, ou `null` (illimité).

    `etat` est l'**état de cycle de vie** du créneau (E12US008), une chaîne `ouvert` / `lance` /
    `clos` **dérivée** (jamais stockée) : `ouvert` = aucun score encore consigné (librement
    éditable) ; `lance` = une session de tir est en cours ; `clos` = toutes les séries sont closes.
    Le front en fait un badge et sait qu'éditer/supprimer un créneau non *ouvert* demandera une
    confirmation.
    """

    id: int
    tournoi_id: int
    numero: int
    horaire: str
    tarif_centimes: int
    quota: int | None
    etat: str

    @staticmethod
    def de_agregat(depart: Depart, etat: EtatDepart) -> DepartReponse:
        """Traduit un agrégat de domaine (persisté) et son état de cycle en DTO de réponse."""
        assert depart.id is not None, "Un départ persisté a toujours un identifiant."
        return DepartReponse(
            id=depart.id,
            tournoi_id=depart.tournoi_id,
            numero=depart.numero,
            horaire=depart.horaire,
            tarif_centimes=depart.tarif_centimes,
            quota=depart.quota,
            etat=etat.value,
        )


@router.post(
    "",
    status_code=201,
    response_model=DepartReponse,
    dependencies=[Depends(exiger_admin)],
)
async def creer_depart(
    tournoi_id: int, requete: CreerDepartRequete, request: Request
) -> DepartReponse:
    """Crée un départ dans un tournoi (**action admin**) : écriture via la file (ADR-0005)."""
    service: ServiceDeparts = request.app.state.service_departs
    write_queue: WriteQueue = request.app.state.write_queue
    depart = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.creer(
                tournoi_id, requete.tarif_centimes, requete.horaire, requete.quota
            )
        )
    )
    # Un créneau qui vient de naître n'a ni placement ni score : il est **ouvert** par construction
    # (E12US008). Inutile de relire l'avancement pour l'apprendre.
    return DepartReponse.de_agregat(depart, EtatDepart.OUVERT)


@router.get("", response_model=list[DepartReponse])
async def lister_departs(tournoi_id: int, request: Request) -> list[DepartReponse]:
    """Liste les départs d'un tournoi (triés par numéro), **avec leur état de cycle** (E12US008).

    Lecture directe hors boucle. L'état (ouvert / lancé / clos) est dérivé au vol par le service
    (placements · séries · forfaits) — le front en fait un badge par créneau.
    """
    service: ServiceDeparts = request.app.state.service_departs
    departs = await run_in_threadpool(service.lister_avec_etat, tournoi_id)
    return [DepartReponse.de_agregat(depart, etat) for depart, etat in departs]


@router.put(
    "/{depart_id}",
    response_model=DepartReponse,
    dependencies=[Depends(exiger_admin)],
)
async def modifier_depart(
    tournoi_id: int,
    depart_id: int,
    requete: ModifierDepartRequete,
    request: Request,
    confirme_cycle: bool = False,
) -> DepartReponse:
    """Édite le tarif et l'horaire d'un départ (**action admin**) : écriture via la file.

    Renvoie `409 depart_en_cours_non_confirme` si le créneau est *lancé* ou *clos* (E12US008) : un
    **signalement chiffré** (`details` : état + archers ayant tiré), que le client lève en rejouant
    l'appel avec `confirme_cycle=true`. Le drapeau est en **paramètre de requête** (le corps porte
    déjà les valeurs éditées), comme `autoriser_suppression_inscrits` de la suppression.
    """
    service: ServiceDeparts = request.app.state.service_departs
    write_queue: WriteQueue = request.app.state.write_queue

    def _modifier_et_lire_etat() -> tuple[Depart, EtatDepart]:
        # Édition puis relecture de l'état dans **le même passage du writer** (règle 7) : l'état
        # renvoyé reflète l'écriture qu'on vient d'appliquer, sans course avec une autre tablette.
        depart = service.modifier(
            tournoi_id,
            depart_id,
            requete.tarif_centimes,
            requete.horaire,
            requete.quota,
            confirme_cycle=confirme_cycle,
        )
        assert depart.id is not None
        return depart, service.etat(tournoi_id, depart.id)

    depart, etat = await asyncio.wrap_future(write_queue.submit(_modifier_et_lire_etat))
    return DepartReponse.de_agregat(depart, etat)


@router.delete(
    "/{depart_id}",
    status_code=204,
    dependencies=[Depends(exiger_admin)],
)
async def supprimer_depart(
    tournoi_id: int,
    depart_id: int,
    request: Request,
    autoriser_suppression_inscrits: bool = False,
    confirme_cycle: bool = False,
) -> Response:
    """Supprime un départ d'un tournoi (**action admin**) : écriture via la file, 204 si succès.

    Deux signalements possibles, selon l'**état de cycle** du créneau (E12US008) :

    - `409 depart_en_cours_non_confirme` si le créneau est *lancé* ou *clos* (une session de tir y a
      eu lieu) : `details` chiffre l'état et les archers ayant tiré. Le client lève en rejouant avec
      `confirme_cycle=true` — elle **subsume** le signalement d'inscriptions ci-dessous (pas de
      double dialogue) ;
    - `409 depart_avec_inscriptions` si le créneau est *ouvert* mais porte des inscriptions
      ([ADR-0018](../../../docs/adr/0018-supprimer-un-depart-a-inscriptions-confirmable.md)), levé
      par `autoriser_suppression_inscrits=true` ; efface les inscriptions (payées à rembourser —
      E08US005).

    Les drapeaux sont en **paramètres de requête**, comme `autoriser_suppression_engage` de la
    suppression d'archer : un `DELETE` n'a pas de corps par convention HTTP (même divergence assumée
    qu'en E02US003, sanctionnée par ADR-0016).
    """
    service: ServiceDeparts = request.app.state.service_departs
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.supprimer(
                tournoi_id,
                depart_id,
                autoriser_suppression_inscrits=autoriser_suppression_inscrits,
                confirme_cycle=confirme_cycle,
            )
        )
    )
    return Response(status_code=204)
