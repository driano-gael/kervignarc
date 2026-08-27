"""Routeur **colline** — un défi *est* un duel ordinaire ; seule la navigation diffère (ADR-0083).
`numero` est **dérivé** du rejeu, jamais stocké ; un tir dont les duellistes ne correspondent plus
s'affiche « non tiré » plutôt que d'être ré-attribué (ADR-0049 §4).

⚠️ **Il n'y a pas de route « manche suivante », et c'est structurel** : les défis de la manche `n+1`
se calculent sur les positions issues de `n`. Tant qu'un défi n'est pas tranché, ces positions
n'existent pas — un tel geste permettrait de demander un appariement **faux**.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin, exiger_scoreur
from api.v1.saisie_duels import DuellisteReponse, DuelReponse
from application.colline import (
    DefiDeLaManche,
    EtatColline,
    MancheAffichee,
    ServiceColline,
)
from application.erreurs import ScoreurHorsTournoi
from application.saisie_duels import Duelliste, EtatDuel
from domain.blason import ZoneScore
from domain.duel import Cote
from domain.scoreur import Scoreur
from infrastructure.db import WriteQueue
from infrastructure.idempotence import RegistreIdempotence

router = APIRouter(prefix="/api/v1/colline", tags=["colline"])


# --- DTO ---


def _couloirs(
    places: tuple[tuple[int, str], tuple[int, str]] | None,
) -> list[list[int | str]] | None:
    """Sérialise un couple de couloirs en `[[cible, lettre], …]`, ou `null` si rien n'est posé."""
    if places is None:
        return None
    return [[cible, lettre] for cible, lettre in places]


def _au_repos(duellistes: tuple[Duelliste, ...]) -> list[DuellisteReponse]:
    """Sérialise les archers **au repos** d'une manche.

    ⚠️ **`DuellisteReponse.de_duelliste` ne convient pas ici**, et l'écart est significatif plutôt
    qu'ennuyeux : cette fabrique accepte `None` et le propage, parce que les deux camps d'un duel
    peuvent légitimement être vides (un bye de tableau n'oppose personne). Un archer au repos, lui,
    est toujours **quelqu'un** — c'est un tireur nommé qui ne tire pas de cette manche. Passer par
    la fabrique optionnelle produirait un `DuellisteReponse | None` que le typage strict refuse, et
    surtout laisserait croire à l'écran qu'un repos peut être anonyme.
    """
    return [DuellisteReponse(archer_id=d.archer_id, nom=d.nom, prenom=d.prenom) for d in duellistes]


class ConflitReponse(BaseModel):
    """Ce que la pose du plan n'a pas pu faire, et pourquoi — rapporté, jamais tu (ADR-0024)."""

    groupe: int
    raison: str


