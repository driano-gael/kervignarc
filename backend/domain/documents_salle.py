"""Étiquettes de cible et cartes de scoreur — de simples valeurs décrivant **ce qui** figure sur le
support, jamais comment on le rend (le PDF est un adapter, ADR-0031).

⚠️ **Le domaine ne construit PAS l'URL** : il ne connaît ni HTTP ni l'origine réseau du serveur.
C'est le service qui la compose et la dépose ici prête à encoder. Le QR n'encode qu'une URL — il ne
porte pas le rattachement lui-même.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EtiquetteCible:
    """Une étiquette de cible : son QR (l'`url` à encoder) et le `code` imprimé en clair dessous.

    `cible_index` est le rang **1-based** de la cible dans le plan (`GabaritSalle.cibles`) ; il
    titre l'étiquette pour que le bénévole sache **quelle** étiquette va sur **quel** pied.
    """

    cible_index: int
    code: str
    url: str


@dataclass(frozen=True)
class EtiquettesCibles:
    """Le document « étiquettes de cible » d'un tournoi : une page par cible préparée.

    `nom_tournoi` en-tête chaque page (« lié au tournoi » : de nouveaux QR pour un nouveau tournoi,
    et pas de mélange à l'impression). `etiquettes` est ordonné par le service (numéro de cible
    croissant) pour suivre l'ordre physique de la salle.
    """

    nom_tournoi: str
    etiquettes: tuple[EtiquetteCible, ...]


@dataclass(frozen=True)
class CarteScoreur:
    """La carte d'un scoreur : son `nom` (pour la remettre à la bonne personne) et son `code`.

    Pas de QR : le scoreur **saisit** son code pour ouvrir sa session (E10US003), il ne scanne rien.
    """

    nom: str
    code: str


@dataclass(frozen=True)
class CartesScoreurs:
    """Le document « cartes de scoreur » d'un tournoi : un papier par scoreur.

    `nom_tournoi` en-tête chaque carte (« lié au tournoi »). `cartes` est ordonné par le service
    (par nom) pour une distribution prévisible.
    """

    nom_tournoi: str
    cartes: tuple[CarteScoreur, ...]
