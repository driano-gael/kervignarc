"""Endpoints REST du **Big Shoot Off** (E05US028) — l'atelier règle, la salle fait tirer.

Expose `ServiceBigShootOff` sur deux surfaces qui n'ont ni le même public ni les mêmes droits :

- **l'atelier** (admin) lit la **projection** que la liste de sortants produit sur l'effectif réel
  (« avec vos 12 inscrits : 12 → 8 → 6 → 5 ») ;
- **la salle et le public** lisent l'**état** de la phase — qui est en lice, qui est sorti et à quel
  rang, où en est la manche courante ;
- **le scoreur** lit la même photo augmentée de l'adressage de saisie (`/saisie/`) et **saisit** les
  volées avec le pavé de la qualification.

⚠️ **Un tir de Big Shoot Off *est* une série de volées**, et ce routeur le montre : la saisie écrit
dans la table `serie`/`volee`, sans table ni migration propres. C'est le pendant exact d'ADR-0083
§7, où une rencontre de poule réutilise `duel`. Ce qui diffère est le **décor** — la volée est
**collective**, tout le monde sur la ligne, et c'est le classement de la manche qui élimine.

`numero` est le numéro de volée dans la feuille de l'archer, **dérivé** du réglage et jamais
stocké : la manche *m* occupe les volées `(m-1)·V + 1 … m·V`.

Écritures routées par la **file** (writer unique, ADR-0005) et dédoublonnées par identifiant de
saisie (ADR-0036) — mêmes garanties que la saisie de qualification et celle des poules.

**Trois surfaces de lecture, trois droits** (E05US031). `/etat/` est **ouvert**, `/saisie/` est
**scoreur**, `/projection/` est **admin** — c'est un écran d'atelier, pas un panneau de salle.

⚠️ **La frontière entre les deux premières a changé de justification, pas seulement de place.** Ce
routeur affirmait que l'état complet devait rester scoreur parce qu'« il porte les scores manche par
manche, donc ce que le public n'a pas à voir avant validation ». C'est faux depuis toujours :
`_scores_par_manche` ne rend que les manches **entièrement validées**, et s'arrête à la première
incomplète. Le secret invoqué n'existait pas ; ce qui distingue réellement les deux formes est
l'**adressage de saisie** (`prochaine_volee`, `volees`), qui n'a de sens que devant un pavé. Cf.
`TireurPubliqueReponse`.
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

    ⚠️ **C'est ici que vit la restriction de contenu (règle 6)**, et c'est la raison d'être de ce
    DTO. Il retire `prochaine_volee`, qui est une **affordance de saisie** : elle dit au pavé du
    scoreur quelle volée poser, et n'a aucun sens hors de lui.

    ⚠️ **Ce qu'on croyait devoir retirer et qui n'existait pas.** L'en-tête de ce routeur justifiait
    jusqu'ici l'accès scoreur par « l'état porte les scores manche par manche, donc ce que le
    public n'a pas à voir **avant validation** ». Vérification faite au moment d'ouvrir la route :
    `TireurAffiche.scores` ne porte **que** les manches entièrement validées —
    `_scores_par_manche` s'arrête à la première manche incomplète, précisément pour ne pas faire
    lire un total partiel. La confidentialité invoquée était donc **déjà** assurée par la couche
    application, un cran plus bas ; l'authentification protégeait un secret qui n'était pas là. On
    le note plutôt que de le taire : c'est la différence entre une frontière tenue et une frontière
    crue tenue.

    Comme dans `poules.py` et `suisse.py`, un DTO **distinct** et non un `exclude` : un champ ajouté
    au DTO du scoreur n'apparaît pas ici par défaut, alors qu'une liste d'exclusions aurait laissé
    passer le suivant.
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

    Mêmes champs de cadrage que la forme complète ; seuls les **tireurs**, les **manches** et le
    format sont réduits. C'est le détail de saisie qui est retiré, pas la structure de la phase, que
    l'écran de salle doit précisément montrer (même parti qu'`EtatSuissePubliqueReponse`).

    `barrage` réutilise `BarrageEnAttenteReponse` **à dessein**, et c'est la seule réutilisation
    ici : ce DTO est une feuille — des identifiants, des noms, un nombre de places — qui ne porte
    aucun contenu de tir et ne peut donc pas en acquérir par dérive. La règle « un DTO distinct »
    protège des DTO qui **embarquent** le détail du tir (`DuelReponse`, `prochaine_volee`) ;
    l'appliquer ici dupliquerait trois champs sans rien fermer.
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

    ⚠️ **Cette route était scoreur jusqu'à E05US031**, et la lecture du scoreur a migré sur
    `/saisie/` — c'est le couple exact que portent déjà `poules.py` et `suisse.py` (`/etat/` ouvert,
    `/saisie/` restreint). Le Big Shoot Off était le seul des trois formats sans surface publique,
    d'où un onglet public muet pendant une finale ; l'aligner valait mieux qu'inventer un troisième
    nom de route pour la même idée.

    **Rupture de contrat assumée** plutôt qu'un ajout à côté : `/etat/` change de forme au lieu
    que `/public/` s'ajoute. `/api/v1` n'a qu'un seul client, livré dans le même bundle par le même
    serveur (mono-club, réseau local, règle 12) — il n'existe aucun consommateur tiers à ménager,
    et laisser deux routes servir la même photo aurait figé pour de bon l'asymétrie entre les trois
    formats.
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