class DefiReponse(BaseModel):
    """Un défi d'une manche : son numéro, sa manche, ses positions, ses duellistes et son tir."""

    numero: int
    manche: int
    position_haute: int
    """La position du **défié** dans la colline, 1-indexée — « le n°4 ».

    Rendue parce que c'est l'information que le format rend lisible : un spectateur suit des
    **positions** qui montent et descendent, pas des numéros de match. L'écran l'affiche telle
    quelle (« le 6 défie le 4 »)."""

    position_basse: int
    """La position du **challenger**, 1-indexée — toujours strictement supérieure à la haute."""

    haut: DuellisteReponse | None
    """Le **défié** — celui qui occupe la meilleure position, donc celui qui a quelque chose à
    perdre."""

    bas: DuellisteReponse | None
    """Le **challenger**, qui monte s'il l'emporte."""

    couloirs: list[list[int | str]] | None
    """Les deux couloirs `[[cible, lettre], [cible, lettre]]`, ou `null` si le plan n'est pas posé.

    Dérivés du bloc de la phase, jamais persistés : c'est le **bloc** qui l'est (ADR-0083 §3).
    Un plan non posé rend `null` plutôt qu'un couloir deviné — l'écran doit pouvoir dire
    « générez le plan » au lieu d'afficher une salle plausible et fausse."""

    duel: DuelReponse
    """Le pavé **et** le tir : `DuelReponse` dimensionne l'écran de saisie même sans flèche tirée
    (mode, barème, zones du blason), exactement comme pour un duel de tableau, de poule ou de
    ronde."""

    desynchronisee: bool
    """Un tir existe mais oppose d'autres duellistes : il est **masqué**, jamais ré-attribué.

    L'écran doit le **dire** — sans ce drapeau le défi s'afficherait « à tirer », indiscernable
    d'un défi jamais commencé, et le scoreur se prendrait un 409 sur un écran qui l'invitait
    à saisir (leçon de la revue d'E05US023).
    """

    @staticmethod
    def de_defi(defi: DefiDeLaManche) -> DefiReponse:
        return DefiReponse(
            numero=defi.numero,
            manche=defi.manche,
            position_haute=defi.position_haute,
            position_basse=defi.position_basse,
            haut=None if defi.haut is None else DuellisteReponse.de_duelliste(defi.haut),
            bas=None if defi.bas is None else DuellisteReponse.de_duelliste(defi.bas),
            couloirs=_couloirs(defi.couloirs),
            duel=DuelReponse.de_etat(_en_etat_duel(defi)),
            desynchronisee=defi.desynchronisee,
        )


class DefiPubliqueReponse(BaseModel):
    """Le **même** défi, vu de qui n'a pas à saisir — écran de salle, public, écran admin.

    ⚠️ **C'est ici que vit la restriction de contenu (règle 6)**, et ce DTO n'est pas une précaution
    théorique : le routeur du suisse a dû l'ajouter **en correctif de revue**, après l'avoir recopié
    d'`api/v1/poules.py` sans la leçon qu'il portait — la forme complète, servie sur une route
    anonyme, expose chaque flèche de chaque volée, le barrage, les zones et le barème du pavé, et le
    **nom du bénévole qui a validé**. Rien de cela n'a de raison d'être lu hors de la saisie.

    Comme là-bas, un DTO **distinct** et non un `exclude` : un champ ajouté au DTO du scoreur
    n'apparaît pas ici par défaut, alors qu'une liste d'exclusions aurait laissé passer le suivant.
    """

    numero: int
    manche: int
    position_haute: int
    position_basse: int
    couloirs: list[list[int | str]] | None
    haut: DuellisteReponse | None
    bas: DuellisteReponse | None
    points_haut: int | None
    points_bas: int | None
    vainqueur: str | None
    termine: bool
    validee: bool
    desynchronisee: bool
    """Cf. `DefiReponse.desynchronisee`. Servi au public aussi : un écran de salle qui afficherait
    « à tirer » sur un défi bloqué ferait attendre des archers pour rien."""

    @staticmethod
    def de_defi(defi: DefiDeLaManche) -> DefiPubliqueReponse:
        duel = defi.duel
        issue = None if duel is None else duel.resultat
        return DefiPubliqueReponse(
            numero=defi.numero,
            manche=defi.manche,
            position_haute=defi.position_haute,
            position_basse=defi.position_basse,
            couloirs=_couloirs(defi.couloirs),
            haut=None if defi.haut is None else DuellisteReponse.de_duelliste(defi.haut),
            bas=None if defi.bas is None else DuellisteReponse.de_duelliste(defi.bas),
            points_haut=None if issue is None else issue.points_haut,
            points_bas=None if issue is None else issue.points_bas,
            vainqueur=None if issue is None or issue.vainqueur is None else issue.vainqueur.value,
            termine=duel is not None and issue is not None and issue.vainqueur is not None,
            validee=duel is not None and duel.verrouille,
            desynchronisee=defi.desynchronisee,
        )


