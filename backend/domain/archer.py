"""Agrégat `Archer` — participant d'un tournoi (tranche verticale E00US011).

Gabarit d'agrégat **pur** (aucune dépendance framework, immuable) : un archer appartient
à un tournoi, porte un nom, peut être rattaché à un **club** (E02US001) et peut être **placé**
sur une cible (numéro de peloton). Le placement du walking skeleton est volontairement trivial
(un simple numéro de cible) ; les vraies contraintes (capacité 1/2/4, ≥2 clubs/cible, blason =
fraction de place) l'enrichiront en E03. On garde donc un modèle minimal, jetable/évolutif.

**`club_id` est facultatif ici, et ne le restera pas.** E02US001 pose le lien vers le
référentiel global des clubs ; E02US002 rendra le club **obligatoire**, en même temps qu'il
ajoutera `prenom` et `categorie_id`. Le lien naît avec le référentiel, et non avec
l'inscription complète, parce qu'il est ce qui rend le CA « un club utilisé n'est pas
supprimable » **exerçable** : sans lui, le refus serait un garde-fou qu'aucun chemin réel ne
pourrait déclencher.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from domain.club import ClubId
from domain.erreurs import CibleInvalide, NomArcherInvalide
from domain.tournoi import TournoiId

ArcherId = int
"""Identifiant technique d'un archer, attribué par la persistance."""


@dataclass(frozen=True)
class Archer:
    """Un archer inscrit à un tournoi. `id` vaut `None` tant qu'il n'est pas persisté.

    `cible` vaut `None` tant que l'archer n'est pas placé (E00US011 : un simple numéro).
    `club_id` vaut `None` tant que l'archer n'est rattaché à aucun club (E02US001) ; l'existence
    du club référencé est vérifiée par le service — le domaine ne lit pas la persistance.
    """

    nom: str
    tournoi_id: TournoiId
    cible: int | None = None
    club_id: ClubId | None = None
    id: ArcherId | None = None

    @staticmethod
    def creer(nom: str, tournoi_id: TournoiId, club_id: ClubId | None = None) -> Archer:
        """Crée un archer valide ; lève `NomArcherInvalide` si le nom est vide."""
        nom_normalise = nom.strip()
        if not nom_normalise:
            raise NomArcherInvalide("Le nom de l'archer ne peut pas être vide.")
        return Archer(nom=nom_normalise, tournoi_id=tournoi_id, club_id=club_id)

    def placer(self, cible: int) -> Archer:
        """Renvoie une copie placée sur `cible` ; lève `CibleInvalide` si `cible < 1`."""
        if cible < 1:
            raise CibleInvalide("Le numéro de cible doit être un entier strictement positif.")
        return replace(self, cible=cible)
