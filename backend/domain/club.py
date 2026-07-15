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
une contrainte `UNIQUE` en base (cf. `application/clubs.py`).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from domain.erreurs import NomClubInvalide

ClubId = int
"""Identifiant technique d'un club, attribué par la persistance."""


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
