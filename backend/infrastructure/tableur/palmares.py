"""Rendu tableur du **palmarès** — le classement final repris dans un tableur (E16US016).

Même port que le rendu PDF (`GenerateurPalmares`) : le service compose un contenu, le format
n'agit qu'ici. ⚠️ Le PDF et le tableur ne se **ressemblent pas**, et c'est voulu (ADR-0101 §4) :
le PDF ouvre sur les podiums — c'est l'affiche du mur —, le tableur rend **le classement à plat**,
une ligne par archer, parce qu'un podium recopié en blocs casse le tri et le filtre.
"""

from __future__ import annotations

from domain.palmares import LignePalmares, Palmares
from domain.podium import ReglagePodiums
from infrastructure.tableur.tableau import Cellule, RenduTableur, Tableau

_ENTETE = (
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
        complet: Palmares,
        affiche: Palmares,
        reglage: ReglagePodiums,
    ) -> bytes:
        """Rend le classement en tableur. ⚠️ `complet` et `reglage` ne servent qu'aux podiums,
        que ce format ne porte pas : c'est **`affiche`** qui est rendu, donc la restriction par
        catégorie est respectée — la rendre sur `complet` exporterait le tournoi entier à qui a
        demandé une catégorie.
        """
        lignes: tuple[tuple[Cellule, ...], ...] = tuple(
            (
                _rang(ligne.rang_min, ligne.rang_max),
                ligne.nom,
                ligne.prenom,
                ligne.categorie_libelle,
                _rang(ligne.rang_categorie_min, ligne.rang_categorie_max),
                ligne.club_libelle or "",
                _rang(ligne.rang_club_min, ligne.rang_club_max),
                _statut(ligne),
            )
            for ligne in affiche.lignes
        )
        return self._rendu(Tableau(_ENTETE, lignes))


def _rang(borne_min: int | None, borne_max: int | None) -> str:
    """Rend une fourchette de rangs : « 5 », « 5-8 », ou vide si l'archer est hors classement.

    ⚠️ Rendu en **texte** et non en nombre : « 5-8 » n'est pas sommable, et faire varier le type
    d'une colonne selon la ligne casse le tri du tableur bien plus sûrement qu'un texte homogène.
    """
    if borne_min is None or borne_max is None:
        return ""
    return str(borne_min) if borne_min == borne_max else f"{borne_min}-{borne_max}"


def _statut(ligne: LignePalmares) -> str:
    """Ce que la ligne dit d'elle-même : une place acquise, une attente, ou un statut de forfait."""
    if ligne.statut.value != "en_lice":
        return ligne.statut.value
    if ligne.en_lice:
        return "en cours"
    return "acquis" if ligne.decerne else ""
