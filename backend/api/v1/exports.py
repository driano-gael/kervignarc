"""Frontière API — catalogue d'exports (E16US007).

⚠️ Le catalogue porte les **formats**, pas les URL ni les libellés d'écran : ajouter un format ne
touche pas l'écran, ajouter un export si —
[ADR-0101](../../../docs/adr/0101-le-catalogue-d-exports-porte-les-formats-pas-les-url.md).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from api.dependances import exiger_admin
from application.exports import LIBELLES_FORMAT, CatalogueExports

router = APIRouter(prefix="/api/v1", tags=["exports"])


class FormatReponse(BaseModel):
    """Un format proposé pour un export. `code` sert **aussi** d'extension de fichier."""

    code: str
    libelle: str


class EntreeCatalogueReponse(BaseModel):
    """Un document exportable et les formats que le serveur sait en produire."""

    identifiant: str
    formats: list[FormatReponse]


@router.get("/exports", dependencies=[Depends(exiger_admin)])
async def catalogue(request: Request) -> list[EntreeCatalogueReponse]:
    """Énumère les exports proposés et, pour chacun, ses formats disponibles.

    Pas de `tournoi_id` : le catalogue ne dépend d'aucun tournoi — il décrit ce que **ce serveur**
    sait produire. Le scoper à un tournoi laisserait croire qu'il en varie.
    """
    catalogue_exports: CatalogueExports = request.app.state.catalogue_exports
    return [
        EntreeCatalogueReponse(
            identifiant=entree.identifiant,
            formats=[
                FormatReponse(code=format_.value, libelle=LIBELLES_FORMAT[format_])
                for format_ in entree.formats
            ],
        )
        for entree in catalogue_exports.entrees
    ]
