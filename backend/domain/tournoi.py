"""Agrégat `Tournoi` — graine minimale du walking skeleton (E00US009).

Gabarit d'agrégat de domaine **pur** (aucune dépendance framework, immuable) : validé à
la création. Les vraies règles métier (catégories, blasons, gabarit de salle, barème,
tarif…) l'enrichiront en E01US001 — d'où un modèle volontairement trivial ici.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.erreurs import NomTournoiInvalide

TournoiId = int
"""Identifiant technique d'un tournoi, attribué par la persistance."""


@dataclass(frozen=True)
class Tournoi:
    """Un tournoi. `id` vaut `None` tant que l'agrégat n'est pas persisté."""

    nom: str
    id: TournoiId | None = None

    @staticmethod
    def creer(nom: str) -> Tournoi:
        """Crée un tournoi valide ; lève `NomTournoiInvalide` si le nom est vide."""
        nom_normalise = nom.strip()
        if not nom_normalise:
            raise NomTournoiInvalide("Le nom du tournoi ne peut pas être vide.")
        return Tournoi(nom=nom_normalise)
