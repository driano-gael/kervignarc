"""Frontière API — catalogue d'exports, et réponse binaire commune aux documents (E16US007).

⚠️ Le catalogue porte les **formats**, pas les URL ni les paramètres d'IHM : ajouter un format ne
touche pas l'écran, ajouter un export si —
[ADR-0101](../../../docs/adr/0101-le-catalogue-d-exports-porte-les-formats-pas-les-url.md).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from api.dependances import exiger_admin
from application.exports import DESCRIPTIONS_FORMAT, CatalogueExports, FormatExport

router = APIRouter(prefix="/api/v1", tags=["exports"])

# Réponse binaire déclarée à OpenAPI pour les routes de document : le contenu dépend du format
# demandé, donc les deux types y figurent.
REPONSE_DOCUMENT: dict[int | str, dict[str, Any]] = {
    200: {
        "content": {media_type: {} for media_type in ("application/pdf", "text/csv")},
        "description": "Document, au format demandé",
    }
}


class FormatReponse(BaseModel):
    """Un format proposé pour un export. `code` sert **aussi** d'extension de fichier."""

    code: str
    libelle: str


class EntreeCatalogueReponse(BaseModel):
    """Un document exportable et les formats que le serveur sait en produire."""

    identifiant: str
    libelle: str
    description: str
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
            libelle=entree.libelle,
            description=entree.description,
            formats=[
                FormatReponse(code=format_.value, libelle=DESCRIPTIONS_FORMAT[format_].libelle)
                for format_ in entree.formats
            ],
        )
        for entree in catalogue_exports.entrees
    ]


def reponse_document(
    contenu: bytes, format_: FormatExport, nom_sans_extension: str, *, inline: bool = False
) -> Response:
    """Sert un document au format demandé — type de contenu et extension **dérivés du format**.

    ⚠️ Point unique : sans lui, chaque route recopierait la paire (media type, extension) et un
    format ajouté se téléchargerait en `.pdf` contenant du CSV — un fichier qu'aucun outil n'ouvre
    et dont rien, côté serveur, ne dirait qu'il est faux.
    """
    disposition = "inline" if inline else "attachment"
    nom_fichier = f"{nom_sans_extension}.{format_.value}"
    return Response(
        content=contenu,
        media_type=DESCRIPTIONS_FORMAT[format_].media_type,
        headers={"Content-Disposition": f'{disposition}; filename="{nom_fichier}"'},
    )
