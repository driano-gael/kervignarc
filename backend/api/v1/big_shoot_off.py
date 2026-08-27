"""Routeur **Big Shoot Off** — un tir *est* une série de volées, dans `serie`/`volee` (ADR-0083 §7).
La volée est **collective** ; `numero` est dérivé du réglage, jamais stocké. Trois surfaces, trois
droits : `/etat/` ouvert, `/saisie/` scoreur, `/projection/` admin.

⚠️ **Ce qui sépare `/etat/` de `/saisie/` est l'ADRESSAGE, pas un secret.** `_scores_par_manche` ne
rend que les manches entièrement validées : il n'y a rien à cacher au public. Ce qui n'a de sens que
devant un pavé, c'est `prochaine_volee` / `volees`.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin, exiger_scoreur
from application.big_shoot_off import (
    EtatBigShootOffAffiche,
    MancheAffichee,
    ProjectionBigShootOff,
    ServiceBigShootOff,
    TireurAffiche,
)
from application.erreurs import ScoreurHorsTournoi
from domain.blason import ZoneScore
from domain.scoreur import Scoreur
from infrastructure.db.write_queue import WriteQueue
from infrastructure.idempotence import RegistreIdempotence

router = APIRouter(prefix="/api/v1/big-shoot-off", tags=["big-shoot-off"])


class ProjectionReponse(BaseModel):
    """Ce que la liste de sortants donne sur l'effectif réel — l'aperçu de l'atelier.

    `manches_ignorees` n'est **pas** une erreur : c'est la contrepartie de « on joue tant que la
    manche est possible », qui rend un format réutilisable sur un effectif qu'il ignore. Mais c'est
    une information que l'écran doit **dire**, sinon l'organisateur croit jouer une liste qu'il ne
    joue pas.
    """

    effectif: int
    eliminations: list[int]
    paliers: list[int]
    volees: int
    fleches_par_volee: int
    restants: int
    manches_jouables: int
    manches_ignorees: int

    @staticmethod
    def de_projection(projection: ProjectionBigShootOff) -> ProjectionReponse:
        return ProjectionReponse(
            effectif=projection.effectif,
            eliminations=list(projection.eliminations),
            paliers=list(projection.paliers),
            volees=projection.volees,
            fleches_par_volee=projection.fleches_par_volee,
            restants=projection.restants,
            manches_jouables=projection.manches_jouables,
            manches_ignorees=projection.manches_ignorees,
        )


class TireurReponse(BaseModel):
    """Un finaliste : son sort et ce qu'il a marqué manche par manche.

    `rang` est `null` tant qu'il est **en lice** : un rang annoncé avant la sortie serait un faux
    départ. `scores` ne porte que les manches **entièrement validées** — un total partiel ferait
    lire « 12 » pour une manche dont deux volées manquent, et le scoreur croirait l'archer en
    difficulté.
    """

    archer_id: int
    nom: str
    prenom: str
    en_lice: bool
    rang: int | None
    scores: list[int]
    prochaine_volee: int | None = None
    """La **prochaine volée à saisir** pour cet archer, ou `null` s'il n'y a rien à tirer.

    ⚠️ **Sans ce champ, l'écran devait deviner** — et il devinait « la première volée de la manche
    », juste seulement à `volees = 1` : dès 2, la seconde n'était jamais saisissable et la finale
    se bloquait. La manche *m* occupe les volées `(m-1)·V+1 … m·V`, numérotation que le serveur
    persiste et que le front n'a pas à re-dériver. `null` = archer sorti, phase terminée, ou
    barrage en cours — dans les trois cas l'écran ferme le pavé.
    """

    @staticmethod
    def de_tireur(tireur: TireurAffiche) -> TireurReponse:
        return TireurReponse(
            archer_id=tireur.archer_id,
            nom=tireur.nom,
            prenom=tireur.prenom,
            en_lice=tireur.en_lice,
            rang=tireur.rang,
            scores=list(tireur.scores),
            prochaine_volee=tireur.prochaine_volee,
        )


class MancheReponse(BaseModel):
    """Une manche : son rang, combien elle élimine, où en est sa saisie.

    `complete` se juge sur les archers **encore en lice à cette manche-là**, pas sur tous les
    participants : un archer sorti à la manche 1 n'a pas à tirer la manche 2, et exiger ses volées
    bloquerait la phase pour toujours.
    """

    numero: int
    elimine: int
    volees: list[int]
    complete: bool
    jouee: bool

    @staticmethod
    def de_manche(manche: MancheAffichee) -> MancheReponse:
        return MancheReponse(
            numero=manche.numero,
            elimine=manche.elimine,
            volees=list(manche.volees),
            complete=manche.complete,
            jouee=manche.jouee,
        )


class BarrageEnAttenteReponse(BaseModel):
    """L'égalité qui **suspend** la phase, et combien de places elle dispute.

    Sans ce relais, le scoreur verrait une manche saisie **et validée** qui n'élimine personne, sans
    comprendre pourquoi la suivante refuse de s'ouvrir. `places` distingue les deux barrages du
    format : à la barre il est strictement inférieur au nombre d'ex æquo (trois archers à 22 pour
    une seule place) ; entre sortants il leur est **égal** — ils sortent tous, le barrage n'ordonne
    que leurs rangs.
    """

    archer_ids: list[int]
    noms: list[str]
    places: int


class EtatReponse(BaseModel):
    """La photo d'un Big Shoot Off, telle que la salle la lit."""

    phase_id: int
    projection: ProjectionReponse
    tireurs: list[TireurReponse]
    manches: list[MancheReponse]
    termine: bool
    barrage: BarrageEnAttenteReponse | None

    @staticmethod
    def de_etat(etat: EtatBigShootOffAffiche) -> EtatReponse:
        return EtatReponse(
            phase_id=etat.phase_id,
            projection=ProjectionReponse.de_projection(etat.projection),
            tireurs=[TireurReponse.de_tireur(tireur) for tireur in etat.tireurs],
            manches=[MancheReponse.de_manche(manche) for manche in etat.manches],
            termine=etat.termine,
            barrage=_barrage(etat),
        )


