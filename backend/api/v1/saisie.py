"""Endpoints REST de la saisie de qualification (E04US002) — le **poste marqueur** en action.

Expose le moteur `Serie`/`Volee` (persisté en PR2a, gardé en PR2b) au poste de cible :

- **fixer le départ courant** (« mode départ X », ADR-0034) — préalable à toute saisie : sans lui,
  le poste connaît son lieu mais pas *qui* afficher ;
- **lister ses archers** (la grille) — reconstitués des affectations `(cible, départ)`, ADR-0033 ;
- **saisir une volée** — écriture routée par la **file** (writer unique, ADR-0005) et
  **dédoublonnée** par identifiant de saisie (idempotence, ADR-0036) ; la garde « SA cible / SON
  départ » vit **au service** (ADR-0033 §3), pas ici ;
- **relire l'état d'une série** — volées, marqueurs, verrou, cumul, et le « quand » de chaque volée
  (`created_at`, ex-017).

Rôles (E10US007) : la saisie est ouverte à l'**admin** *ou* au **poste** (`autoriser_saisie`) ;
départ courant et grille sont **propres au poste** (`exiger_poste`). La **validation** (scoreur) et
la **correction** (rôle habilité) ont leurs propres endpoints, ailleurs. DTO Pydantic distincts des
agrégats ; erreurs typées traduites à la frontière (`api/erreurs.py`).
"""

from __future__ import annotations

import asyncio
import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from api.dependances import autoriser_saisie, exiger_poste, extraire_jeton_poste
from application.erreurs import DepartCourantNonDefini, SaisieHorsCible
from application.postes import ServicePostes
from application.saisie import ArcherPositionne, ContexteSaisie, EtatSerie, ServiceSaisie
from domain.blason import ZoneScore
from domain.depart import Depart
from domain.poste import Poste
from infrastructure.db import WriteQueue
from infrastructure.idempotence import RegistreIdempotence

router = APIRouter(prefix="/api/v1/saisie", tags=["saisie"])


# --- DTO ---


class DepartCourantRequete(BaseModel):
    """Corps de « mettre le poste en mode départ X » : l'identifiant du départ à servir."""

    depart_id: int


class DepartCourantReponse(BaseModel):
    """Le départ courant fixé : de quoi confirmer **quel** créneau le poste sert désormais."""

    depart_id: int
    numero: int

    @staticmethod
    def de_agregat(depart: Depart) -> DepartCourantReponse:
        assert depart.id is not None, "Un départ persisté a toujours un identifiant."
        return DepartCourantReponse(depart_id=depart.id, numero=depart.numero)


class ArcherGrilleReponse(BaseModel):
    """Une ligne de la grille : la position A..D et l'archer qui l'occupe (pour la saisie)."""

    position: str
    archer_id: int
    nom: str
    prenom: str

    @staticmethod
    def de_ligne(ligne: ArcherPositionne) -> ArcherGrilleReponse:
        assert ligne.archer.id is not None, "Un archer placé est persisté."
        return ArcherGrilleReponse(
            position=ligne.position,
            archer_id=ligne.archer.id,
            nom=ligne.archer.nom,
            prenom=ligne.archer.prenom,
        )


class SaisirVoleeRequete(BaseModel):
    """Corps de saisie d'une volée. `valeurs` est validé contre `ZoneScore` (une valeur hors énum
    → 400) ; le **barème** (nombre de flèches) et le **blason** (zones admises) restent jugés par le
    domaine (422). `identifiant_saisie` (facultatif) rend l'écriture **idempotente** : un rejeu
    réseau portant le même identifiant ne saisit pas deux fois (ADR-0036)."""

    tournoi_id: int
    archer_id: int
    numero: int = Field(ge=1)
    valeurs: list[ZoneScore] = Field(min_length=1)
    saisie_par: str | None = None
    identifiant_saisie: str | None = None


class VoleeReponse(BaseModel):
    """Une volée telle que relue : valeurs, marqueurs déclaratifs, verrou, et son « quand »."""

    numero: int
    valeurs: list[str]
    saisie_par: str | None
    validee_par: str | None
    verrouillee: bool
    saisie_le: datetime.datetime | None


class SerieReponse(BaseModel):
    """L'état d'une série : ses volées (avec le « quand » de chacune) et le cumul courant."""

    tournoi_id: int
    archer_id: int
    cumul: int
    volees: list[VoleeReponse]

    @staticmethod
    def de_etat(etat: EtatSerie) -> SerieReponse:
        return SerieReponse(
            tournoi_id=etat.serie.tournoi_id,
            archer_id=etat.serie.archer_id,
            cumul=etat.serie.cumul,
            volees=[
                VoleeReponse(
                    numero=volee.numero,
                    valeurs=[zone.value for zone in volee.valeurs],
                    saisie_par=volee.saisie_par,
                    validee_par=volee.validee_par,
                    verrouillee=volee.verrouillee,
                    saisie_le=etat.horodatages.get(volee.numero),
                )
                for volee in etat.serie.volees
            ],
        )

    @staticmethod
    def vide(tournoi_id: int, archer_id: int) -> SerieReponse:
        """Série encore vierge (rien de saisi) : un pavé vide pour le front, pas un 404."""
        return SerieReponse(tournoi_id=tournoi_id, archer_id=archer_id, cumul=0, volees=[])


