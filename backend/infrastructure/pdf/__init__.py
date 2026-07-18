"""Adapters de génération PDF (socle E09US001, ReportLab — ADR-0031).

Regroupe les implémentations des ports de rendu PDF du domaine. ReportLab est retenu pour son
embarquabilité (wheels autoportantes, aucune dépendance native, PyInstaller — ADR-0031) ; c'est le
seul endroit du code qui l'importe, les couches supérieures ne connaissant que les ports.
"""

from __future__ import annotations

from infrastructure.pdf.documents_salle import GenerateurDocumentsSallePdf
from infrastructure.pdf.feuille_de_marque import GenerateurFeuilleDeMarquePdf

__all__ = ["GenerateurDocumentsSallePdf", "GenerateurFeuilleDeMarquePdf"]
