"""Agrégat `Club` — référentiel des clubs d'appartenance des archers (E02US001).

Agrégat de domaine **pur** (aucune dépendance framework, immuable) : un club porte un `nom`,
et rien d'autre — c'est un simple référentiel de rattachement, saisi une fois puis réutilisé.

**Portée globale, hors tournoi.** Contrairement à tous les autres agrégats de configuration
(`Categorie`, `Blason`, `GabaritSalle`, `Phase`), un club **n'appartient pas** à un tournoi :
il n'a pas de `tournoi_id`. C'est ce qui réalise le « réutilisable entre tournois » d'E02US001
— les clubs voisins reviennent d'une compétition à l'autre, les ressaisir chaque fois serait
la corvée que cette US supprime. Conséquence : un club **survit** à la suppression d'un
tournoi ; il n'appartient pas à sa descendance (cf. DETTE-001).

L'unicité du nom n'est **pas** vérifiée ici : le domaine ne voit qu'un club à la fois, jamais
la collection. C'est une règle d'ensemble, portée par le service applicatif et garantie par
une contrainte `UNIQUE` en base (cf. `application/clubs.py`). En revanche, **ce qui fait que
deux noms désignent le même club** est une notion métier : elle vit ici, dans `cle_nom`.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, replace

from domain.erreurs import NomClubInvalide

ClubId = int
"""Identifiant technique d'un club, attribué par la persistance."""


def cle_nom(nom: str) -> str:
    """Clé d'équivalence d'un nom de club : deux noms de **même clé** désignent le même club.

    Replie les espaces de bord, la **casse** et les **accents** : « Élan de Fougères »,
    « elan de fougeres » et « ÉLAN DE FOUGÈRES » ont la même clé. Un référentiel dont l'intérêt
    est de ne pas ressaisir ne doit pas offrir deux entrées pour un même club — or saisir un nom
    sans ses accents est le doublon le plus probable sur une tablette.

    Sert à **deux** usages, qui doivent rester cohérents : refuser un homonyme (`ClubRepository.
    par_nom`) et **classer** le référentiel à l'écran (`ServiceClubs.lister`) — sans le repli des
    accents, un tri par code point renverrait « Élan » après « Zénith ».

    Implémentation : décomposition NFKD puis retrait des marques combinantes (l'accent devient un
    caractère distinct, qu'on jette), avant `casefold`. `casefold` seul ne suffirait pas : il
    replie la casse **d'**une lettre accentuée (« É » → « é ») mais ne retire pas l'accent.
    """
    decompose = unicodedata.normalize("NFKD", nom.strip())
    sans_accents = "".join(c for c in decompose if not unicodedata.combining(c))
    return sans_accents.casefold()


@dataclass(frozen=True)
class Club:
    """Un club du référentiel. `id` vaut `None` tant qu'il n'est pas persisté."""

    nom: str
    id: ClubId | None = None

    @staticmethod
    def creer(nom: str) -> Club:
        """Crée un club valide.

        Le `nom` est normalisé (espaces de bord retirés) et ne peut pas être vide ; lève
        `NomClubInvalide` sinon.
        """
        return Club(nom=_nom_valide(nom))

    def modifier(self, nom: str) -> Club:
        """Renvoie une copie au nom mis à jour (mêmes règles que `creer`).

        L'`id` est **préservé** : renommer un club (faute de frappe, changement de
        dénomination) ne rompt pas le rattachement des archers qui le référencent.
        """
        return replace(self, nom=_nom_valide(nom))


def _nom_valide(nom: str) -> str:
    """Normalise le nom ; lève `NomClubInvalide` s'il est vide."""
    nom_normalise = nom.strip()
    if not nom_normalise:
        raise NomClubInvalide("Le nom d'un club ne peut pas être vide.")
    return nom_normalise
