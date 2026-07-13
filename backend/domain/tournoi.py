"""Agrégat `Tournoi` — contexte d'un tournoi (E01US001, E01US002).

Enrichit la graine du walking skeleton (E00US009, nom seul) avec les métadonnées de
création — **date**, **lieu** (facultatif), **type** officiel / non officiel (E01US001) — et
son **cycle de vie** (`statut` : brouillon → en cours → terminé, E01US002). Agrégat de domaine
**pur** (aucune dépendance framework, immuable) : `creer`/`modifier` valident les valeurs, les
transitions renvoient une copie. Les autres aspects de configuration (catégories, blasons,
gabarit de salle, barème, tarif…) l'enrichiront dans les US suivantes d'EPIC-01.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, replace
from enum import Enum

from domain.erreurs import NomTournoiInvalide

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
    """Un tournoi. `id` vaut `None` tant que l'agrégat n'est pas persisté."""

    nom: str
    date: datetime.date
    lieu: str | None = None
    type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL
    statut: StatutTournoi = StatutTournoi.BROUILLON
    id: TournoiId | None = None

    @staticmethod
    def creer(
        nom: str,
        date: datetime.date,
        lieu: str | None = None,
        type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL,
    ) -> Tournoi:
        """Crée un tournoi valide (statut `brouillon`) ; lève `NomTournoiInvalide` si le nom
        est vide.

        Le nom et le lieu sont normalisés (espaces de bord retirés) ; un lieu vide devient
        `None` (facultatif). La date et le type sont requis (garantis par la frontière API).
        """
        return Tournoi(
            nom=_nom_valide(nom),
            date=date,
            lieu=_lieu_normalise(lieu),
            type_tournoi=type_tournoi,
            statut=StatutTournoi.BROUILLON,
        )

    def modifier(
        self,
        nom: str,
        date: datetime.date,
        lieu: str | None = None,
        type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL,
    ) -> Tournoi:
        """Renvoie une copie aux métadonnées mises à jour (mêmes règles que `creer`).

        L'`id` et le `statut` sont **préservés** : l'édition des métadonnées (nom, date, lieu,
        type) est autorisée quel que soit le cycle de vie ; seule la **suppression** dépend du
        statut. Lève `NomTournoiInvalide` si le nom est vide.
        """
        return replace(
            self,
            nom=_nom_valide(nom),
            date=date,
            lieu=_lieu_normalise(lieu),
            type_tournoi=type_tournoi,
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
