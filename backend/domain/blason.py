"""Agrégat `Blason` — une cible en carton d'un tournoi (E01US005 ; zones : E01US014).

Modélise l'**occupation d'une cible** : un blason porte un `nom`, une `taille` (fraction de
place occupée sur une cible, `0 < taille <= 1`) et une `capacite` (nombre d'archers admis,
`>= 1`). Agrégat de domaine **pur** (aucune dépendance framework, immuable), validé à la
création/édition. Les blasons appartiennent à un tournoi ; l'association d'une **catégorie** à
un blason par défaut viendra en E01US006. Reprend et formalise le prototype `Blason`.

Il porte aussi ses `zones` — les **valeurs de score admises** (E01US014) : un blason ne se
réduit pas à sa taille, un triple 40 n'a pas les zones 5 → 1 (référentiel §4.4). C'est cette
donnée qui permet au pavé de saisie (EPIC-04) de ne proposer que le tirable.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace

from domain.erreurs import (
    CapaciteBlasonInvalide,
    NomBlasonInvalide,
    TailleBlasonInvalide,
    ZonesBlasonInvalides,
)
from domain.tournoi import TournoiId

BlasonId = int
"""Identifiant technique d'un blason, attribué par la persistance."""

ZONE_MANQUE = "M"
"""La zone « manqué » (hors blanc, référentiel §4.2) — toujours admise, sur tout blason."""

ZONES_CANONIQUES = ("10", "9", "8", "7", "6", "5", "4", "3", "2", "1", ZONE_MANQUE)
"""Vocabulaire des zones en salle, du centre vers l'extérieur (référentiel §4.2).

Fait aussi office d'**ordre canonique** : les zones d'un blason sont normalisées dans cet ordre,
l'ordre de saisie ne portant aucune information. La « mouche » (X) n'en fait pas partie : c'est
le centre du 10, elle ne vaut pas une valeur de score distincte et aucun consommateur ne la
demande à ce jour (le départage FFTA au nombre de X relèverait d'EPIC-06).
"""

ZONES_DEFAUT = ZONES_CANONIQUES
"""Zones par défaut : le jeu complet d'un **blason simple** (10 → 1 + M).

`taille` étant une *fraction de place* et non un diamètre, le domaine ne peut pas déduire s'il
s'agit d'un triple 40 : le défaut est donc le **sur-ensemble**, que l'administrateur restreint
explicitement pour un triple (arbitrage du 17/07/2026, cf. CA d'E01US014).
"""


@dataclass(frozen=True)
class Blason:
    """Un blason rattaché à un tournoi. `id` vaut `None` tant qu'il n'est pas persisté."""

    tournoi_id: TournoiId
    nom: str
    taille: float
    capacite: int
    zones: tuple[str, ...] = ZONES_DEFAUT
    id: BlasonId | None = None

    @staticmethod
    def creer(
        tournoi_id: TournoiId,
        nom: str,
        taille: float,
        capacite: int,
        zones: Iterable[str] | None = None,
    ) -> Blason:
        """Crée un blason valide.

        Le `nom` est normalisé (espaces de bord retirés) et ne peut pas être vide ; la `taille`
        doit être dans `]0, 1]` (fraction de place) ; la `capacite` doit être un entier `>= 1` ;
        les `zones`, omises, valent `ZONES_DEFAUT` (blason simple complet).
        Lève l'erreur de domaine correspondante en cas de valeur invalide.
        """
        return Blason(
            tournoi_id=tournoi_id,
            nom=_nom_valide(nom),
            taille=_taille_valide(taille),
            capacite=_capacite_valide(capacite),
            zones=ZONES_DEFAUT if zones is None else _zones_valides(zones),
        )

    def modifier(
        self,
        nom: str,
        taille: float,
        capacite: int,
        zones: Iterable[str] | None = None,
    ) -> Blason:
        """Renvoie une copie aux attributs mis à jour (mêmes règles que `creer`).

        L'`id` et le `tournoi_id` sont **préservés** (on ne déplace pas un blason d'un tournoi à
        l'autre). Des `zones` omises laissent celles du blason inchangées.
        Lève l'erreur de domaine correspondante en cas de valeur invalide.
        """
        return replace(
            self,
            nom=_nom_valide(nom),
            taille=_taille_valide(taille),
            capacite=_capacite_valide(capacite),
            zones=self.zones if zones is None else _zones_valides(zones),
        )


def _nom_valide(nom: str) -> str:
    """Normalise le nom ; lève `NomBlasonInvalide` s'il est vide."""
    nom_normalise = nom.strip()
    if not nom_normalise:
        raise NomBlasonInvalide("Le nom d'un blason ne peut pas être vide.")
    return nom_normalise


def _taille_valide(taille: float) -> float:
    """Vérifie que la taille est une fraction de place dans `]0, 1]`."""
    if not 0 < taille <= 1:
        raise TailleBlasonInvalide(
            "La taille d'un blason doit être une fraction de place strictement positive "
            "et au plus égale à 1."
        )
    return taille


def _capacite_valide(capacite: int) -> int:
    """Vérifie que la capacité est un entier `>= 1`."""
    if capacite < 1:
        raise CapaciteBlasonInvalide("La capacité d'un blason doit être d'au moins 1.")
    return capacite


def _zones_valides(zones: Iterable[str]) -> tuple[str, ...]:
    """Valide et normalise les valeurs de score admises ; lève `ZonesBlasonInvalides`.

    Ne vérifie **pas** la conformité FFTA du jeu de zones : RG-8 l'interdit explicitement
    (« l'application n'impose ni ne vérifie la conformité au règlement »). Un jeu non contigu est
    donc admis — il n'existe sur aucun carton réel, mais l'interdire serait normer le blason
    alors que le CA veut seulement **restreindre la saisie**. Ne sont refusées que les entrées
    ininterprétables en aval : EPIC-04 doit sommer ces valeurs.
    """
    saisies = [zone.strip() for zone in zones]

    inconnues = [zone for zone in saisies if zone not in ZONES_CANONIQUES]
    if inconnues:
        raise ZonesBlasonInvalides(
            f"Zone(s) de score inconnue(s) : {', '.join(repr(z) for z in inconnues)}. "
            f"Valeurs admises : {', '.join(ZONES_CANONIQUES)}."
        )
    if len(set(saisies)) != len(saisies):
        raise ZonesBlasonInvalides("Une même zone de score ne peut pas être admise deux fois.")
    if ZONE_MANQUE not in saisies:
        raise ZonesBlasonInvalides(
            f"La zone « {ZONE_MANQUE} » (manqué) est toujours admise et ne peut pas être retirée."
        )
    if not any(zone != ZONE_MANQUE for zone in saisies):
        raise ZonesBlasonInvalides("Un blason doit admettre au moins une zone marquante.")

    retenues = set(saisies)
    return tuple(zone for zone in ZONES_CANONIQUES if zone in retenues)
