"""Cloisonnement catégorie/blason d'une cible (E03US007, RG-4) — value object du domaine.

**Pourquoi un module à part.** Deux agrégats en ont besoin : le moteur de placement
(`domain/placement.py`), qui l'applique, et `Tournoi`, qui le **porte** — c'est un réglage de
tournoi, activable, indépendant du type de tournoi (RG-4). Or `domain/placement` importe déjà
`domain/archer`, qui importe `domain/tournoi` : loger l'énumération dans le moteur et l'importer
depuis `Tournoi` fermerait un **cycle d'imports**. Un value object partagé, sans dépendance, est la
sortie habituelle — et il dit ce qu'il est : une valeur de configuration, pas un morceau
d'algorithme.

`domain/placement` l'importe et s'en sert ; c'est ici qu'elle est **définie**.
"""

from __future__ import annotations

from enum import Enum


class Cloisonnement(str, Enum):
    """Ce qu'une cible n'a pas le droit de mêler (réglage **de tournoi**, RG-4).

    Quatre positions, du plus permissif au plus strict :

    - `AUCUN` (défaut) : aucune séparation — comportement d'E03US001, une cible mêle ce que ses
      budgets permettent ;
    - `CATEGORIE` : une cible ne porte qu'une seule catégorie ;
    - `BLASON` : une cible ne porte qu'un seul blason (deux catégories tirant le **même** carton y
      restent donc ensemble) ;
    - `BLASON_ET_CATEGORIE` : conjonction des deux — séparation dès qu'une des deux grandeurs
      diffère.

    ⚠️ **Aujourd'hui `CATEGORIE` implique `BLASON`** : le blason d'un archer est celui de sa
    catégorie (`Categorie.blason_id`, cf. `application/placement._archer_a_placer`), donc deux
    archers de même catégorie ont forcément le même blason, et `BLASON_ET_CATEGORIE` rend le même
    plan que `CATEGORIE`. Les deux positions se distingueront le jour où une **phase pourra
    surcharger le blason** (cahier des charges EF-1.4, « toutes les finales sur triples ») : le
    couple (catégorie, blason) cessera alors d'être fonctionnel. Le réglage est livré à quatre
    positions par choix du commanditaire, en connaissance de cette redondance temporaire
    (ADR-0071 §3).
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
