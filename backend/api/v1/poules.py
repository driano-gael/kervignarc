"""Endpoints REST des **poules** (E05US023, [ADR-0083]) — l'atelier règle, la salle fait tirer.

Expose `ServicePoules` sur deux surfaces qui n'ont ni le même public ni les mêmes droits :

- **l'atelier** (admin) lit la **répartition** que le réglage produit sur l'effectif réel (« 30
  archers → 7 poules : cinq de 4, deux de 5 ») et **pose le plan** de couloirs ;
- **la salle** (scoreur) lit l'**état** de la phase — groupes, blocs de couloirs, rencontres par
  tour, classements — et **saisit** les rencontres avec le pavé de duel d'E04US013.

⚠️ **Une rencontre de poule *est* un duel ordinaire** (ADR-0083 §7), et ce routeur le montre : les
trois écritures de tir sont les jumelles de celles de `api/v1/saisie_duels.py`, au même corps près,
et écrivent dans la même table `duel`. Ce qui diffère est la **navigation** — on entre par la poule
et le tour, pas par le numéro de match d'un arbre. C'est le `decor` du contrat de phase, et c'est
tout ce que la duplication porte.

`numero` est le `match_numero` de la table `duel`, **dérivé** de la composition et jamais stocké :
poules dans l'ordre, rencontres dans l'ordre du cercle, numérotation continue depuis 1. Un tir dont
les duellistes ne correspondent plus à la composition recalculée s'affiche « non tiré » plutôt que
d'être ré-attribué (ADR-0049 §4) — d'où `duel: null` sur une rencontre qui a pourtant une ligne.

Écritures routées par la **file** (writer unique, ADR-0005) et dédoublonnées par identifiant de
saisie (ADR-0036) pour les trois actes du scoreur. La pose du plan, elle, est un geste **admin** et
non idempotent par nature : elle **remplace** le plan existant, comme `plan-de-duels/regenerer`.

[ADR-0083]: ../../../docs/adr/0083-le-contrat-de-phase-jouable.md
"""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin, exiger_scoreur
from api.v1.saisie_duels import DuellisteReponse, DuelReponse
from application.erreurs import ScoreurHorsTournoi
from application.poules import (
    EtatPoules,
    PouleAffichee,
    RencontreAffichee,
    RepartitionPoules,
    ServicePoules,
)
from application.saisie_duels import EtatDuel
from domain.blason import ZoneScore
from domain.duel import Cote
from domain.scoreur import Scoreur
from infrastructure.db import WriteQueue
from infrastructure.idempotence import RegistreIdempotence

router = APIRouter(prefix="/api/v1/poules", tags=["poules"])


# --- DTO ---


class RepartitionReponse(BaseModel):
    """Ce que le réglage produit sur l'effectif **réel** — le CA « la répartition est montrée ».

    `tailles` porte l'effectif de chaque groupe, dans l'ordre : c'est ce qui rend l'arrondi lisible
    plutôt que surprenant (30 archers en poules de 4 → sept groupes, cinq de 4 et deux de 5) et ce
    qui rend inoffensif le cas extrême (7 archers en poules de 4 → **une** poule de 7, que
    l'organisateur voit et corrige s'il n'en veut pas).
    """

    effectif: int
    taille_visee: int
    nb_poules: int
    tailles: list[int]

    @staticmethod
    def de_repartition(repartition: RepartitionPoules) -> RepartitionReponse:
        return RepartitionReponse(
            effectif=repartition.effectif,
            taille_visee=repartition.taille_visee,
            nb_poules=repartition.nb_poules,
            tailles=list(repartition.tailles),
        )


class RencontreReponse(BaseModel):
    """Une rencontre de poule, prête pour le pavé de saisie d'E04US013.

    `couloirs` porte les deux places que les adversaires occupent **à ce tour** — `[cible, couloir]`
    chacune, dérivées du bloc de la poule et jamais persistées (le membre au repos change à chaque
    tour, ADR-0083 §3). `null` si le plan n'est pas posé, ou trop court pour cette position.

    `duel` est le **même** DTO que celui d'un match de tableau : une rencontre *est* un duel
    ordinaire, et servir une seconde forme obligerait le front à écrire un second pavé.
    """

    numero: int
    poule: int
    tour: int
    couloirs: list[list[int | str]] | None
    duel: DuelReponse

    @staticmethod
    def de_rencontre(rencontre: RencontreAffichee) -> RencontreReponse:
        return RencontreReponse(
            numero=rencontre.numero,
            poule=rencontre.poule,
            tour=rencontre.tour,
            couloirs=(
                None
                if rencontre.couloirs is None
                else [[cible, couloir] for cible, couloir in rencontre.couloirs]
            ),
            duel=DuelReponse.de_etat(_en_etat_duel(rencontre)),
        )


