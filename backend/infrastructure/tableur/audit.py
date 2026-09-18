"""Rendu tableur du **journal d'audit** — la trace reprise dans un tableur (E16US016).

⚠️ Pas de rendu PDF pour ce document, et c'est un choix : un journal dépasse couramment le millier
de lignes. Le registre câblé le dit tout seul au catalogue (ADR-0101 §5).
"""

from __future__ import annotations

from domain.entree_audit import ActionAuditee, JournalAudit
from infrastructure.tableur.grille import Cellule, Grille, RenduTableur

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
                _libelle_action(entree.action),
                entree.objet,
                entree.avant or "",
                entree.apres or "",
            )
            for entree in journal.entrees
        )
        return self._rendu(Grille(_ENTETE, lignes, titre="Journal d'audit"))


# Les mots de l'écran (`frontend/src/features/audit/presentation.ts`) : l'organisateur qui compare
# le tableau et le fichier lit le même acte deux fois, pas un libellé et un slug (règle 3).
# ⚠️ Registre jumeau d'`ActionAuditee` — le repli rend le slug brut plutôt qu'une case vide.
_LIBELLES_ACTION = {
    ActionAuditee.VALIDATION: "Validation",
    ActionAuditee.CORRECTION_SCORE: "Correction",
    ActionAuditee.ANNULATION_VALIDATION: "Annulation de validation",
    ActionAuditee.FORFAIT: "Forfait",
    ActionAuditee.REPLACEMENT: "Replacement",
    ActionAuditee.PAIEMENT: "Paiement",
    ActionAuditee.LANCEMENT: "Lancement",
    ActionAuditee.REMBOURSEMENT: "Remboursement",
}


def _libelle_action(action: ActionAuditee) -> str:
    """L'acte en clair ; repli sur le slug pour un membre neuf non encore traduit."""
    return _LIBELLES_ACTION.get(action, action.value)
