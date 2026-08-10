"""Endpoints REST du **barrage de places décisives** (E06US003, ADR-0066).

Expose `ServiceBarrage` à l'organisateur : **annoncer** un barrage sur une égalité que la politique
`tiebreak` signale, **saisir** (ou corriger) ses manches, le **clore**. Écritures routées par la
**file** du writer unique (règle 7), derrière `exiger_admin` — annoncer un barrage change le
classement publié, c'est un acte d'organisation, pas de saisie de cible.

Les **égalités à départager** ne sont pas exposées ici : elles voyagent avec le classement
(`GET /tournois/{id}/classement`), qui est la seule surface qui sache les calculer. Un second
endpoint qui les recalculerait produirait une réponse qui dériverait de celle affichée à l'écran.

⚠️ **La distance au centre est en dixièmes de millimètre**, et son absence n'est **pas** un zéro :
c'est une mesure non faite, sur laquelle le moteur refuse de départager (il fait retirer). C'est le
cas le plus fréquent du jour J — le juge mesure la flèche litigieuse, rarement les deux.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, model_validator
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from application.barrages import ServiceBarrage
from domain.barrage import BarrageDePlaces, PorteeBarrage, ResultatBarrage
from domain.erreurs import ConfigurationBarrageInvalide
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["barrages"])


# --- DTO ---


class TirRequete(BaseModel):
    """Ce qu'un archer a réalisé au barrage.

    `score` **nul** signifie **absent au barrage annoncé** — issue réglementaire (B.6.5.2.4 :
    l'archer est déclaré perdant), et non « je ne l'ai pas encore saisi ». Une flèche pas encore
    notée ne s'envoie tout simplement pas.
    """

    archer_id: int
    score: int | None = Field(default=None, ge=0, le=10)
    distance_au_centre: int | None = Field(default=None, ge=0)


class MancheRequete(BaseModel):
    """Les tirs d'une manche. `manche` absent = la suivante ; fourni = la manche à **corriger**."""

    tirs: list[TirRequete] = Field(min_length=2, max_length=64)
    """Un barrage oppose **au moins deux** tireurs, et le groupe se retire **en entier**.

    `min_length=2` n'est pas décoratif : une liste vide effaçait la manche, et une liste d'un seul
    tir faisait « gagner » celui qui avait tiré, faute d'adversaire. Le plafond borne l'entrée
    cliente, comme `ConfigPhaseRequete.sources`.
    """

    manche: int | None = Field(default=None, ge=1)


class AnnonceRequete(BaseModel):
    """Ce qu'on fait tirer — **deux régimes** selon la portée (ADR-0066).

    - `qualification` (défaut) : `rang` suffit, et il est **obligatoire**. Les tireurs sont dérivés
      du classement, donc l'organisateur n'a rien à désigner — et ne le peut pas : seule une
      égalité **signalée** par la politique est annonçable.
    - `poule` / `big_shoot_off` : `archer_ids` est obligatoire, parce qu'aucun classement calculé
      n'existe où lire les ex æquo (DETTE-028). `phase_id` et `reference` (numéro de poule ou de
      manche) situent le barrage ; `rang` reste facultatif — un Big Shoot Off désigne un sortant,
      pas une place.
    """

    depart_id: int = Field(ge=1)
    """Le créneau où se tire ce barrage (E01US025, ADR-0075).

    **Obligatoire dans les deux régimes** : un barrage départage une place dans le classement d'un
    départ, et deux créneaux ont des classements distincts. Le déduire du tournoi n'est pas
    possible — c'est justement la confusion que l'ADR corrige.
    """

    rang: int | None = Field(default=None, ge=1)
    portee: PorteeBarrage = PorteeBarrage.QUALIFICATION
    archer_ids: list[int] = Field(default_factory=list, max_length=64)
    phase_id: int | None = None
    reference: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def _coherence_du_regime(self) -> AnnonceRequete:
        """Chaque régime n'accepte **que** ses champs.

        ⚠️ Sans cette garde, `phase_id`/`reference` étaient acceptés en **qualification** alors
        qu'ils y sont sans objet — et comme ils entrent dans la clé d'idempotence, deux `POST` au
        même rang avec des références différentes ouvraient **deux** barrages sur la même place.
        Leurs verdicts, contradictoires, passaient tous deux le filtre d'applicabilité (même
        ensemble de tireurs), et le dernier lu l'emportait **en silence**. L'UI ne le permettait
        pas ; l'API est le contrat.
        """
        # `""` et `None` désignent le même « endroit » : ne pas les normaliser laisserait ouvrir
        # deux barrages concurrents sur la même poule, aux mêmes tireurs et aux verdicts opposés.
        if self.reference is not None and self.reference.strip() == "":
            self.reference = None
        elif self.reference is not None:
            self.reference = self.reference.strip()
        if self.portee is PorteeBarrage.QUALIFICATION:
            if self.rang is None:
                raise ValueError(
                    "Un barrage de qualification départage une place : indiquez son rang."
                )
            if self.archer_ids or self.phase_id is not None or self.reference is not None:
                raise ValueError(
                    "En qualification, les tireurs sont dérivés du classement : ne fournissez ni "
                    "archer_ids, ni phase_id, ni reference."
                )
        elif not self.archer_ids:
            raise ValueError(
                "Hors qualification, aucun classement n'est calculé : désignez les archers à "
                "départager (archer_ids)."
            )
        # DETTE-055 — en portée `poule`, `phase_id` et `rang` restent **facultatifs au contrat**
        # alors qu'un barrage qui en manque ne referme plus rien depuis E05US023. Le formulaire les
        # exige, le serveur non : c'est exactement l'écart que le bloc ci-dessus reproche au régime
        # de qualification (« L'UI ne le permettait pas ; l'API est le contrat »). Les resserrer
        # invalide un comportement que les tests d'E06US003 documentent comme voulu — donc un
        # arbitrage, pas de la plomberie. Relevé en 2ᵉ passe de revue d'E05US023.
        return self


class TirReponse(BaseModel):
    archer_id: int
    score: int | None
    distance_au_centre: int | None


class BarrageReponse(BaseModel):
    """Un barrage et son état — y compris ce qu'il **reste** à faire tirer.

    `ordre` est le verdict quand le barrage a tout départagé, et **vide** sinon :
    `groupes_a_rejouer` nomme alors qui doit retirer, **par groupe**. Les deux sont exclusifs, et
    les groupes ne sont pas aplatis — un barrage à quatre dont deux à 10 et deux à 8 laisse *deux*
    égalités distinctes, qui se retirent séparément.
    """

    perime: bool = False
    """Ce barrage ne porte plus sur le groupe d'ex æquo actuellement constaté (E06US003).

    ⚠️ **Signalé, et non simplement refusé à l'annonce.** Une première version ne gardait que le
    chemin `annoncer` : le barrage déjà ouvert, lui, restait tirable, résoluble et **actable**. Le
    panneau affichait côte à côte « 2ᵉ place — A, B, C » et un formulaire ne contenant que A et B ;
    le geste naturel était de remplir celui qui était là. L'application répondait « Départagé »,
    acceptait la clôture — et le classement ne bougeait pas d'un rang, le verdict étant écarté,
    sans un mot d'explication.
    """

    incoherent: bool = False
    """L'agrégat en base ne se relit pas (correction partielle, écriture directe…).

    ⚠️ **Ce drapeau existe pour que le panneau ne meure jamais.** Le verdict se recalcule à chaque
    lecture ; s'il lève, une première version faisait tomber `GET /barrages` en 422 — donc *tous*
    les barrages du tournoi disparaissaient de l'écran, **avec** les boutons « Annuler » et
    « Corriger » qui seraient la réparation. Le filet posé sur le classement ne couvrait que le côté
    public. On dégrade donc ici aussi : le barrage reste listé, marqué incohérent, et actionnable.
    """

    id: int
    """Toujours renseigné : un barrage **rendu** par l'API est persisté.

    Typé non nullable pour que le contrat dise la vérité — le front s'appuyait déjà sur cette
    garantie (`clore.mutate(barrage.id)`) sans qu'elle soit exprimée.
    """

    depart_id: int
    portee: str
    rang_dispute: int | None
    reference: str | None
    participants: list[int]
    manches: list[list[TirReponse]]
    clos: bool
    est_resolu: bool
    ordre: list[int]
    groupes_a_rejouer: list[list[int]]

    @staticmethod
    def de_agregat(barrage: BarrageDePlaces, perime: bool = False) -> BarrageReponse:
        assert barrage.id is not None, "Un barrage rendu par le service est persisté."
        try:
            resultat = barrage.resultat()
            incoherent = False
        except ConfigurationBarrageInvalide:
            resultat = ResultatBarrage(groupes_a_rejouer=(barrage.participants,))
            incoherent = True
        return BarrageReponse(
            perime=perime,
            incoherent=incoherent,
            id=barrage.id,
            depart_id=barrage.depart_id,
            portee=barrage.portee.value,
            rang_dispute=barrage.rang_dispute,
            reference=barrage.reference,
            participants=[p.ref_id for p in barrage.participants],
            manches=[
                [
                    TirReponse(
                        archer_id=tir.participant.ref_id,
                        score=tir.score,
                        distance_au_centre=tir.distance_au_centre,
                    )
                    for tir in manche
                ]
                for manche in barrage.manches
            ],
            clos=barrage.clos,
            est_resolu=resultat.est_resolu,
            ordre=[p.ref_id for p in resultat.ordre],
            groupes_a_rejouer=[[p.ref_id for p in groupe] for groupe in resultat.groupes_a_rejouer],
        )


# --- routes ---


@router.get("/tournois/{tournoi_id}/barrages", response_model=list[BarrageReponse])
async def lister_barrages(tournoi_id: int, request: Request) -> list[BarrageReponse]:
    """Les barrages d'un tournoi, **clos compris** — ce sont eux qui portent les verdicts acquis."""
    service: ServiceBarrage = request.app.state.service_barrage
    affiches = await run_in_threadpool(service.lister, tournoi_id)
    return [BarrageReponse.de_agregat(a.barrage, perime=a.perime) for a in affiches]


@router.post(
    "/tournois/{tournoi_id}/barrages",
    response_model=BarrageReponse,
    status_code=201,
    dependencies=[Depends(exiger_admin)],
)
async def annoncer_barrage(
    tournoi_id: int, requete: AnnonceRequete, request: Request
) -> BarrageReponse:
    """Annonce un barrage sur l'égalité signalée à ce rang (**idempotent** : rend celui en cours).

    409 `egalite_non_departageable` si plus rien n'est à départager à ce rang — le classement a pu
    bouger entre l'affichage et le clic.
    """
    service: ServiceBarrage = request.app.state.service_barrage
    write_queue: WriteQueue = request.app.state.write_queue
    barrage = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.annoncer(
                tournoi_id,
                requete.depart_id,
                rang=requete.rang,
                portee=requete.portee,
                archer_ids=requete.archer_ids,
                phase_id=requete.phase_id,
                reference=requete.reference,
            )
        )
    )
    return BarrageReponse.de_agregat(barrage)


