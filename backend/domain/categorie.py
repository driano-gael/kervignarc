"""Agrégat `Categorie` — une catégorie de tir d'un tournoi (E01US003, `ages` : E01US013).

Sert à **classer et cloisonner** les archers (arme, tranches d'âge, sexe). Agrégat de domaine
**pur** (aucune dépendance framework, immuable), validé à la création/édition : seul le `libelle`
est obligatoire ; `arme`, `ages` et `sexe` sont facultatifs (le référentiel FFTA officiel sera
pré-chargé et modifiable en E01US004). Une catégorie peut porter un **blason par défaut** facultatif
(`blason_id`, E01US006) exploité par le placement (EPIC-03) ; la cohérence de ce lien (le blason
doit appartenir au même tournoi) relève d'une règle **inter-agrégats**, vérifiée par le service
applicatif, non par cet agrégat.

**E01US013 — pourquoi `ages` (liste) et non `tranche_age` (scalaire).** La FFTA regroupe des
tranches d'âge sous une même catégorie de classement : en arc nu, « U18 » couvre **U15 et U18**,
« Scratch » couvre **U21, S1, S2, S3** (`docs/referentiel-ffta.md` §3). Un scalaire rendait ces cas
indistinguables (`tranche_age = "U18"` = « U18 seul » en classique, « U15 ou U18 » en arc nu — même
valeur, deux sens). `ages` porte donc **l'ensemble** des tranches éligibles, et les regroupements
(« U18 », « Scratch ») redeviennent de simples **libellés** de catégorie, pas des tranches.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from enum import Enum

from domain.blason import BlasonId
from domain.erreurs import LibelleCategorieInvalide
from domain.tournoi import TournoiId

CategorieId = int
"""Identifiant technique d'une catégorie, attribué par la persistance."""


class TrancheAge(str, Enum):
    """Tranche d'âge FFTA (art. C.3.1) — âge atteint dans l'année civile.

    Vocabulaire **fermé** des huit tranches officielles à 18 m (`docs/referentiel-ffta.md` §2). Une
    catégorie est éligible à **une ou plusieurs** de ces tranches (`Categorie.ages`). Les
    regroupements de classement de l'arc nu (« U18 » = U15+U18, « Scratch » = U21..S3) sont des
    **libellés** de catégorie, pas des tranches : ils n'apparaissent donc jamais ici.
    """

    U11 = "U11"
    U13 = "U13"
    U15 = "U15"
    U18 = "U18"
    U21 = "U21"
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"


class SexeCategorie(str, Enum):
    """Sexe d'une catégorie : homme, femme ou mixte (facultatif au niveau de la catégorie)."""

    HOMME = "H"
    FEMME = "F"
    MIXTE = "mixte"


@dataclass(frozen=True)
class Categorie:
    """Une catégorie rattachée à un tournoi. `id` vaut `None` tant qu'elle n'est pas persistée.

    `ages` est un **tuple** (immuable, règle 4) de tranches éligibles, vide par défaut (aucune
    contrainte d'âge). Il représente un **ensemble** : dédoublonné et ordonné canoniquement à la
    construction (cf. `_ages_valides`), pour que deux catégories aux mêmes tranches soient égales.
    """

    tournoi_id: TournoiId
    libelle: str
    arme: str | None = None
    ages: tuple[TrancheAge, ...] = ()
    sexe: SexeCategorie | None = None
    blason_id: BlasonId | None = None
    id: CategorieId | None = None

    @staticmethod
    def creer(
        tournoi_id: TournoiId,
        libelle: str,
        arme: str | None = None,
        ages: Iterable[TrancheAge] = (),
        sexe: SexeCategorie | None = None,
        blason_id: BlasonId | None = None,
    ) -> Categorie:
        """Crée une catégorie valide ; lève `LibelleCategorieInvalide` si le libellé est vide.

        Le libellé et l'arme sont normalisés (espaces de bord retirés) ; une arme vide devient
        `None`. `ages` accepte une ou plusieurs `TrancheAge`, dans n'importe quel ordre et avec
        d'éventuels doublons — la valeur stockée est canonique (cf. `_ages_valides`). `blason_id`
        est le blason par défaut, facultatif : `None` = aucun. L'agrégat ne **vérifie pas**
        l'existence ni le rattachement du blason (règle inter-agrégats portée par le service).
        """
        return Categorie(
            tournoi_id=tournoi_id,
            libelle=_libelle_valide(libelle),
            arme=_texte_facultatif(arme),
            ages=_ages_valides(ages),
            sexe=sexe,
            blason_id=blason_id,
        )

    def modifier(
        self,
        libelle: str,
        arme: str | None = None,
        ages: Iterable[TrancheAge] = (),
        sexe: SexeCategorie | None = None,
        blason_id: BlasonId | None = None,
    ) -> Categorie:
        """Renvoie une copie aux attributs mis à jour (mêmes règles que `creer`).

        L'`id` et le `tournoi_id` sont **préservés** (on ne déplace pas une catégorie d'un
        tournoi à l'autre). `blason_id` remplace le blason par défaut (`None` le retire). Lève
        `LibelleCategorieInvalide` si le libellé est vide.
        """
        return replace(
            self,
            libelle=_libelle_valide(libelle),
            arme=_texte_facultatif(arme),
            ages=_ages_valides(ages),
            sexe=sexe,
            blason_id=blason_id,
        )


def _libelle_valide(libelle: str) -> str:
    """Normalise le libellé ; lève `LibelleCategorieInvalide` s'il est vide."""
    libelle_normalise = libelle.strip()
    if not libelle_normalise:
        raise LibelleCategorieInvalide("Le libellé d'une catégorie ne peut pas être vide.")
    return libelle_normalise


def _texte_facultatif(valeur: str | None) -> str | None:
    """Normalise un champ texte facultatif ; une valeur vide ou absente devient `None`."""
    if valeur is None:
        return None
    valeur_normalisee = valeur.strip()
    return valeur_normalisee or None


def _ages_valides(ages: Iterable[TrancheAge]) -> tuple[TrancheAge, ...]:
    """Renvoie les tranches **dédoublonnées et ordonnées** par âge canonique (U11 → S3).

    `ages` est un **ensemble** d'éligibilité, pas une séquence significative pour l'appelant : deux
    catégories aux mêmes tranches dans un ordre différent sont identiques. On renvoie donc une
    représentation canonique (parcours de `TrancheAge` dans son ordre de déclaration), ce qui rend
    l'égalité de deux `Categorie` stable et la comparaison d'ensembles (invariant d'éligibilité,
    testé sur le référentiel) directe. Le typage `TrancheAge` ferme le vocabulaire : une valeur hors
    des huit tranches ne peut pas atteindre le domaine (rejetée à la frontière API).
    """
    presentes = set(ages)
    return tuple(tranche for tranche in TrancheAge if tranche in presentes)