# --- Endpoints ---


@router.post("/depart-courant", response_model=DepartCourantReponse)
async def fixer_depart_courant(
    requete: DepartCourantRequete,
    request: Request,
    _poste: Annotated[Poste, Depends(exiger_poste)],
) -> DepartCourantReponse:
    """Met le poste « en mode départ X » (ADR-0034). Jeton de poste requis (`exiger_poste`).

    `404 depart_introuvable` si le départ n'existe pas ou relève d'un autre tournoi que le poste
    (ADR-0034 §4). Mutation de **session** (départ courant en mémoire) + lectures de cohérence :
    hors file d'écriture, exécutée dans le threadpool (le service relit la base).
    """
    service: ServicePostes = request.app.state.service_postes
    jeton = extraire_jeton_poste(request)
    depart = await run_in_threadpool(service.fixer_depart_courant, jeton, requete.depart_id)
    return DepartCourantReponse.de_agregat(depart)


@router.get("/archers", response_model=list[ArcherGrilleReponse])
async def archers_du_poste(
    request: Request,
    poste: Annotated[Poste, Depends(exiger_poste)],
) -> list[ArcherGrilleReponse]:
    """La grille du poste : les archers placés sur sa cible pour son **départ courant** (ADR-0033).

    `409 depart_courant_non_defini` tant que le poste n'a pas fixé son départ (ADR-0034 §1 : refus
    explicite, pas d'affichage vide ambigu). Lecture (placement + inscriptions), hors file.
    """
    service_postes: ServicePostes = request.app.state.service_postes
    service_saisie: ServiceSaisie = request.app.state.service_saisie
    depart_id = service_postes.depart_courant(extraire_jeton_poste(request))
    if depart_id is None:
        raise DepartCourantNonDefini("Le poste doit d'abord choisir son départ courant.")
    grille = await run_in_threadpool(
        service_saisie.archers_du_poste, poste.tournoi_id, poste.cible_index, depart_id
    )
    return [ArcherGrilleReponse.de_ligne(ligne) for ligne in grille]


@router.post("/volees", response_model=SerieReponse)
async def saisir_volee(
    requete: SaisirVoleeRequete,
    request: Request,
    poste: Annotated[Poste | None, Depends(autoriser_saisie)],
) -> SerieReponse:
    """Saisit (ou réédite) une volée. **Admin ou poste** (`autoriser_saisie`, E10US007).

    Un **poste** ne saisit que pour un archer de **sa** cible / **son** départ courant (`403
    saisie_hors_cible`, garde au service ADR-0033 §3) ; il doit avoir fixé son départ (`409
    depart_courant_non_defini`). L'écriture passe par la **file** (writer unique) et est
    **dédoublonnée** par `identifiant_saisie` (idempotence ADR-0036). Renvoie l'état de la série.
    """
    service_saisie: ServiceSaisie = request.app.state.service_saisie
    service_postes: ServicePostes = request.app.state.service_postes
    write_queue: WriteQueue = request.app.state.write_queue
    registre: RegistreIdempotence = request.app.state.registre_idempotence

    contexte: ContexteSaisie | None = None
    if poste is not None:
        if requete.tournoi_id != poste.tournoi_id:
            raise SaisieHorsCible("Ce poste ne sert pas ce tournoi.")
        depart_id = service_postes.depart_courant(extraire_jeton_poste(request))
        if depart_id is None:
            raise DepartCourantNonDefini("Le poste doit d'abord choisir son départ courant.")
        contexte = ContexteSaisie(cible_index=poste.cible_index, depart_id=depart_id)

    valeurs = tuple(requete.valeurs)

    def acte() -> EtatSerie | None:
        service_saisie.saisir_volee(
            requete.tournoi_id,
            requete.archer_id,
            requete.numero,
            valeurs,
            requete.saisie_par,
            contexte,
        )
        return service_saisie.etat_serie(requete.tournoi_id, requete.archer_id)

    etat = await asyncio.wrap_future(
        write_queue.submit(lambda: registre.executer(requete.identifiant_saisie, acte))
    )
    assert etat is not None, "Une volée vient d'être saisie : l'état de la série existe."
    return SerieReponse.de_etat(etat)


@router.get("/series/{tournoi_id}/{archer_id}", response_model=SerieReponse)
async def lire_serie(
    tournoi_id: int,
    archer_id: int,
    request: Request,
    poste: Annotated[Poste | None, Depends(autoriser_saisie)],
) -> SerieReponse:
    """L'état de la série d'un archer (volées, verrou, cumul, « quand » de chacune). Admin ou poste.

    Un poste ne lit que dans **son** tournoi (`403 saisie_hors_cible`). Un archer qui n'a rien
    saisi renvoie une série **vide** (200), pas un 404 : le front affiche un pavé vierge. Lecture.
    """
    service_saisie: ServiceSaisie = request.app.state.service_saisie
    if poste is not None and tournoi_id != poste.tournoi_id:
        raise SaisieHorsCible("Ce poste ne sert pas ce tournoi.")
    etat = await run_in_threadpool(service_saisie.etat_serie, tournoi_id, archer_id)
    if etat is None:
        return SerieReponse.vide(tournoi_id, archer_id)
    return SerieReponse.de_etat(etat)
