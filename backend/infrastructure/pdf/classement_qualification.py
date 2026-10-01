"""Rendu PDF du classement de qualification — **une page par catégorie** (E09US005, ADR-0031).

Chaque page se lit seule (tournoi, créneau, catégorie, provisoire) : c'est la feuille qu'on
affiche au mur, et une feuille décrochée n'a plus sa voisine pour la situer.
"""

from __future__ import annotations

from collections.abc import Mapping
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from domain.classement import LigneClassement
from domain.classement_imprime import (
    BlocCategorie,
    ClassementQualificationImprime,
    SectionClassementQualification,
)
from domain.club import ClubId
from infrastructure.erreurs import InfrastructureError
from infrastructure.pdf._commun import echapper, libelle_statut

_MARGE = 15 * mm

_STYLE_TABLE = TableStyle(
    [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (5, 1), (7, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
)

_ENTETE = ["Rang", "Général", "Nom", "Prénom", "Club", "Total", "10", "9", "Statut"]

PROVISOIRE = "Classement provisoire — des volées restent à valider."
"""⚠️ Le papier circule : une feuille imprimée à la pause n'a plus d'indice de fraîcheur."""


class GenerateurClassementQualificationPdf:
    """Implémentation ReportLab du port `GenerateurClassementQualification`."""

    def __init__(self) -> None:
        styles = getSampleStyleSheet()
        self._titre = ParagraphStyle(
            "titre_classement", parent=styles["Title"], fontSize=15, spaceAfter=2 * mm
        )
        self._creneau = ParagraphStyle(
            "creneau_classement", parent=styles["Normal"], fontSize=11, textColor="#555555"
        )
        self._categorie = ParagraphStyle(
            "categorie_classement",
            parent=styles["Heading1"],
            fontSize=14,
            spaceBefore=3 * mm,
            spaceAfter=2 * mm,
        )
        self._info = ParagraphStyle("info_classement", parent=styles["Normal"], fontSize=11)

    def classement_qualification(self, document: ClassementQualificationImprime) -> bytes:
        """Rend le document en PDF. Enveloppe tout échec en `InfrastructureError`."""
        try:
            return self._rendre(self._corps(document))
        # ReportLab lève une famille d'exceptions hétérogène : on enveloppe (aucune fuite brute).
        except Exception as exc:
            raise InfrastructureError(
                "Échec de génération du PDF du classement de qualification."
            ) from exc

    def _corps(self, document: ClassementQualificationImprime) -> list[Flowable]:
        pages: list[list[Flowable]] = []
        for section in document.sections:
            if not section.categories:
                pages.append(
                    [
                        *self._entete(document.tournoi, section),
                        Paragraph("Aucun archer engagé dans ce créneau.", self._info),
                    ]
                )
            for bloc in section.categories:
                pages.append(
                    [
                        *self._entete(document.tournoi, section),
                        Paragraph(echapper(bloc.libelle), self._categorie),
                        self._table(bloc, document.clubs),
                    ]
                )
        elements: list[Flowable] = []
        for indice, page in enumerate(pages):
            if indice:
                elements.append(PageBreak())
            elements.extend(page)
        return elements

    def _entete(self, tournoi: str, section: SectionClassementQualification) -> list[Flowable]:
        elements: list[Flowable] = [
            Paragraph(f"Classement de qualification — {echapper(tournoi)}", self._titre),
            Paragraph(echapper(section.libelle), self._creneau),
        ]
        if section.provisoire:
            elements.append(Paragraph(PROVISOIRE, self._info))
        elements.append(Spacer(1, 2 * mm))
        return elements

    def _table(self, bloc: BlocCategorie, clubs: Mapping[ClubId, str]) -> Table:
        # Cellules de `Table` : chaînes **brutes**, jamais échappées (cf. `_commun.echapper`).
        corps = [_cellules(ligne, clubs) for ligne in bloc.lignes]
        table = Table([_ENTETE, *corps], repeatRows=1)
        table.setStyle(_STYLE_TABLE)
        return table

    def _rendre(self, elements: list[Flowable]) -> bytes:
        tampon = BytesIO()
        document = SimpleDocTemplate(
            tampon,
            pagesize=A4,
            title="Classement de qualification",
            topMargin=_MARGE,
            bottomMargin=_MARGE,
            leftMargin=_MARGE,
            rightMargin=_MARGE,
        )
        document.build(elements)
        return tampon.getvalue()


def _cellules(ligne: LigneClassement, clubs: Mapping[ClubId, str]) -> list[str]:
    return [
        _rang(ligne.rang_categorie),
        _rang(ligne.rang_scratch),
        ligne.nom,
        ligne.prenom,
        clubs.get(ligne.club_id, "") if ligne.club_id is not None else "",
        str(ligne.total),
        str(ligne.nb_dix),
        str(ligne.nb_neuf),
        libelle_statut(ligne.statut),
    ]


def _rang(rang: int | None) -> str:
    """« — » pour un disqualifié, qui n'est pas rangé (ADR-0050)."""
    return "—" if rang is None else str(rang)
