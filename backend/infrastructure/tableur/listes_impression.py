"""Rendu tableur des listes — placement, et club & paiement (E16US007, E16US016).

Même port que le rendu PDF : le service compose **un** contenu, le format n'agit qu'ici.

⚠️ **Une classe, deux formats** (ADR-0101 §6) : recopier ces colonnes pour changer de format est le
mode de panne de `DETTE-085`. Ce qui rend le fichier ouvrable est motivé en
[ADR-0101 §4](../../../docs/adr/0101-le-catalogue-d-exports-porte-les-formats-pas-les-url.md).
"""

from __future__ import annotations

from domain.listes_impression import (
    ListeClubPaiement,
    ListePlacement,
    StatutPaiement,
)
from infrastructure.tableur.grille import Cellule, Grille, Montant, RenduTableur

_ENTETE_PLACEMENT = ("Départ", "Cible", "Couloir", "Nom", "Prénom", "Catégorie")
_ENTETE_CLUB_PAIEMENT = (
    "Club",
    "Nom",
    "Prénom",
    "Départs",
    "Nb départs",
    "Dû",
    "Payé",
    "Reste",
    "Réglé",
)


class GenerateurListesImpressionTableur:
    """Adapter tableur du port `GenerateurListesImpression` — un rendu par instance."""

    def __init__(self, rendu: RenduTableur) -> None:
        self._rendu = rendu

    def placement(self, liste: ListePlacement) -> bytes:
        """Rend la liste de placement (une ligne par archer placé, en-tête compris)."""
        lignes: tuple[tuple[Cellule, ...], ...] = tuple(
            (
                ligne.depart_numero,
                ligne.cible_index,
                ligne.position,
                ligne.nom,
                ligne.prenom,
                ligne.categorie,
            )
            for ligne in liste.lignes
        )
        return self._rendu(Grille(_ENTETE_PLACEMENT, lignes, titre="Placement"))

    def club_paiement(self, liste: ListeClubPaiement) -> bytes:
        """Rend la liste club & paiement — **une ligne par archer**, le club en colonne."""
        lignes: tuple[tuple[Cellule, ...], ...] = tuple(
            (
                groupe.club,
                ligne.nom,
                ligne.prenom,
                " ".join(str(numero) for numero in ligne.departs),
                ligne.nb_departs,
                Montant(ligne.du_centimes),
                Montant(ligne.paye_centimes),
                Montant(ligne.reste_centimes),
                _libelle_statut(ligne.statut),
            )
            for groupe in liste.groupes
            for ligne in groupe.lignes
        )
        return self._rendu(Grille(_ENTETE_CLUB_PAIEMENT, lignes, titre="Club et paiement"))


def _libelle_statut(statut: StatutPaiement) -> str:
    """Statut en clair. `RIEN` vaut « — » côté domaine : illisible en colonne filtrable."""
    return "" if statut is StatutPaiement.RIEN else statut.value
