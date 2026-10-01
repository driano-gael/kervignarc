"""Rendu tableur du classement de qualification — **à plat**, une ligne par archer (E09US005).

Le PDF pagine par catégorie ; le tableur ne le fait pas, et c'est voulu (ADR-0101 §4) : départ,
catégorie et provisoire deviennent des **colonnes**, qui se trient et se filtrent.
"""

from __future__ import annotations

from domain.classement_imprime import ClassementQualificationImprime
from infrastructure.libelles import libelle_statut
from infrastructure.tableur.grille import Cellule, Grille, RenduTableur

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
                libelle_statut(ligne.statut),
                "Provisoire" if section.provisoire else "Définitif",
            )
            for section in document.sections
            for bloc in section.categories
            for ligne in bloc.lignes
        )
        return self._rendu(Grille(_ENTETE, lignes, titre="Classement qualification"))


def _rang(rang: int | None) -> Cellule:
    """Un **nombre**, pour que la colonne se trie 1, 2, … 10 et non 1, 10, 2 (revue, axe D).

    Le palmarès écrit ses rangs en texte parce qu'ils sont des fourchettes (« 5-8 ») ; ici un rang
    est exact ou absent. Vide pour un disqualifié, qui n'est pas rangé (ADR-0050).
    """
    return "" if rang is None else rang
