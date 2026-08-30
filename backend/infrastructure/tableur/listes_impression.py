"""Rendu CSV des listes — placement, et club & paiement (E16US007).

Même port que le rendu PDF : le service compose **un** contenu, le format n'agit qu'ici.

⚠️ Les trois choix qui font que le fichier s'ouvre vraiment (BOM, point-virgule, montants sans
symbole) et l'absence de totaux sont motivés en
[ADR-0101 §4](../../../docs/adr/0101-le-catalogue-d-exports-porte-les-formats-pas-les-url.md).
"""

from __future__ import annotations

import csv
import io

from domain.listes_impression import (
    ListeClubPaiement,
    ListePlacement,
    StatutPaiement,
)
from infrastructure.erreurs import InfrastructureError

_SEPARATEUR = ";"

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


class GenerateurListesImpressionCsv:
    """Adapter CSV du port `GenerateurListesImpression` (E16US007)."""

    def placement(self, liste: ListePlacement) -> bytes:
        """Rend la liste de placement en CSV (une ligne par archer placé, en-tête compris)."""
        return _rendre(
            _ENTETE_PLACEMENT,
            [
                (
                    str(ligne.depart_numero),
                    str(ligne.cible_index),
                    ligne.position,
                    ligne.nom,
                    ligne.prenom,
                    ligne.categorie,
                )
                for ligne in liste.lignes
            ],
        )

    def club_paiement(self, liste: ListeClubPaiement) -> bytes:
        """Rend la liste club & paiement en CSV — **une ligne par archer**, le club en colonne."""
        return _rendre(
            _ENTETE_CLUB_PAIEMENT,
            [
                (
                    groupe.club,
                    ligne.nom,
                    ligne.prenom,
                    " ".join(str(numero) for numero in ligne.departs),
                    str(ligne.nb_departs),
                    _montant(ligne.du_centimes),
                    _montant(ligne.paye_centimes),
                    _montant(ligne.reste_centimes),
                    _libelle_statut(ligne.statut),
                )
                for groupe in liste.groupes
                for ligne in groupe.lignes
            ],
        )


def _rendre(entete: tuple[str, ...], lignes: list[tuple[str, ...]]) -> bytes:
    try:
        tampon = io.StringIO(newline="")
        # `\r\n` : fin de ligne attendue par la RFC 4180 et par Excel sous Windows.
        redacteur = csv.writer(tampon, delimiter=_SEPARATEUR, lineterminator="\r\n")
        redacteur.writerow(entete)
        redacteur.writerows(lignes)
        return tampon.getvalue().encode("utf-8-sig")
    except Exception as echec:  # pragma: no cover - défense, `csv` n'échoue pas sur du `str`
        raise InfrastructureError("Échec du rendu CSV de la liste.") from echec


def _montant(centimes: int) -> str:
    """Montant en euros, virgule décimale et **sans symbole** — pour rester sommable au tableur."""
    return f"{centimes / 100:.2f}".replace(".", ",")


def _libelle_statut(statut: StatutPaiement) -> str:
    """Statut en clair. `RIEN` vaut « — » côté domaine : illisible en colonne filtrable."""
    return "" if statut is StatutPaiement.RIEN else statut.value
