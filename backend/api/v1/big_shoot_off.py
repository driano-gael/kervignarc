"""Endpoints REST du **Big Shoot Off** (E05US028) — l'atelier règle, la salle fait tirer.

Expose `ServiceBigShootOff` sur deux surfaces qui n'ont ni le même public ni les mêmes droits :

- **l'atelier** (admin) lit la **projection** que la liste de sortants produit sur l'effectif réel
  (« avec vos 12 inscrits : 12 → 8 → 6 → 5 ») ;
- **la salle** (scoreur) lit l'**état** de la phase — qui est en lice, qui est sorti et à quel rang,
  où en est la manche courante — et **saisit** les volées avec le pavé de la qualification.

⚠️ **Un tir de Big Shoot Off *est* une série de volées**, et ce routeur le montre : la saisie écrit
dans la table `serie`/`volee`, sans table ni migration propres. C'est le pendant exact d'ADR-0083
§7, où une rencontre de poule réutilise `duel`. Ce qui diffère est le **décor** — la volée est
**collective**, tout le monde sur la ligne, et c'est le classement de la manche qui élimine.

`numero` est le numéro de volée dans la feuille de l'archer, **dérivé** du réglage et jamais
stocké : la manche *m* occupe les volées `(m-1)·V + 1 … m·V`.

Écritures routées par la **file** (writer unique, ADR-0005) et dédoublonnées par identifiant de
saisie (ADR-0036) — mêmes garanties que la saisie de qualification et celle des poules.

**Trois surfaces de lecture, trois droits** (E05US031, ADR-0089 §5 —
`docs/adr/0089-les-vues-publiques-rendent-les-formats-sans-arbre.md`) :

- `/saisie` — **scoreur** : l'état complet, avec `prochaine_volee` et la numérotation des volées ;
- `/etat` — **public et anonyme** : l'avancement rédigé, sans aucune affordance de saisie ;
- `/projection` — **admin** : l'aperçu de l'atelier, qui n'exige ni tir ni plan de salle.

⚠️ **Les deux premières routes ont échangé leur nom le 17/08/2026.** Jusqu'à E05US031, `/etat`
désignait ici la lecture **scoreur**, alors que ses deux formats jumeaux (`poules.py`, `suisse.py`)
appellent `/etat` la lecture **publique** et `/saisie` celle du scoreur. Trois moteurs frères, deux
conventions, dont une qui plaçait une lecture protégée derrière le nom de la lecture ouverte : c'est
le genre d'écart qui ne coûte rien jusqu'au jour où l'on ajoute une route en recopiant le mauvais
voisin. Le front et le serveur étant livrés ensemble (SPA servie par le backend), il n'y avait aucun
client tiers à ménager.
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

    ⚠️ **Sans ce champ, l'écran de saisie devait deviner** — et il devinait « la première volée de
    la manche », ce qui n'est juste qu'à `volees = 1`. Dès `volees = 2`, la seconde n'était jamais
    saisissable et la finale se bloquait (revue d'E05US028). La manche *m* occupe les volées
    `(m-1)·V+1 … m·V` : c'est une numérotation que le serveur persiste et que le front n'a pas à
    re-dériver.

    `null` a trois causes, toutes légitimes : l'archer est sorti, la phase est terminée, ou un
    barrage la suspend. Dans les trois cas l'écran doit fermer le pavé plutôt que proposer une
    saisie qui sera refusée."""

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
            barrage=(
                BarrageEnAttenteReponse(
                    archer_ids=[duelliste.archer_id for duelliste in etat.barrage_entre],
                    noms=[
                        f"{duelliste.prenom} {duelliste.nom}" for duelliste in etat.barrage_entre
                    ],
                    places=etat.places_au_barrage,
                )
                if etat.barrage_entre
                else None
            ),
        )


