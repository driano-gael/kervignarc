"""Endpoints REST du **système suisse** (E05US026, [ADR-0083]) — régler, puis faire tirer.

Expose `ServiceSuisse` sur deux surfaces qui n'ont ni le même public ni les mêmes droits :

- **la salle et le public** lisent l'**état** de la phase — rondes appariées, rencontres, porteur de
  bye, classement — ainsi que la **borne** de rondes que l'effectif du jour autorise ;
- **le scoreur** saisit les rencontres avec le pavé de duel d'E04US013.

⚠️ **Une rencontre de ronde *est* un duel ordinaire** (ADR-0083 §7), et ce routeur le montre : les
trois écritures de tir sont les jumelles de celles de `api/v1/poules.py` et de
`api/v1/saisie_duels.py`, et écrivent dans la même table `duel`. Ce qui diffère est la
**navigation** — on entre par la **ronde**, pas par la poule ni par le numéro de match d'un arbre.
C'est le `decor` du contrat (`RONDES_APPARIEES`), et c'est tout ce que la duplication porte.

`numero` est le `match_numero` de la table `duel`, **dérivé** du rejeu et jamais stocké : rondes
dans l'ordre, rencontres dans l'ordre de l'appariement, numérotation continue depuis 1 sur toute
la phase. Un tir dont les duellistes ne correspondent plus à l'appariement recalculé s'affiche « non
tiré » plutôt que d'être ré-attribué (ADR-0049 §4) — la rencontre rend alors un pavé **vierge** et
lève `desynchronisee`, plutôt que de prêter un score au mauvais couple.

⚠️ **Il n'y a pas de route « ronde suivante »**, et c'est structurel : les rondes ne se déclenchent
pas, elles se **déduisent**. La ronde `n+1` apparaît dans l'état dès que la ronde `n` est close,
c'est-à-dire dès que sa dernière rencontre est validée. Exposer un geste « apparier la ronde
suivante » aurait laissé croire à une décision d'organisateur là où il n'y a qu'une conséquence.

Écritures routées par la **file** (writer unique, ADR-0005) et dédoublonnées par identifiant de
saisie (ADR-0036), comme les deux autres décors.

[ADR-0083]: ../../../docs/adr/0083-le-contrat-de-phase-jouable.md
"""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_scoreur
from api.v1.saisie_duels import DuellisteReponse, DuelReponse
from application.erreurs import ScoreurHorsTournoi
from application.saisie_duels import EtatDuel
from application.suisse import EtatSuisse, RencontreDeRonde, RondeAffichee, ServiceSuisse
from domain.blason import ZoneScore
from domain.duel import Cote
from domain.scoreur import Scoreur
from infrastructure.db import WriteQueue
from infrastructure.idempotence import RegistreIdempotence

router = APIRouter(prefix="/api/v1/suisse", tags=["suisse"])


# --- DTO ---


class RencontreReponse(BaseModel):
    """Une rencontre d'une ronde : son numéro, sa ronde, ses duellistes et son tir."""

    numero: int
    ronde: int
    haut: DuellisteReponse | None
    bas: DuellisteReponse | None
    duel: DuelReponse
    """Le pavé **et** le tir : `DuelReponse` dimensionne l'écran de saisie même sans flèche tirée
    (mode, barème, zones du blason), exactement comme pour un duel de tableau ou de poule."""

    desynchronisee: bool
    """Un tir existe mais oppose d'autres duellistes : il est **masqué**, jamais ré-attribué.

    L'écran doit le **dire** — sans ce drapeau la rencontre s'afficherait « à tirer », indiscernable
    d'une rencontre jamais commencée, et le scoreur se prendrait un 409 sur un écran qui l'invitait
    à saisir (leçon de la revue d'E05US023).
    """

    @staticmethod
    def de_rencontre(rencontre: RencontreDeRonde) -> RencontreReponse:
        return RencontreReponse(
            numero=rencontre.numero,
            ronde=rencontre.ronde,
            haut=None if rencontre.haut is None else DuellisteReponse.de_duelliste(rencontre.haut),
            bas=None if rencontre.bas is None else DuellisteReponse.de_duelliste(rencontre.bas),
            duel=DuelReponse.de_etat(_en_etat_duel(rencontre)),
            desynchronisee=rencontre.desynchronisee,
        )


