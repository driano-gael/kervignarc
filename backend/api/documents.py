"""Frontière API — servir un document au format demandé (E16US007).

Module d'API **sans routeur** (comme `api/dependances.py`) : deux routeurs y puisent.

⚠️ Le **type MIME est une décision HTTP**, d'où sa place ici et non dans `application/` — motivé
au § Conséquences d'`docs/adr/0101-le-catalogue-d-exports-porte-les-formats-pas-les-url.md`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import Response

from application.exports import FormatExport

# Registre jumeau de `FormatExport` : un membre ajouté sans son type MIME lèverait un `KeyError`
# — au démarrage pour `reponses_document`, à la requête pour `reponse_document` — d'où le test
# d'exhaustivité (`test_listes_impression_api.py`).
MEDIA_TYPES: Mapping[FormatExport, str] = {
    FormatExport.PDF: "application/pdf",
    FormatExport.CSV: "text/csv",
    # Type officiel OOXML. ⚠️ Pas `application/vnd.ms-excel`, qui désigne l'ancien `.xls` binaire :
    # certains navigateurs renomment alors le fichier en `.xls` et Excel proteste à l'ouverture.
    FormatExport.XLSX: ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
}


def reponses_document(*formats: FormatExport) -> dict[int | str, dict[str, Any]]:
    """Déclare à OpenAPI les types de contenu qu'une route de document peut rendre.

    ⚠️ Documentation seulement — la **source de vérité** des formats servis reste le catalogue,
    dérivé du câblage (ADR-0101 §3). Déclarer ici tous les formats du produit ferait promettre du
    CSV à la feuille de marque, qui répond 400 dessus.
    """
    return {
        200: {
            "content": {MEDIA_TYPES[format_]: {} for format_ in formats},
            "description": "Document, au format demandé",
        }
    }


def reponse_document(
    contenu: bytes,
    format_: FormatExport,
    nom_sans_extension: str,
    disposition: str = "attachment",
) -> Response:
    """Sert un document — type de contenu **et** extension dérivés du même format.

    ⚠️ Point unique : sans lui, chaque route recopierait la paire (type MIME, extension) et un
    format ajouté se téléchargerait en `.pdf` contenant du CSV.
    ⚠️ `disposition` est décidée par l'appelant : seul le **PDF** du palmarès est servi `inline`
    (« ouvrir, vérifier, imprimer au mur », E06US004) ; les tableurs partent en `attachment`.
    """
    nom_fichier = f"{nom_sans_extension}.{format_.value}"
    return Response(
        content=contenu,
        media_type=MEDIA_TYPES[format_],
        headers={
            "Content-Disposition": f'{disposition}; filename="{nom_fichier}"',
            # Le contenu vient de la saisie et de l'import FFTA, et sort sur une origine partagée
            # avec la SPA : le navigateur ne doit pas re-deviner le type (E16US016, revue axe C2).
            "X-Content-Type-Options": "nosniff",
        },
    )
