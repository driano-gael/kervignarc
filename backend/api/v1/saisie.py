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

from api.dependances import (
    autoriser_saisie,
    exiger_poste,
    exiger_scoreur,
    extraire_jeton_poste,
)
from application.erreurs import DepartCourantNonDefini, SaisieHorsCible, ScoreurHorsTournoi
from application.postes import ServicePostes
from application.saisie import ArcherPositionne, ContexteSaisie, EtatSerie, ServiceSaisie
from domain.blason import ZoneScore
from domain.depart import Depart
from domain.poste import Poste
from domain.scoreur import Scoreur
from domain.serie import Serie
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
    """Une ligne de la grille : position A..D, archer, et son **pavé** (zones légales du blason).

    `zones` porte le pavé de saisie **déduit du blason tiré** (CA « pavé ») dans l'ordre canonique
    centre→extérieur : sur un triple 40 les touches basses en sont **absentes**. Le front l'affiche
    tel quel — le serveur reste l'autorité du barème. `[]` = blason indéterminable (pavé indispo.).
    """

    position: str
    archer_id: int
    nom: str
    prenom: str
    zones: list[str]

    @staticmethod
    def de_ligne(ligne: ArcherPositionne) -> ArcherGrilleReponse:
        assert ligne.archer.id is not None, "Un archer placé est persisté."
        return ArcherGrilleReponse(
            position=ligne.position,
            archer_id=ligne.archer.id,
            nom=ligne.archer.nom,
            prenom=ligne.archer.prenom,
            zones=[zone.value for zone in ligne.zones],
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


class ValiderRequete(BaseModel):
    """Corps de validation d'une série (acte du scoreur). `identifiant_saisie` rend l'acte
    **idempotent** : un rejeu ne consigne pas une seconde trace d'audit (ADR-0036)."""

    tournoi_id: int
    archer_id: int
    identifiant_saisie: str | None = None


class CorrigerRequete(BaseModel):
    """Corps de correction d'une volée verrouillée (rôle habilité = le scoreur). Idempotent par
    `identifiant_saisie`. `valeurs` validé contre `ZoneScore` (hors énum → 400)."""

    tournoi_id: int
    archer_id: int
    numero: int = Field(ge=1)
    valeurs: list[ZoneScore] = Field(min_length=1)
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
    def de_serie(serie: Serie, horodatages: dict[int, datetime.datetime]) -> SerieReponse:
        """Bâtit la réponse depuis la `Serie` (renvoyée par l'acte d'écriture) + le « quand »."""
        return SerieReponse(
            tournoi_id=serie.tournoi_id,
            archer_id=serie.archer_id,
            cumul=serie.cumul,
            volees=[
                VoleeReponse(
                    numero=volee.numero,
                    valeurs=[zone.value for zone in volee.valeurs],
                    saisie_par=volee.saisie_par,
                    validee_par=volee.validee_par,
                    verrouillee=volee.verrouillee,
                    saisie_le=horodatages.get(volee.numero),
                )
                for volee in serie.volees
            ],
        )

    @staticmethod
    def de_etat(etat: EtatSerie) -> SerieReponse:
        return SerieReponse.de_serie(etat.serie, etat.horodatages)

    @staticmethod
    def vide(tournoi_id: int, archer_id: int) -> SerieReponse:
        """Série encore vierge (rien de saisi) : un pavé vide pour le front, pas un 404."""
        return SerieReponse(tournoi_id=tournoi_id, archer_id=archer_id, cumul=0, volees=[])


# --- Endpoints ---


def _cle_idempotence(operation: str, identifiant: str | None, *portee: int) -> str | None:
    """Clé d'idempotence **scopée** (opération + cible), ou `None` si le client n'en fournit pas.

    Scoper la clé serveur-side ferme la **perte d'écriture silencieuse** (revue A/B/C1) : un
    `identifiant_saisie` réutilisé par erreur sur un autre acte, un autre archer ou une autre volée
    ne dédoublonne **plus à tort** — le client n'a qu'à rendre son identifiant unique **par geste**,
    pas globalement. Sans identifiant, pas de déduplication (`None` → exécution simple, ADR-0036).
    """
    if not identifiant:
        return None
    return ":".join([operation, *(str(p) for p in portee), identifiant])


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
    cle = _cle_idempotence(
        "volee", requete.identifiant_saisie, requete.tournoi_id, requete.archer_id, requete.numero
    )

    def ecrire() -> Serie:
        return service_saisie.saisir_volee(
            requete.tournoi_id,
            requete.archer_id,
            requete.numero,
            valeurs,
            requete.saisie_par,
            contexte,
        )

    # L'écriture SEULE est dédoublonnée (unité mémorisée) ; le « quand » se lit **après**, hors de
    # l'unité idempotente : un échec de cette lecture ne fait pas ré-exécuter l'écriture au rejeu.
    serie = await asyncio.wrap_future(write_queue.submit(lambda: registre.executer(cle, ecrire)))
    horodatages = await run_in_threadpool(
        service_saisie.horodatages, requete.tournoi_id, requete.archer_id
    )
    return SerieReponse.de_serie(serie, horodatages)


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


def _exiger_meme_tournoi(scoreur: Scoreur, tournoi_id: int) -> None:
    """Refuse (`403 scoreur_hors_tournoi`) un scoreur agissant hors de **son** tournoi."""
    if scoreur.tournoi_id != tournoi_id:
        raise ScoreurHorsTournoi("Ce scoreur n'officie pas dans ce tournoi.")


@router.post("/validations", response_model=SerieReponse)
async def valider_serie(
    requete: ValiderRequete,
    request: Request,
    scoreur: Annotated[Scoreur, Depends(exiger_scoreur)],
) -> SerieReponse:
    """Valide la série d'un archer, **au nom du scoreur** (E04US002 : validation = scoreur seul).

    Le scoreur, itinérant, valide **son** tournoi seulement (`403 scoreur_hors_tournoi` sinon) ; sa
    validation tient lieu de seconde marque (`D-03`) et **trace** qui/quand (E10US005). Verrou selon
    le grain de la phase. Écriture via la **file**, **dédoublonnée** par identifiant (ADR-0036) : un
    rejeu ne consigne pas une seconde trace. Renvoie l'état de la série.
    """
    service_saisie: ServiceSaisie = request.app.state.service_saisie
    write_queue: WriteQueue = request.app.state.write_queue
    registre: RegistreIdempotence = request.app.state.registre_idempotence
    _exiger_meme_tournoi(scoreur, requete.tournoi_id)
    cle = _cle_idempotence(
        "validation", requete.identifiant_saisie, requete.tournoi_id, requete.archer_id
    )

    def ecrire() -> Serie:
        return service_saisie.valider(requete.tournoi_id, requete.archer_id, scoreur.nom)

    serie = await asyncio.wrap_future(write_queue.submit(lambda: registre.executer(cle, ecrire)))
    horodatages = await run_in_threadpool(
        service_saisie.horodatages, requete.tournoi_id, requete.archer_id
    )
    return SerieReponse.de_serie(serie, horodatages)


@router.post("/corrections", response_model=SerieReponse)
async def corriger_volee(
    requete: CorrigerRequete,
    request: Request,
    scoreur: Annotated[Scoreur, Depends(exiger_scoreur)],
) -> SerieReponse:
    """Corrige une volée **verrouillée**, au nom du scoreur (le « rôle habilité » du CA ex-012).

    Seul chemin d'écriture sur une série verrouillée ; **trace** l'avant/après (E10US005) et
    recalcule le cumul. Scoreur borné à **son** tournoi (`403` sinon). Via la **file**,
    **dédoublonnée** par identifiant (ADR-0036). Renvoie l'état de la série.
    """
    service_saisie: ServiceSaisie = request.app.state.service_saisie
    write_queue: WriteQueue = request.app.state.write_queue
    registre: RegistreIdempotence = request.app.state.registre_idempotence
    _exiger_meme_tournoi(scoreur, requete.tournoi_id)
    valeurs = tuple(requete.valeurs)
    cle = _cle_idempotence(
        "correction",
        requete.identifiant_saisie,
        requete.tournoi_id,
        requete.archer_id,
        requete.numero,
    )

    def ecrire() -> Serie:
        return service_saisie.corriger_volee(
            requete.tournoi_id, requete.archer_id, requete.numero, valeurs, scoreur.nom
        )

    serie = await asyncio.wrap_future(write_queue.submit(lambda: registre.executer(cle, ecrire)))
    horodatages = await run_in_threadpool(
        service_saisie.horodatages, requete.tournoi_id, requete.archer_id
    )
    return SerieReponse.de_serie(serie, horodatages)
