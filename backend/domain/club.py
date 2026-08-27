"""Agrégat **Club** — portée **globale**, hors tournoi : il n'a pas de `tournoi_id`.

C'est ce qui réalise le « réutilisable entre tournois » — et un club **survit** à la suppression
d'un tournoi, il n'appartient pas à sa descendance.

⚠️ **L'unicité du nom n'est pas vérifiée ici** (règle d'ensemble, portée par le service). En
revanche, **ce qui fait que deux noms désignent le même club** est du métier : c'est `cle_nom`.
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

    Sert à **quatre** usages, qui doivent rester cohérents : refuser un homonyme de club
    (`ClubRepository.par_nom`), **classer** le référentiel à l'écran (`ServiceClubs.lister`) — sans
    le repli des accents, un tri par code point renverrait « Élan » après « Zénith » — puis, depuis
    E02US002, replier **nom et prénom d'archer** (`domain.archer.cle_identite`) et, depuis E02US003,
    **classer les archers** d'un tournoi (`ServiceArchers.lister`, même raison que pour les clubs).

    Deux règles de repli qui divergeraient accepteraient un doublon ici et le refuseraient là : d'où
    la réutilisation plutôt que la copie.

    # DETTE-006 : les **deux** derniers usages sont hors du concept « club », soit le seuil que
    # cette docstring s'était fixé en E02US002 pour justifier l'extraction dans un
    # `domain/texte.py`. `cle_nom` n'est plus une notion métier du référentiel des clubs, c'est la
    # règle de repli des noms propres du projet — voir `docs/dette.md` pour le constat et l'US de
    # résorption. E02US003 a ajouté l'usage et constaté le déclenchement, rien de plus : un remède
    # structurel se traite en ADR + US dédiée, jamais en douce dans l'US courante
    # (`CLAUDE.md` § Dette).

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
