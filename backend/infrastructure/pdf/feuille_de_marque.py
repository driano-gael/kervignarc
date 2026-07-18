"""Adapter ReportLab du port `GenerateurFeuilleDeMarque` (socle PDF, E09US001 — ADR-0031).

Rend une `FeuilleDeMarque` (décrite par le domaine) en octets PDF : **une page par archer placé**,
avec son en-tête d'identité (tournoi, départ, cible, position, catégorie, blason) et une **grille de
scores vierge** dimensionnée par le barème (volées et flèches) — les « zones de scores » à remplir à
la main, plus les colonnes *total de volée* et *cumul* de la feuille FFTA (référentiel §6.1).

Seule couche à importer ReportLab (règle 1 : le domaine et l'application n'en dépendent pas). Toute
défaillance de rendu est **enveloppée** en `InfrastructureError` (ADR-0007) : aucune exception de
bibliothèque brute ne remonte ; à la frontière API elle devient un 500 au message générique.
"""

from __future__ import annotations

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

from domain.feuille_marque import FeuilleDeMarque, LigneArcher
from infrastructure.erreurs import InfrastructureError

_MARGE = 15 * mm


class GenerateurFeuilleDeMarquePdf:
    """Implémentation ReportLab du port `GenerateurFeuilleDeMarque`."""

    def __init__(self) -> None:
        styles = getSampleStyleSheet()
        self._titre = ParagraphStyle(
            "titre", parent=styles["Title"], fontSize=15, spaceAfter=2 * mm
        )
        self._entete = ParagraphStyle("entete", parent=styles["Normal"], fontSize=11, leading=15)
        self._info = ParagraphStyle("info", parent=styles["Normal"], fontSize=11)

    def generer(self, feuille: FeuilleDeMarque) -> bytes:
        """Rend la feuille de marque en un document PDF (octets). Enveloppe tout échec en
        `InfrastructureError`."""
        try:
            return self._rendre(feuille)
        except InfrastructureError:
            raise
        # ReportLab lève une famille d'exceptions hétérogène (police, mise en page) : on enveloppe.
        except Exception as exc:
            raise InfrastructureError("Échec de génération du PDF de feuille de marque.") from exc

    def _rendre(self, feuille: FeuilleDeMarque) -> bytes:
        tampon = BytesIO()
        document = SimpleDocTemplate(
            tampon,
            pagesize=A4,
            title="Feuille de marque",
            topMargin=_MARGE,
            bottomMargin=_MARGE,
            leftMargin=_MARGE,
            rightMargin=_MARGE,
        )
        elements: list[Flowable] = []
        if not feuille.archers:
            elements.append(Paragraph("Aucun archer placé sur ce départ.", self._info))
        for rang, ligne in enumerate(feuille.archers):
            if rang > 0:
                elements.append(PageBreak())
            elements.extend(self._page_archer(feuille, ligne))
        document.build(elements)
        return tampon.getvalue()

    def _page_archer(self, feuille: FeuilleDeMarque, ligne: LigneArcher) -> list[Flowable]:
        """Le contenu d'une page : en-tête d'identité + grille de scores vierge."""
        entete = (
            f"<b>{_echapper(ligne.prenom)} {_echapper(ligne.nom)}</b> — "
            f"{_echapper(ligne.categorie)}<br/>"
            f"Cible <b>{ligne.cible_index}</b> · Position <b>{_echapper(ligne.position)}</b> · "
            f"Blason {_echapper(ligne.blason)}"
        )
        return [
            Paragraph(
                f"Feuille de marque — {_echapper(feuille.tournoi)} · "
                f"Départ {feuille.depart_numero}",
                self._titre,
            ),
            Paragraph(entete, self._entete),
            Spacer(1, 6 * mm),
            self._grille(feuille.nb_volees, feuille.nb_fleches_par_volee),
        ]

    def _grille(self, nb_volees: int, nb_fleches_par_volee: int) -> Table:
        """Grille vierge : une ligne par volée, une colonne par flèche + total de volée + cumul."""
        entete = (
            ["Volée"]
            + [f"F{numero}" for numero in range(1, nb_fleches_par_volee + 1)]
            + ["Total", "Cumul"]
        )
        lignes = [
            [str(volee)] + [""] * (nb_fleches_par_volee + 2) for volee in range(1, nb_volees + 1)
        ]
        table = Table([entete, *lignes], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 1), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
                ]
            )
        )
        return table


def _echapper(texte: str) -> str:
    """Neutralise les caractères spéciaux du mini-HTML des `Paragraph` ReportLab.

    Un nom d'archer contenant `&`, `<` ou `>` casserait le balisage : on l'échappe pour que la
    feuille reste conforme à la donnée, quel que soit le texte saisi."""
    return texte.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
