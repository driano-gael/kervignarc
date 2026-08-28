"""Rendu PDF des documents de salle — seule couche à importer ReportLab (règle 1).

Le QR est produit **nativement** par ReportLab : pas de dépendance supplémentaire (règle 11).

⚠️ **Toute défaillance de rendu est enveloppée en `InfrastructureError`** (ADR-0007) : aucune
exception de bibliothèque brute ne remonte — à la frontière, elle devient un 500 générique.
"""

from __future__ import annotations

from io import BytesIO

from reportlab.graphics import renderSVG
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Flowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer

from domain.documents_salle import CartesScoreurs, EtiquettesCibles
from infrastructure.erreurs import InfrastructureError
from infrastructure.pdf._commun import echapper as _echapper

_MARGE = 15 * mm
_COTE_QR = 90 * mm
# Côté du QR **écran** (E11US008), en points : ne fixe que les dimensions intrinsèques du SVG —
# vectoriel, il est ensuite mis à l'échelle par le CSS (vignette puis plein écran pour le scan).
_COTE_QR_ECRAN = 320.0


class GenerateurDocumentsSallePdf:
    """Implémentation ReportLab du port `GenerateurDocumentsSalle`."""

    def __init__(self) -> None:
        styles = getSampleStyleSheet()
        self._titre = ParagraphStyle(
            "titre_salle", parent=styles["Title"], fontSize=15, spaceAfter=4 * mm
        )
        self._sujet = ParagraphStyle(
            "sujet_salle",
            parent=styles["Title"],
            fontSize=26,
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
        )
        self._code = ParagraphStyle(
            "code_salle",
            parent=styles["Title"],
            fontName="Courier-Bold",
            fontSize=34,
            spaceBefore=6 * mm,
            spaceAfter=4 * mm,
        )
        self._aide = ParagraphStyle(
            "aide_salle", parent=styles["Normal"], fontSize=11, alignment=1, textColor="#555555"
        )

    # --- Étiquettes de cible ---

    def etiquettes_cibles(self, document: EtiquettesCibles) -> bytes:
        """Rend les étiquettes de cible en PDF. Enveloppe tout échec en `InfrastructureError`."""
        try:
            return self._rendre(
                document.nom_tournoi, "Étiquettes de cible", self._pages_cibles(document)
            )
        except InfrastructureError:
            raise
        # ReportLab (QR compris) lève une famille d'exceptions hétérogène : on enveloppe.
        except Exception as exc:
            raise InfrastructureError(
                "Échec de génération du PDF des étiquettes de cible."
            ) from exc

    def _pages_cibles(self, document: EtiquettesCibles) -> list[Flowable]:
        if not document.etiquettes:
            return [Paragraph("Aucune cible préparée pour ce tournoi.", self._aide)]
        pages: list[Flowable] = []
        for rang, etiquette in enumerate(document.etiquettes):
            if rang > 0:
                pages.append(PageBreak())
            pages.extend(
                [
                    Paragraph(_echapper(document.nom_tournoi), self._titre),
                    Paragraph(f"Cible {etiquette.cible_index}", self._sujet),
                    _dessin_qr(etiquette.url, _COTE_QR),
                    Paragraph(_echapper(etiquette.code), self._code),
                    Spacer(1, 4 * mm),
                    Paragraph(
                        "Scannez ce QR pour rattacher la tablette à cette cible "
                        "(ou saisissez le code ci-dessus).",
                        self._aide,
                    ),
                ]
            )
        return pages

    # --- Cartes de scoreur ---

    def cartes_scoreurs(self, document: CartesScoreurs) -> bytes:
        """Rend les cartes de scoreur en PDF. Enveloppe tout échec en `InfrastructureError`."""
        try:
            return self._rendre(
                document.nom_tournoi, "Cartes de scoreur", self._pages_scoreurs(document)
            )
        except InfrastructureError:
            raise
        except Exception as exc:
            raise InfrastructureError("Échec de génération du PDF des cartes de scoreur.") from exc

    def _pages_scoreurs(self, document: CartesScoreurs) -> list[Flowable]:
        if not document.cartes:
            return [Paragraph("Aucun scoreur défini pour ce tournoi.", self._aide)]
        pages: list[Flowable] = []
        for rang, carte in enumerate(document.cartes):
            if rang > 0:
                pages.append(PageBreak())
            pages.extend(
                [
                    Paragraph(_echapper(document.nom_tournoi), self._titre),
                    Paragraph(_echapper(carte.nom), self._sujet),
                    Paragraph(_echapper(carte.code), self._code),
                    Spacer(1, 4 * mm),
                    Paragraph(
                        "Code personnel — à saisir sur une tablette pour valider les scores.",
                        self._aide,
                    ),
                ]
            )
        return pages

    # --- QR de rattachement à l'écran (E11US008) ---

    def qr_rattachement(self, url: str) -> bytes:
        """Rend le QR de rattachement d'une cible en **SVG** (octets UTF-8). Écran, pas impression.

        Réutilise `_dessin_qr` (le même widget QR natif que l'étiquette PDF) mais le sérialise via
        le backend **SVG** de ReportLab (`renderSVG`, pur Python — aucune dépendance ajoutée,
        contrairement au backend raster `renderPM` qui exigerait `rlPyCairo`). Enveloppe tout échec
        de rendu en `InfrastructureError` (ADR-0007), comme les deux méthodes PDF.
        """
        try:
            # `renderSVG.drawToString` renvoie du texte SVG (typé `Any` faute de stubs ReportLab) :
            # `str(...)` fige le type, `.encode` donne les octets attendus par la frontière.
            return str(renderSVG.drawToString(_dessin_qr(url, _COTE_QR_ECRAN))).encode("utf-8")
        except InfrastructureError:
            raise
        except Exception as exc:
            raise InfrastructureError("Échec de génération du QR de rattachement.") from exc

    # --- Rendu commun ---

    def _rendre(self, titre_doc: str, sujet_pdf: str, elements: list[Flowable]) -> bytes:
        tampon = BytesIO()
        document = SimpleDocTemplate(
            tampon,
            pagesize=A4,
            title=f"{sujet_pdf} — {titre_doc}",
            topMargin=_MARGE,
            bottomMargin=_MARGE,
            leftMargin=_MARGE,
            rightMargin=_MARGE,
        )
        document.build(elements)
        return tampon.getvalue()


def _dessin_qr(url: str, cote: float) -> Drawing:
    """Un `Drawing` carré de `cote` points portant le QR de `url`, centré dans le flux Platypus.

    `QrCodeWidget` dessine à une échelle de module fixe : on récupère ses bornes réelles
    (`getBounds`) et on applique une `transform` d'échelle pour le carré voulu (recette ReportLab).
    """
    widget = QrCodeWidget(url)
    x1, y1, x2, y2 = widget.getBounds()
    largeur, hauteur = x2 - x1, y2 - y1
    dessin = Drawing(cote, cote, transform=[cote / largeur, 0, 0, cote / hauteur, 0, 0])
    dessin.add(widget)
    dessin.hAlign = "CENTER"
    return dessin
