"""Endpoints REST des forfaits (E04US015, ADR-0050) — qui déclare abandon / DSQ.

Déclarer et **annuler** (`D-15`), en qualification (relégation / exclusion au classement) comme en
duels (l'adversaire passe). Écritures dédoublonnées par identifiant de saisie (ADR-0036).
⚠️ **Une seule portée depuis le 30/08/2026** : les quatre routes acceptent **admin ou scoreur**.
Seul le scoreur est borné à **son** tournoi (`403 scoreur_hors_tournoi`), le secret admin valant
pour l'instance (`D-13`) ; l'auteur tracé est la personne, ou `AUTEUR_ADMIN` (`DETTE-017`).
"""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from api.dependances import autoriser_forfait
from application.erreurs import ScoreurHorsTournoi
from application.forfaits import AUTEUR_ADMIN, ServiceForfait
from domain.forfait import Forfait, NatureForfait
from domain.scoreur import Scoreur
from infrastructure.db import WriteQueue
from infrastructure.idempotence import RegistreIdempotence

router = APIRouter(prefix="/api/v1/forfaits", tags=["forfaits"])


# --- DTO ---


class ForfaitReponse(BaseModel):
    """Un forfait déclaré : identité, phase, nature, qui/quand et motif optionnel."""

    id: int | None
    tournoi_id: int
    archer_id: int
    phase_id: int
    nature: str
    declare_par: str
    declare_le: str
    motif: str | None

    @staticmethod
    def de_forfait(forfait: Forfait) -> ForfaitReponse:
        return ForfaitReponse(
            id=forfait.id,
            tournoi_id=forfait.tournoi_id,
            archer_id=forfait.archer_id,
            phase_id=forfait.phase_id,
            nature=forfait.nature.value,
            declare_par=forfait.declare_par,
            declare_le=forfait.declare_le.isoformat(),
            motif=forfait.motif,
        )


class AnnulationReponse(BaseModel):
    """Confirmation d'annulation d'un forfait (la déclaration a été supprimée)."""

    annule: bool = True


class DeclarerQualificationRequete(BaseModel):
    """Corps d'une déclaration de forfait en **qualification** : archer, nature, motif optionnel."""

    tournoi_id: int
    archer_id: int
    nature: NatureForfait
    motif: str | None = None
    identifiant_saisie: str | None = None


class AnnulerQualificationRequete(BaseModel):
    """Corps d'une annulation de forfait en **qualification** : l'archer concerné."""

    tournoi_id: int
    archer_id: int
    identifiant_saisie: str | None = None


class DeclarerDuelRequete(BaseModel):
    """Corps d'une déclaration de forfait en **duels** : phase de tableau, archer, nature."""

    tournoi_id: int
    phase_id: int
    archer_id: int
    nature: NatureForfait
    motif: str | None = None
    identifiant_saisie: str | None = None


class AnnulerDuelRequete(BaseModel):
    """Corps d'une annulation de forfait en **duels** : la phase de tableau et l'archer."""

    tournoi_id: int
    phase_id: int
    archer_id: int
    identifiant_saisie: str | None = None


def _exiger_meme_tournoi(scoreur: Scoreur, tournoi_id: int) -> None:
    # DETTE-065 : 6ᵉ copie verbatim de ce **garde d'autorisation**. Un 7ᵉ routeur d'écriture qui
    # l'oublierait ne ferait rougir personne — résorption : `api/dependances.py`.
    """Refuse (`403 scoreur_hors_tournoi`) un scoreur agissant hors de **son** tournoi."""
    if scoreur.tournoi_id != tournoi_id:
        raise ScoreurHorsTournoi("Ce scoreur n'officie pas dans ce tournoi.")


def _garder_tournoi(scoreur: Scoreur | None, tournoi_id: int) -> None:
    """Même garde, appliquée au seul scoreur : un admin n'est rattaché à aucun tournoi."""
    if scoreur is not None:
        _exiger_meme_tournoi(scoreur, tournoi_id)


def _auteur(scoreur: Scoreur | None) -> str:
    """Qui a agi, pour la trace persistée : la personne, ou le rôle admin (DETTE-017)."""
    return AUTEUR_ADMIN if scoreur is None else scoreur.nom


def _cle_idempotence(operation: str, identifiant: str | None, *portee: int) -> str | None:
    """Clé d'idempotence **scopée** (opération + cible), ou `None` sans identifiant (ADR-0036)."""
    if not identifiant:
        return None
    return ":".join((operation, identifiant, *(str(p) for p in portee)))


# --- Écritures (via la file) ---