@router.put(
    "/tournois/{tournoi_id}/barrages/{barrage_id}/manche",
    response_model=BarrageReponse,
    dependencies=[Depends(exiger_admin)],
)
async def saisir_manche(
    tournoi_id: int, barrage_id: int, requete: MancheRequete, request: Request
) -> BarrageReponse:
    """Saisit la manche suivante, ou **réécrit** celle indiquée (correction d'une flèche mal notée).

    Le verdict n'étant jamais stocké mais recalculé depuis les tirs, corriger une flèche corrige le
    classement. 422 si la manche est incohérente (tireur déjà départagé, groupe retiré à moitié).
    """
    service: ServiceBarrage = request.app.state.service_barrage
    write_queue: WriteQueue = request.app.state.write_queue
    tirs = [
        ServiceBarrage.tir(tir.archer_id, tir.score, tir.distance_au_centre) for tir in requete.tirs
    ]
    barrage = await asyncio.wrap_future(
        write_queue.submit(
            lambda: service.saisir_manche(tournoi_id, barrage_id, tirs, requete.manche)
        )
    )
    return BarrageReponse.de_agregat(barrage)


@router.delete(
    "/tournois/{tournoi_id}/barrages/{barrage_id}",
    status_code=204,
    dependencies=[Depends(exiger_admin)],
)
async def annuler_barrage(tournoi_id: int, barrage_id: int, request: Request) -> None:
    """Annule un barrage annoncé par erreur (mauvais rang, égalité disparue).

    Sans cette route, un barrage qu'on ne veut pas faire tirer était **définitif** : la clôture
    exige un barrage résolu, et son rang bloquait toute nouvelle annonce. Un barrage **clos**
    s'annule aussi — son verdict n'est jamais stocké, `clos` ne dit que « le juge a acté ».
    """
    service: ServiceBarrage = request.app.state.service_barrage
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(write_queue.submit(lambda: service.annuler(tournoi_id, barrage_id)))


@router.post(
    "/tournois/{tournoi_id}/barrages/{barrage_id}/cloture",
    response_model=BarrageReponse,
    dependencies=[Depends(exiger_admin)],
)
async def clore_barrage(tournoi_id: int, barrage_id: int, request: Request) -> BarrageReponse:
    """Clôt un barrage **résolu**. 409 s'il reste un groupe à faire retirer."""
    service: ServiceBarrage = request.app.state.service_barrage
    write_queue: WriteQueue = request.app.state.write_queue
    barrage = await asyncio.wrap_future(
        write_queue.submit(lambda: service.clore(tournoi_id, barrage_id))
    )
    return BarrageReponse.de_agregat(barrage)
