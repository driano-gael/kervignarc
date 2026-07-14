"""Agrégat `GabaritSalle` — un plan de salle réutilisable (E01US007) et son application à un
tournoi (E01US008).

Décrit une disposition de cibles portant un `nom` et, pour chaque **cible**, un **plafond
d'archers** (`capacite`, de 1 à 4, défaut 4). Ce plafond borne le nombre d'archers admis sur la
cible ; les **positions** occupées (A, B, C, D) en découlent (plafond 4 → A/B/C/D, 2 → A/B,
1 → A). Le **remplissage réel** d'une cible selon la taille des blasons — et le regroupement des
blasons de même type — relève du **placement** (EPIC-03), pas de cet agrégat.

Un gabarit est soit un **modèle de bibliothèque** (`tournoi_id is None`), réutilisable d'un
tournoi à l'autre, soit une **instance appliquée** à un tournoi (`tournoi_id` renseigné).
Appliquer un modèle à un tournoi en produit une **copie** (`pour_tournoi`) : l'instance est
ensuite ajustable **sans altérer** le modèle d'origine (`ajuster`, plafond cible par cible).
Agrégat de domaine **pur** (immuable, sans dépendance framework), validé à la création/édition.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from domain.erreurs import CapaciteCibleInvalide, NombreCiblesInvalide, NomGabaritInvalide
from domain.tournoi import TournoiId

GabaritSalleId = int
"""Identifiant technique d'un gabarit de salle, attribué par la persistance."""

POSITIONS = ("A", "B", "C", "D")
"""Positions physiques d'une cible, dans l'ordre de remplissage."""

CAPACITE_CIBLE_MIN = 1
CAPACITE_CIBLE_MAX = len(POSITIONS)  # 4 : autant de positions que de lettres A/B/C/D
CAPACITE_CIBLE_DEFAUT = CAPACITE_CIBLE_MAX  # une cible accueille 4 archers par défaut


@dataclass(frozen=True)
class Cible:
    """Une cible du gabarit : son rang (1-based) et son plafond d'archers."""

    index: int
    capacite: int

    @property
    def positions(self) -> tuple[str, ...]:
        """Positions occupables, déduites du plafond (les `capacite` premières lettres)."""
        return POSITIONS[: self.capacite]


@dataclass(frozen=True)
class GabaritSalle:
    """Un gabarit de salle. `id` vaut `None` tant qu'il n'est pas persisté.

    L'état porte le plafond d'archers de **chaque** cible (`capacites`, une valeur par cible) :
    la représentation est par-cible, ce qui permet l'ajustement fin d'E01US008 (`ajuster`), même
    si la création d'E01US007 remplit ces plafonds de façon **uniforme**.

    `tournoi_id` distingue les deux natures d'un gabarit : `None` pour un **modèle** de
    bibliothèque (réutilisable), un identifiant de tournoi pour une **instance appliquée** —
    copie propre à ce tournoi, ajustable sans toucher au modèle.
    """

    nom: str
    capacites: tuple[int, ...]
    id: GabaritSalleId | None = None
    tournoi_id: TournoiId | None = None

    @staticmethod
    def creer(nom: str, nb_cibles: int, capacite: int = CAPACITE_CIBLE_DEFAUT) -> GabaritSalle:
        """Crée un gabarit **modèle** de `nb_cibles` cibles, toutes au même plafond (défaut 4).

        Le `nom` est normalisé (espaces de bord retirés) et ne peut pas être vide ; `nb_cibles`
        doit être `>= 1` ; `capacite` doit être dans `[1, 4]`. Lève l'erreur de domaine
        correspondante en cas de valeur invalide.
        """
        return GabaritSalle(
            nom=_nom_valide(nom), capacites=_capacites_uniformes(nb_cibles, capacite)
        )

    def modifier(
        self, nom: str, nb_cibles: int, capacite: int = CAPACITE_CIBLE_DEFAUT
    ) -> GabaritSalle:
        """Renvoie une copie aux attributs mis à jour (mêmes règles que `creer`).

        L'`id` (et `tournoi_id`) sont **préservés**. Comme `creer`, le plafond est appliqué
        uniformément à toutes les cibles ; l'ajustement cible par cible passe par `ajuster`.
        """
        return replace(
            self, nom=_nom_valide(nom), capacites=_capacites_uniformes(nb_cibles, capacite)
        )

    def pour_tournoi(self, tournoi_id: TournoiId) -> GabaritSalle:
        """Instancie ce modèle pour un tournoi (E01US008) : renvoie une **copie détachée**.

        La copie reprend `nom` et `capacites` mais **repart d'un `id` neuf** (`None`, à
        persister) et porte le `tournoi_id` : elle est propre au tournoi, si bien qu'un ajustement
        ultérieur ne touche jamais au modèle d'origine. À appeler sur un modèle (`tournoi_id`
        None) ; le service garantit cette précondition.
        """
        return replace(self, id=None, tournoi_id=tournoi_id)

    def ajuster(self, nom: str, capacites: tuple[int, ...]) -> GabaritSalle:
        """Ajuste une instance de tournoi (E01US008) : nom + plafond **cible par cible**.

        `capacites` porte une valeur par cible (son nombre fixe donc le nombre de cibles, `>= 1`) ;
        chaque plafond doit être dans `[1, 4]`. `id` et `tournoi_id` sont **préservés**. Lève
        l'erreur de domaine correspondante en cas de valeur invalide.
        """
        return replace(self, nom=_nom_valide(nom), capacites=_capacites_par_cible(capacites))

    @property
    def nb_cibles(self) -> int:
        """Nombre de cibles du gabarit."""
        return len(self.capacites)

    @property
    def cibles(self) -> tuple[Cible, ...]:
        """Les cibles du gabarit, numérotées à partir de 1, avec leur plafond."""
        return tuple(
            Cible(index=index, capacite=capacite)
            for index, capacite in enumerate(self.capacites, start=1)
        )


def _nom_valide(nom: str) -> str:
    """Normalise le nom ; lève `NomGabaritInvalide` s'il est vide."""
    nom_normalise = nom.strip()
    if not nom_normalise:
        raise NomGabaritInvalide("Le nom d'un gabarit de salle ne peut pas être vide.")
    return nom_normalise


def _capacites_uniformes(nb_cibles: int, capacite: int) -> tuple[int, ...]:
    """Construit `nb_cibles` plafonds identiques ; valide le nombre de cibles et le plafond."""
    if nb_cibles < 1:
        raise NombreCiblesInvalide("Un gabarit de salle doit compter au moins une cible.")
    return tuple(_capacite_valide(capacite) for _ in range(nb_cibles))


def _capacites_par_cible(capacites: tuple[int, ...]) -> tuple[int, ...]:
    """Valide une liste de plafonds cible par cible : au moins une cible, chaque plafond dans
    `[1, 4]`."""
    if not capacites:
        raise NombreCiblesInvalide("Un gabarit de salle doit compter au moins une cible.")
    return tuple(_capacite_valide(capacite) for capacite in capacites)


def _capacite_valide(capacite: int) -> int:
    """Vérifie que le plafond d'archers d'une cible est un entier dans `[1, 4]`."""
    if not CAPACITE_CIBLE_MIN <= capacite <= CAPACITE_CIBLE_MAX:
        raise CapaciteCibleInvalide(
            f"Le plafond d'archers d'une cible doit être compris entre {CAPACITE_CIBLE_MIN} "
            f"et {CAPACITE_CIBLE_MAX}."
        )
    return capacite
