"""Endpoints REST du **palmarès** (`/api/v1`) — classement final d'un tournoi (E06US004).

JSON et PDF passent tous deux par `ServicePalmares` : un document qui recalculerait de son côté
finirait par contredire l'écran.

⚠️ **Public, sans authentification**, comme le classement (E07US001) et les affectations (E07US008).
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from api.dependances import exiger_admin
from application.palmares import RenduPalmares, ServicePalmares
from domain.palmares import LignePalmares
from domain.podium import PorteePodium, ReglagePodiums
from infrastructure.db import WriteQueue

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


class PlacePodiumReponse(BaseModel):
    """Une place d'un podium : le rang **dans la portée du bloc**, et l'archer qui l'occupe.

    Le rang est rendu à part de la ligne pour que le client n'ait pas à choisir entre trois couples
    de bornes selon la portée du bloc — c'est le serveur qui sait laquelle s'applique (E16US014).
    """

    rang: int
    ligne: LignePalmaresReponse


class PodiumReponse(BaseModel):
    """Un podium : ce qu'il récompense, et ses rangs **décernés** dans la profondeur réglée.

    Il peut être **partiel** (rangs 1-2 seuls, la petite finale n'étant pas tirée) — la lecture au
    fil de l'eau de tout le projet. Les *ex æquo* n'y figurent pas : on ne remet pas une médaille à
    quatre archers 5ᵉ-8ᵉ. `cle` vaut `null` pour le scratch, qui ne regroupe rien.
    """

    portee: PorteePodium
    cle: int | None
    libelle: str
    places: list[PlacePodiumReponse]
    effectif: int
    """Les archers du groupe qui peuvent **occuper une place** — recopié du bloc, jamais recalculé.

    Le client ne voit que les lignes qu'il a demandées : un effectif compté là-bas vient d'une autre
    population que celle du bloc. C'est `BlocPodium` qui le porte (ADR-0103 §6).
    """

    en_attente: bool
    """Un archer du groupe a-t-il encore un match ? Sépare « pas encore » de « plus jamais »."""


class ReglagePodiumsReponse(BaseModel):
    """Ce que ce tournoi récompense — la **lecture** est ouverte, comme le palmarès lui-même."""

    portees: list[PorteePodium]
    profondeur: int

    @staticmethod
    def de_reglage(reglage: ReglagePodiums) -> ReglagePodiumsReponse:
        return ReglagePodiumsReponse(
            portees=list(reglage.portees_actives()),
            profondeur=reglage.profondeur,
        )


class ReglerPodiumsRequete(BaseModel):
    """La demande de réglage. Une liste **vide** est licite : ne rien récompenser est un choix.

    ⚠️ **Aucune borne `Field(ge=…, le=…)` sur `profondeur`**, même parti qu'`ReglagePages`
    (E16US009) : `ReglagePodiums` la borne déjà, et la répéter ici dégraderait le refus en **400
    générique** là où `DomainError` rend un **422** portant le code métier
    (`profondeur_podium_invalide`) et la phrase du domaine.
    """

    portees: list[PorteePodium]
    profondeur: int


class PalmaresReponse(BaseModel):
    """Le palmarès d'un tournoi : les podiums réglés, puis le classement complet."""

    tournoi_id: int
    podiums: list[PodiumReponse]
    profondeur_podium: int
    """Les places récompensées (E16US014) — rendue ici pour que l'écran sache si un podium est
    complet **sans** payer une seconde requête sur les surfaces publiques."""

    classement_vide: bool
    """Le palmarès complet ne porte **aucune ligne** — donc aucun archer au classement du créneau de
    référence (`DETTE-045`). Dit par le serveur, jamais déduit par le client.

    ⚠️ **C'est le fait que quatre gardes successives ont tenté d'inférer, et raté quatre fois.** Ni
    `podiums` (que le réglage vide à bon droit) ni `lignes` (que le filtre restreint) n'y répondent.
    """

    lignes: list[LignePalmaresReponse]

    @staticmethod
    def de_rendu(tournoi_id: int, rendu: RenduPalmares) -> PalmaresReponse:
        """⚠️ **Les podiums viennent de `complet`, les lignes d'`affiche`.**

        Les composer sur la vue filtrée rendait un bloc « Scratch » réduit aux archers d'une seule
        catégorie — un podium faux, à l'écran public comme sur le PDF (bloquant de revue).
        """
        return PalmaresReponse(
            tournoi_id=tournoi_id,
            profondeur_podium=rendu.reglage.profondeur,
            classement_vide=not rendu.complet.lignes,
            podiums=[
                PodiumReponse(
                    portee=bloc.portee,
                    cle=bloc.cle,
                    libelle=bloc.libelle,
                    effectif=bloc.effectif,
                    en_attente=bloc.en_attente,
                    places=[
                        PlacePodiumReponse(
                            rang=place.rang, ligne=LignePalmaresReponse.de_ligne(place.ligne)
                        )
                        for place in bloc.places
                    ],
                )
                for bloc in rendu.complet.podiums(rendu.reglage)
            ],
            lignes=[LignePalmaresReponse.de_ligne(ligne) for ligne in rendu.affiche.lignes],
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
    # Une seule lecture : le réglage et le palmarès doivent venir du **même** instant, sans quoi un
    # PUT intercalé fait sortir une profondeur qui ne correspond pas aux blocs rendus.
    rendu = await run_in_threadpool(service.rendu, tournoi_id, categorie_id)
    return PalmaresReponse.de_rendu(tournoi_id, rendu)


@router.get("/tournois/{tournoi_id}/reglage-podiums", response_model=ReglagePodiumsReponse)
async def reglage_podiums(tournoi_id: int, request: Request) -> ReglagePodiumsReponse:
    """Lit ce que ce tournoi récompense (E16US014).

    **Ouverte**, comme le palmarès lui-même : savoir qu'un tournoi remet des médailles par club
    n'est pas un secret, et l'écran public en a besoin pour titrer ses blocs. 404 si le tournoi est
    inconnu. Lecture d'une ligne — elle ne paie pas la reconstruction des tableaux (`DETTE-031`).
    """
    service: ServicePalmares = request.app.state.service_palmares
    reglage = await run_in_threadpool(service.reglage_podiums, tournoi_id)
    return ReglagePodiumsReponse.de_reglage(reglage)


@router.put(
    "/tournois/{tournoi_id}/reglage-podiums",
    response_model=ReglagePodiumsReponse,
    dependencies=[Depends(exiger_admin)],
)
async def regler_podiums(
    tournoi_id: int, requete: ReglerPodiumsRequete, request: Request
) -> ReglagePodiumsReponse:
    """Règle ce que le tournoi récompense (**action admin**) : écriture via la file.

    **Ne fige aucun résultat** : le palmarès se recalcule à chaque lecture, ce réglage ne fait que
    décider quels blocs en sortent. Le front réinvalide donc le palmarès après ce PUT.
    """
    service: ServicePalmares = request.app.state.service_palmares
    write_queue: WriteQueue = request.app.state.write_queue
    reglage = ReglagePodiums(portees=frozenset(requete.portees), profondeur=requete.profondeur)
    valeur = await asyncio.wrap_future(
        write_queue.submit(lambda: service.definir_reglage_podiums(tournoi_id, reglage))
    )
    return ReglagePodiumsReponse.de_reglage(valeur)


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
