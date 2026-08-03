"""Adapter ReportLab du port `GenerateurListesImpression` (E09US003, socle PDF ADR-0031).

Rend les deux listes papier d'organisation :

- `placement` : un tableau **archer → départ / cible / position** (une ligne par archer placé),
  ordonné en amont par le service (par cible ou par nom) — pour l'accueil des archers ;
- `club_paiement` : un bloc **par club**, tableau des archers (départs, dû, payé, statut) suivi de
  la ligne de total du club — pour l'administratif.

Documents **tabulaires** : le point fort de ReportLab (`Table`/`TableStyle`), pas de mise en page
libre (ADR-0031). Seule couche à importer ReportLab (règle 1). Toute défaillance de rendu est
**enveloppée** en `InfrastructureError` (ADR-0007) : aucune exception de bibliothèque brute ne
remonte ; à la frontière API elle devient un 500 au message générique.
"""

from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
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

from domain.listes_impression import (
    GroupePaiementClub,
    ListeClubPaiement,
    ListePlacement,
    StatutPaiement,
    TriPlacement,
)
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


class GenerateurListesImpressionPdf:
    """Implémentation ReportLab du port `GenerateurListesImpression`."""

    def __init__(self) -> None:
        styles = getSampleStyleSheet()
        self._titre = ParagraphStyle(
            "titre_liste", parent=styles["Title"], fontSize=15, spaceAfter=2 * mm
        )
        self._sous_titre = ParagraphStyle(
            "sous_titre_liste", parent=styles["Normal"], fontSize=10, textColor="#555555"
        )
        self._club = ParagraphStyle(
            "club_liste",
            parent=styles["Heading2"],
            fontSize=12,
            spaceBefore=5 * mm,
            spaceAfter=1 * mm,
        )
        self._info = ParagraphStyle("info_liste", parent=styles["Normal"], fontSize=11)

    # --- Liste de placement ---

    def placement(self, liste: ListePlacement) -> bytes:
        """Rend la liste de placement en PDF. Enveloppe tout échec en `InfrastructureError`."""
        try:
            return self._rendre("Liste de placement", self._corps_placement(liste))
        # ReportLab lève une famille d'exceptions hétérogène : on enveloppe (aucune fuite brute).
        except Exception as exc:
            raise InfrastructureError(
                "Échec de génération du PDF de la liste de placement."
            ) from exc

    def _corps_placement(self, liste: ListePlacement) -> list[Flowable]:
        portee = (
            f"Départ {liste.depart_numero}"
            if liste.depart_numero is not None
            else "Tout le tournoi"
        )
        tri = "cible" if liste.tri is TriPlacement.CIBLE else "nom"
        elements: list[Flowable] = [
            Paragraph(f"Liste de placement — {_echapper(liste.tournoi)}", self._titre),
            Paragraph(f"{portee} · trié par {tri}", self._sous_titre),
            Spacer(1, 4 * mm),
        ]
        if not liste.lignes:
            elements.append(Paragraph("Aucun archer placé.", self._info))
            return elements
        entete = ["Départ", "Cible", "Pos.", "Nom", "Prénom", "Catégorie"]
        # Cellules de `Table` : chaînes **brutes** — ReportLab les dessine telles quelles
        # (`drawString`), sans passer par le parseur mini-HTML des `Paragraph`. Les échapper y
        # afficherait « Dupont &amp; Cie » au lieu de « Dupont & Cie » (le mini-HTML ne vaut que
        # pour les `Paragraph`, cf. titres ci-dessus et en-têtes de club).
        corps = [
            [
                str(ligne.depart_numero),
                str(ligne.cible_index),
                ligne.position,
                ligne.nom,
                ligne.prenom,
                ligne.categorie,
            ]
            for ligne in liste.lignes
        ]
        table = Table([entete, *corps], repeatRows=1)
        table.setStyle(_STYLE_TABLE)
        elements.append(table)
        return elements

    # --- Liste club & paiement ---

    def club_paiement(self, liste: ListeClubPaiement) -> bytes:
        """Rend la liste club & paiement en PDF. Enveloppe tout échec en `InfrastructureError`."""
        try:
            return self._rendre("Liste club & paiement", self._corps_club_paiement(liste))
        except Exception as exc:
            raise InfrastructureError(
                "Échec de génération du PDF de la liste club & paiement."
            ) from exc

    def _corps_club_paiement(self, liste: ListeClubPaiement) -> list[Flowable]:
        elements: list[Flowable] = [
            Paragraph(f"Liste club & paiement — {_echapper(liste.tournoi)}", self._titre),
            Spacer(1, 2 * mm),
        ]
        if not liste.groupes:
            elements.append(Paragraph("Aucun archer inscrit.", self._info))
            return elements
        for groupe in liste.groupes:
            elements.append(Paragraph(_echapper(groupe.club), self._club))
            elements.append(self._table_club(groupe))
        return elements

    def _table_club(self, groupe: GroupePaiementClub) -> Table:
        entete = ["Nom", "Prénom", "Départs", "Nb", "Dû", "Payé", "Réglé"]
        # Chaînes brutes en cellules de `Table` (pas d'échappement — cf. `_corps_placement`).
        corps = [
            [
                ligne.nom,
                ligne.prenom,
                ", ".join(str(numero) for numero in ligne.departs) or "—",
                str(ligne.nb_departs),
                _euros(ligne.du_centimes),
                _euros(ligne.paye_centimes),
                _libelle_statut(ligne.statut),
            ]
            for ligne in groupe.lignes
        ]
        total = [
            "Total",
            "",
            "",
            "",
            _euros(groupe.total_du_centimes),
            _euros(groupe.total_paye_centimes),
            "",
        ]
        table = Table([entete, *corps, total], repeatRows=1)
        style = TableStyle(_STYLE_TABLE.getCommands())
        # Ligne de total : fond distinct et gras (dernière ligne du tableau du club).
        style.add("BACKGROUND", (0, -1), (-1, -1), colors.whitesmoke)
        style.add("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")
        table.setStyle(style)
        return table

    # --- Rendu commun ---

    def _rendre(self, sujet: str, elements: list[Flowable]) -> bytes:
        tampon = BytesIO()
        document = SimpleDocTemplate(
            tampon,
            pagesize=landscape(A4),
            title=sujet,
            topMargin=_MARGE,
            bottomMargin=_MARGE,
            leftMargin=_MARGE,
            rightMargin=_MARGE,
        )
        document.build(elements)
        return tampon.getvalue()


def _euros(centimes: int) -> str:
    """Formate un montant en centimes entiers en euros (« 8,00 € »), séparateur décimal virgule."""
    return f"{centimes / 100:.2f} €".replace(".", ",")


def _libelle_statut(statut: StatutPaiement) -> str:
    """Libellé imprimé du statut de règlement (« Oui » / « Non » / « — »)."""
    if statut is StatutPaiement.PAYE:
        return "Oui"
    if statut is StatutPaiement.DU:
        return "Non"
    return "—"
