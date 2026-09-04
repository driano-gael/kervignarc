"""Value object du **réglage des podiums** — de la configuration, pas un morceau d'algorithme.

⚠️ **Module à part pour éviter un cycle**, même raison que `domain/cloisonnement.py` : `Tournoi`
porte ce réglage, et `domain/palmares` importe `domain/classement` — loger l'énumération dans le
palmarès et l'importer depuis `Tournoi` fermerait la boucle.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from domain.erreurs import ProfondeurPodiumInvalide

PROFONDEUR_PODIUM_PAR_DEFAUT = 4
"""Les quatre places d'E06US004 : finale et petite finale d'un tableau."""

PROFONDEUR_PODIUM_MAX = 64
"""Plafond d'un podium — au-delà, ce n'est plus un podium mais le classement, qui suit déjà.

⚠️ **Borné au domaine et non à la frontière**, même parti qu'`ReglagePages` (E16US009) : une borne
Pydantic dégraderait le refus en 400 générique là où `DomainError` rend un 422 portant le code
métier. Sans plafond, `profondeur = 10**30` traversait le domaine et cassait à l'insertion SQLite.
"""


class PorteePodium(str, Enum):
    """Ce qu'un podium récompense (réglage **de tournoi**, A16).

    ⚠️ **L'ordre de déclaration est l'ordre d'affichage** — du plus large au plus fin, ce qui rend
    deux réglages équivalents identiques à l'écran.
    ⚠️ La portée *équipe* d'A16 **n'est pas ici** : `Equipe` n'existe pas (EPIC-13, ADR-0028).
    ⚠️ Une portée neuve se range dans `classement_clubs.PORTEES_INTER_CLUBS` ou s'en exclut
    explicitement — `test_toute_portee_est_rangee_dans_un_camp` rougit sinon (ADR-0104 §2).
    """

    SCRATCH = "scratch"
    CATEGORIE = "categorie"
    CLUB = "club"


@dataclass(frozen=True)
class ReglagePodiums:
    """Ce que le tournoi récompense, et sur combien de places.

    Un **ensemble** de portées, pas un choix unique : le club qui remet des médailles par catégorie
    et un trophée scratch ne doit pas changer de réglage entre deux remises (A16, « tout doit être
    possible »). L'ensemble **vide** est valide — un tournoi peut ne rien récompenser.
    """

    portees: frozenset[PorteePodium] = frozenset({PorteePodium.CATEGORIE})
    profondeur: int = PROFONDEUR_PODIUM_PAR_DEFAUT

    def __post_init__(self) -> None:
        # Invariant tenu quelle que soit la porte d'entrée — `replace()` et la reconstruction du
        # repository comprises, comme `Tournoi.effectif_minimum_exige`.
        if not 1 <= self.profondeur <= PROFONDEUR_PODIUM_MAX:
            raise ProfondeurPodiumInvalide(
                f"Un podium compte de 1 à {PROFONDEUR_PODIUM_MAX} places (reçu "
                f"{self.profondeur}) ; « ne rien récompenser » se dit en ne retenant aucune portée."
            )

    def portees_actives(self) -> tuple[PorteePodium, ...]:
        """Les portées retenues, dans l'ordre d'affichage (celui de l'énumération)."""
        return tuple(portee for portee in PorteePodium if portee in self.portees)
