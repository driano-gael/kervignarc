"""Panneau de routage — **lecture publique, sans authentification** (ADR-0039, E10US001).

Rien ici n'est confidentiel : la cible d'un match est affichée en salle.

⚠️ **Aucune erreur métier propre** : un archer qu'on ne sait pas router rend une ligne **motivée**,
jamais un 4xx. Un panneau qui échoue en bloc parce qu'un archer sur quatre n'est pas au tableau
serait inutilisable le jour J.
"""

from __future__ import annotations

from typing import Annotated, Literal, cast

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.v1.saisie_duels import DuellisteReponse
from application.routage import (
    DestinationRepechage,
    ProchainDuel,
    ProchaineManche,
    Routage,
    RoutageArcher,
    ServiceRoutage,
)
from domain.phase import TypePhase

router = APIRouter(prefix="/api/v1/routage", tags=["routage"])

IssueRoutageReponse = Literal[
    "prochain_duel", "prochaine_manche", "termine", "repeche", "en_attente", "indisponible"
]
"""Les seules issues du panneau, publiées au schéma OpenAPI plutôt que laissées en `str`.

Miroir fermé de `IssueRoutage`, sans exposer l'énumération d'application (règle 6) : le client les
code en dur, il doit voir une divergence au lieu de la subir. `en_attente` (E05US030) **rétrécit**
`indisponible`, là où `repeche` (E07US008) n'était qu'un élargissement. ⚠️ **Le test miroir ne
garde que la cohérence énumération ↔ DTO** ; le `Record` du front ne rougit qu'une fois l'union TS
élargie, donc une issue ajoutée **côté serveur seul** ne rougit nulle part.
"""


# --- DTO ---


class ProchaineMancheReponse(BaseModel):
    """Le prochain rendez-vous d'un finaliste de **Big Shoot Off** (E05US028).

    ⚠️ **Un DTO distinct de `ProchainDuelReponse`, et non son élargissement** : un Big Shoot Off
    n'oppose personne, réutiliser le DTO de duel aurait publié un `adversaire` toujours `null` et
    un `numero` de match inexistant. `elimine` dit combien d'archers sortiront à l'issue du tour.
    ⚠️ `cible`/`position` sont **toujours `null` aujourd'hui** et `manque` le dit en clair : le
    routage ne lit pas le plan du créneau pour cette phase (`DETTE-059`, règle `P-3`).
    """

    numero: int
    elimine: int
    cible: int | None
    position: str | None
    manque: str | None

    @staticmethod
    def de_manche(manche: ProchaineManche) -> ProchaineMancheReponse:
        return ProchaineMancheReponse(
            numero=manche.numero,
            elimine=manche.elimine,
            cible=manche.cible,
            position=manche.position,
            manque=manche.manque,
        )


class ProchainDuelReponse(BaseModel):
    """Le prochain rendez-vous d'un archer : où, quand dans l'arbre, contre qui.

    `cible`/`position` sont `null` au-delà du tour 1 (placement intégral = E05US010) et `manque` dit
    alors pourquoi. `alerte` est l'inverse : la cible **est** là, mais quelque chose cloche (le duel
    n'est pas côte à côte). Les deux ne se remplacent pas : l'un dit « je n'ai pas », l'autre
    « j'ai, mais méfiance ». Pas de champ « heure » : aucun horaire n'existe par tour de tableau —
    c'est le lancement du tour (E12US002) qui fait partir les duels.
    """

    numero: int
    tour: int
    libelle: str
    cible: int | None
    position: str | None
    adversaire: DuellisteReponse | None
    sources_en_attente: list[int]
    manque: str | None
    alerte: str | None

    @staticmethod
    def de_prochain(prochain: ProchainDuel) -> ProchainDuelReponse:
        return ProchainDuelReponse(
            numero=prochain.numero,
            tour=prochain.tour,
            libelle=prochain.libelle,
            cible=prochain.cible,
            position=prochain.position,
            adversaire=DuellisteReponse.de_duelliste(prochain.adversaire),
            sources_en_attente=list(prochain.sources_en_attente),
            manque=prochain.manque,
            alerte=prochain.alerte,
        )


class DestinationRepechageReponse(BaseModel):
    """La phase qui **reprend** un repêché (E07US008) : son id, son rang de séquence, son type.

    Pas de libellé tout fait : le front sait nommer un type (`LIBELLE_TYPE`), le dupliquer côté
    serveur le ferait diverger. `type` est déclaré sur l'**énumération** `TypePhase` (correctif de
    revue, axe A) — un `str` ouvert publiait une chaîne libre au schéma. ⚠️ Le miroir TS reste
    volontairement `type: string` : le front doit pouvoir nommer un type qu'un serveur **plus
    récent** lui enverrait, sans quoi le repli de `nommerType` est mort.
    """

    phase_id: int
    ordre: int
    type: TypePhase

    @staticmethod
    def de_destination(destination: DestinationRepechage) -> DestinationRepechageReponse:
        return DestinationRepechageReponse(
            phase_id=destination.phase_id,
            ordre=destination.ordre,
            type=destination.type,
        )


