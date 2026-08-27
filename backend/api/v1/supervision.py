"""Supervision des postes — état, dernière saisie, avancement, plus révocation et heartbeat.

⚠️ **Le passage HORS LIGNE naît du temps qui passe, pas d'un événement** (ADR-0038 §4) : d'où un
poll court côté front, et non une diffusion. Révocation et heartbeat n'écrivent qu'**en mémoire** —
hors file. L'IP relevée est un indice de diagnostic (`D-06`), jamais une identité.
"""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin, exiger_poste
from application.ecrans import PriseActive
from application.supervision import EtatSupervision, LigneSupervision, ServiceSupervision
from domain.ecran import VueEcran
from domain.poste import Poste

router = APIRouter(prefix="/api/v1/tournois/{tournoi_id}", tags=["supervision"])
heartbeat_router = APIRouter(prefix="/api/v1/postes/session", tags=["supervision"])


class AvancementReponse(BaseModel):
    """Avancement affichable : la volée en cours sur le total attendu (« 8/12 »)."""

    volee_courante: int
    nb_volees: int


class PriseReponse(BaseModel):
    """La prise de contrôle en vigueur sur un écran de salle (E07US004).

    `reste_s` est `None` quand la prise n'a **pas** d'échéance ; `exige_rappel` vaut alors `true`,
    et c'est ce drapeau que la console transforme en rappel très visible — le CA « jamais un état
    forcé qu'on oublie ». Les deux champs disent la même chose sous deux angles : l'un se compte,
    l'autre s'alarme.
    """

    vue_figee: VueEcran | None
    reste_s: float | None
    exige_rappel: bool

    @staticmethod
    def de_prise(prise: PriseActive) -> PriseReponse:
        """Traduit une prise du service en DTO de réponse."""
        return PriseReponse(
            vue_figee=prise.vue_figee,
            reste_s=prise.reste_s,
            exige_rappel=prise.exige_rappel,
        )


class LigneSupervisionReponse(BaseModel):
    """Une ligne de la console : un poste (cible **ou** écran) et son état à cet instant.

    `etat` ∈ `en_ligne` · `hors_ligne` · `non_rattache` (valeur de `EtatPoste`). `derniere_saisie`
    est un horodatage ISO (le front calcule « il y a 14 mn »), `None` si rien n'a été saisi. `ip`
    est un indice de diagnostic, `None` si le poste n'est pas rattaché. Le **code** n'est
    pas exposé (secret de rattachement) : le poste se désigne par sa `cible_index` ou son `libelle`.

    `type` ∈ `cible` · `ecran`. Une **cible** porte `cible_index` et `avancement` ; un **écran**
    porte `libelle` et, s'il est sous contrôle, `prise`. Les deux dans le même tableau, parce que
    c'est précisément là que le CA veut qu'on découvre un écran figé.
    """

    poste_id: int
    type: str
    cible_index: int | None
    libelle: str | None
    etat: str
    derniere_saisie: datetime.datetime | None
    ip: str | None
    avancement: AvancementReponse | None
    prise: PriseReponse | None

    @staticmethod
    def de_ligne(ligne: LigneSupervision) -> LigneSupervisionReponse:
        """Traduit une ligne du service en DTO de réponse."""
        avancement = (
            AvancementReponse(
                volee_courante=ligne.avancement.volee_courante,
                nb_volees=ligne.avancement.nb_volees,
            )
            if ligne.avancement is not None
            else None
        )
        return LigneSupervisionReponse(
            poste_id=ligne.poste_id,
            type=ligne.type.value,
            cible_index=ligne.cible_index,
            libelle=ligne.libelle,
            etat=ligne.etat.value,
            derniere_saisie=ligne.derniere_saisie,
            ip=ligne.ip,
            avancement=avancement,
            prise=None if ligne.prise is None else PriseReponse.de_prise(ligne.prise),
        )


class SupervisionReponse(BaseModel):
    """Instantané complet de la console : les lignes (cibles puis écrans) + les compteurs.

    `nb_en_ligne`/`nb_total` comptent **les cibles seules** — c'est l'indicateur « 28/30 tablettes »
    sur lequel l'organisateur juge s'il peut lancer un tour ; un écran hors ligne n'empêche personne
    de tirer. Les écrans ont `nb_ecrans_en_ligne`/`nb_ecrans`.
    """

    postes: list[LigneSupervisionReponse]
    nb_en_ligne: int
    nb_total: int
    nb_ecrans_en_ligne: int
    nb_ecrans: int

    @staticmethod
    def de_etat(etat: EtatSupervision) -> SupervisionReponse:
        """Traduit l'instantané du service en DTO de réponse."""
        return SupervisionReponse(
            postes=[LigneSupervisionReponse.de_ligne(ligne) for ligne in etat.postes],
            nb_en_ligne=etat.nb_en_ligne,
            nb_total=etat.nb_total,
            nb_ecrans_en_ligne=etat.nb_ecrans_en_ligne,
            nb_ecrans=etat.nb_ecrans,
        )


@router.get(
    "/supervision",
    response_model=SupervisionReponse,
    dependencies=[Depends(exiger_admin)],
)
async def superviser_postes(tournoi_id: int, request: Request) -> SupervisionReponse:
    """Instantané de supervision des postes d'un tournoi (**admin**). `404` si tournoi inexistant.

    Lecture (sessions/présence en mémoire, postes/séries en base) : hors file, dans le threadpool.
    """
    service: ServiceSupervision = request.app.state.service_supervision
    etat = await run_in_threadpool(service.etat, tournoi_id)
    return SupervisionReponse.de_etat(etat)


@router.post(
    "/postes/{poste_id}/revocation",
    status_code=204,
    dependencies=[Depends(exiger_admin)],
)
async def revoquer_poste(tournoi_id: int, poste_id: int, request: Request) -> None:
    """Révoque un poste : ferme ses sessions, oublie sa présence (**admin**, `D-07`).

    `404 poste_introuvable` si le poste n'existe pas ou relève d'un autre tournoi. Idempotent.
    N'écrit qu'en mémoire (sessions) : hors file, mais relit la base (`par_id`) → threadpool.
    """
    service: ServiceSupervision = request.app.state.service_supervision
    await run_in_threadpool(service.revoquer_poste, tournoi_id, poste_id)


@heartbeat_router.post("/heartbeat", status_code=204)
async def heartbeat_poste(request: Request, poste: Annotated[Poste, Depends(exiger_poste)]) -> None:
    """Signe de vie d'un poste (jeton de poste valide requis). `401` si jeton absent/invalide.

    Horodate la dernière vue du poste et mémorise son IP (diagnostic). `exiger_poste` relit la base
    (statut du tournoi) et tourne dans le threadpool ; l'enregistrement lui-même est en mémoire.
    """
    assert poste.id is not None  # un poste résolu par sa session a toujours un id
    service: ServiceSupervision = request.app.state.service_supervision
    ip = request.client.host if request.client is not None else None
    await run_in_threadpool(service.enregistrer_heartbeat, poste.id, ip)
