"""Agrégat `Tournoi` — contexte d'un tournoi (E01US001, E01US002).

Enrichit la graine du walking skeleton (E00US009, nom seul) avec les métadonnées de
création — **date**, **lieu** (facultatif), **type** officiel / non officiel (E01US001) — et son
**cycle de vie** (`statut`, sept statuts — E01US002 puis E01US017/[ADR-0026]). Agrégat **pur**
(aucune dépendance framework, immuable) : `creer`/`modifier` valident les valeurs, les transitions
renvoient une copie. Les autres aspects de configuration (catégories, blasons, gabarit de salle,
barème, **départs**…) vivent dans leurs propres agrégats.

Le **tarif** n'est plus porté par le tournoi : depuis ADR-0017 (E02US004) il vit sur chaque
`Depart` (créneau), le tournoi pouvant se jouer sur plusieurs créneaux à des prix différents.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, replace
from enum import Enum

from domain.erreurs import NomTournoiInvalide

TournoiId = int
"""Identifiant technique d'un tournoi, attribué par la persistance."""


class TypeTournoi(str, Enum):
    """Type d'un tournoi : conforme (officiel) ou libre (non officiel)."""

    OFFICIEL = "officiel"
    NON_OFFICIEL = "non_officiel"


class StatutTournoi(str, Enum):
    """Cycle de vie d'un tournoi à **sept statuts** (E01US017, [ADR-0026]).

    Enrichit le cycle à trois statuts d'E01US002 (`brouillon → en_cours → terminé`) : chaque
    statut porte un comportement distinct (règle « un statut n'existe que s'il change un
    comportement »).

    ```
    brouillon ⇄ prêt ─(démarrer)→ en_cours ─(terminer)→ terminé ─(archiver)→ archivé
        │        │                  ⇅ (mettre en pause / reprendre)
        │        │                en_pause
        └────────┴──────────────────┴──(annuler)──→ annulé   (terminal)
    ```

    - `prêt` : config **complète et validée** (feu vert au démarrage) ; suppression encore libre.
    - `en_pause` : **gèle la saisie** de tout le tournoi sans le terminer ; reprend en `en_cours`.
    - `archivé` : **verrou total**, lecture seule définitive (après export, EPIC-11).
    - `annulé` : tournoi abandonné, **conserve la trace** (≠ suppression) ; terminal.

    L'**enchaînement** (qui peut passer de quoi à quoi) et les **gardes** sont arbitrés par le
    service applicatif (ADR-0007/0026 §4) : l'agrégat, lui, ne porte que la valeur et des
    transitions **pures** (précondition garantie en amont).
    """

    BROUILLON = "brouillon"
    PRET = "pret"
    EN_COURS = "en_cours"
    EN_PAUSE = "en_pause"
    TERMINE = "termine"
    ARCHIVE = "archive"
    ANNULE = "annule"


@dataclass(frozen=True)
class Tournoi:
    """Un tournoi. `id` vaut `None` tant que l'agrégat n'est pas persisté."""

    nom: str
    date: datetime.date
    lieu: str | None = None
    type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL
    statut: StatutTournoi = StatutTournoi.BROUILLON
    id: TournoiId | None = None

    @staticmethod
    def creer(
        nom: str,
        date: datetime.date,
        lieu: str | None = None,
        type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL,
    ) -> Tournoi:
        """Crée un tournoi valide (statut `brouillon`) ; lève `NomTournoiInvalide` si le nom
        est vide.

        Le nom et le lieu sont normalisés (espaces de bord retirés) ; un lieu vide devient
        `None` (facultatif). La date et le type sont requis (garantis par la frontière API).
        """
        return Tournoi(
            nom=_nom_valide(nom),
            date=date,
            lieu=_lieu_normalise(lieu),
            type_tournoi=type_tournoi,
            statut=StatutTournoi.BROUILLON,
        )

    def modifier(
        self,
        nom: str,
        date: datetime.date,
        lieu: str | None = None,
        type_tournoi: TypeTournoi = TypeTournoi.NON_OFFICIEL,
    ) -> Tournoi:
        """Renvoie une copie aux métadonnées mises à jour (mêmes règles que `creer`).

        L'`id` et le `statut` sont **préservés** : l'édition des métadonnées (nom, date, lieu,
        type) est autorisée quel que soit le cycle de vie ; seule la **suppression** dépend du
        statut. Lève `NomTournoiInvalide` si le nom est vide.
        """
        return replace(
            self,
            nom=_nom_valide(nom),
            date=date,
            lieu=_lieu_normalise(lieu),
            type_tournoi=type_tournoi,
        )

    def vers_pret(self) -> Tournoi:
        """Renvoie une copie passée `prêt` (précondition `brouillon` + complétude garantie en
        amont)."""
        return replace(self, statut=StatutTournoi.PRET)

    def revenir_brouillon(self) -> Tournoi:
        """Renvoie une copie repassée `brouillon` (rétrogradation d'un `prêt` dont la config n'est
        plus complète, ou renoncement au feu vert — précondition `prêt` garantie en amont)."""
        return replace(self, statut=StatutTournoi.BROUILLON)

    def demarrer(self) -> Tournoi:
        """Renvoie une copie passée `en_cours` (précondition `prêt` garantie en amont)."""
        return replace(self, statut=StatutTournoi.EN_COURS)

    def mettre_en_pause(self) -> Tournoi:
        """Renvoie une copie passée `en_pause` (précondition `en_cours` garantie en amont)."""
        return replace(self, statut=StatutTournoi.EN_PAUSE)

    def reprendre(self) -> Tournoi:
        """Renvoie une copie repassée `en_cours` (précondition `en_pause` garantie en amont)."""
        return replace(self, statut=StatutTournoi.EN_COURS)

    def terminer(self) -> Tournoi:
        """Renvoie une copie passée `terminé` (précondition `en_cours` garantie en amont)."""
        return replace(self, statut=StatutTournoi.TERMINE)

    def archiver(self) -> Tournoi:
        """Renvoie une copie passée `archivé` (verrou total ; précondition `terminé` en amont)."""
        return replace(self, statut=StatutTournoi.ARCHIVE)

    def annuler(self) -> Tournoi:
        """Renvoie une copie passée `annulé` — terminal, conserve la trace (précondition : non
        `terminé`/`archivé`/`annulé`, garantie en amont)."""
        return replace(self, statut=StatutTournoi.ANNULE)


