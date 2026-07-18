"""Documents de préparation de salle — contenu **imprimable** de l'identité des postes (E09US008).

Deux supports qu'on prépare **à l'avance** (`D-07`, principe `P-6` : « tout ce qui s'identifie se
prépare à l'avance ; le jour J on distribue, on ne configure pas ») et qu'on imprime pour monter la
salle sans rien configurer sur place :

- les **étiquettes de cible** — un QR par cible, à poser sur le pied — qui encodent l'**URL de
  rattachement** du poste (E04US001) et portent le **code lisible en clair** en dessous (recours si
  le QR est abîmé ou l'appareil photo capricieux) ;
- les **cartes de scoreur** — un papier par scoreur avec son **code personnel** (E10US003).

Domaine **pur** (règle 1) : de simples valeurs immuables décrivant *ce qui* figure sur le support,
sans savoir *comment* on le rend. Le rendu PDF est un adapter d'infrastructure (ReportLab, ADR-0031)
branché derrière le port `GenerateurDocumentsSalle` (`domain/ports.py`), à l'image de la feuille de
marque (`domain/feuille_marque.py`).

Le domaine ne construit **pas** l'URL (il ne connaît ni HTTP ni l'origine réseau du serveur) : c'est
le service applicatif qui la compose à partir de l'origine de la requête et du code, et la dépose
ici prête à encoder. Le QR **ne porte pas** le rattachement lui-même (c'est E04US001) — il n'encode
qu'une URL.
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