class ManchePubliqueReponse(BaseModel):
    """Une manche, vue du public : ses défis rédigés, ses archers au repos, si elle est close."""

    numero: int
    defis: list[DefiPubliqueReponse]
    au_repos: list[DuellisteReponse]
    close: bool

    @staticmethod
    def de_manche(manche: MancheAffichee) -> ManchePubliqueReponse:
        return ManchePubliqueReponse(
            numero=manche.numero,
            defis=[DefiPubliqueReponse.de_defi(defi) for defi in manche.defis],
            au_repos=_au_repos(manche.au_repos),
            close=manche.close,
        )


class MancheReponse(BaseModel):
    """Une manche : ses défis, ses archers au repos, et si elle est close.

    `close` est ce dont l'écran a besoin pour savoir si la manche suivante peut exister — et c'est
    aussi ce qui autorise le moteur à l'apparier. Une manche ouverte n'est pas une anomalie : c'est
    le régime normal d'une manche en cours de saisie.

    ⚠️ **`au_repos` n'est pas décoratif.** À portée 1 les deux extrémités de la colline ne tirent
    pas de la manche, et l'écran doit pouvoir le **dire** — sinon ces archers disparaissent de la
    manche sans explication, et le scoreur les cherche.
    """

    numero: int
    defis: list[DefiReponse]
    au_repos: list[DuellisteReponse]
    close: bool

    @staticmethod
    def de_manche(manche: MancheAffichee) -> MancheReponse:
        return MancheReponse(
            numero=manche.numero,
            defis=[DefiReponse.de_defi(defi) for defi in manche.defis],
            au_repos=_au_repos(manche.au_repos),
            close=manche.close,
        )


class RangCollineReponse(BaseModel):
    """Une position de la colline — le classement, qui **est** l'état courant du format.

    ⚠️ **Pas de convention « 1224 » ici, et pas d'ex æquo**, à la différence du suisse : deux
    archers n'occupent jamais la même position. La position affichée et la position que le
    prélèvement lit coïncident donc — c'est ce qui rend `domain/classement_de_colline.py` le plus
    court des quatre classements de phase.
    """

    position: int
    archer_id: int


class EtatCollineReponse(BaseModel):
    """L'état d'une phase de colline : son réglage, sa borne, ses manches, son ordre."""

    phase_id: int
    nb_manches: int
    portee_de_defi: int
    """Ce que l'organisateur a **réglé** : 1 = King of the Hill, 2+ = Ladder."""

    portee_maximale: int
    """La portée la plus grande que l'effectif du jour autorise (`effectif - 1`).

    Rendue par le service et non recalculée à l'écran : deux arithmétiques pour une même règle sont
    une divergence en attente — la leçon des dix filtres d'ADR-0083. Les deux nombres coexistent
    pour que l'atelier **montre** l'écart au lieu de le subir : au-delà de la borne, le service
    borne à la lecture plutôt que de refuser d'ouvrir l'écran.
    """

    effectif: int
    manches: list[MancheReponse]
    classement: list[RangCollineReponse]
    conflits: list[ConflitReponse]

    @staticmethod
    def de_etat(etat: EtatColline) -> EtatCollineReponse:
        return EtatCollineReponse(
            phase_id=etat.phase_id,
            nb_manches=etat.nb_manches,
            portee_de_defi=etat.portee_de_defi,
            portee_maximale=etat.portee_maximale,
            effectif=etat.effectif,
            manches=[MancheReponse.de_manche(manche) for manche in etat.manches],
            classement=[
                RangCollineReponse(position=rang.position, archer_id=rang.duelliste.archer_id)
                for rang in etat.classement
            ],
            conflits=[
                ConflitReponse(groupe=c.groupe, raison=c.raison.value) for c in etat.conflits
            ],
        )