class ProjectionPubliqueReponse(BaseModel):
    """Le déroulé **annoncé** du format, tel qu'un spectateur peut le lire : « 12 → 8 → 6 → 5 ».

    Trois champs de `ProjectionReponse` n'y figurent pas, et l'absence **est** la décision (règle
    6 — un DTO public est un contrat distinct, pas l'objet interne appauvri par politesse) :
    `volees` et `fleches_par_volee` sont le **format du tir**, dont seul le pavé de saisie a
    besoin ; `manches_ignorees` est un avertissement d'**atelier** (« votre liste de sortants
    dépasse votre effectif »), adressé à l'organisateur qui règle, pas au public qui regarde.
    """

    effectif: int
    eliminations: list[int]
    paliers: list[int]
    restants: int
    manches_jouables: int

    @staticmethod
    def de_projection(projection: ProjectionBigShootOff) -> ProjectionPubliqueReponse:
        return ProjectionPubliqueReponse(
            effectif=projection.effectif,
            eliminations=list(projection.eliminations),
            paliers=list(projection.paliers),
            restants=projection.restants,
            manches_jouables=projection.manches_jouables,
        )


class TireurPublicReponse(BaseModel):
    """Un finaliste **en consultation** : son sort et ce qu'il a marqué, jamais ce qu'il doit tirer.

    `scores` est conservé tel quel : `TireurAffiche.scores` ne porte que les manches **entièrement
    validées**, donc rien qui ne soit acquis — c'est le pendant exact des points d'un duel sur la
    route publique des tableaux. `prochaine_volee` est retiré : c'est une **affordance de saisie**,
    elle n'a aucun sens pour un lecteur et la publier apprendrait au passage où en est la feuille
    d'un archer.
    """

    archer_id: int
    nom: str
    prenom: str
    en_lice: bool
    rang: int | None
    scores: list[int]

    @staticmethod
    def de_tireur(tireur: TireurAffiche) -> TireurPublicReponse:
        return TireurPublicReponse(
            archer_id=tireur.archer_id,
            nom=tireur.nom,
            prenom=tireur.prenom,
            en_lice=tireur.en_lice,
            rang=tireur.rang,
            scores=list(tireur.scores),
        )


class ManchePubliqueReponse(BaseModel):
    """Une manche **en consultation** : son rang, ce qu'elle élimine, où elle en est.

    `volees` (les numéros de volée qu'occupe la manche) n'y figure pas : c'est la numérotation de la
    feuille de saisie, dérivée du réglage (`(m-1)·V+1 … m·V`), et elle ne dit rien à qui regarde.
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
    """La photo d'un Big Shoot Off **rédigée** — appli publique et écran de salle (ADR-0089 §5).

    Le barrage y figure : c'est **lui** qui explique pourquoi la manche suivante ne s'ouvre pas. Le
    taire laisserait le public devant une finale qui n'avance plus sans raison visible — le même
    motif qui a fait remonter `BarrageEnAttenteReponse` jusqu'au scoreur en E05US028.
    """

    phase_id: int
    projection: ProjectionPubliqueReponse
    tireurs: list[TireurPublicReponse]
    manches: list[ManchePubliqueReponse]
    termine: bool
    barrage: BarrageEnAttenteReponse | None

    @staticmethod
    def de_etat(etat: EtatBigShootOffAffiche) -> EtatPubliqueReponse:
        return EtatPubliqueReponse(
            phase_id=etat.phase_id,
            projection=ProjectionPubliqueReponse.de_projection(etat.projection),
            tireurs=[TireurPublicReponse.de_tireur(tireur) for tireur in etat.tireurs],
            manches=[ManchePubliqueReponse.de_manche(manche) for manche in etat.manches],
            termine=etat.termine,
            barrage=(
                BarrageEnAttenteReponse(
                    archer_ids=[duelliste.archer_id for duelliste in etat.barrage_entre],
                    noms=[
                        f"{duelliste.prenom} {duelliste.nom}" for duelliste in etat.barrage_entre
                    ],
                    places=etat.places_au_barrage,
                )
                if etat.barrage_entre
                else None
            ),
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
    """L'état **rédigé** de la phase — ouvert, comme `/poules/etat` et `/suisse/etat` (E05US031).

    C'est la lecture de l'appli publique et de l'écran de salle : qui est en lice, qui est sorti et
    à quel rang, où en est la manche courante. Aucune affordance de saisie n'y circule (ADR-0089
    §5) ; le détail complet se lit sur `/saisie`, derrière `exiger_scoreur`.
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
    """L'état complet de la phase — **scoreur**, parce qu'il porte de quoi saisir.

    ⚠️ **Cette route s'appelait `/etat` jusqu'au 17/08/2026** ; elle a pris le nom que ses deux
    formats jumeaux donnent à leur lecture de saisie, et rendu `/etat` au public (cf. en-tête).
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
