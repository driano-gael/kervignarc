"""**Recherche transverse** — « chercher partout », entité par entité (E16US010).

Politique pure : ce qui décide *si* un fragment correspond et dans *quel ordre* les propositions
tombent ; la lecture des dépôts appartient au service.
⚠️ Le repli casse/accents est celui de `domain.club.cle_nom` — `DETTE-006`, **6ᵉ usage, 4ᵉ hors du
concept « club »**. En écrire un second donnerait deux replis divergents pour les mêmes noms
propres : « Lévêque » trouvé par la recherche mais pas par la détection de doublons.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from domain.club import cle_nom
from domain.tournoi import TournoiId

# Nombre de propositions rendues. ⚠️ Le total réel voyage à côté (`Recherche.total`) : une liste
# tronquée en silence se lit « il n'y a que ça », et l'organisateur cesse de préciser sa saisie.
LIMITE_COMPLETION = 8


class EntiteRecherchable(str, Enum):
    """Ce que la déroulante du CA propose de chercher.

    Trois entités et pas plus : ce sont celles qui ont une **fiche modifiable** aujourd'hui, donc
    les seules dont le résultat puisse tenir la promesse « ouvrir la fiche en modification ».
    """

    TOURNOI = "tournoi"
    ARCHER = "archer"
    CLUB = "club"


@dataclass(frozen=True)
class ResultatRecherche:
    """Une proposition : de quoi l'afficher et de quoi l'ouvrir.

    `precision` désambiguïse deux homonymes (le club et le tournoi d'un archer) — sans elle, la
    complétion propose deux lignes identiques et l'organisateur ne peut pas choisir.
    """

    entite: EntiteRecherchable
    id: int
    libelle: str
    precision: str | None = None
    tournoi_id: TournoiId | None = None
    """Le tournoi **où ouvrir la fiche** — sans lui, un archer d'une autre édition est introuvable.

    Vaut l'identifiant du tournoi pour un archer, le sien pour un tournoi, `None` pour un club
    (référentiel global). ⚠️ Ce n'est pas de la décoration : `precision` porte le **nom** du
    tournoi, qui se lit mais ne s'adresse pas.
    """


@dataclass(frozen=True)
class Recherche:
    """Les propositions rendues **et** combien il y en avait — voir `LIMITE_COMPLETION`."""

    resultats: tuple[ResultatRecherche, ...]
    total: int


def correspond(fragment: str, *champs: str) -> bool:
    """Le fragment se retrouve-t-il dans l'un des champs, casse et accents repliés ?

    ⚠️ **« Contient », pas « commence par »** : on cherche « dupont » dans un libellé qui porte
    d'abord le prénom, et un nom composé se saisit souvent par sa seconde moitié. Le préfixe garde
    son privilège — au **classement** (`classer`), pas au filtrage.
    """
    aiguille = cle_nom(fragment)
    if not aiguille:
        return False
    return any(aiguille in cle_nom(champ) for champ in champs if champ)


def classer(resultats: Sequence[ResultatRecherche], fragment: str) -> list[ResultatRecherche]:
    """Trie une complétion : les préfixes d'abord, puis l'ordre alphabétique replié.

    Sans ce classement, taper « du » proposerait « Bordu » avant « Dupont » — la complétion cesse
    alors de faire gagner du temps, qui est sa seule raison d'être.
    """
    aiguille = cle_nom(fragment)
    return sorted(
        resultats,
        key=lambda r: (not cle_nom(r.libelle).startswith(aiguille), cle_nom(r.libelle), r.id),
    )


def completer(resultats: Sequence[ResultatRecherche], fragment: str) -> Recherche:
    """Classe puis borne — le total rendu est celui d'**avant** la coupe."""
    classes = classer(resultats, fragment)
    return Recherche(resultats=tuple(classes[:LIMITE_COMPLETION]), total=len(classes))
