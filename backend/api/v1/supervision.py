"""Endpoints REST de la **supervision des postes** (E12US001, ADR-0038).

Trois routes, deux portées :

- **Console** (`GET /api/v1/tournois/{tournoi_id}/supervision`, admin) : l'instantané de tous les
  postes de cible — état, dernière saisie, avancement — et le compteur global. Lecture ; le front la
  rafraîchit par un poll court (le passage *hors ligne* naît du **temps qui passe**, pas d'un
  événement — ADR-0038 §4).
- **Révocation** (`POST /api/v1/tournois/{tournoi_id}/postes/{poste_id}/revocation`, admin) : ferme
  les sessions d'un poste et oublie sa présence (`D-07`). N'écrit qu'en mémoire (sessions), pas en
  base : hors file.
- **Heartbeat** (`POST /api/v1/postes/session/heartbeat`, poste) : le signe de vie périodique. Le
  poste s'authentifie par son jeton (`exiger_poste`) ; on horodate sa dernière vue et son IP (indice
  de diagnostic, `D-06`, jamais une identité). Écrit en mémoire, sans transaction ni diffusion.

DTO Pydantic distincts des agrégats (règle 6). Erreurs typées traduites à la frontière
(`api/erreurs.py`) : tournoi/poste introuvable → 404, jeton de poste absent/invalide → 401.
"""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin, exiger_poste
from application.supervision import EtatSupervision, LigneSupervision, ServiceSupervision
from domain.poste import Poste

router = APIRouter(prefix="/api/v1/tournois/{tournoi_id}", tags=["supervision"])
heartbeat_router = APIRouter(prefix="/api/v1/postes/session", tags=["supervision"])


class AvancementReponse(BaseModel):
    """Avancement affichable : la volée en cours sur le total attendu (« 8/12 »)."""

    volee_courante: int
    nb_volees: int


class LigneSupervisionReponse(BaseModel):
    """Une ligne de la console : un poste de cible et son état à cet instant.

    `etat` ∈ `en_ligne` · `hors_ligne` · `non_rattache` (valeur de `EtatPoste`). `derniere_saisie`
    est un horodatage ISO (le front calcule « il y a 14 mn »), `None` si rien n'a été saisi. `ip`
    est un indice de diagnostic, `None` si le poste n'est pas rattaché. Le **code** de cible n'est
    pas exposé (secret de rattachement) : le poste se désigne par sa `cible_index`.
    """

    poste_id: int
    cible_index: int
    etat: str
    derniere_saisie: datetime.datetime | None
    ip: str | None
    avancement: AvancementReponse | None

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
            cible_index=ligne.cible_index,
            etat=ligne.etat.value,
            derniere_saisie=ligne.derniere_saisie,
            ip=ligne.ip,
            avancement=avancement,
        )


class SupervisionReponse(BaseModel):
    """Instantané complet de la console : les lignes triées par cible + le compteur global."""

    postes: list[LigneSupervisionReponse]
    nb_en_ligne: int
    nb_total: int

    @staticmethod
    def de_etat(etat: EtatSupervision) -> SupervisionReponse:
        """Traduit l'instantané du service en DTO de réponse."""
        return SupervisionReponse(
            postes=[LigneSupervisionReponse.de_ligne(ligne) for ligne in etat.postes],
            nb_en_ligne=etat.nb_en_ligne,
            nb_total=etat.nb_total,
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