class EtatCollinePubliqueReponse(BaseModel):
    """L'état d'une phase, **rédigé** — la forme servie aux surfaces ouvertes.

    Mêmes champs de cadrage que la forme complète (réglage, borne, effectif, conflits de pose) ;
    seuls les **défis** sont réduits. C'est le contenu du tir qui est protégé, pas la structure de
    la phase, que l'écran de salle doit précisément montrer.
    """

    phase_id: int
    nb_manches: int
    portee_de_defi: int
    portee_maximale: int
    effectif: int
    manches: list[ManchePubliqueReponse]
    classement: list[RangCollineReponse]
    conflits: list[ConflitReponse]

    @staticmethod
    def de_etat(etat: EtatColline) -> EtatCollinePubliqueReponse:
        return EtatCollinePubliqueReponse(
            phase_id=etat.phase_id,
            nb_manches=etat.nb_manches,
            portee_de_defi=etat.portee_de_defi,
            portee_maximale=etat.portee_maximale,
            effectif=etat.effectif,
            manches=[ManchePubliqueReponse.de_manche(manche) for manche in etat.manches],
            classement=[
                RangCollineReponse(position=rang.position, archer_id=rang.duelliste.archer_id)
                for rang in etat.classement
            ],
            conflits=[
                ConflitReponse(groupe=c.groupe, raison=c.raison.value) for c in etat.conflits
            ],
        )


class SaisirMancheRequete(BaseModel):
    """Corps de la saisie d'une manche de duel : les deux volées opposées.

    ⚠️ **`manche` est la manche du DUEL** (le set FFTA), pas la manche de la colline. L'homonymie
    est réelle et assumée : le champ porte le même nom que dans les trois autres routeurs de tir,
    parce que c'est le même agrégat `Duel` qui le reçoit. La manche de la colline, elle, se lit sur
    `DefiReponse.manche` et ne se saisit jamais — elle se déduit.
    """

    tournoi_id: int
    phase_id: int
    numero: int
    manche: int
    valeurs_haut: list[ZoneScore]
    valeurs_bas: list[ZoneScore]
    identifiant_saisie: str | None = None


class SaisirBarrageRequete(BaseModel):
    """Corps du barrage **interne** à un défi nul (§8.2, E04US013).

    ⚠️ **Exigé pour valider**, et ici plus strictement qu'ailleurs : `Duel.valider` refuse déjà un
    duel non tranché dans les quatre formats, mais un défi de colline décide d'un **échange de
    positions** — `appliquer_manche` exige un vainqueur qui soit l'un des deux engagés. Un nul n'a
    aucune traduction dans ce format : il n'existe pas d'état « les deux restent où ils sont » qui
    soit distinct de « le défié a gagné ».
    """

    tournoi_id: int
    phase_id: int
    numero: int
    fleche_haut: ZoneScore
    fleche_bas: ZoneScore
    gagnant_designe: Cote | None = None
    identifiant_saisie: str | None = None


class ValiderDefiRequete(BaseModel):
    """Corps de la validation : le défi à sceller au nom du scoreur.

    ⚠️ **C'est le geste qui fait bouger les positions**, donc celui qui clôt une manche et fait
    exister la suivante. Un tir non validé laisse la manche ouverte et la colline inchangée — sinon
    l'appariement changerait sous les yeux du juge à chaque flèche.
    """

    tournoi_id: int
    phase_id: int
    numero: int
    identifiant_saisie: str | None = None


def _en_etat_duel(defi: DefiDeLaManche) -> EtatDuel:
    """Projette un défi dans la forme que `DuelReponse` sait sérialiser.

    ⚠️ **Adaptation de frontière, pas une conversion métier.** Même parti que `api/v1/poules.py` et
    `api/v1/suisse.py` : `EtatDuel` porte deux champs qu'un défi n'a pas — `place_en_jeu` (un défi
    ne décerne aucune place, c'est la colline qui situe) et `est_bye` (une colline n'a **pas** de
    bye ; elle a des archers **au repos**, portés par la manche et opposés à personne).

    On réutilise le DTO parce que le **pavé** est le même (ADR-0083 §7) ; en écrire un second, à
    trois champs près, obligerait le front à écrire un quatrième écran de saisie — ce que toute
    cette série de tranches s'applique à éviter.
    """
    return EtatDuel(
        numero=defi.numero,
        tour=defi.manche,
        place_en_jeu=None,
        haut=defi.haut,
        bas=defi.bas,
        est_bye=False,
        duel=defi.duel,
        bareme=defi.bareme,
        zones=defi.zones,
        libelle=f"Manche {defi.manche}",
    )


