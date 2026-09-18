"""Rendu tableur du **journal d'audit** — la trace reprise dans un tableur (E16US016).

⚠️ Pas de rendu PDF pour ce document, et c'est un choix : un journal dépasse couramment le millier
de lignes. Le registre câblé le dit tout seul au catalogue (ADR-0101 §5).
"""

from __future__ import annotations

from domain.entree_audit import JournalAudit
from infrastructure.tableur.tableau import Cellule, RenduTableur, Tableau

_ENTETE = ("Horodatage", "Auteur", "Action", "Objet", "Avant", "Après")

# Horodatage **UTC**, écrit tel qu'il est stocké — le fuseau n'est pas rendu implicite : un
# « 10 h 12 » sans repère ne prouve rien dans un litige, qui est le seul usage de ce document.
_FORMAT_HORODATAGE = "%Y-%m-%d %H:%M:%S UTC"


class GenerateurJournalAuditTableur:
    """Adapter tableur du port `GenerateurJournalAudit` — un rendu par instance."""

    def __init__(self, rendu: RenduTableur) -> None:
        self._rendu = rendu

    def journal(self, journal: JournalAudit) -> bytes:
        """Rend le journal, une ligne par entrée, dans l'ordre chronologique reçu."""
        lignes: tuple[tuple[Cellule, ...], ...] = tuple(
            (
                entree.horodatage.strftime(_FORMAT_HORODATAGE),
                entree.auteur,
                entree.action.value,
                entree.objet,
                entree.avant or "",
                entree.apres or "",
            )
            for entree in journal.entrees
        )
        return self._rendu(Tableau(_ENTETE, lignes))