@dataclass(frozen=True)
class TransitionTournoi:
    """Une arête sortante de la machine à états du cycle de vie ([ADR-0026] §2).

    - `nom` : identifiant **stable** de l'action, aligné sur le **suffixe d'endpoint**
      (`POST /api/v1/tournois/{id}/<nom>`) pour que le client mappe directement action → route ;
    - `libelle` : texte du bouton en **langage organisateur** (E14US001, accueil admin) ;
    - `vers` : statut cible une fois la transition appliquée.
    """

    nom: str
    libelle: str
    vers: StatutTournoi


# Topologie du cycle de vie ([ADR-0026] §2), source **unique** côté lecture. Les *gardes* (qui peut
# passer de quoi à quoi, complétude du passage à `prêt`…) restent dans `ServiceTournois`
# (ADR-0026 §4) ; un test de cohérence recoupe cette table avec la légalité effective du service.
_TRANSITIONS: dict[StatutTournoi, tuple[TransitionTournoi, ...]] = {
    StatutTournoi.BROUILLON: (
        TransitionTournoi("vers-pret", "Marquer prêt", StatutTournoi.PRET),
        TransitionTournoi("annuler", "Annuler le tournoi", StatutTournoi.ANNULE),
    ),
    StatutTournoi.PRET: (
        TransitionTournoi("demarrer", "Démarrer", StatutTournoi.EN_COURS),
        TransitionTournoi("revenir-brouillon", "Revenir en brouillon", StatutTournoi.BROUILLON),
        TransitionTournoi("annuler", "Annuler le tournoi", StatutTournoi.ANNULE),
    ),
    StatutTournoi.EN_COURS: (
        TransitionTournoi("mettre-en-pause", "Mettre en pause", StatutTournoi.EN_PAUSE),
        TransitionTournoi("terminer", "Terminer", StatutTournoi.TERMINE),
        TransitionTournoi("annuler", "Annuler le tournoi", StatutTournoi.ANNULE),
    ),
    StatutTournoi.EN_PAUSE: (
        TransitionTournoi("reprendre", "Reprendre", StatutTournoi.EN_COURS),
        TransitionTournoi("annuler", "Annuler le tournoi", StatutTournoi.ANNULE),
    ),
    StatutTournoi.TERMINE: (TransitionTournoi("archiver", "Archiver", StatutTournoi.ARCHIVE),),
    StatutTournoi.ARCHIVE: (),
    StatutTournoi.ANNULE: (),
}


def transitions_possibles(statut: StatutTournoi) -> tuple[TransitionTournoi, ...]:
    """Renvoie les transitions **offertes** depuis `statut` (arêtes d'[ADR-0026] §2).

    Fonction **pure** : topologie du cycle de vie destinée à la lecture (accueil admin E14US001,
    frise à boutons). N'évalue **aucune** garde — une arête offerte peut encore échouer à
    l'exécution (ex. `vers-pret` sans départ → `TournoiSansDepart`), car les gardes vivent dans
    `ServiceTournois` (ADR-0026 §4, règle 2). Les statuts terminaux (`archivé`, `annulé`) renvoient
    un tuple vide.
    """
    return _TRANSITIONS[statut]


def _nom_valide(nom: str) -> str:
    """Normalise le nom (espaces de bord retirés) ; lève `NomTournoiInvalide` si vide."""
    nom_normalise = nom.strip()
    if not nom_normalise:
        raise NomTournoiInvalide("Le nom du tournoi ne peut pas être vide.")
    return nom_normalise


def _lieu_normalise(lieu: str | None) -> str | None:
    """Normalise le lieu ; un lieu vide ou absent devient `None` (facultatif)."""
    if lieu is None:
        return None
    lieu_normalise = lieu.strip()
    return lieu_normalise or None