class RangPouleReponse(BaseModel):
    """Une ligne du classement d'une poule : son rang, son archer, son décompte (§10.1).

    Le décompte est servi **en entier** — les cinq critères — parce que le CA veut le départage
    « traçable » : on doit voir *pourquoi* deux archers à points égaux sont ordonnés ainsi, sans
    rejouer le calcul. `ex_aequo` marque ce que les cinq critères n'ont pas séparé.
    """

    rang: int
    archer_id: int
    points_match: int
    diff_sets: int
    diff_score: int
    nb_dix: int
    nb_neuf: int
    ex_aequo: bool


class PouleReponse(BaseModel):
    """Une poule : ses membres, son bloc de couloirs, ses rencontres, son classement.

    `barrage_requis` porte le **régime d'ex æquo** d'ADR-0083 §5, et c'est le seul champ dont le
    sens dépende du réglage : la poule qui *classe* départage **tout** ex æquo irréductible, celle
    qui *qualifie* ne départage que la barre. C'est lui qui déclenche l'annonce à l'écran — le
    barrage lui-même se tire par `POST /api/v1/tournois/{id}/barrages` en portée `poule` (E06US003).

    `bloc` est la liste des places contiguës que la poule occupe, `[cible, couloir]` chacune ;
    `null` tant que le plan n'est pas posé.
    """

    numero: int
    membres: list[DuellisteReponse]
    bloc: list[list[int | str]] | None
    rencontres: list[RencontreReponse]
    classement: list[RangPouleReponse]
    qualifies: list[DuellisteReponse]
    barrage_requis: bool

    @staticmethod
    def de_poule(poule: PouleAffichee) -> PouleReponse:
        return PouleReponse(
            numero=poule.numero,
            membres=[
                reponse
                for membre in poule.membres
                if (reponse := DuellisteReponse.de_duelliste(membre)) is not None
            ],
            bloc=(
                None
                if poule.bloc is None
                else [[cible, couloir] for cible, couloir in poule.bloc.places]
            ),
            rencontres=[RencontreReponse.de_rencontre(r) for r in poule.rencontres],
            classement=[
                RangPouleReponse(
                    rang=ligne.rang,
                    archer_id=ligne.participant.ref_id,
                    points_match=ligne.decompte.points_match,
                    diff_sets=ligne.decompte.diff_sets,
                    diff_score=ligne.decompte.diff_score,
                    nb_dix=ligne.decompte.nb_dix,
                    nb_neuf=ligne.decompte.nb_neuf,
                    ex_aequo=ligne.ex_aequo,
                )
                for ligne in poule.classement
            ],
            qualifies=[
                reponse
                for qualifie in poule.qualifies
                if (reponse := DuellisteReponse.de_duelliste(qualifie)) is not None
            ],
            barrage_requis=poule.barrage_requis,
        )


class ConflitReponse(BaseModel):
    """Une poule composée que le plan ne porte pas — plan non posé, ou salle trop petite.

    Rendu plutôt que comblé : poser la poule manquante à la lecture reviendrait à décider du
    placement dans une réponse dont l'appelant croit qu'elle ne fait que lire.
    """

    poule: int
    raison: str


class EtatPoulesReponse(BaseModel):
    """La photo d'une phase de poules : sa répartition, ses groupes, ce qui n'a pas pu être posé."""

    phase_id: int
    repartition: RepartitionReponse
    poules: list[PouleReponse]
    conflits: list[ConflitReponse]

    @staticmethod
    def de_etat(etat: EtatPoules) -> EtatPoulesReponse:
        return EtatPoulesReponse(
            phase_id=etat.phase_id,
            repartition=RepartitionReponse.de_repartition(etat.repartition),
            poules=[PouleReponse.de_poule(poule) for poule in etat.poules],
            conflits=[
                ConflitReponse(poule=conflit.poule, raison=conflit.raison.value)
                for conflit in etat.conflits
            ],
        )


class SaisirMancheRequete(BaseModel):
    """Corps de la saisie d'une manche d'une rencontre : les deux volées opposées."""

    tournoi_id: int
    phase_id: int
    numero: int
    manche: int
    valeurs_haut: list[ZoneScore]
    valeurs_bas: list[ZoneScore]
    identifiant_saisie: str | None = None


