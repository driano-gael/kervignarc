"""Agrégat `Tournoi` — contexte d'un tournoi (E01US001, E01US002, E01US010).

Enrichit la graine du walking skeleton (E00US009, nom seul) avec les métadonnées de
création — **date**, **lieu** (facultatif), **type** officiel / non officiel (E01US001) —, son
**cycle de vie** (`statut` : brouillon → en cours → terminé, E01US002) et le **tarif d'un départ**
(E01US010). Agrégat de domaine **pur** (aucune dépendance framework, immuable) : `creer`/`modifier`
valident les valeurs, les transitions renvoient une copie. Les autres aspects de configuration
(catégories, blasons, gabarit de salle, barème…) vivent dans leurs propres agrégats.

**L'argent est compté en centimes entiers**, jamais en flottants — d'où le suffixe `_centimes`,
qui met l'unité dans le nom plutôt que dans un commentaire qu'on ne lit pas. Un `float` ne
représente pas 8,10 € exactement, et EPIC-08/09 **somment** ces montants (montant dû par archer,
par club, EF-8.1 / EF-9.6) : la dérive y serait visible à l'euro près sur une liste de club.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, replace
from enum import Enum

from domain.erreurs import NomTournoiInvalide, TarifDepartInvalide

TournoiId = int
"""Identifiant technique d'un tournoi, attribué par la persistance."""


class TypeTournoi(str, Enum):
    """Type d'un tournoi : conforme (officiel) ou libre (non officiel)."""

    OFFICIEL = "officiel"
    NON_OFFICIEL = "non_officiel"


class StatutTournoi(str, Enum):
    """Cycle de vie d'un tournoi (E01US002).

    `brouillon` → **démarrer** → `en_cours` → **terminer** → `terminé`. Un tournoi `en_cours`
    n'est pas supprimable (il faut d'abord le terminer). L'**enchaînement** de ces états (qui
    peut passer de quoi à quoi) est un **conflit d'état** arbitré par le service applicatif
    (ADR-0007), au même titre que l'existence : l'agrégat, lui, ne porte que la valeur.
    """

    BROUILLON = "brouillon"
    EN_COURS = "en_cours"
    TERMINE = "termine"


@dataclass(frozen=True)
class Tournoi:
    """Un tournoi. `id` vaut `None` tant que l'agrégat n'est pas persisté.

    `tarif_depart_centimes` est le prix **d'un départ**, en **centimes** (E01US010) ; le montant dû
    par un archer en découlera (tarif multiplié par le nombre de départs, EF-8.1 / E08US001). Trois
    états, tous
    distincts : `None` = **non défini** (l'organisateur ne l'a pas encore fixé), `0` = **gratuit**,
    `> 0` = payant. Confondre les deux premiers ferait annoncer « 0 € dû » à toute une compétition
    dont le tarif a simplement été oublié.
    """

    nom: str
    date: datetime.date
    lieu: str | None = None
    type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL
    statut: StatutTournoi = StatutTournoi.BROUILLON
    tarif_depart_centimes: int | None = None
    id: TournoiId | None = None

    @staticmethod
    def creer(
        nom: str,
        date: datetime.date,
        lieu: str | None = None,
        type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL,
        tarif_depart_centimes: int | None = None,
    ) -> Tournoi:
        """Crée un tournoi valide (statut `brouillon`) ; lève `NomTournoiInvalide` si le nom
        est vide.

        Le nom et le lieu sont normalisés (espaces de bord retirés) ; un lieu vide devient
        `None` (facultatif). La date et le type sont requis (garantis par la frontière API). Le
        tarif est **facultatif** : un tournoi naît sans tarif défini (`None`), pas à zéro. Lève
        `TarifDepartInvalide` s'il est négatif.
        """
        return Tournoi(
            nom=_nom_valide(nom),
            date=date,
            lieu=_lieu_normalise(lieu),
            type_tournoi=type_tournoi,
            statut=StatutTournoi.BROUILLON,
            tarif_depart_centimes=_tarif_valide(tarif_depart_centimes),
        )

    def modifier(
        self,
        nom: str,
        date: datetime.date,
        lieu: str | None = None,
        type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL,
        tarif_depart_centimes: int | None = None,
    ) -> Tournoi:
        """Renvoie une copie aux métadonnées mises à jour (mêmes règles que `creer`).

        L'`id` et le `statut` sont **préservés** : l'édition des métadonnées (nom, date, lieu,
        type, tarif) est autorisée quel que soit le cycle de vie — le tarif reste corrigeable
        **tournoi en cours** (un tarif mal saisi se découvre à la table d'inscription, `P-3`) ;
        seule la **suppression** dépend du statut. Lève `NomTournoiInvalide` si le nom est vide,
        `TarifDepartInvalide` si le tarif est négatif.
        """
        return replace(
            self,
            nom=_nom_valide(nom),
            date=date,
            lieu=_lieu_normalise(lieu),
            type_tournoi=type_tournoi,
            tarif_depart_centimes=_tarif_valide(tarif_depart_centimes),
        )

    def demarrer(self) -> Tournoi:
        """Renvoie une copie passée `en_cours` (précondition `brouillon` garantie en amont)."""
        return replace(self, statut=StatutTournoi.EN_COURS)

    def terminer(self) -> Tournoi:
        """Renvoie une copie passée `terminé` (précondition `en_cours` garantie en amont)."""
        return replace(self, statut=StatutTournoi.TERMINE)


def _nom_valide(nom: str) -> str:
    """Normalise le nom (espaces de bord retirés) ; lève `NomTournoiInvalide` si vide."""
    nom_normalise = nom.strip()
    if not nom_normalise:
        raise NomTournoiInvalide("Le nom du tournoi ne peut pas être vide.")
    return nom_normalise


def _lieu_normalise(lieu: str | None) -> str | None:
    """Normalise le lieu ; un lieu vide ou absent devient `None` (facultatif)."""
    if lieu is None:
        return None
    lieu_normalise = lieu.strip()
    return lieu_normalise or None


def _tarif_valide(tarif_depart_centimes: int | None) -> int | None:
    """Valide le tarif : `None` (non défini) ou un nombre de centimes `>= 0`.

    Lève `TarifDepartInvalide` s'il est négatif. Zéro est **admis** — un tournoi peut être gratuit,
    et c'est un choix différent de « pas encore fixé ».
    """
    if tarif_depart_centimes is None:
        return None
    if tarif_depart_centimes < 0:
        raise TarifDepartInvalide("Le tarif d'un départ ne peut pas être négatif.")
    return tarif_depart_centimes
