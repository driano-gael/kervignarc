"""Endpoint **public** du déroulé du tour (E07US009, [ADR-0039]).

Projection publique, en lecture seule et **sans authentification** (E10US001), de la feuille de
marque d'un archer suivi (E07US006) : ses volées du jour et la volée en cours, chacune avec ses
valeurs, son total, un **statut explicite** « en attente de validation » / « validé » (dérivé du
verrou) et le « quand ». C'est le canal de suivi de l'appli publique — **distinct** de la projection
poste/admin (`api/v1/saisie.py`), qui, elle, porte les marqueurs de scoreur.

Frontière de confidentialité (règle 6, ADR-0039) : le DTO **n'expose jamais** l'identité du scoreur
(`saisie_par` / `validee_par`), le code de cible ni l'IP — seul le `statut` filtre vers le public.
Il expose **délibérément** des scores **provisoires** (volées non validées) : transparence assumée
par l'organisateur, le **classement** (validé seul) restant la source de vérité des scores.

Lecture directe hors boucle (`run_in_threadpool`) sur le service de saisie déjà câblé
(`ServiceSaisie.etat_serie`) : aucun nouveau modèle. Le live passe par la diffusion générique
post-commit (`donnees_modifiees`), qui invalide le cache front → refetch (ADR-0039 §5).

[ADR-0039]: ../../../docs/adr/0039-exposition-publique-du-deroule-scores-provisoires.md
"""

from __future__ import annotations

import datetime
from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from application.saisie import EtatSerie, ServiceSaisie
from domain.serie import Volee

router = APIRouter(prefix="/api/v1", tags=["deroule"])

StatutVolee = Literal["en_attente", "valide"]


class VoleeDerouleReponse(BaseModel):
    """Une volée telle que **suivie par le public** : valeurs, total, statut, « quand ».

    Restriction (règle 6, ADR-0039) : ni `saisie_par` ni `validee_par` (identité du scoreur) — seul
    le `statut` dérivé du verrou passe la frontière publique. `valeurs` liste les zones dans l'ordre
    de saisie (« 10 », « 9 », « M »…) ; `points` en est le total (le manqué vaut 0).
    """

    numero: int
    valeurs: list[str]
    points: int
    statut: StatutVolee
    horodatage: datetime.datetime | None

    @staticmethod
    def de_volee(volee: Volee, horodatage: datetime.datetime | None) -> VoleeDerouleReponse:
        return VoleeDerouleReponse(
            numero=volee.numero,
            valeurs=[zone.value for zone in volee.valeurs],
            points=volee.points,
            statut="valide" if volee.verrouillee else "en_attente",
            horodatage=horodatage,
        )


class DerouleReponse(BaseModel):
    """Le déroulé du tour d'un archer suivi : ses volées (statut inclus) et son cumul **validé**.

    `cumul` ne compte que les volées **validées** (invariant de l'agrégat `Serie`) : le total
    provisoire n'est pas présenté comme officiel. Un archer sans rien de saisi rend un déroulé
    **vide** (pas un 404) : « pas encore tiré » se lit comme une liste vide, pas une erreur — et
    l'endpoint ne révèle pas l'existence d'un couple (tournoi, archer).
    """

    tournoi_id: int
    archer_id: int
    cumul: int
    volees: list[VoleeDerouleReponse]

    @staticmethod
    def de_etat(etat: EtatSerie) -> DerouleReponse:
        serie = etat.serie
        return DerouleReponse(
            tournoi_id=serie.tournoi_id,
            archer_id=serie.archer_id,
            cumul=serie.cumul,
            volees=[
                VoleeDerouleReponse.de_volee(volee, etat.horodatages.get(volee.numero))
                for volee in serie.volees
            ],
        )

    @staticmethod
    def vide(tournoi_id: int, archer_id: int) -> DerouleReponse:
        """Déroulé d'un archer qui n'a encore rien fait saisir : vide, pas un 404."""
        return DerouleReponse(tournoi_id=tournoi_id, archer_id=archer_id, cumul=0, volees=[])


@router.get("/tournois/{tournoi_id}/archers/{archer_id}/deroule", response_model=DerouleReponse)
async def consulter_deroule(tournoi_id: int, archer_id: int, request: Request) -> DerouleReponse:
    """Déroulé public du tour d'un archer : volées du jour + volée en cours, statut attente/validé.

    Lecture seule, sans authentification (E10US001) et hors boucle (`run_in_threadpool`). Rien de
    saisi → déroulé **vide** (200), pas un 404 : le suivi affiche « pas encore tiré » sans erreur.
    """
    service: ServiceSaisie = request.app.state.service_saisie
    etat = await run_in_threadpool(service.etat_serie, tournoi_id, archer_id)
    if etat is None:
        return DerouleReponse.vide(tournoi_id, archer_id)
    return DerouleReponse.de_etat(etat)
