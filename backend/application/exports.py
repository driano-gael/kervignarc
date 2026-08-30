"""Catalogue d'exports — quels documents l'organisateur sort, et dans quels formats (E16US007).

Concern d'**exploitation**, défini ici et non dans `domain/` : un format de fichier n'est pas du
vocabulaire FFTA (règle 3). Même parti que le port `ConstructeurArchive` (`application/archive.py`).

Voir [ADR-0101](../../docs/adr/0101-le-catalogue-d-exports-porte-les-formats-pas-les-url.md) pour
ce que le catalogue porte — et ce qu'il ne porte pas.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypeVar

from application.erreurs import FormatExportIndisponible


class FormatExport(Enum):
    """Format de fichier d'un export (E16US007).

    ⚠️ La valeur est à la fois le **code** échangé avec le client et l'**extension** du fichier
    proposé au téléchargement : les faire diverger demanderait une table de plus.
    """

    PDF = "pdf"
    CSV = "csv"


@dataclass(frozen=True)
class DescriptionFormat:
    """Ce que le client a besoin de savoir d'un format : comment le nommer, comment le servir."""

    libelle: str
    media_type: str


# ⚠️ Registre jumeau de `FormatExport` : un membre ajouté sans sa description ne casserait rien
# avant la première requête — d'où le test de cohérence (`test_service_exports.py`).
DESCRIPTIONS_FORMAT: Mapping[FormatExport, DescriptionFormat] = {
    FormatExport.PDF: DescriptionFormat(libelle="PDF", media_type="application/pdf"),
    FormatExport.CSV: DescriptionFormat(libelle="CSV (tableur)", media_type="text/csv"),
}


G = TypeVar("G")


class RegistreDeFormats(Generic[G]):
    """Les générateurs d'un même document, indexés par format (ADR-0101).

    ⚠️ **Source unique** des formats annoncés au catalogue : `formats` dérive des clés réellement
    câblées. Une liste écrite à côté finirait par proposer un format que rien ne sait produire —
    le client recevrait alors une 400 sur un choix que le serveur lui a lui-même offert.
    """

    def __init__(self, generateurs: Mapping[FormatExport, G]) -> None:
        if not generateurs:
            raise ValueError("Un export doit être câblé sur au moins un générateur.")
        self._generateurs = dict(generateurs)

    @property
    def formats(self) -> tuple[FormatExport, ...]:
        """Formats câblés, dans l'ordre de `FormatExport` — jamais dans celui du câblage.

        L'ordre de déclaration au composition root est un détail invisible en revue ; l'y laisser
        commander l'affichage déplacerait un bouton sous le doigt de l'organisateur.
        """
        return tuple(format_ for format_ in FormatExport if format_ in self._generateurs)

    def pour(self, format_: FormatExport) -> G:
        """Générateur du format demandé ; lève `FormatExportIndisponible` s'il n'est pas câblé."""
        generateur = self._generateurs.get(format_)
        if generateur is None:
            disponibles = ", ".join(disponible.value for disponible in self.formats)
            raise FormatExportIndisponible(
                f"Le format « {format_.value} » n'est pas disponible pour ce document "
                f"(disponibles : {disponibles})."
            )
        return generateur


@dataclass(frozen=True)
class EntreeCatalogueExport:
    """Un document exportable, tel qu'annoncé au client.

    `formats` se remplit depuis un `RegistreDeFormats`, jamais à la main (ADR-0101 §3).
    """

    identifiant: str
    libelle: str
    description: str
    formats: tuple[FormatExport, ...]


@dataclass(frozen=True)
class CatalogueExports:
    """Ce que l'écran « Exports & impressions » sait proposer, composé au composition root.

    ⚠️ Le catalogue ne porte **ni URL ni paramètres** (tri, départ) : ce sont des choix d'IHM, et
    les inscrire ici obligerait à décrire un gabarit d'URL par export — l'union de toutes les
    entrées que l'instruction de la famille « prêt à… » (E16US012) a déjà refusée une fois.
    """

    entrees: tuple[EntreeCatalogueExport, ...]
