"""Écrans de salle — préparation admin, et affichage lu par l'écran rattaché.

⚠️ **Aucun endpoint ne pousse un ordre à un écran** (ADR-0064) : l'affichage est une **lecture** que
l'écran répète, la prise de contrôle un **état** que l'admin pose — `prendre_le_controle` répond à
l'admin, pas à l'écran. Prendre le contrôle et rendre la main n'écrivent qu'en mémoire : hors file.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin, extraire_jeton_poste
from application.ecrans import AffichageEcran, PriseActive, ServiceEcrans
from application.postes import ServicePostes
from domain.ecran import (
    Consigne,
    ReglagePages,
    SequenceVues,
    VueEcran,
    VueProgrammee,
)
from domain.poste import Poste
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1/tournois/{tournoi_id}/ecrans", tags=["ecrans"])
session_router = APIRouter(prefix="/api/v1/ecrans/session", tags=["ecrans"])


class VueProgrammeeDTO(BaseModel):
    """Une étape d'un déroulé : quelle vue, combien de temps.

    ⚠️ **La vue est typée `VueEcran`, la cadence ne l'est pas.** `vue` désigne un **catalogue
    fermé** — affaire de **format**, donc Pydantic rejette une valeur inconnue en **400** avec le
    champ fautif ; déclarée `str`, elle levait un `ValueError` nu → **500 + traceback**, et sur les
    deux valeurs que le CA nomme sans les livrer. `cadence_s` porte au contraire une **règle** (5 s
    ≤ c ≤ 3600 s) : la répéter en `Field(ge=…)` la ferait vivre à deux endroits (règle 2).
    """

    vue: VueEcran
    cadence_s: int


class ReglagePagesDTO(BaseModel):
    """Comment une liste projetée se découpe et à quel rythme elle tourne (E16US009).

    **Aucune borne `Field(ge=…, le=…)`**, pour la raison écrite au-dessus pour `cadence_s` : les
    bornes sont un **jugement** sur ce qui se lit à dix mètres, elles vivent dans le domaine, et les
    répéter ici les dégraderait en 400 générique là où le domaine rend un **422** portant le champ
    fautif (`nombre_de_noms_par_page_invalide` / `cadence_de_page_invalide`).
    """

    noms_par_page: int
    cadence_page_s: int

    @staticmethod
    def de_domaine(pages: ReglagePages) -> ReglagePagesDTO:
        """Traduit le value object de domaine en DTO de réponse."""
        return ReglagePagesDTO(
            noms_par_page=pages.noms_par_page, cadence_page_s=pages.cadence_page_s
        )

    def vers_domaine(self) -> ReglagePages:
        """Traduit le DTO en value object de domaine (qui revalide les bornes)."""
        return ReglagePages(noms_par_page=self.noms_par_page, cadence_page_s=self.cadence_page_s)


class EcranReponse(BaseModel):
    """Un écran de salle vu de l'admin : son libellé, son code, son déroulé effectif.

    `deroule` est **toujours** rempli : c'est `deroule_effectif`, donc le déroulé par défaut tant
    que rien n'a été réglé. Le front n'a ainsi jamais à savoir qu'un défaut existe — et ne peut pas
    afficher « aucune vue ». `pages` suit **exactement** le même parti (`pages_effectives`,
    E16US009) : le formulaire d'admin affiche donc toujours des valeurs, jamais des champs vides
    qu'il faudrait remplir d'un défaut qu'il aurait fallu recopier côté front.
    """

    id: int
    tournoi_id: int
    libelle: str
    code: str
    deroule: list[VueProgrammeeDTO]
    pages: ReglagePagesDTO

    @staticmethod
    def de_agregat(ecran: Poste) -> EcranReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert ecran.id is not None, "Un écran persisté a toujours un identifiant."
        assert ecran.libelle is not None, "Un écran a toujours un libellé (invariant du domaine)."
        return EcranReponse(
            id=ecran.id,
            tournoi_id=ecran.tournoi_id,
            libelle=ecran.libelle,
            code=ecran.code,
            deroule=[
                VueProgrammeeDTO(vue=v.vue, cadence_s=v.cadence_s)
                for v in ecran.deroule_effectif.vues
            ],
            pages=ReglagePagesDTO.de_domaine(ecran.pages_effectives),
        )


class CreerEcranRequete(BaseModel):
    """Corps de création : le libellé de la place de l'écran (« près du pas de tir »).

    Vide ou blanc → `422 libelle_ecran_invalide` (le domaine), et non un `400` de validation : même
    parti que la cadence ci-dessus.
    """

    libelle: str


class ReglerDerouleRequete(BaseModel):
    """Corps de réglage : la séquence de vues, dans l'ordre, avec sa cadence.

    Liste vide → `422 sequence_vues_vide` (le domaine). Aucune contrainte de longueur ici, pour la
    même raison que les bornes de cadence : une seule maison pour la règle, un code exploitable.
    """

    vues: list[VueProgrammeeDTO]

    def vers_domaine(self) -> SequenceVues:
        """Traduit le DTO en value object de domaine (qui revalide les bornes de cadence)."""
        return SequenceVues(tuple(VueProgrammee(etape.vue, etape.cadence_s) for etape in self.vues))


class ReglerPagesRequete(BaseModel):
    """Corps de réglage des pages projetées : les deux valeurs, ensemble.

    **Les deux, toujours** — pas de champ facultatif : `ReglagePages` est un value object
    indivisible, et un réglage partiel obligerait la frontière à décider quoi faire de la moitié
    manquante (garder l'ancienne ? reprendre le défaut ?), c'est-à-dire à porter une règle.
    """

    pages: ReglagePagesDTO


class PrendreLeControleRequete(BaseModel):
    """Corps de prise de contrôle : **une** vue figée **ou** une autre séquence, plus une durée.

    `duree_s` absente signifie « jusqu'à ce que je rende la main » (arbitrage Q-UX7 du 01/08/2026) ;
    une durée nulle ou négative → `422 duree_prise_de_controle_invalide`. L'exclusivité
    vue/séquence n'est pas vérifiée ici mais dans le domaine (`Consigne`) : c'est une règle métier,
    elle ne se duplique pas à la frontière (règle 2).
    """

    vue: VueEcran | None = None
    vues: list[VueProgrammeeDTO] | None = None
    duree_s: int | None = None

    def vers_domaine(self) -> Consigne:
        """Traduit le DTO en `Consigne` de domaine (qui porte les invariants)."""
        sequence = (
            None
            if self.vues is None
            else SequenceVues(
                tuple(VueProgrammee(etape.vue, etape.cadence_s) for etape in self.vues)
            )
        )
        return Consigne(
            vue=self.vue,
            sequence=sequence,
            duree_s=self.duree_s,
        )


class PriseReponse(BaseModel):
    """La prise posée : ce qui est imposé, pour combien de temps, et faut-il s'en alarmer."""

    poste_id: int
    vue_figee: VueEcran | None
    reste_s: float | None
    exige_rappel: bool

    @staticmethod
    def de_prise(prise: PriseActive) -> PriseReponse:
        """Traduit une prise du service en DTO de réponse."""
        return PriseReponse(
            poste_id=prise.poste_id,
            vue_figee=prise.vue_figee,
            reste_s=prise.reste_s,
            exige_rappel=prise.exige_rappel,
        )


class AffichageReponse(BaseModel):
    """Ce que l'écran doit montrer maintenant — la seule réponse qu'il consomme.

    **Exactement l'un** de `vues` (il tourne) ou `vue_figee` (il est figé) est renseigné : l'écran
    n'arbitre jamais. `reste_s` alimente son compte à rebours **local** — la reprise du déroulé ne
    dépend donc d'aucun message serveur, ce qui la rend insensible à une coupure réseau.
    """

    vues: list[VueProgrammeeDTO] | None
    deroule_repli: list[VueProgrammeeDTO]
    vue_figee: VueEcran | None
    sous_controle: bool
    reste_s: float | None
    pages: ReglagePagesDTO

    @staticmethod
    def de_affichage(affichage: AffichageEcran) -> AffichageReponse:
        """Traduit l'affichage du service en DTO de réponse."""
        return AffichageReponse(
            vues=(
                None
                if affichage.sequence is None
                else [
                    VueProgrammeeDTO(vue=v.vue, cadence_s=v.cadence_s)
                    for v in affichage.sequence.vues
                ]
            ),
            deroule_repli=[
                VueProgrammeeDTO(vue=v.vue, cadence_s=v.cadence_s)
                for v in affichage.deroule_repli.vues
            ],
            vue_figee=affichage.vue_figee,
            sous_controle=affichage.sous_controle,
            reste_s=affichage.reste_s,
            pages=ReglagePagesDTO.de_domaine(affichage.pages),
        )


# --- Préparation & pilotage (admin) ---


@router.get("", response_model=list[EcranReponse], dependencies=[Depends(exiger_admin)])
async def lister_ecrans(tournoi_id: int, request: Request) -> list[EcranReponse]:
    """Liste les écrans de salle d'un tournoi (**admin**). `404` si le tournoi n'existe pas."""
    service: ServiceEcrans = request.app.state.service_ecrans
    ecrans = await run_in_threadpool(service.lister, tournoi_id)
    return [EcranReponse.de_agregat(ecran) for ecran in ecrans]


@router.post("", response_model=EcranReponse, dependencies=[Depends(exiger_admin)])
async def creer_ecran(
    tournoi_id: int, requete: CreerEcranRequete, request: Request
) -> EcranReponse:
    """Crée un écran de salle et lui alloue un code de rattachement (**admin**, écriture via file).

    `404 tournoi_introuvable` si le tournoi n'existe pas ; `422 libelle_ecran_invalide` si le
    libellé est vide. Aucune garde de statut : un écran se prépare **à l'avance** (`D-07`).
    """
    service: ServicePostes = request.app.state.service_postes
    write_queue: WriteQueue = request.app.state.write_queue
    ecran = await asyncio.wrap_future(
        write_queue.submit(lambda: service.creer_ecran(tournoi_id, requete.libelle))
    )
    return EcranReponse.de_agregat(ecran)


@router.put("/{poste_id}", response_model=EcranReponse, dependencies=[Depends(exiger_admin)])
async def renommer_ecran(
    tournoi_id: int, poste_id: int, requete: CreerEcranRequete, request: Request
) -> EcranReponse:
    """Renomme un écran (**admin**). Le **code ne change pas** : le QR est peut-être déjà imprimé.

    `404 poste_introuvable` (inconnu ou autre tournoi), `409 poste_n_est_pas_un_ecran` si la cible
    du geste est une tablette.
    """
    service: ServicePostes = request.app.state.service_postes
    write_queue: WriteQueue = request.app.state.write_queue
    ecran = await asyncio.wrap_future(
        write_queue.submit(lambda: service.renommer_ecran(tournoi_id, poste_id, requete.libelle))
    )
    return EcranReponse.de_agregat(ecran)


@router.put(
    "/{poste_id}/deroule", response_model=EcranReponse, dependencies=[Depends(exiger_admin)]
)
async def regler_deroule(
    tournoi_id: int, poste_id: int, requete: ReglerDerouleRequete, request: Request
) -> EcranReponse:
    """Fixe le déroulé de vues d'un écran (**admin**, écriture via file).

    Réglage **persisté** — il survit au redémarrage du serveur le matin du jour J, contrairement à
    la prise de contrôle. `404` / `409` comme le renommage ; `422 cadence_ecran_invalide` si une
    cadence sort des bornes.
    """
    service: ServicePostes = request.app.state.service_postes
    write_queue: WriteQueue = request.app.state.write_queue
    deroule = requete.vers_domaine()
    ecran = await asyncio.wrap_future(
        write_queue.submit(lambda: service.regler_deroule_ecran(tournoi_id, poste_id, deroule))
    )
    return EcranReponse.de_agregat(ecran)


@router.put("/{poste_id}/pages", response_model=EcranReponse, dependencies=[Depends(exiger_admin)])
async def regler_pages(
    tournoi_id: int, poste_id: int, requete: ReglerPagesRequete, request: Request
) -> EcranReponse:
    """Fixe le découpage et la cadence des listes projetées par un écran (**admin**, via file).

    **Route distincte du déroulé**, et non un champ de plus sur `PUT …/deroule` : deux questions
    différentes (*quelles vues* / *comment une liste se lit de loin*), posées à deux moments. Les
    fondre aurait obligé l'écran d'admin à renvoyer la séquence entière pour corriger une cadence —
    donc à pouvoir l'écraser par inadvertance. `404`/`409` comme le renommage ; `422
    nombre_de_noms_par_page_invalide` ou `422 cadence_de_page_invalide` hors bornes.
    """
    service: ServicePostes = request.app.state.service_postes
    write_queue: WriteQueue = request.app.state.write_queue
    pages = requete.pages.vers_domaine()
    ecran = await asyncio.wrap_future(
        write_queue.submit(lambda: service.regler_pages_ecran(tournoi_id, poste_id, pages))
    )
    return EcranReponse.de_agregat(ecran)


@router.delete("/{poste_id}", status_code=204, dependencies=[Depends(exiger_admin)])
async def supprimer_ecran(tournoi_id: int, poste_id: int, request: Request) -> None:
    """Retire un écran (**admin**) : sessions fermées, consigne retirée, ligne supprimée."""
    service: ServicePostes = request.app.state.service_postes
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(
        write_queue.submit(lambda: service.supprimer_ecran(tournoi_id, poste_id))
    )


@router.post(
    "/{poste_id}/controle", response_model=PriseReponse, dependencies=[Depends(exiger_admin)]
)
async def prendre_le_controle(
    tournoi_id: int, poste_id: int, requete: PrendreLeControleRequete, request: Request
) -> PriseReponse:
    """Impose une vue figée ou une autre séquence à un écran (**admin**).

    `422 consigne_ecran_invalide` si le corps n'impose ni exactement une vue ni exactement une
    séquence. N'écrit qu'en mémoire (registre de consignes) : hors file, mais relit la base pour
    vérifier l'écran → threadpool.
    """
    service: ServiceEcrans = request.app.state.service_ecrans
    consigne = requete.vers_domaine()
    prise = await run_in_threadpool(service.prendre_le_controle, tournoi_id, poste_id, consigne)
    return PriseReponse.de_prise(prise)


@router.delete("/{poste_id}/controle", status_code=204, dependencies=[Depends(exiger_admin)])
async def rendre_la_main(tournoi_id: int, poste_id: int, request: Request) -> None:
    """Rend la main sur un écran (**admin**) : il reprend son déroulé. **Idempotent**."""
    service: ServiceEcrans = request.app.state.service_ecrans
    await run_in_threadpool(service.rendre_la_main, tournoi_id, poste_id)


# --- Affichage (écran rattaché) ---


@session_router.get("/affichage", response_model=AffichageReponse)
async def affichage_courant(request: Request) -> AffichageReponse:
    """Ce que l'écran rattaché doit montrer maintenant.

    `401` si le jeton est absent ou inconnu ; `409 poste_n_est_pas_un_ecran` si le jeton est celui
    d'une tablette de cible. C'est la lecture que l'écran répète — il n'y a **rien à acquitter**.
    """
    service: ServiceEcrans = request.app.state.service_ecrans
    affichage = await run_in_threadpool(service.affichage, extraire_jeton_poste(request))
    return AffichageReponse.de_affichage(affichage)