class SaisirBarrageRequete(BaseModel):
    """Corps du barrage **interne** à une rencontre nulle (§8.2).

    ⚠️ À ne pas confondre avec le **barrage de poule** (portée `poule`, E06US003), qui départage des
    ex æquo *du classement* et vit sur `/api/v1/tournois/{id}/barrages`. Celui-ci tranche une
    rencontre, c'est le barrage d'E04US013.
    """

    tournoi_id: int
    phase_id: int
    numero: int
    fleche_haut: ZoneScore
    fleche_bas: ZoneScore
    gagnant_designe: Cote | None = None
    identifiant_saisie: str | None = None


class ValiderRencontreRequete(BaseModel):
    """Corps de la validation : la rencontre à sceller au nom du scoreur.

    Seules les rencontres **validées** entrent au classement de la poule — un tir en cours de saisie
    ferait bouger le classement à chaque flèche, et le barrage requis apparaîtrait puis
    disparaîtrait sous les yeux du juge.
    """

    tournoi_id: int
    phase_id: int
    numero: int
    identifiant_saisie: str | None = None


def _en_etat_duel(rencontre: RencontreAffichee) -> EtatDuel:
    """Projette une rencontre dans la forme que `DuelReponse` sait sérialiser.

    ⚠️ **Adaptation de frontière, pas une conversion métier.** `EtatDuel` porte deux champs qu'une
    poule n'a pas : `place_en_jeu` (une rencontre ne décerne aucune place — c'est le classement de
    poule qui le fait) et `est_bye` (le cercle met au repos, il n'exempte personne). Le `libelle`
    dit le tour du groupe, pas un nom d'arbre — « Quart de finale » n'a aucun sens ici.

    On réutilise le DTO parce que le **pavé** est le même (ADR-0083 §7) ; en écrire un second, à
    trois champs près, obligerait le front à écrire un second écran de saisie, ce que toute cette
    tranche s'applique à éviter.
    """
    return EtatDuel(
        numero=rencontre.numero,
        tour=rencontre.tour,
        place_en_jeu=None,
        haut=rencontre.haut,
        bas=rencontre.bas,
        est_bye=False,
        duel=rencontre.duel,
        bareme=rencontre.bareme,
        zones=rencontre.zones,
        libelle=f"Tour {rencontre.tour}",
    )


def _exiger_meme_tournoi(scoreur: Scoreur, tournoi_id: int) -> None:
    """Refuse (`403 scoreur_hors_tournoi`) un scoreur agissant hors de **son** tournoi."""
    if scoreur.tournoi_id != tournoi_id:
        raise ScoreurHorsTournoi("Ce scoreur n'officie pas dans ce tournoi.")


def _cle_idempotence(operation: str, identifiant: str | None, *portee: int) -> str | None:
    """Clé d'idempotence **scopée** (opération + cible), ou `None` sans identifiant (ADR-0036)."""
    if not identifiant:
        return None
    return ":".join((operation, identifiant, *(str(p) for p in portee)))


# --- Lecture ---


@router.get("/repartition/{tournoi_id}/{phase_id}", response_model=RepartitionReponse)
async def lire_repartition(tournoi_id: int, phase_id: int, request: Request) -> RepartitionReponse:
    """Ce que le réglage produit sur l'effectif réel, **sans rien poser ni écrire**.

    Volontairement séparé de l'état : montrer la répartition ne doit exiger ni gabarit de salle, ni
    plan posé, ni le moindre tir — sans quoi l'organisateur ne pourrait pas régler ses poules avant
    d'avoir fait sa salle. Lecture ouverte, comme les autres consultations (E10US001).

    `404` si le tournoi ou la phase est inconnu, `409 phase_pas_des_poules` sur un autre type,
    `409 phase_pas_reglee` tant que la taille de poule n'est pas fixée.
    """
    service: ServicePoules = request.app.state.service_poules
    repartition = await run_in_threadpool(service.repartition, tournoi_id, phase_id)
    return RepartitionReponse.de_repartition(repartition)


@router.get("/etat/{tournoi_id}/{phase_id}", response_model=EtatPoulesReponse)
async def lire_etat(tournoi_id: int, phase_id: int, request: Request) -> EtatPoulesReponse:
    """La photo complète : composition, plan posé, rencontres tirées, classements, barrages requis.

    Lecture ouverte : c'est aussi ce que l'écran de salle et le public affichent.
    """
    service: ServicePoules = request.app.state.service_poules
    etat = await run_in_threadpool(service.etat, tournoi_id, phase_id)
    return EtatPoulesReponse.de_etat(etat)


# --- Écriture du plan (admin, via la file) ---


