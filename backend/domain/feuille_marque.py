"""Feuille de marque — contenu **imprimable** d'un départ (E09US001), domaine **pur**.

Décrit *ce qui* figure sur les feuilles de marque d'un départ, sans savoir *comment* on les rend :
le rendu PDF est un adapter d'infrastructure (ReportLab, ADR-0031) branché derrière le port
`GenerateurFeuilleDeMarque` (`domain/ports.py`). Ici, aucune dépendance framework (règle 1) : de
simples valeurs immuables.

**Un document par départ, une page par archer placé.** Le service `application.feuille_de_marque`
lit le plan de cibles (E03US001) — qui tire sur quelle cible, à quelle position — reconstitue la
jointure archer → catégorie → blason, et pose une `LigneArcher` par archer *placé* (la réserve ne
tire pas, donc pas de feuille). La **grille de scores** (volées et flèches par volée) n'est pas en
dur : elle dérive du **barème de qualification** du tournoi (`domain/bareme.py`), pour rester
« conforme aux données » — 20 volées de 3 en preset FFTA 18 m, mais un tournoi peut le configurer.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LigneArcher:
    """Un archer placé, tel qu'il figure en tête de **sa** feuille de marque.

    Les libellés (`categorie`, `blason`) sont déjà résolus par le service : le domaine du rendu ne
    manipule que du texte prêt à imprimer, pas des identifiants à rejoindre.
    """

    cible_index: int  # rang de la cible dans la salle (1-based)
    position: str  # lettre de la position sur la cible ("A".."D")
    nom: str
    prenom: str
    categorie: str
    blason: str


@dataclass(frozen=True)
class FeuilleDeMarque:
    """Le document « feuille de marque » d'un départ : en-tête commun + une page par archer placé.

    `nb_volees` et `nb_fleches_par_volee` dimensionnent la **grille de scores** vierge de chaque
    page (les « zones de scores » à remplir à la main) ; ils proviennent du barème de qualification
    du tournoi. `archers` est ordonné par le service (cible puis position) pour que l'impression
    suive l'ordre physique de la salle.
    """

    tournoi: str
    depart_numero: int
    nb_volees: int
    nb_fleches_par_volee: int
    archers: tuple[LigneArcher, ...]

    @property
    def nb_fleches_total(self) -> int:
        """Nombre total de flèches de la grille (repère de rendu et de test)."""
        return self.nb_volees * self.nb_fleches_par_volee
