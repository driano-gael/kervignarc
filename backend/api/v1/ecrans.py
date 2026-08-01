"""Endpoints REST des **écrans de salle** (E07US004, ADR-0064).

Deux routers, deux portées — le même partage que les postes de cible :

- **Préparation & pilotage** (`/api/v1/tournois/{tournoi_id}/ecrans`) : réservés à l'admin. Créer,
  renommer, régler le déroulé, supprimer, **prendre le contrôle** et **rendre la main**. Les
  réponses portent le `code` : ce sont des secrets d'usage à imprimer, comme pour les cibles.
- **Affichage** (`/api/v1/ecrans/session/affichage`) : ce que l'écran rattaché doit montrer
  *maintenant*, protégé par la session de poste (`exiger_poste`) — le rattachement lui-même passe
  par `/api/v1/postes/session`, strictement inchangé (CA : *« même mécanisme que la tablette »*).

**Aucun endpoint ne pousse un ordre à un écran.** L'affichage est une **lecture** que l'écran
répète ; la prise de contrôle est un **état** que l'admin pose. C'est la décision d'ADR-0064, et
elle se voit ici : `prendre_le_controle` répond à l'admin, pas à l'écran.

Écritures et lectures : seuls la création, le renommage, le réglage du déroulé et la suppression
touchent la base — donc la **file** (writer unique, ADR-0005). Prendre le contrôle et rendre la main
n'écrivent qu'en mémoire (registre de consignes) : hors file, threadpool.
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

    **La vue est typée `VueEcran`, la cadence ne l'est pas** — et la distinction n'est pas un
    caprice (correctif de revue) :

    - `vue` désigne un **catalogue fermé**. Son appartenance relève du **format** de la requête, pas
      d'une règle métier : `VueEcran` *est* le type. La typer ici fait rejeter une valeur inconnue
      par Pydantic, en **400 `requete_invalide`** avec le champ fautif. La version d'origine
      déclarait `vue: str` et traduisait dans le corps du handler :
      `VueEcran("affectations")` levait
      un `ValueError` nu, sans gestionnaire typé, qui retombait sur le filet `Exception` → **500 +
      traceback journalisé**. Et les deux valeurs qui déclenchaient le cas — `affectations`,
      `tableaux` — sont précisément celles que le CA nomme et que le catalogue ne livre pas encore,
      donc les premières qu'un client enverra.
    - `cadence_s` porte au contraire une **règle** (5 s ≤ cadence ≤ 3600 s est un jugement sur la
      lisibilité à dix mètres). La répéter en `Field(ge=…, le=…)` la ferait vivre à deux endroits
      (règle 2) et la dégraderait en 400 générique, là où le domaine rend un **422
      `cadence_ecran_invalide`** exploitable. Même parti pour le libellé et la longueur de séquence.
    """

    vue: VueEcran
    cadence_s: int


class EcranReponse(BaseModel):
    """Un écran de salle vu de l'admin : son libellé, son code, son déroulé effectif.

    `deroule` est **toujours** rempli : c'est `deroule_effectif`, donc le déroulé par défaut tant
    que rien n'a été réglé. Le front n'a ainsi jamais à savoir qu'un défaut existe — et ne peut pas
    afficher « aucune vue ».
    """

    id: int
    tournoi_id: int
    libelle: str
    code: str
    deroule: list[VueProgrammeeDTO]

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
    vue_figee: VueEcran | None
    sous_controle: bool
    reste_s: float | None

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
            vue_figee=affichage.vue_figee,
            sous_controle=affichage.sous_controle,
            reste_s=affichage.reste_s,
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