@router.post(
    "/plan/{tournoi_id}/{phase_id}/regenerer",
    response_model=EtatPoulesReponse,
    dependencies=[Depends(exiger_admin)],
)
async def regenerer_plan(tournoi_id: int, phase_id: int, request: Request) -> EtatPoulesReponse:
    """Pose les poules sur la salle et **remplace** le plan existant (**action admin**).

    Le geste est volontairement grossier — on repose tout — parce que l'unité déplaçable est la
    **poule** et que la contiguïté de son bloc est l'invariant du format. `404
    gabarit_du_tournoi_absent` si aucune salle n'est appliquée au tournoi.
    """
    service: ServicePoules = request.app.state.service_poules
    write_queue: WriteQueue = request.app.state.write_queue
    etat = await asyncio.wrap_future(
        write_queue.submit(lambda: service.regenerer_plan(tournoi_id, phase_id))
    )
    return EtatPoulesReponse.de_etat(etat)


# --- Saisie d'une rencontre (scoreur, via la file) ---


@router.post("/manches", response_model=RencontreReponse)
async def saisir_manche(
    requete: SaisirMancheRequete,
    request: Request,
    scoreur: Annotated[Scoreur, Depends(exiger_scoreur)],
) -> RencontreReponse:
    """Saisit (ou réédite) une manche d'une rencontre. Scoreur ; via la **file**, dédoublonnée."""
    service: ServicePoules = request.app.state.service_poules
    write_queue: WriteQueue = request.app.state.write_queue
    registre: RegistreIdempotence = request.app.state.registre_idempotence
    _exiger_meme_tournoi(scoreur, requete.tournoi_id)
    valeurs_haut = tuple(requete.valeurs_haut)
    valeurs_bas = tuple(requete.valeurs_bas)
    cle = _cle_idempotence(
        "manche_poule",
        requete.identifiant_saisie,
        requete.tournoi_id,
        requete.phase_id,
        requete.numero,
        requete.manche,
    )

    def ecrire() -> RencontreAffichee:
        return service.saisir_manche(
            requete.tournoi_id,
            requete.phase_id,
            requete.numero,
            requete.manche,
            valeurs_haut,
            valeurs_bas,
        )

    rencontre = await asyncio.wrap_future(
        write_queue.submit(lambda: registre.executer(cle, ecrire))
    )
    return RencontreReponse.de_rencontre(rencontre)


@router.post("/barrages", response_model=RencontreReponse)
async def saisir_barrage(
    requete: SaisirBarrageRequete,
    request: Request,
    scoreur: Annotated[Scoreur, Depends(exiger_scoreur)],
) -> RencontreReponse:
    """Saisit le tir de barrage d'une rencontre nulle (§8.2). Scoreur ; via la **file**."""
    service: ServicePoules = request.app.state.service_poules
    write_queue: WriteQueue = request.app.state.write_queue
    registre: RegistreIdempotence = request.app.state.registre_idempotence
    _exiger_meme_tournoi(scoreur, requete.tournoi_id)
    fleche_haut = requete.fleche_haut
    fleche_bas = requete.fleche_bas
    designe = requete.gagnant_designe
    cle = _cle_idempotence(
        "barrage_poule",
        requete.identifiant_saisie,
        requete.tournoi_id,
        requete.phase_id,
        requete.numero,
    )

    def ecrire() -> RencontreAffichee:
        return service.saisir_barrage(
            requete.tournoi_id,
            requete.phase_id,
            requete.numero,
            fleche_haut,
            fleche_bas,
            designe,
        )

    rencontre = await asyncio.wrap_future(
        write_queue.submit(lambda: registre.executer(cle, ecrire))
    )
    return RencontreReponse.de_rencontre(rencontre)


@router.post("/validations", response_model=RencontreReponse)
async def valider_rencontre(
    requete: ValiderRencontreRequete,
    request: Request,
    scoreur: Annotated[Scoreur, Depends(exiger_scoreur)],
) -> RencontreReponse:
    """Valide une rencontre tranchée : c'est elle qui entrera au classement de la poule.

    Scoreur borné à **son** tournoi (`403` sinon). `422 duel_incomplet` si le vainqueur n'est pas
    connu. Via la **file**, dédoublonnée par identifiant (ADR-0036).
    """
    service: ServicePoules = request.app.state.service_poules
    write_queue: WriteQueue = request.app.state.write_queue
    registre: RegistreIdempotence = request.app.state.registre_idempotence
    _exiger_meme_tournoi(scoreur, requete.tournoi_id)
    cle = _cle_idempotence(
        "validation_poule",
        requete.identifiant_saisie,
        requete.tournoi_id,
        requete.phase_id,
        requete.numero,
    )

    def ecrire() -> RencontreAffichee:
        return service.valider(requete.tournoi_id, requete.phase_id, requete.numero, scoreur.nom)

    rencontre = await asyncio.wrap_future(
        write_queue.submit(lambda: registre.executer(cle, ecrire))
    )
    return RencontreReponse.de_rencontre(rencontre)
