"""Endpoints REST des formats de tournoi (`/api/v1`) — la brique « déroulé » (E01US023).

ADR-0060 §5. Suit le patron de bout en bout (E00US009) : DTO Pydantic distincts des agrégats,
écriture routée par la **file** (writer unique, ADR-0005) et protégée par `exiger_admin`, lecture
directe **hors boucle** (threadpool), erreurs typées traduites à la frontière.

Deux familles de routes, calquées sur `/gabarits` (E01US007/E01US008) :

- **bibliothèque** de formats réutilisables, à plat sous `/formats` ;
- **déroulé d'un tournoi**, sous `/tournois/{id}/format` : appliquer un format (crée les phases) et
  promouvoir le déroulé courant en format de bibliothèque.

Noter l'asymétrie avec les autres briques : un format appliqué ne produit **pas** un format
rattaché au tournoi, mais des **phases** — il n'y a donc pas de `GET /tournois/{id}/format`, la
lecture du déroulé restant `GET /tournois/{id}/phases` (E05US001). Exposer une route qui laisserait
croire qu'un tournoi « a » un format entretiendrait exactement la confusion que l'ADR écarte.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from api.dependances import exiger_admin
from api.v1.phases import PhaseReponse
from application.formats import ServiceFormats
from domain.bareme import BaremeQualification
from domain.format_tournoi import FormatTournoi, ModelePhase
from domain.grain_validation import GrainValidation, TypeGrain
from domain.patrimoine import OrigineBrique
from domain.phase import IssueTour, NatureSource, SourcePhase, TypePhase
from infrastructure.db import WriteQueue

router = APIRouter(prefix="/api/v1", tags=["formats"])


class BaremeDTO(BaseModel):
    """Barème d'une étape : `nb_volees` volées de `nb_fleches_par_volee` flèches, au cumul."""

    nb_volees: int
    nb_fleches_par_volee: int


class GrainDTO(BaseModel):
    """Grain de validation d'une étape ; `n_volees` n'a de sens que pour « toutes les N volées »."""

    type: TypeGrain
    n_volees: int | None = None


class SourceDTO(BaseModel):
    """Un **prélèvement** d'une étape de format (E05US010) — mêmes natures que sur une phase réelle.

    Jumeau assumé de `api/v1/phases.SourceDTO` : les deux routeurs exposent la même notion mais des
    ressources distinctes (une phase de tournoi / une étape de brique de bibliothèque), et un DTO
    partagé les coupleraient — la duplication à la frontière est le prix de leur indépendance
    (déjà tranché à E01US023). Le **domaine**, lui, n'a qu'un seul `SourcePhase` : c'est là que la
    règle vit, ici il n'y a que du transport.
    """

    ordre_source: int
    nature: NatureSource = NatureSource.RANGS
    rang_debut: int = 1
    rang_fin: int | None = None
    tour: int | None = None
    issue: IssueTour | None = None

    def vers_agregat(self) -> SourcePhase:
        return SourcePhase(
            ordre_source=self.ordre_source,
            nature=self.nature,
            rang_debut=self.rang_debut,
            rang_fin=self.rang_fin,
            tour=self.tour,
            issue=self.issue,
        )

    @staticmethod
    def de_agregat(source: SourcePhase) -> SourceDTO:
        return SourceDTO(
            ordre_source=source.ordre_source,
            nature=source.nature,
            rang_debut=source.rang_debut,
            rang_fin=source.rang_fin,
            tour=source.tour,
            issue=source.issue,
        )


