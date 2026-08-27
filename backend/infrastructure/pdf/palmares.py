"""Rendu PDF du palmarès — **les podiums d'abord** : sans eux, 120 lignes obligent à parcourir les
pages pour retrouver les médaillés. Document tabulaire (ADR-0031).

⚠️ **Toute défaillance de rendu est enveloppée en `InfrastructureError`** : aucune exception de
bibliothèque brute ne remonte.
"""

from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from domain.classement import StatutClassement
from domain.palmares import LignePalmares, Palmares
from infrastructure.erreurs import InfrastructureError
from infrastructure.pdf._commun import echapper as _echapper

_MARGE = 15 * mm

_STYLE_TABLE = TableStyle(
    [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
)

_MEDAILLES = {1: "Or", 2: "Argent", 3: "Bronze"}
"""Les trois métaux, pour que le podium imprimé se lise sans compter les lignes. Le 4ᵉ n'en a pas —
il figure au podium (la petite finale l'a décerné) mais ne reçoit rien."""


class GenerateurPalmaresPdf:
    """Implémentation ReportLab du port `GenerateurPalmares`."""

    def __init__(self) -> None:
        styles = getSampleStyleSheet()
        self._titre = ParagraphStyle(
            "titre_palmares", parent=styles["Title"], fontSize=15, spaceAfter=2 * mm
        )
        self._sous_titre = ParagraphStyle(
            "sous_titre_palmares", parent=styles["Normal"], fontSize=10, textColor="#555555"
        )
        self._section = ParagraphStyle(
            "section_palmares",
            parent=styles["Heading2"],
            fontSize=12,
            spaceBefore=5 * mm,
            spaceAfter=1 * mm,
        )
        self._info = ParagraphStyle("info_palmares", parent=styles["Normal"], fontSize=11)

    def palmares(self, tournoi: str, palmares: Palmares) -> bytes:
        """Rend le palmarès en PDF. Enveloppe tout échec en `InfrastructureError`."""
        try:
            return self._rendre("Palmarès", self._corps(tournoi, palmares))
        # ReportLab lève une famille d'exceptions hétérogène : on enveloppe (aucune fuite brute).
        except Exception as exc:
            raise InfrastructureError("Échec de génération du PDF du palmarès.") from exc

    def _corps(self, tournoi: str, palmares: Palmares) -> list[Flowable]:
        elements: list[Flowable] = [
            Paragraph(f"Palmarès — {_echapper(tournoi)}", self._titre),
            Paragraph("Podiums par catégorie, puis classement complet", self._sous_titre),
            Spacer(1, 4 * mm),
        ]
        if not palmares.lignes:
            elements.append(Paragraph("Aucun archer classé.", self._info))
            return elements
        elements.extend(self._podiums(palmares))
        elements.append(Paragraph("Classement complet", self._section))
        elements.append(self._table_classement(palmares.lignes))
        return elements

    def _podiums(self, palmares: Palmares) -> list[Flowable]:
        """Un bloc par catégorie — et rien du tout pour celles dont aucun rang n'est décerné.

        Un podium vide s'imprimerait comme un tableau à en-tête seul, que le lecteur prendrait
        pour une catégorie sans archers plutôt que pour une finale non encore tirée.
        """
        elements: list[Flowable] = []
        for categorie_id, libelle in palmares.categories():
            podium = palmares.podium(categorie_id)
            if not podium:
                continue
            elements.append(Paragraph(f"Podium — {_echapper(libelle)}", self._section))
            table = Table(
                [
                    ["Rang", "Médaille", "Nom", "Prénom"],
                    *[
                        [
                            _rang(ligne.rang_categorie_min, ligne.rang_categorie_max),
                            _medaille(ligne),
                            ligne.nom,
                            ligne.prenom,
                        ]
                        for ligne in podium
                    ],
                ],
                repeatRows=1,
            )
            table.setStyle(_STYLE_TABLE)
            elements.append(table)
        return elements

    def _table_classement(self, lignes: tuple[LignePalmares, ...]) -> Table:
        entete = ["Rang", "Cat.", "Nom", "Prénom", "Catégorie", "Statut"]
        # Cellules de `Table` : chaînes **brutes** — ReportLab les dessine telles quelles
        # (`drawString`), sans passer par le parseur mini-HTML des `Paragraph`. Les échapper y
        # afficherait « Dupont &amp; Cie » au lieu de « Dupont & Cie ».
        corps = [
            [
                _rang(ligne.rang_min, ligne.rang_max),
                _rang(ligne.rang_categorie_min, ligne.rang_categorie_max),
                ligne.nom,
                ligne.prenom,
                ligne.categorie_libelle,
                _libelle_statut(ligne.statut),
            ]
            for ligne in lignes
        ]
        table = Table([entete, *corps], repeatRows=1)
        table.setStyle(_STYLE_TABLE)
        return table

    def _rendre(self, sujet: str, elements: list[Flowable]) -> bytes:
        tampon = BytesIO()
        document = SimpleDocTemplate(
            tampon,
            # Portrait, contrairement aux listes d'organisation : six colonnes étroites, et le
            # document est fait pour être **affiché au mur**, où le portrait se lit de plus loin.
            pagesize=A4,
            title=sujet,
            topMargin=_MARGE,
            bottomMargin=_MARGE,
            leftMargin=_MARGE,
            rightMargin=_MARGE,
        )
        document.build(elements)
        return tampon.getvalue()


def _medaille(ligne: LignePalmares) -> str:
    """Le métal, suivi de sa **provenance** quand aucun match ne l'a décerné.

    Le moteur ne monte qu'un seul tableau scratch (`DETTE-028`) : dans la plupart des catégories,
    le bronze est rangé par le **classement de qualification** faute d'un match qui les départage.
    Le podium l'affiche quand même (arbitrage du 03/08/2026 — l'amputer laissait la majorité des
    catégories sans médailles), mais le document **le dit** : c'est le mur du gymnase, et une
    médaille dont on ignore d'où elle vient s'y discute toute la soirée.
    """
    metal = _MEDAILLES.get(ligne.rang_categorie_min or 0, "—")
    return metal if ligne.decerne else f"{metal} (au classement)"


def _rang(minimum: int | None, maximum: int | None) -> str:
    """« 3 », « 5-8 » ou « — » (hors classement) — la fourchette **s'imprime telle quelle**.

    Un ex æquo publié en « 5ᵉ-8ᵉ » est le résultat exact du tournoi quand aucun match n'a
    départagé les quatre battus ; choisir un chiffre sur le papier ferait dire au document ce que
    la compétition n'a pas décidé.
    """
    if minimum is None or maximum is None:
        return "—"
    return str(minimum) if minimum == maximum else f"{minimum}-{maximum}"


def _libelle_statut(statut: StatutClassement) -> str:
    """Libellé imprimé du statut (ADR-0050) — vide pour le cas normal, qui n'a rien à signaler."""
    if statut is StatutClassement.ABANDON:
        return "Abandon"
    if statut is StatutClassement.DISQUALIFIE:
        return "Disqualifié"
    return ""
