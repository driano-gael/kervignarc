"""Endpoints REST du **panneau de routage** (E04US018) — « où est-ce que je tire ensuite ? ».

Expose `ServiceRoutage` aux deux surfaces de saisie : la tablette de **qualification** (E04US002),
qui route ses archers A→D vers leur duel de 1ᵉʳ tour une fois les séries validées, et l'écran
**scoreur de duels** (E04US013), qui route les deux duellistes dès le duel tranché. Une seule route
sert les deux : c'est la même question, seul l'ensemble d'archers change.

**Lecture publique, sans authentification** — comme le déroulé (E07US009, ADR-0039) et conformément
au contrat d'E10US001 (toute lecture répond sans jeton). C'est cohérent avec la destination de cette
projection : les trois autres canaux de routage (`D-09`) sont l'appli publique (E07US008) et l'écran
de salle (E07US004). Rien ici n'est confidentiel — la cible d'un match est affichée en salle.

Aucune erreur métier propre : un archer qu'on ne sait pas router rend une ligne **motivée**
(`indisponible`), jamais un 4xx — un panneau qui échoue en bloc parce qu'un archer sur quatre n'est
pas au tableau serait inutilisable le jour J. Les gardes de phase (`PhaseIntrouvable` /
`PhasePasUnTableau`) ne remontent que si le client **impose** un `phase_id`, comme partout ailleurs.

DTO Pydantic distincts des dataclasses d'application (règle 6) ; on réutilise `DuellisteReponse` de
la saisie de duels — l'adversaire s'affiche avec les mêmes noms que la grille du scoreur.
"""

from __future__ import annotations

from typing import Annotated, Literal, cast

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.v1.saisie_duels import DuellisteReponse
from application.routage import ProchainDuel, Routage, RoutageArcher, ServiceRoutage

router = APIRouter(prefix="/api/v1/routage", tags=["routage"])

IssueRoutageReponse = Literal["prochain_duel", "termine", "indisponible"]
"""Les trois seules issues du panneau — publiées au schéma OpenAPI plutôt que laissées en `str`,
pour que le client (qui les code en dur) voie une divergence d'énumération au lieu de la subir.
Miroir fermé de `IssueRoutage`, sans exposer l'énumération d'application (règle 6)."""


# --- DTO ---


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


class RoutageArcherReponse(BaseModel):
    """La ligne d'un archer : son issue (`prochain_duel` / `termine` / `indisponible`) et le détail.

    `issue` est fermée aux trois valeurs ci-dessus, et chacune dit quel champ lire ensuite
    (`prochain`, `rang_final`, `motif`).
    """

    archer_id: int
    nom: str
    prenom: str
    issue: IssueRoutageReponse
    prochain: ProchainDuelReponse | None
    rang_final: int | None
    tour_sortie: str | None
    motif: str | None

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
            tour_sortie=ligne.tour_sortie,
            motif=ligne.motif,
        )


class RoutageReponse(BaseModel):
    """La réponse du panneau : la phase de tableau visée et une ligne par archer demandé."""

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

(400 et non 422 : ce projet mappe `RequestValidationError` sur 400, le 422 étant réservé aux
`DomainError` — cf. la table de `api/erreurs.py`.)

Les deux appelants réels en demandent 4 (une cible) et 2 (un duel) ; 64 laisse une marge
confortable. La borne est **secondaire** dans la défense : le coût dominant d'un appel est la
reconstruction de l'arbre, payée **une fois par requête** quel que soit le nombre d'identifiants, et
elle n'est bornée par rien. Ce plafond ne ferme donc que l'amplification requête→réponse (le
régime
de DETTE-008) sur une route **publique et non authentifiée** ; à ne pas lire comme une protection
générale contre la charge."""


# --- Lecture ---


@router.get("/{tournoi_id}", response_model=RoutageReponse)
async def lire_routage(
    tournoi_id: int,
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

    `phase_id` omis ⇒ le service vise la première phase d'élimination directe du tournoi : la
    tablette de qualification ne connaît que sa cible et son départ. L'ordre des `archer_id` est
    **conservé** dans la réponse — le panneau affiche A, B, C, D dans l'ordre de la grille.
    """
    service: ServiceRoutage = request.app.state.service_routage
    routage = await run_in_threadpool(service.routage, tournoi_id, tuple(archer_id or ()), phase_id)
    return RoutageReponse.de_routage(routage)