class EtapeDTO(BaseModel):
    """Un modèle de phase dans un format — **ni statut, ni tournoi** (ADR-0060 §5).

    L'absence de ces deux champs n'est pas un oubli du DTO : ils n'existent pas sur le modèle, et
    naissent à l'application. Les exposer ici inviterait un client à les fournir, donc à croire
    qu'un format porte un avancement.
    """

    ordre: int
    type: TypePhase
    bareme: BaremeDTO | None = None
    validation: GrainDTO | None = None
    sources: list[SourceDTO] = Field(default_factory=list, max_length=16)
    effectif: int | None = None

    def vers_modele(self) -> ModelePhase:
        """Traduit le DTO en agrégat de domaine — les invariants sont revérifiés par `ModelePhase`.

        Une étape incohérente (qualification sans barème, grain inadmissible pour le type) lève
        donc une `DomainError` → 422 à la frontière, jamais un format silencieusement invalide.
        """
        return ModelePhase(
            ordre=self.ordre,
            type=self.type,
            bareme=(
                None
                if self.bareme is None
                else BaremeQualification.creer(
                    self.bareme.nb_volees, self.bareme.nb_fleches_par_volee
                )
            ),
            validation=(
                None
                if self.validation is None
                else GrainValidation.creer(self.validation.type, self.validation.n_volees)
            ),
            sources=tuple(source.vers_agregat() for source in self.sources),
            effectif=self.effectif,
        )

    @staticmethod
    def de_modele(etape: ModelePhase) -> EtapeDTO:
        return EtapeDTO(
            ordre=etape.ordre,
            type=etape.type,
            bareme=(
                None
                if etape.bareme is None
                else BaremeDTO(
                    nb_volees=etape.bareme.nb_volees,
                    nb_fleches_par_volee=etape.bareme.nb_fleches_par_volee,
                )
            ),
            validation=(
                None
                if etape.validation is None
                else GrainDTO(type=etape.validation.type, n_volees=etape.validation.n_volees)
            ),
            sources=[SourceDTO.de_agregat(source) for source in etape.sources],
            effectif=etape.effectif,
        )


class FormatRequete(BaseModel):
    """Corps de création ou d'édition d'un format (nom + séquence d'étapes)."""

    nom: str
    # Borné pour la même raison que l'import de clubs : l'écriture passe par le writer unique. Un
    # format réel compte quelques étapes ; 64 est déjà hors de tout usage.
    etapes: list[EtapeDTO] = Field(default_factory=list, max_length=64)


class RenommerRequete(BaseModel):
    """Corps d'une duplication ou d'une promotion : le nom sous lequel ranger le format."""

    nom: str


class AppliquerFormatRequete(BaseModel):
    """Corps d'application d'un format à un tournoi : l'identifiant du format de bibliothèque."""

    format_id: int


class FormatReponse(BaseModel):
    """Représentation d'un format de tournoi renvoyée au client."""

    id: int
    nom: str
    # Provenance de la brique (E01US023) : sert les **deux listes séparées** de l'atelier. Ne dit
    # **pas** la conformité au règlement (ADR-0060 §4).
    origine: OrigineBrique
    etapes: list[EtapeDTO]

    @staticmethod
    def de_agregat(format_tournoi: FormatTournoi) -> FormatReponse:
        """Traduit un agrégat de domaine (persisté) en DTO de réponse."""
        assert format_tournoi.id is not None, "Un format persisté a toujours un identifiant."
        return FormatReponse(
            id=format_tournoi.id,
            nom=format_tournoi.nom,
            origine=format_tournoi.origine,
            etapes=[EtapeDTO.de_modele(etape) for etape in format_tournoi.etapes],
        )


# --- Bibliothèque de formats --------------------------------------------------------------------


@router.get("/formats", response_model=list[FormatReponse])
async def lister_formats(request: Request) -> list[FormatReponse]:
    """Liste la bibliothèque de formats : lecture directe exécutée hors de la boucle."""
    service: ServiceFormats = request.app.state.service_formats
    formats = await run_in_threadpool(service.lister)
    return [FormatReponse.de_agregat(format_tournoi) for format_tournoi in formats]


@router.post(
    "/formats",
    status_code=201,
    response_model=FormatReponse,
    dependencies=[Depends(exiger_admin)],
)
async def creer_format(requete: FormatRequete, request: Request) -> FormatReponse:
    """Crée un format (**action admin**) : écriture via la file (ADR-0005).

    Renvoie 409 (`nom_format_deja_pris`) si le nom est déjà porté, 422 si le format est invalide
    (aucune étape, séquence incohérente).
    """
    service: ServiceFormats = request.app.state.service_formats
    write_queue: WriteQueue = request.app.state.write_queue
    etapes = [etape.vers_modele() for etape in requete.etapes]
    format_tournoi = await asyncio.wrap_future(
        write_queue.submit(lambda: service.creer(requete.nom, etapes))
    )
    return FormatReponse.de_agregat(format_tournoi)


@router.post(
    "/formats/precharger-presets",
    status_code=201,
    response_model=list[FormatReponse],
    dependencies=[Depends(exiger_admin)],
)
async def precharger_presets(request: Request) -> list[FormatReponse]:
    """Pré-charge les formats presets (**action admin**) : FFTA officiel et format club (E01US009).

    Idempotent sur le nom ; renvoie les formats effectivement **créés** (liste vide si tout était
    déjà présent).
    """
    service: ServiceFormats = request.app.state.service_formats
    write_queue: WriteQueue = request.app.state.write_queue
    crees = await asyncio.wrap_future(write_queue.submit(service.precharger_presets))
    return [FormatReponse.de_agregat(format_tournoi) for format_tournoi in crees]


