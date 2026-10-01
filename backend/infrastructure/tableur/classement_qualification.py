"""Rendu tableur du classement de qualification — **à plat**, une ligne par archer (E09US005).

Le PDF pagine par catégorie ; le tableur ne le fait pas, et c'est voulu (ADR-0101 §4) : départ,
catégorie et provisoire deviennent des **colonnes**, qui se trient et se filtrent.
"""

from __future__ import annotations

from domain.classement import StatutClassement
from domain.classement_imprime import ClassementQualificationImprime
from infrastructure.tableur.grille import Cellule, Grille, RenduTableur
from infrastructure.tableur.palmares import LIBELLES_STATUT

_ENTETE = (
    "Départ",
    "Catégorie",
    "Rang catégorie",
    "Rang général",
    "Nom",
    "Prénom",
    "Club",
    "Total",
    "10",
    "9",
    "Statut",
    "Classement",
)


class GenerateurClassementQualificationTableur:
    """Adapter tableur du port `GenerateurClassementQualification` — un rendu par instance."""

    def __init__(self, rendu: RenduTableur) -> None:
        self._rendu = rendu

    def classement_qualification(self, document: ClassementQualificationImprime) -> bytes:
        """⚠️ Le rang n'est pas unique dans sa colonne : chaque créneau recommence à 1."""
        lignes: tuple[tuple[Cellule, ...], ...] = tuple(
            (
                section.libelle,
                bloc.libelle,
                _rang(ligne.rang_categorie),
                _rang(ligne.rang_scratch),
                ligne.nom,
                ligne.prenom,
                document.clubs.get(ligne.club_id, "") if ligne.club_id is not None else "",
                ligne.total,
                ligne.nb_dix,
                ligne.nb_neuf,
                ""
                if ligne.statut is StatutClassement.EN_LICE
                else LIBELLES_STATUT.get(ligne.statut, ligne.statut.value),
                "Provisoire" if section.provisoire else "Définitif",
            )
            for section in document.sections
            for bloc in section.categories
            for ligne in bloc.lignes
        )
        return self._rendu(Grille(_ENTETE, lignes, titre="Classement qualification"))


def _rang(rang: int | None) -> str:
    """En **texte**, comme le palmarès : vide pour un disqualifié, et une colonne homogène."""
    return "" if rang is None else str(rang)
