"""Rendu PDF du déroulé horaire — un bloc par créneau, une ligne par phase (E09US007).

Les blocs se suivent sans saut de page : le déroulé se communique d'une feuille quand il tient.
"""

from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from domain.deroule_imprime import BlocDeroule, DerouleImprime, LigneDeroule
from domain.horaire_prevu import HeurePrevue
from infrastructure.erreurs import InfrastructureError
from infrastructure.libelles import LIBELLES_TYPE_PHASE
from infrastructure.pdf._commun import echapper

_MARGE = 15 * mm

_STYLE_TABLE = TableStyle(
    [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
)

_ENTETE = ["Phase", "Début", "Fin", "Tours"]
_LARGEURS = [80 * mm, 30 * mm, 30 * mm, 40 * mm]

A_PRECISER = "à préciser"
"""Une heure inconnue (durée non saisie, repêchage) ne s'invente pas — CA 2 d'E09US007."""


class GenerateurDerouleHorairePdf:
    """Implémentation ReportLab du port `GenerateurDerouleHoraire`."""

    def __init__(self) -> None:
        styles = getSampleStyleSheet()
        self._titre = ParagraphStyle(
            "titre_deroule", parent=styles["Title"], fontSize=15, spaceAfter=3 * mm
        )
        self._creneau = ParagraphStyle(
            "creneau_deroule",
            parent=styles["Heading2"],
            fontSize=13,
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
        )
        self._info = ParagraphStyle("info_deroule", parent=styles["Normal"], fontSize=11)

    def deroule_horaire(self, document: DerouleImprime) -> bytes:
        """Rend le document en PDF. Enveloppe tout échec en `InfrastructureError`."""
        try:
            return self._rendre(self._corps(document))
        # ReportLab lève une famille d'exceptions hétérogène : on enveloppe (aucune fuite brute).
        except Exception as exc:
            raise InfrastructureError("Échec de génération du PDF du déroulé horaire.") from exc

    def _corps(self, document: DerouleImprime) -> list[Flowable]:
        elements: list[Flowable] = [
            Paragraph(f"Déroulé horaire — {echapper(document.tournoi)}", self._titre)
        ]
        for bloc in document.blocs:
            elements.append(KeepTogether(self._bloc(bloc)))
        return elements

    def _bloc(self, bloc: BlocDeroule) -> list[Flowable]:
        entete = Paragraph(echapper(bloc.libelle), self._creneau)
        if not bloc.lignes:
            return [entete, Paragraph("Aucune phase au déroulé.", self._info), Spacer(1, 2 * mm)]
        # Cellules de `Table` : chaînes **brutes**, jamais échappées (cf. `_commun.echapper`).
        table = Table(
            [_ENTETE, *(_cellules(ligne) for ligne in bloc.lignes)],
            colWidths=_LARGEURS,
            repeatRows=1,
        )
        table.setStyle(_STYLE_TABLE)
        return [entete, table]

    def _rendre(self, elements: list[Flowable]) -> bytes:
        tampon = BytesIO()
        document = SimpleDocTemplate(
            tampon,
            pagesize=A4,
            title="Déroulé horaire",
            topMargin=_MARGE,
            bottomMargin=_MARGE,
            leftMargin=_MARGE,
            rightMargin=_MARGE,
        )
        document.build(elements)
        return tampon.getvalue()


def _cellules(ligne: LigneDeroule) -> list[str]:
    return [
        ligne.titre or LIBELLES_TYPE_PHASE[ligne.type],
        _heure(ligne.debut),
        _heure(ligne.fin),
        ligne.tours or "",
    ]


def _heure(heure: HeurePrevue | None) -> str:
    if heure is None:
        return A_PRECISER
    if heure.jours_apres:
        return f"{heure.libelle} (J+{heure.jours_apres})"
    return heure.libelle