class RoutageArcherReponse(BaseModel):
    """La ligne d'un archer : son issue et le détail qui va avec.

    `issue` est fermée et chaque valeur dit quel champ lire ensuite (`prochain_duel`,
    `prochaine_manche`, `rang_final`, `destination`, `motif`). ⚠️ **`en_attente` ≠ `indisponible`**
    malgré le champ commun : le premier est « en course, rien d'apparié à cet instant » et **compte
    parmi les en-lice** ; le second, « on ne sait pas router » (E05US026, corrigé en E05US030).
    `rang_min`/`rang_max` portent la fourchette d'ex æquo, refermée quand le rang exact existe.
    """

    archer_id: int
    nom: str
    prenom: str
    issue: IssueRoutageReponse
    prochain: ProchainDuelReponse | None
    rang_final: int | None
    rang_min: int | None
    rang_max: int | None
    tour_sortie: str | None
    destination: DestinationRepechageReponse | None
    motif: str | None
    prochaine_manche: ProchaineMancheReponse | None = None
    """Le rendez-vous d'un finaliste de Big Shoot Off (E05US028), quand `issue` vaut
    `prochaine_manche`. **Exclusif de `prochain`** : un archer n'a jamais les deux, et son issue
    dit lequel lire. Champ **ajouté** avec un défaut, donc un client d'avant E05US028 ne casse
    pas — il ne peut simplement pas rencontrer cette issue sur un tournoi sans Big Shoot Off."""

    @staticmethod
    def de_archer(ligne: RoutageArcher) -> RoutageArcherReponse:
        return RoutageArcherReponse(
            archer_id=ligne.archer_id,
            nom=ligne.nom,
            prenom=ligne.prenom,
            issue=cast(IssueRoutageReponse, ligne.issue.value),
            prochain=(
                ProchainDuelReponse.de_prochain(ligne.prochain)
                if ligne.prochain is not None
                else None
            ),
            rang_final=ligne.rang_final,
            rang_min=ligne.rang_min,
            rang_max=ligne.rang_max,
            tour_sortie=ligne.tour_sortie,
            destination=(
                DestinationRepechageReponse.de_destination(ligne.destination)
                if ligne.destination is not None
                else None
            ),
            motif=ligne.motif,
            prochaine_manche=(
                ProchaineMancheReponse.de_manche(ligne.prochaine_manche)
                if ligne.prochaine_manche is not None
                else None
            ),
        )


class RoutageReponse(BaseModel):
    """La réponse du panneau : la phase de tableau visée et une ligne par archer.

    `phase_id` à `null` signifie **« aucune phase d'élimination configurée »** — à distinguer d'une
    liste vide, qui dirait « le tableau ne route personne ». C'est la seule chose qui permette à
    l'écran de salle de dire « on n'en est pas là » au lieu d'afficher un pas de tir désert.
    """

    phase_id: int | None
    archers: list[RoutageArcherReponse]

    @staticmethod
    def de_routage(routage: Routage) -> RoutageReponse:
        return RoutageReponse(
            phase_id=routage.phase_id,
            archers=[RoutageArcherReponse.de_archer(ligne) for ligne in routage.archers],
        )


_MAX_ARCHERS = 64
"""Plafond du nombre d'archers routés en un appel — au-delà, **400** avant que le service tourne.

400 et non 422 : ce projet mappe `RequestValidationError` sur 400, le 422 étant réservé aux
`DomainError` (`api/erreurs.py`). Les deux appelants réels en demandent 4 et 2 ; 64 laisse de la
marge. ⚠️ **Borne secondaire** : le coût dominant est la reconstruction de l'arbre, payée une fois
par requête et bornée par rien — ce plafond ne ferme que l'amplification requête→réponse
(`DETTE-008`) sur une route publique, pas la charge en général.
"""


# --- Lecture ---


@router.get("/departs/{depart_id}", response_model=RoutageReponse)
async def lire_routage(
    depart_id: int,
    request: Request,
    archer_id: Annotated[
        list[int] | None,
        Query(
            max_length=_MAX_ARCHERS,
            description="Archers à router, dans l'ordre d'affichage",
        ),
    ] = None,
    phase_id: Annotated[int | None, Query(description="Phase de tableau visée")] = None,
) -> RoutageReponse:
    """Où tirent ensuite ces archers. Lecture pure (`D-08`), hors boucle événementielle.

    `phase_id` omis ⇒ le service vise le **tableau qui vient** (la première élimination directe non
    terminée, sinon la dernière) : la tablette de qualification ne connaît que sa cible et son
    départ. Fourni, il est **validé** (404 s'il est inconnu ou d'un autre tournoi). L'ordre des
    `archer_id` est **conservé** — le panneau affiche A, B, C, D dans l'ordre de la grille.
    """
    service: ServiceRoutage = request.app.state.service_routage
    routage = await run_in_threadpool(service.routage, depart_id, tuple(archer_id or ()), phase_id)
    return RoutageReponse.de_routage(routage)


@router.get("/departs/{depart_id}/affectations", response_model=RoutageReponse)
async def lire_affectations(
    depart_id: int,
    request: Request,
    phase_id: Annotated[int | None, Query(description="Phase de tableau visée")] = None,
) -> RoutageReponse:
    """**Toutes** les affectations du tableau, dans l'ordre du pas de tir (E07US008).

    Même projection et **même DTO** que la route précédente : les quatre canaux de routage doivent
    dire la même chose. Seule l'entrée change — aucun `archer_id`, ni l'écran de salle ni la table
    de l'organisation ne connaissant la liste. ⚠️ **Pas de plafond `_MAX_ARCHERS` ici** : le client
    ne demande rien, la réponse est bornée par les inscrits. Le coût dominant reste la
    reconstruction de l'arbre sur une route publique — **`# DETTE-031`**, que cette US aggrave.
    """
    service: ServiceRoutage = request.app.state.service_routage
    routage = await run_in_threadpool(service.affectations, depart_id, phase_id)
    return RoutageReponse.de_routage(routage)