class FormatPubliqueReponse(BaseModel):
    """La **forme** du format, telle qu'un spectateur la lit : « 12 → 8 → 6 → 5, 3 volées de 3 ».

    C'est `ProjectionReponse` amputée de ce qui appartient à l'**atelier** : `eliminations` (la
    liste réglée, à distinguer des paliers réellement joués) et surtout `manches_ignorees`, qui dit
    à l'organisateur que son réglage dépasse son effectif. Devant une salle, ce chiffre ne se lit
    pas — il n'est pas confidentiel, il est **sans destinataire**, et l'afficher ferait croire à un
    incident.
    """

    effectif: int
    paliers: list[int]
    restants: int
    volees: int
    fleches_par_volee: int
    manches_jouables: int

    @staticmethod
    def de_projection(projection: ProjectionBigShootOff) -> FormatPubliqueReponse:
        return FormatPubliqueReponse(
            effectif=projection.effectif,
            paliers=list(projection.paliers),
            restants=projection.restants,
            volees=projection.volees,
            fleches_par_volee=projection.fleches_par_volee,
            manches_jouables=projection.manches_jouables,
        )


class TireurPubliqueReponse(BaseModel):
    """Le **même** finaliste, vu de qui n'a pas à saisir — écran de salle, public, écran admin.

    ⚠️ **C'est ici que vit la restriction de contenu (règle 6)** : il retire `prochaine_volee`, une
    **affordance de saisie** sans objet hors du pavé. ⚠️ **Ce qu'on croyait devoir retirer
    n'existait pas** : `TireurAffiche.scores` ne porte que les manches **entièrement validées**,
    donc la confidentialité invoquée pour l'accès scoreur était déjà assurée un cran plus bas. Un
    DTO **distinct** et non un `exclude`, comme dans `poules.py` et `suisse.py`.
    """

    archer_id: int
    nom: str
    prenom: str
    en_lice: bool
    rang: int | None
    scores: list[int]

    @staticmethod
    def de_tireur(tireur: TireurAffiche) -> TireurPubliqueReponse:
        return TireurPubliqueReponse(
            archer_id=tireur.archer_id,
            nom=tireur.nom,
            prenom=tireur.prenom,
            en_lice=tireur.en_lice,
            rang=tireur.rang,
            scores=list(tireur.scores),
        )


class ManchePubliqueReponse(BaseModel):
    """La **même** manche, sans les numéros de volée de la feuille de saisie.

    `volees` porte `[(m-1)·V+1 … m·V]` : c'est l'adressage dont le pavé a besoin pour écrire au bon
    endroit de la série. Le public lit « manche 2 sur 4 », pas « volées 4, 5, 6 ».
    """

    numero: int
    elimine: int
    complete: bool
    jouee: bool

    @staticmethod
    def de_manche(manche: MancheAffichee) -> ManchePubliqueReponse:
        return ManchePubliqueReponse(
            numero=manche.numero,
            elimine=manche.elimine,
            complete=manche.complete,
            jouee=manche.jouee,
        )


