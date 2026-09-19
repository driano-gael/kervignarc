"""Rendu tableur du **palmarès** — le classement final repris dans un tableur (E16US016).

Même port que le rendu PDF (`GenerateurPalmares`) : le service compose un contenu, le format
n'agit qu'ici. ⚠️ Le PDF et le tableur ne se **ressemblent pas**, et c'est voulu (ADR-0101 §4) :
le PDF ouvre sur les podiums — c'est l'affiche du mur —, le tableur rend **le classement à plat**,
une ligne par archer, parce qu'un podium recopié en blocs casse le tri et le filtre.
"""

from __future__ import annotations

from collections.abc import Sequence

from domain.classement import StatutClassement
from domain.palmares import LignePalmares, SectionPalmares
from domain.podium import ReglagePodiums
from infrastructure.tableur.grille import Cellule, Grille, RenduTableur

_ENTETE = (
    "Départ",
    "Rang",
    "Nom",
    "Prénom",
    "Catégorie",
    "Rang catégorie",
    "Club",
    "Rang club",
    "Statut",
)


class GenerateurPalmaresTableur:
    """Adapter tableur du port `GenerateurPalmares` — un rendu par instance."""

    def __init__(self, rendu: RenduTableur) -> None:
        self._rendu = rendu

    def palmares(
        self,
        tournoi: str,
        *,
        sections: Sequence[SectionPalmares],
        reglage: ReglagePodiums,
    ) -> bytes:
        """Rend le classement en tableur : c'est **`affiche`** qui sort, jamais `complet`.

        ⚠️ Rendre `complet` exporterait le tournoi entier à qui a demandé une catégorie.

        ⚠️ **Les créneaux tiennent dans UNE grille, colonne « Départ »** (E06US009) et non en N
        onglets : le parti de ce format est le classement à plat, qui se trie et se filtre. Donc
        **le rang n'est pas unique** dans sa colonne — chaque créneau recommence à 1.
        """
        lignes: tuple[tuple[Cellule, ...], ...] = tuple(
            (
                section.libelle,
                _rang(ligne.rang_min, ligne.rang_max),
                ligne.nom,
                ligne.prenom,
                ligne.categorie_libelle,
                _rang(ligne.rang_categorie_min, ligne.rang_categorie_max),
                ligne.club_libelle or "",
                _rang(ligne.rang_club_min, ligne.rang_club_max),
                _statut(ligne),
            )
            for section in sections
            for ligne in section.affiche.lignes
        )
        return self._rendu(Grille(_ENTETE, lignes, titre="Palmarès"))


def _rang(borne_min: int | None, borne_max: int | None) -> str:
    """Rend une fourchette de rangs : « 5 », « 5-8 », ou vide si l'archer est hors classement.

    ⚠️ Rendu en **texte** et non en nombre : « 5-8 » n'est pas sommable, et faire varier le type
    d'une colonne selon la ligne casse le tri du tableur bien plus sûrement qu'un texte homogène.
    """
    if borne_min is None or borne_max is None:
        return ""
    return str(borne_min) if borne_min == borne_max else f"{borne_min}-{borne_max}"


# Les **deux statuts de forfait** reprennent les mots du PDF (`infrastructure/pdf/palmares.py`) :
# le document du mur et celui de la presse nomment le même archer pareil (règle 3). « En cours » et
# « Acquis » sont propres au tableur — le PDF n'affiche rien pour un archer en lice.
# ⚠️ Registre jumeau de `StatutClassement`, gardé par `test_tableur_palmares.py`.
_LIBELLES_STATUT = {
    StatutClassement.ABANDON: "Abandon",
    StatutClassement.DISQUALIFIE: "Disqualifié",
}


def _statut(ligne: LignePalmares) -> str:
    """Ce que la ligne dit d'elle-même : une place acquise, une attente, ou un statut de forfait."""
    if ligne.statut is not StatutClassement.EN_LICE:
        return _LIBELLES_STATUT.get(ligne.statut, ligne.statut.value)
    if ligne.en_lice:
        return "En cours"
    return "Acquis" if ligne.decerne else ""