def _exiger_meme_tournoi(scoreur: Scoreur, tournoi_id: int) -> None:
    # DETTE-065 : 7ᵉ copie verbatim de ce **garde d'autorisation**, et le commentaire du routeur du
    # suisse annonçait exactement ce cas (« un 7ᵉ routeur d'écriture qui l'oublierait ne ferait
    # rougir personne »). Résorption : `api/dependances.py`.
    """Refuse (`403 scoreur_hors_tournoi`) un scoreur agissant hors de **son** tournoi."""
    if scoreur.tournoi_id != tournoi_id:
        raise ScoreurHorsTournoi("Ce scoreur n'officie pas dans ce tournoi.")


def _cle_idempotence(operation: str, identifiant: str | None, *portee: int) -> str | None:
    """Clé d'idempotence **scopée** (opération + cible), ou `None` sans identifiant (ADR-0036)."""
    if not identifiant:
        return None
    return ":".join((operation, identifiant, *(str(p) for p in portee)))


# --- Lecture ---


@router.get("/etat/{tournoi_id}/{phase_id}", response_model=EtatCollinePubliqueReponse)
async def lire_etat(tournoi_id: int, phase_id: int, request: Request) -> EtatCollinePubliqueReponse:
    """L'état d'une phase de colline, **rédigé**. Lecture ouverte (E10US001).

    Rédigé **d'emblée** : le routeur du suisse a dû le corriger en revue pour avoir servi la forme
    complète — donc chaque flèche et le nom du bénévole validateur — sans authentification.

    `# DETTE-031` — recomposée intégralement à chaque appel, chaîne de sources amont comprise.
    """
    service: ServiceColline = request.app.state.service_colline
    etat = await run_in_threadpool(service.etat, tournoi_id, phase_id)
    return EtatCollinePubliqueReponse.de_etat(etat)


@router.get("/saisie/{tournoi_id}/{phase_id}", response_model=EtatCollineReponse)
async def lire_pour_saisie(
    tournoi_id: int,
    phase_id: int,
    request: Request,
    scoreur: Annotated[Scoreur, Depends(exiger_scoreur)],
) -> EtatCollineReponse:
    """L'état **complet** — pavé de saisie compris. Réservé au scoreur de **ce** tournoi.

    Jumelle de `GET /suisse/saisie/…`. C'est la seule surface où `DuelReponse` a lieu d'être servi.
    """
    service: ServiceColline = request.app.state.service_colline
    _exiger_meme_tournoi(scoreur, tournoi_id)
    etat = await run_in_threadpool(service.etat, tournoi_id, phase_id)
    return EtatCollineReponse.de_etat(etat)


@router.post(
    "/plan/{tournoi_id}/{phase_id}",
    response_model=EtatCollinePubliqueReponse,
    dependencies=[Depends(exiger_admin)],
)
async def regenerer_plan(
    tournoi_id: int, phase_id: int, request: Request
) -> EtatCollinePubliqueReponse:
    """Pose la phase sur la salle et **remplace** le plan. Admin ; via la **file**.

    Geste **non idempotent par nature** — il repose tout, comme `suisse/plan`, `poules/plan` et
    `plan-de-duels/regenerer`. Pas de clé de déduplication, donc : rejouer la pose est justement ce
    qu'on veut après un changement d'effectif.
    """
    service: ServiceColline = request.app.state.service_colline
    write_queue: WriteQueue = request.app.state.write_queue
    etat = await asyncio.wrap_future(
        write_queue.submit(lambda: service.regenerer_plan(tournoi_id, phase_id))
    )
    # Forme **rédigée** même pour l'admin : poser un plan n'est pas saisir, et l'écran d'atelier
    # n'a pas besoin du pavé. Même parti que `suisse/plan` et `poules/plan`.
    return EtatCollinePubliqueReponse.de_etat(etat)