@router.post("/qualification", response_model=ForfaitReponse)
async def declarer_en_qualification(
    requete: DeclarerQualificationRequete,
    request: Request,
    scoreur: Annotated[Scoreur | None, Depends(autoriser_forfait)],
) -> ForfaitReponse:
    """Déclare un forfait (abandon/DSQ) en qualification. Admin ou scoreur ; via la file."""
    service: ServiceForfait = request.app.state.service_forfait
    write_queue: WriteQueue = request.app.state.write_queue
    registre: RegistreIdempotence = request.app.state.registre_idempotence
    _garder_tournoi(scoreur, requete.tournoi_id)
    cle = _cle_idempotence(
        "forfait_qualif", requete.identifiant_saisie, requete.tournoi_id, requete.archer_id
    )
    auteur = _auteur(scoreur)

    def ecrire() -> Forfait:
        return service.declarer_en_qualification(
            requete.tournoi_id, requete.archer_id, requete.nature, auteur, requete.motif
        )

    forfait = await asyncio.wrap_future(write_queue.submit(lambda: registre.executer(cle, ecrire)))
    return ForfaitReponse.de_forfait(forfait)


@router.post("/qualification/annulation", response_model=AnnulationReponse)
async def annuler_en_qualification(
    requete: AnnulerQualificationRequete,
    request: Request,
    scoreur: Annotated[Scoreur | None, Depends(autoriser_forfait)],
) -> AnnulationReponse:
    """Annule un forfait de qualification (réversibilité, `D-15`). Admin ou scoreur ; file."""
    service: ServiceForfait = request.app.state.service_forfait
    write_queue: WriteQueue = request.app.state.write_queue
    registre: RegistreIdempotence = request.app.state.registre_idempotence
    _garder_tournoi(scoreur, requete.tournoi_id)
    cle = _cle_idempotence(
        "annul_forfait_qualif", requete.identifiant_saisie, requete.tournoi_id, requete.archer_id
    )
    auteur = _auteur(scoreur)

    def ecrire() -> None:
        service.annuler_en_qualification(requete.tournoi_id, requete.archer_id, auteur)

    await asyncio.wrap_future(write_queue.submit(lambda: registre.executer(cle, ecrire)))
    return AnnulationReponse()


@router.post("/duel", response_model=ForfaitReponse)
async def declarer_en_duel(
    requete: DeclarerDuelRequete,
    request: Request,
    scoreur: Annotated[Scoreur | None, Depends(autoriser_forfait)],
) -> ForfaitReponse:
    """Déclare un forfait en duels : l'adversaire passera (walkover). Admin ou scoreur ; file."""
    service: ServiceForfait = request.app.state.service_forfait
    write_queue: WriteQueue = request.app.state.write_queue
    registre: RegistreIdempotence = request.app.state.registre_idempotence
    _garder_tournoi(scoreur, requete.tournoi_id)
    cle = _cle_idempotence(
        "forfait_duel",
        requete.identifiant_saisie,
        requete.tournoi_id,
        requete.phase_id,
        requete.archer_id,
    )

    def ecrire() -> Forfait:
        return service.declarer_en_duel(
            requete.tournoi_id,
            requete.phase_id,
            requete.archer_id,
            requete.nature,
            _auteur(scoreur),
            requete.motif,
        )

    forfait = await asyncio.wrap_future(write_queue.submit(lambda: registre.executer(cle, ecrire)))
    return ForfaitReponse.de_forfait(forfait)


@router.post("/duel/annulation", response_model=AnnulationReponse)
async def annuler_en_duel(
    requete: AnnulerDuelRequete,
    request: Request,
    scoreur: Annotated[Scoreur | None, Depends(autoriser_forfait)],
) -> AnnulationReponse:
    # ⚠️ Élargi **avec** la déclaration : un admin qui peut déclarer et pas annuler laisse une
    # erreur de frappe irréparable sans aller chercher un scoreur — `D-15` (réversibilité).
    """Annule un forfait de duel : le walkover disparaît à la reconstruction. Admin ou scoreur."""
    service: ServiceForfait = request.app.state.service_forfait
    write_queue: WriteQueue = request.app.state.write_queue
    registre: RegistreIdempotence = request.app.state.registre_idempotence
    _garder_tournoi(scoreur, requete.tournoi_id)
    cle = _cle_idempotence(
        "annul_forfait_duel",
        requete.identifiant_saisie,
        requete.tournoi_id,
        requete.phase_id,
        requete.archer_id,
    )

    def ecrire() -> None:
        service.annuler_en_duel(
            requete.tournoi_id, requete.phase_id, requete.archer_id, _auteur(scoreur)
        )

    await asyncio.wrap_future(write_queue.submit(lambda: registre.executer(cle, ecrire)))
    return AnnulationReponse()
