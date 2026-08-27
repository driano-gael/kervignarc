"""Endpoints REST du **palmarès** (`/api/v1`) — classement final d'un tournoi (E06US004).

JSON et PDF passent tous deux par `ServicePalmares` : un document qui recalculerait de son côté
finirait par contredire l'écran.

⚠️ **Public, sans authentification**, comme le classement (E07US001) et les affectations (E07US008).
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from application.palmares import ServicePalmares
from domain.palmares import LignePalmares, Palmares

# DETTE-031 (../../../docs/dette.md) : les deux routes de ce module appellent
# `ServicePalmares`, qui reconstruit **chaque phase à tableau** (classement complet + arbre
# rebâti + duels rejoués) à chaque lecture, sans cache ni plafond — et elles sont **publiques
# et non authentifiées**. Le PDF y ajoute ~40 ms de rendu ReportLab (mesuré en revue, 120
# lignes). C'est la seule route PDF publique du produit ; les quatre autres documents sont
# derrière `exiger_admin`, parce qu'ils portent des données qui ne sont pas publiques.
router = APIRouter(prefix="/api/v1", tags=["palmares"])


class LignePalmaresReponse(BaseModel):
    """Une ligne du palmarès renvoyée au client (E06US004).

    Les rangs sont des **fourchettes** : `rang_min == rang_max` = rang décerné ; `5`/`8` = *ex
    æquo* 5ᵉ-8ᵉ. Les deux bornes sont `null` hors classement (disqualifié, ADR-0050). ⚠️ `decerne`
    ne se déduit **pas** de `rang_min == rang_max` — la renumérotation rend un rang exact dès qu'un
    archer est seul de son groupe, donc au vainqueur d'une demi-finale avant la finale ; `en_lice`
    dit que l'ouverture se tranchera **au tir**. `origine` dit **d'où vient** le rang.
    """

    rang_min: int | None
    rang_max: int | None
    rang_categorie_min: int | None
    rang_categorie_max: int | None
    archer_id: int
    nom: str
    prenom: str
    categorie_id: int
    categorie_libelle: str
    club_id: int | None
    origine: str
    statut: str
    decerne: bool
    en_lice: bool

    @staticmethod
    def de_ligne(ligne: LignePalmares) -> LignePalmaresReponse:
        return LignePalmaresReponse(
            rang_min=ligne.rang_min,
            rang_max=ligne.rang_max,
            rang_categorie_min=ligne.rang_categorie_min,
            rang_categorie_max=ligne.rang_categorie_max,
            archer_id=ligne.archer_id,
            nom=ligne.nom,
            prenom=ligne.prenom,
            categorie_id=ligne.categorie_id,
            categorie_libelle=ligne.categorie_libelle,
            club_id=ligne.club_id,
            origine=ligne.origine.value,
            statut=ligne.statut.value,
            decerne=ligne.decerne,
            en_lice=ligne.en_lice,
        )


class PodiumCategorieReponse(BaseModel):
    """Le podium d'une catégorie : ses rangs **décernés** parmi les quatre premiers.

    Un podium par catégorie, parce que les médailles se remettent par catégorie. Il peut être
    **partiel** (rangs 1-2 seuls, la petite finale n'étant pas tirée) ou **vide** — la lecture au
    fil de l'eau de tout le projet. Les *ex æquo* n'y figurent pas : on ne remet pas une médaille à
    quatre archers 5ᵉ-8ᵉ.
    """

    categorie_id: int
    categorie_libelle: str
    lignes: list[LignePalmaresReponse]


class PalmaresReponse(BaseModel):
    """Le palmarès d'un tournoi : les podiums par catégorie, puis le classement complet."""

    tournoi_id: int
    podiums: list[PodiumCategorieReponse]
    lignes: list[LignePalmaresReponse]

    @staticmethod
    def de_agregat(tournoi_id: int, palmares: Palmares) -> PalmaresReponse:
        return PalmaresReponse(
            tournoi_id=tournoi_id,
            podiums=[
                PodiumCategorieReponse(
                    categorie_id=categorie_id,
                    categorie_libelle=libelle,
                    lignes=[
                        LignePalmaresReponse.de_ligne(ligne)
                        for ligne in palmares.podium(categorie_id)
                    ],
                )
                for categorie_id, libelle in palmares.categories()
            ],
            lignes=[LignePalmaresReponse.de_ligne(ligne) for ligne in palmares.lignes],
        )


@router.get("/tournois/{tournoi_id}/palmares", response_model=PalmaresReponse)
async def consulter_palmares(
    tournoi_id: int, request: Request, categorie_id: int | None = None
) -> PalmaresReponse:
    """Renvoie le palmarès d'un tournoi (lecture directe hors boucle).

    `categorie_id` (optionnel) **filtre** l'affichage à une catégorie ; les rangs (scratch et
    catégorie) restent ceux du palmarès complet — voir une catégorie sans perdre la position
    d'ensemble, comme pour le classement de qualification.
    """
    service: ServicePalmares = request.app.state.service_palmares
    palmares = await run_in_threadpool(service.pour_tournoi, tournoi_id, categorie_id)
    return PalmaresReponse.de_agregat(tournoi_id, palmares)


@router.get(
    "/tournois/{tournoi_id}/palmares.pdf",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def imprimer_palmares(
    tournoi_id: int, request: Request, categorie_id: int | None = None
) -> Response:
    """Rend le palmarès en PDF — le document affiché au mur et remis aux archers.

    `inline` plutôt que `attachment` : le geste réel est « ouvrir, vérifier, imprimer », et un
    téléchargement forcé ajoute un aller-retour par le gestionnaire de fichiers. Même parti que
    les listes d'organisation (E09US003).
    """
    service: ServicePalmares = request.app.state.service_palmares
    document = await run_in_threadpool(service.imprimer, tournoi_id, categorie_id)
    return Response(
        content=document,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="palmares-{tournoi_id}.pdf"'},
    )