@router.put(
    "/formats/{format_id}",
    response_model=FormatReponse,
    dependencies=[Depends(exiger_admin)],
)
async def modifier_format(
    format_id: int, requete: FormatRequete, request: Request
) -> FormatReponse:
    """Édite un format **sur place** (**action admin**) — l'origine est préservée.

    C'est l'issue « intégrer au FFTA officiel » du CA (le règlement évolue). Pour garder les deux
    modèles, passer par `/formats/{id}/duplication`.
    """
    service: ServiceFormats = request.app.state.service_formats
    write_queue: WriteQueue = request.app.state.write_queue
    etapes = [etape.vers_modele() for etape in requete.etapes]
    format_tournoi = await asyncio.wrap_future(
        write_queue.submit(lambda: service.modifier(format_id, requete.nom, etapes))
    )
    return FormatReponse.de_agregat(format_tournoi)


@router.post(
    "/formats/{format_id}/duplication",
    status_code=201,
    response_model=FormatReponse,
    dependencies=[Depends(exiger_admin)],
)
async def dupliquer_format(
    format_id: int, requete: RenommerRequete, request: Request
) -> FormatReponse:
    """Détache une **copie** d'un format (**action admin**), marquée « création utilisateur ».

    L'issue « en faire une copie pour garder les deux modèles » du CA : l'original reste intact.
    """
    service: ServiceFormats = request.app.state.service_formats
    write_queue: WriteQueue = request.app.state.write_queue
    format_tournoi = await asyncio.wrap_future(
        write_queue.submit(lambda: service.dupliquer(format_id, requete.nom))
    )
    return FormatReponse.de_agregat(format_tournoi)


@router.delete(
    "/formats/{format_id}",
    status_code=204,
    dependencies=[Depends(exiger_admin)],
)
async def supprimer_format(format_id: int, request: Request) -> Response:
    """Supprime un format (**action admin**) ; les phases déjà appliquées survivent. Renvoie 204."""
    service: ServiceFormats = request.app.state.service_formats
    write_queue: WriteQueue = request.app.state.write_queue
    await asyncio.wrap_future(write_queue.submit(lambda: service.supprimer(format_id)))
    return Response(status_code=204)


# --- Déroulé d'un tournoi -----------------------------------------------------------------------


@router.put(
    "/tournois/{tournoi_id}/format",
    response_model=list[PhaseReponse],
    dependencies=[Depends(exiger_admin)],
)
async def appliquer_format(
    tournoi_id: int, requete: AppliquerFormatRequete, request: Request
) -> list[PhaseReponse]:
    """Applique un format au tournoi (**action admin**) : **crée ses phases**, via la file.

    **Remplace** la séquence existante. Renvoie 409 (`phases_engagees`) si une phase du tournoi
    n'est plus `à venir` : le remplacement jetterait un déroulé en cours.
    """
    service: ServiceFormats = request.app.state.service_formats
    write_queue: WriteQueue = request.app.state.write_queue
    phases = await asyncio.wrap_future(
        write_queue.submit(lambda: service.appliquer(tournoi_id, requete.format_id))
    )
    return [PhaseReponse.de_agregat(phase) for phase in phases]


@router.post(
    "/tournois/{tournoi_id}/format/promotion",
    status_code=201,
    response_model=FormatReponse,
    dependencies=[Depends(exiger_admin)],
)
async def promouvoir_format(
    tournoi_id: int, requete: RenommerRequete, request: Request
) -> FormatReponse:
    """Capture le déroulé du tournoi en format de bibliothèque (**action admin**, « permanent »).

    Idempotent par nom (met à jour plutôt que d'accumuler des homonymes) et sans rétroaction sur
    les éditions déjà assemblées. Renvoie 409 (`tournoi_sans_phase`) si le tournoi n'a rien à
    promouvoir.
    """
    service: ServiceFormats = request.app.state.service_formats
    write_queue: WriteQueue = request.app.state.write_queue
    format_tournoi = await asyncio.wrap_future(
        write_queue.submit(lambda: service.promouvoir(tournoi_id, requete.nom))
    )
    return FormatReponse.de_agregat(format_tournoi)