class RondeReponse(BaseModel):
    """Une ronde : ses rencontres, son porteur de bye, et si elle est close.

    `close` est ce dont l'écran a besoin pour savoir si la ronde suivante peut exister — et c'est
    aussi ce qui empêche le moteur de l'apparier. Une ronde ouverte n'est pas une anomalie : c'est
    le régime normal d'une ronde en cours de saisie.
    """

    numero: int
    rencontres: list[RencontreReponse]
    bye: DuellisteReponse | None
    close: bool

    @staticmethod
    def de_ronde(ronde: RondeAffichee) -> RondeReponse:
        return RondeReponse(
            numero=ronde.numero,
            rencontres=[RencontreReponse.de_rencontre(r) for r in ronde.rencontres],
            bye=None if ronde.bye is None else DuellisteReponse.de_duelliste(ronde.bye),
            close=ronde.close,
        )


class RangSuisseReponse(BaseModel):
    """Une ligne du classement : rang **sportif**, points, Buchholz, ex æquo.

    ⚠️ Le rang suit la convention **« 1224 »** — deux ex æquo au rang 2 laissent le rang 3 vacant.
    C'est le rang qu'on affiche ; la *position* dans le classement de phase, elle, est ce que le
    prélèvement lit, et les deux ne coïncident pas (cf. `domain/classement_de_suisse.py`).
    """

    rang: int
    archer_id: int
    points: int
    """En **demi-points doublés** : une victoire vaut 2, un nul 1. Le domaine évite le flottant,
    dont les comparaisons d'égalité sont exactement ce sur quoi un départage ne doit pas reposer."""

    buchholz: int
    ex_aequo: bool