class EtatPubliqueReponse(BaseModel):
    """La photo d'un Big Shoot Off, **rédigée** — la forme servie aux surfaces ouvertes.

    Mêmes champs de cadrage ; seuls les tireurs, les manches et le format sont réduits — c'est le
    détail de saisie qui part, pas la structure de la phase. ⚠️ `barrage` réutilise
    `BarrageEnAttenteReponse` **à dessein** : ce DTO est une feuille, sans contenu de tir, qui ne
    peut pas en acquérir par dérive — la règle « un DTO distinct » protège de ceux qui
    **embarquent** le tir, l'appliquer ici dupliquerait trois champs sans rien fermer.
    """

    phase_id: int
    format: FormatPubliqueReponse
    tireurs: list[TireurPubliqueReponse]
    manches: list[ManchePubliqueReponse]
    termine: bool
    barrage: BarrageEnAttenteReponse | None

    @staticmethod
    def de_etat(etat: EtatBigShootOffAffiche) -> EtatPubliqueReponse:
        return EtatPubliqueReponse(
            phase_id=etat.phase_id,
            format=FormatPubliqueReponse.de_projection(etat.projection),
            tireurs=[TireurPubliqueReponse.de_tireur(tireur) for tireur in etat.tireurs],
            manches=[ManchePubliqueReponse.de_manche(manche) for manche in etat.manches],
            termine=etat.termine,
            barrage=_barrage(etat),
        )


def _barrage(etat: EtatBigShootOffAffiche) -> BarrageEnAttenteReponse | None:
    """Le barrage en attente, ou `None` — écrit une fois pour les deux surfaces de lecture."""
    if not etat.barrage_entre:
        return None
    return BarrageEnAttenteReponse(
        archer_ids=[duelliste.archer_id for duelliste in etat.barrage_entre],
        noms=[f"{duelliste.prenom} {duelliste.nom}" for duelliste in etat.barrage_entre],
        places=etat.places_au_barrage,
    )


class SaisirVoleeRequete(BaseModel):
    """Une volée d'un finaliste. `valeurs` porte les zones tirées, dans l'ordre."""

    tournoi_id: int
    phase_id: int
    archer_id: int
    numero: int = Field(ge=1)
    valeurs: list[ZoneScore]
    identifiant_saisie: str | None = None


class ValiderMancheRequete(BaseModel):
    """Valide le lot de volées de la manche courante, **pour un archer**.

    La validation reste par archer — c'est l'agrégat `Serie` qui se verrouille, et chaque finaliste
    a la sienne. C'est la *manche* qui se joue collectivement, pas la validation : le scoreur
    descend la ligne et valide feuille par feuille, exactement comme en qualification.
    """

    tournoi_id: int
    phase_id: int
    archer_id: int
    identifiant_saisie: str | None = None


def _exiger_meme_tournoi(scoreur: Scoreur, tournoi_id: int) -> None:
    # DETTE-065 : copie verbatim de ce **garde d'autorisation**, présent dans six routeurs. Un
    # 7ᵉ routeur d'écriture qui l'oublierait ne ferait rougir personne — résorption :
    # `api/dependances.py`.
    """Un scoreur n'écrit que dans **son** tournoi (403 sinon) — jumeau de `api/v1/poules.py`."""
    if scoreur.tournoi_id != tournoi_id:
        raise ScoreurHorsTournoi("Ce scoreur n'est pas rattaché à ce tournoi.")


def _cle_idempotence(operation: str, identifiant: str | None, *portee: int) -> str | None:
    """La clé de dédoublonnage d'un acte de saisie (ADR-0036), ou `None` sans identifiant.

    ⚠️ La **portée** entre dans la clé : deux archers qui rejouent le même identifiant de
    saisie sur deux phases différentes ne doivent pas se dédoublonner l'un l'autre.
    """
    if identifiant is None:
        return None
    return ":".join((operation, identifiant, *(str(part) for part in portee)))


# --- Lecture ---


@router.get(
    "/projection/{tournoi_id}/{phase_id}",
    response_model=ProjectionReponse,
    dependencies=[Depends(exiger_admin)],
)
async def lire_projection(tournoi_id: int, phase_id: int, request: Request) -> ProjectionReponse:
    """L'aperçu de l'atelier : ce que la liste de sortants donne sur l'effectif du jour.

    **Admin**, et séparé de l'état : montrer la projection ne doit exiger ni tir ni plan de salle,
    sinon l'organisateur ne pourrait pas régler sa phase avant d'avoir fait sa salle.
    """
    service: ServiceBigShootOff = request.app.state.service_big_shoot_off
    projection = await run_in_threadpool(service.projection, tournoi_id, phase_id)
    return ProjectionReponse.de_projection(projection)


