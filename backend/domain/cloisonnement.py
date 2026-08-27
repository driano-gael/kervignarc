"""Value object du **cloisonnement** — une valeur de configuration, pas un morceau d'algorithme.

⚠️ **Module à part pour éviter un cycle** : `domain/placement` importe `domain/archer`, qui importe
`domain/tournoi` — loger l'énumération dans le moteur et l'importer depuis `Tournoi` le fermerait.
"""

from __future__ import annotations

from enum import Enum


class Cloisonnement(str, Enum):
    """Ce qu'une cible n'a pas le droit de mêler (réglage **de tournoi**, RG-4).

    Quatre positions : `AUCUN` (défaut, comportement d'E03US001), `CATEGORIE`, `BLASON` (deux
    catégories tirant le même carton restent ensemble), `BLASON_ET_CATEGORIE`. ⚠️ **Aujourd'hui
    `CATEGORIE` implique `BLASON`** — le blason d'un archer est celui de sa catégorie —, donc les
    deux dernières positions rendent le même plan ; elles se distingueront quand une phase pourra
    **surcharger le blason** (EF-1.4). Redondance temporaire assumée (ADR-0071 §3).
    """

    AUCUN = "aucun"
    CATEGORIE = "categorie"
    BLASON = "blason"
    BLASON_ET_CATEGORIE = "blason_et_categorie"

    @property
    def separe_categorie(self) -> bool:
        """Vrai si ce réglage interdit deux catégories sur une même cible."""
        # DETTE-036 : `BLASON_ET_CATEGORIE` rend ici la même réponse que `CATEGORIE`, et là-bas la
        # même que `BLASON` — la quatrième position n'a pas d'effet distinct tant que le blason
        # dérive de la catégorie. Se résorbe d'elle-même avec EF-1.4 (surcharge par phase).
        return self in (Cloisonnement.CATEGORIE, Cloisonnement.BLASON_ET_CATEGORIE)

    @property
    def separe_blason(self) -> bool:
        """Vrai si ce réglage interdit deux blasons sur une même cible."""
        # DETTE-036 (voir ci-dessus).
        return self in (Cloisonnement.BLASON, Cloisonnement.BLASON_ET_CATEGORIE)