class EtatSuisseReponse(BaseModel):
    """L'état d'une phase de suisse : son réglage, sa borne, ses rondes, son classement."""

    phase_id: int
    nb_rondes: int
    rondes_maximales: int
    """Le maximum appariable **sans ré-affrontement** sur l'effectif du jour (CA).

    Rendu par le service et non recalculé à l'écran : deux arithmétiques pour une même règle sont
    une divergence en attente — la leçon des dix filtres d'ADR-0083.
    """

    effectif: int
    rondes: list[RondeReponse]
    classement: list[RangSuisseReponse]

    @staticmethod
    def de_etat(etat: EtatSuisse) -> EtatSuisseReponse:
        return EtatSuisseReponse(
            phase_id=etat.phase_id,
            nb_rondes=etat.nb_rondes,
            rondes_maximales=etat.rondes_maximales,
            effectif=etat.effectif,
            rondes=[RondeReponse.de_ronde(ronde) for ronde in etat.rondes],
            classement=[
                RangSuisseReponse(
                    rang=ligne.rang,
                    archer_id=ligne.participant.ref_id,
                    points=ligne.points,
                    buchholz=ligne.buchholz,
                    ex_aequo=ligne.ex_aequo,
                )
                for ligne in etat.classement
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
    """Corps du barrage **interne** à une rencontre nulle (§8.2, E04US013).

    ⚠️ **Offert, mais pas exigé — et c'est propre au suisse.** Un nul est ici un résultat légitime :
    le barème du format le prévoit, là où une poule ou un tableau doivent toujours désigner un
    vainqueur. Ne pas tirer le barrage laisse la rencontre à 1-1, ce qui est une réponse.
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

    ⚠️ **C'est le geste qui clôt une ronde**, donc celui qui fait exister la suivante. Un tir non
    validé laisse la ronde ouverte et le moteur refuse d'apparier par-dessus — sinon l'appariement
    changerait sous les yeux du juge à chaque flèche.
    """

    tournoi_id: int
    phase_id: int
    numero: int
    identifiant_saisie: str | None = None


def _en_etat_duel(rencontre: RencontreDeRonde) -> EtatDuel:
    """Projette une rencontre dans la forme que `DuelReponse` sait sérialiser.

    ⚠️ **Adaptation de frontière, pas une conversion métier.** Même parti que `api/v1/poules.py` :
    `EtatDuel` porte deux champs qu'une ronde n'a pas — `place_en_jeu` (une rencontre de ronde ne
    décerne aucune place, c'est le classement qui le fait) et `est_bye` (le bye d'un suisse est
    porté par la **ronde**, pas par une rencontre : personne n'y est opposé à personne).

    On réutilise le DTO parce que le **pavé** est le même (ADR-0083 §7) ; en écrire un second, à
    trois champs près, obligerait le front à écrire un troisième écran de saisie — ce que toute
    cette série de tranches s'applique à éviter.
    """
    return EtatDuel(
        numero=rencontre.numero,
        tour=rencontre.ronde,
        place_en_jeu=None,
        haut=rencontre.haut,
        bas=rencontre.bas,
        est_bye=False,
        duel=rencontre.duel,
        bareme=rencontre.bareme,
        zones=rencontre.zones,
        libelle=f"Ronde {rencontre.ronde}",
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


@router.get("/etat/{tournoi_id}/{phase_id}", response_model=EtatSuisseReponse)
async def lire_etat(tournoi_id: int, phase_id: int, request: Request) -> EtatSuisseReponse:
    """L'état complet d'une phase de suisse. Lecture **ouverte** (E10US001).

    `# DETTE-031` — recomposée intégralement à chaque appel, chaîne de sources amont comprise.
    """
    service: ServiceSuisse = request.app.state.service_suisse
    etat = await run_in_threadpool(service.etat, tournoi_id, phase_id)
    return EtatSuisseReponse.de_etat(etat)


# --- Saisie d'une rencontre (scoreur, via la file) ---


@router.post("/manches", response_model=RencontreReponse)
async def saisir_manche(
    requete: SaisirMancheRequete,
    request: Request,
    scoreur: Annotated[Scoreur, Depends(exiger_scoreur)],
) -> RencontreReponse:
    """Saisit (ou réédite) une manche d'une rencontre. Scoreur ; via la **file**, dédoublonnée."""
    service: ServiceSuisse = request.app.state.service_suisse
    write_queue: WriteQueue = request.app.state.write_queue
    registre: RegistreIdempotence = request.app.state.registre_idempotence
    _exiger_meme_tournoi(scoreur, requete.tournoi_id)
    valeurs_haut = tuple(requete.valeurs_haut)
    valeurs_bas = tuple(requete.valeurs_bas)
    cle = _cle_idempotence(
        "manche_suisse",
        requete.identifiant_saisie,
        requete.tournoi_id,
        requete.phase_id,
        requete.numero,
        requete.manche,
    )

    def ecrire() -> RencontreDeRonde:
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
    service: ServiceSuisse = request.app.state.service_suisse
    write_queue: WriteQueue = request.app.state.write_queue
    registre: RegistreIdempotence = request.app.state.registre_idempotence
    _exiger_meme_tournoi(scoreur, requete.tournoi_id)
    fleche_haut = requete.fleche_haut
    fleche_bas = requete.fleche_bas
    gagnant = requete.gagnant_designe
    cle = _cle_idempotence(
        "barrage_suisse",
        requete.identifiant_saisie,
        requete.tournoi_id,
        requete.phase_id,
        requete.numero,
    )

    def ecrire() -> RencontreDeRonde:
        return service.saisir_barrage(
            requete.tournoi_id,
            requete.phase_id,
            requete.numero,
            fleche_haut,
            fleche_bas,
            gagnant,
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
    """Valide une rencontre — c'est elle qui entrera au classement, et qui clôt la ronde."""
    service: ServiceSuisse = request.app.state.service_suisse
    write_queue: WriteQueue = request.app.state.write_queue
    registre: RegistreIdempotence = request.app.state.registre_idempotence
    _exiger_meme_tournoi(scoreur, requete.tournoi_id)
    cle = _cle_idempotence(
        "validation_suisse",
        requete.identifiant_saisie,
        requete.tournoi_id,
        requete.phase_id,
        requete.numero,
    )

    def ecrire() -> RencontreDeRonde:
        return service.valider(requete.tournoi_id, requete.phase_id, requete.numero, scoreur.nom)

    rencontre = await asyncio.wrap_future(
        write_queue.submit(lambda: registre.executer(cle, ecrire))
    )
    return RencontreReponse.de_rencontre(rencontre)