# --- Saisie d'un défi (scoreur, via la file) ---


@router.post("/manches", response_model=DefiReponse)
async def saisir_manche(
    requete: SaisirMancheRequete,
    request: Request,
    scoreur: Annotated[Scoreur, Depends(exiger_scoreur)],
) -> DefiReponse:
    """Saisit (ou réédite) une manche d'un défi. Scoreur ; via la **file**, dédoublonnée."""
    service: ServiceColline = request.app.state.service_colline
    write_queue: WriteQueue = request.app.state.write_queue
    registre: RegistreIdempotence = request.app.state.registre_idempotence
    _exiger_meme_tournoi(scoreur, requete.tournoi_id)
    valeurs_haut = tuple(requete.valeurs_haut)
    valeurs_bas = tuple(requete.valeurs_bas)
    cle = _cle_idempotence(
        "manche_colline",
        requete.identifiant_saisie,
        requete.tournoi_id,
        requete.phase_id,
        requete.numero,
        requete.manche,
    )

    def ecrire() -> DefiDeLaManche:
        return service.saisir_manche(
            requete.tournoi_id,
            requete.phase_id,
            requete.numero,
            requete.manche,
            valeurs_haut,
            valeurs_bas,
        )

    defi = await asyncio.wrap_future(write_queue.submit(lambda: registre.executer(cle, ecrire)))
    return DefiReponse.de_defi(defi)


@router.post("/barrages", response_model=DefiReponse)
async def saisir_barrage(
    requete: SaisirBarrageRequete,
    request: Request,
    scoreur: Annotated[Scoreur, Depends(exiger_scoreur)],
) -> DefiReponse:
    """Saisit le tir de barrage d'un défi nul (§8.2). Scoreur ; via la **file**."""
    service: ServiceColline = request.app.state.service_colline
    write_queue: WriteQueue = request.app.state.write_queue
    registre: RegistreIdempotence = request.app.state.registre_idempotence
    _exiger_meme_tournoi(scoreur, requete.tournoi_id)
    fleche_haut = requete.fleche_haut
    fleche_bas = requete.fleche_bas
    gagnant = requete.gagnant_designe
    cle = _cle_idempotence(
        "barrage_colline",
        requete.identifiant_saisie,
        requete.tournoi_id,
        requete.phase_id,
        requete.numero,
    )

    def ecrire() -> DefiDeLaManche:
        return service.saisir_barrage(
            requete.tournoi_id,
            requete.phase_id,
            requete.numero,
            fleche_haut,
            fleche_bas,
            gagnant,
        )

    defi = await asyncio.wrap_future(write_queue.submit(lambda: registre.executer(cle, ecrire)))
    return DefiReponse.de_defi(defi)


@router.post("/validations", response_model=DefiReponse)
async def valider_defi(
    requete: ValiderDefiRequete,
    request: Request,
    scoreur: Annotated[Scoreur, Depends(exiger_scoreur)],
) -> DefiReponse:
    """Valide un défi — c'est lui qui fera monter le gagnant, et qui clôt la manche."""
    service: ServiceColline = request.app.state.service_colline
    write_queue: WriteQueue = request.app.state.write_queue
    registre: RegistreIdempotence = request.app.state.registre_idempotence
    _exiger_meme_tournoi(scoreur, requete.tournoi_id)
    cle = _cle_idempotence(
        "validation_colline",
        requete.identifiant_saisie,
        requete.tournoi_id,
        requete.phase_id,
        requete.numero,
    )

    def ecrire() -> DefiDeLaManche:
        return service.valider(requete.tournoi_id, requete.phase_id, requete.numero, scoreur.nom)

    defi = await asyncio.wrap_future(write_queue.submit(lambda: registre.executer(cle, ecrire)))
    return DefiReponse.de_defi(defi)
