"""Agrégat **Club** — portée **globale**, hors tournoi : il n'a pas de `tournoi_id`.

C'est ce qui réalise le « réutilisable entre tournois » : un club **survit** à la suppression d'un
tournoi, il n'appartient pas à sa descendance — **exception explicite** à `DETTE-001`, dont
l'inventaire de cascade est énuméré au registre. ⚠️ **L'unicité du nom n'est pas vérifiée ici**
(règle d'ensemble, portée par le service) ; en revanche, **ce qui fait que deux noms désignent le
même club** est du métier : c'est `cle_nom`.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, replace

from domain.erreurs import NomClubInvalide

ClubId = int
"""Identifiant technique d'un club, attribué par la persistance."""


def cle_nom(nom: str) -> str:
    """Clé d'équivalence d'un nom de club : deux noms de **même clé** désignent le même club.

    Replie espaces de bord, **casse** et **accents** — un nom saisi sans accents est le doublon le
    plus probable sur une tablette. Sert à **quatre** usages qui doivent rester cohérents : refus
    d'homonyme, tri du référentiel, repli nom+prénom d'archer, tri des archers. ⚠️ `# DETTE-006` :
    les deux derniers sont hors du concept « club » — seuil d'extraction vers `domain/texte.py`, en
    US dédiée. NFKD (retrait des marques combinantes) **puis** `casefold`, seul insuffisant.
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
