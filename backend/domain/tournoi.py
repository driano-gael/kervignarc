"""Agrégat `Tournoi` — contexte d'un tournoi (E01US001).

Enrichit la graine du walking skeleton (E00US009, nom seul) avec les métadonnées de
création : **date**, **lieu** (facultatif) et **type** officiel / non officiel. Agrégat de
domaine **pur** (aucune dépendance framework, immuable), validé à la création. Les autres
aspects de configuration (catégories, blasons, gabarit de salle, barème, tarif, statut…)
l'enrichiront dans les US suivantes d'EPIC-01.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum

from domain.erreurs import NomTournoiInvalide

TournoiId = int
"""Identifiant technique d'un tournoi, attribué par la persistance."""


class TypeTournoi(str, Enum):
    """Type d'un tournoi : conforme (officiel) ou libre (non officiel)."""

    OFFICIEL = "officiel"
    NON_OFFICIEL = "non_officiel"


@dataclass(frozen=True)
class Tournoi:
    """Un tournoi. `id` vaut `None` tant que l'agrégat n'est pas persisté."""

    nom: str
    date: datetime.date
    lieu: str | None = None
    type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL
    id: TournoiId | None = None

    @staticmethod
    def creer(
        nom: str,
        date: datetime.date,
        lieu: str | None = None,
        type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL,
    ) -> Tournoi:
        """Crée un tournoi valide ; lève `NomTournoiInvalide` si le nom est vide.

        Le nom et le lieu sont normalisés (espaces de bord retirés) ; un lieu vide devient
        `None` (facultatif). La date et le type sont requis (garantis par la frontière API).
        """
        nom_normalise = nom.strip()
        if not nom_normalise:
            raise NomTournoiInvalide("Le nom du tournoi ne peut pas être vide.")
        lieu_normalise = lieu.strip() if lieu is not None else None
        if not lieu_normalise:
            lieu_normalise = None
        return Tournoi(
            nom=nom_normalise,
            date=date,
            lieu=lieu_normalise,
            type_tournoi=type_tournoi,
        )