@router.get("/etat/{tournoi_id}/{phase_id}", response_model=EtatPubliqueReponse)
async def lire_etat(tournoi_id: int, phase_id: int, request: Request) -> EtatPubliqueReponse:
    """L'état **rédigé** — lecture ouverte : appli publique, écran de salle, écran admin.

    ⚠️ **Cette route était scoreur jusqu'à E05US031** ; la lecture du scoreur a migré sur
    `/saisie/`, le couple exact de `poules.py` et `suisse.py`. **Rupture de contrat assumée**
    plutôt qu'un `/public/` ajouté à côté : `/api/v1` n'a qu'un seul client, livré dans le même
    bundle par le même serveur (règle 12), et deux routes servant la même photo auraient figé
    l'asymétrie entre les trois formats.
    """
    service: ServiceBigShootOff = request.app.state.service_big_shoot_off
    etat = await run_in_threadpool(service.etat, tournoi_id, phase_id)
    return EtatPubliqueReponse.de_etat(etat)


@router.get("/saisie/{tournoi_id}/{phase_id}", response_model=EtatReponse)
async def lire_pour_saisie(
    tournoi_id: int,
    phase_id: int,
    request: Request,
    scoreur: Annotated[Scoreur, Depends(exiger_scoreur)],
) -> EtatReponse:
    """L'état complet — **scoreur**, parce qu'il porte l'adressage de la feuille de saisie.

    Ce que cette forme ajoute à la publique tient en deux champs : `prochaine_volee` par tireur et
    `volees` par manche. Ni l'un ni l'autre n'est un secret ; ce sont les coordonnées d'écriture du
    pavé, sans destinataire ailleurs.
    """
    service: ServiceBigShootOff = request.app.state.service_big_shoot_off
    _exiger_meme_tournoi(scoreur, tournoi_id)
    etat = await run_in_threadpool(service.etat, tournoi_id, phase_id)
    return EtatReponse.de_etat(etat)


# --- Saisie (scoreur, via la file) ---


@router.post("/volees", response_model=EtatReponse)
async def saisir_volee(
    requete: SaisirVoleeRequete,
    request: Request,
    scoreur: Annotated[Scoreur, Depends(exiger_scoreur)],
) -> EtatReponse:
    """Saisit (ou réédite) une volée d'un finaliste. Scoreur ; via la **file**, dédoublonnée.

    Rend l'**état complet** plutôt que la seule volée : une manche validée peut éliminer, donc
    changer la lice de tout le monde. Renvoyer la volée seule obligerait la tablette à relire
    aussitôt, et laisserait une fenêtre où l'écran montre un archer sorti comme encore en lice.
    """
    service: ServiceBigShootOff = request.app.state.service_big_shoot_off
    write_queue: WriteQueue = request.app.state.write_queue
    registre: RegistreIdempotence = request.app.state.registre_idempotence
    _exiger_meme_tournoi(scoreur, requete.tournoi_id)
    valeurs = tuple(requete.valeurs)
    cle = _cle_idempotence(
        "volee_big_shoot_off",
        requete.identifiant_saisie,
        requete.tournoi_id,
        requete.phase_id,
        requete.archer_id,
        requete.numero,
    )

    def ecrire() -> EtatBigShootOffAffiche:
        return service.saisir_volee(
            requete.tournoi_id,
            requete.phase_id,
            requete.archer_id,
            requete.numero,
            valeurs,
            scoreur.nom,
        )

    etat = await asyncio.wrap_future(write_queue.submit(lambda: registre.executer(cle, ecrire)))
    return EtatReponse.de_etat(etat)


@router.post("/validations", response_model=EtatReponse)
async def valider_manche(
    requete: ValiderMancheRequete,
    request: Request,
    scoreur: Annotated[Scoreur, Depends(exiger_scoreur)],
) -> EtatReponse:
    """Valide la manche courante d'un finaliste : c'est elle qui entrera au classement.

    Seules les volées **validées** comptent — un tir en cours de saisie ferait bouger l'élimination
    à chaque flèche, et un archer apparaîtrait sorti puis rentré sous les yeux du juge.
    """
    service: ServiceBigShootOff = request.app.state.service_big_shoot_off
    write_queue: WriteQueue = request.app.state.write_queue
    registre: RegistreIdempotence = request.app.state.registre_idempotence
    _exiger_meme_tournoi(scoreur, requete.tournoi_id)
    cle = _cle_idempotence(
        "validation_big_shoot_off",
        requete.identifiant_saisie,
        requete.tournoi_id,
        requete.phase_id,
        requete.archer_id,
    )

    def ecrire() -> EtatBigShootOffAffiche:
        return service.valider_manche(
            requete.tournoi_id, requete.phase_id, requete.archer_id, scoreur.nom
        )

    etat = await asyncio.wrap_future(write_queue.submit(lambda: registre.executer(cle, ecrire)))
    return EtatReponse.de_etat(etat)
