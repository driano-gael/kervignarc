"""Agrégat **Categorie** — le blason par défaut est facultatif ; sa cohérence est au service.

⚠️ **`ages` est une LISTE, pas un scalaire** : la FFTA regroupe des tranches sous une même
catégorie de classement — en arc nu, « U18 » couvre U15 **et** U18. Un scalaire rendait les cas
indistinguables (`"U18"` valant « U18 seul » en classique, « U15 ou U18 » en arc nu). Les
regroupements redeviennent ainsi de simples **libellés**.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from enum import Enum

from domain.blason import BlasonId
from domain.erreurs import HauteurCentreInvalide, LibelleCategorieInvalide
from domain.patrimoine import OrigineBrique
from domain.tournoi import TournoiId

CategorieId = int
"""Identifiant technique d'une catégorie, attribué par la persistance."""

HAUTEUR_CENTRE_DEFAUT = 130
"""Hauteur du centre de l'or (sol → centre), en cm — cas FFTA majoritaire (art. B.2.2.1.1).

Les U11 tirent à **110 cm** (blason 80 cm, art. C.3.1.1) : cette valeur-là est portée par le
**référentiel** (`application/referentiel_ffta.py`), pas ici — le domaine ne connaît que le défaut
et sa validation (ADR-0022). C'est cette hauteur qui pilote la contrainte de placement « une butte,
une seule hauteur » (E03US001, `docs/referentiel-ffta.md` §5)."""


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
    """Une catégorie — **modèle de bibliothèque** ou copie d'un tournoi (E01US023, ADR-0060).

    `tournoi_id is None` : modèle du **patrimoine du club**, réutilisable d'une année sur l'autre.
    Renseigné : **copie** d'un tournoi, ajustable sans altérer le modèle (même patron que
    `gabarit_salle`). `ages` est un **tuple** (règle 4) de tranches éligibles, vide par défaut, qui
    représente un **ensemble** : dédoublonné et ordonné canoniquement (`_ages_valides`), pour que
    deux catégories aux mêmes tranches soient égales.
    """

    tournoi_id: TournoiId | None
    libelle: str
    arme: str | None = None
    ages: tuple[TrancheAge, ...] = ()
    sexe: SexeCategorie | None = None
    blason_id: BlasonId | None = None
    hauteur_cm: int = HAUTEUR_CENTRE_DEFAUT
    origine: OrigineBrique = OrigineBrique.UTILISATEUR
    id: CategorieId | None = None

    @staticmethod
    def creer(
        tournoi_id: TournoiId | None,
        libelle: str,
        arme: str | None = None,
        ages: Iterable[TrancheAge] = (),
        sexe: SexeCategorie | None = None,
        blason_id: BlasonId | None = None,
        hauteur_cm: int = HAUTEUR_CENTRE_DEFAUT,
        *,
        origine: OrigineBrique = OrigineBrique.UTILISATEUR,
    ) -> Categorie:
        """Crée une catégorie valide ; lève `LibelleCategorieInvalide` si le libellé est vide.

        Libellé et arme normalisés (arme vide → `None`). `ages` accepte n'importe quel ordre et des
        doublons — la valeur stockée est canonique. `blason_id` facultatif : l'agrégat ne **vérifie
        pas** l'existence ni le rattachement du blason (règle inter-agrégats portée par le
        service). `hauteur_cm` (centre de l'or, défaut 130) : `HauteurCentreInvalide` si non entier
        > 0.
        """
        return Categorie(
            tournoi_id=tournoi_id,
            libelle=_libelle_valide(libelle),
            arme=_texte_facultatif(arme),
            ages=_ages_valides(ages),
            sexe=sexe,
            blason_id=blason_id,
            hauteur_cm=_hauteur_valide(hauteur_cm),
            origine=origine,
        )

    def pour_tournoi(self, tournoi_id: TournoiId, blason_id: BlasonId | None) -> Categorie:
        """Copie ce modèle de bibliothèque en **catégorie d'un tournoi**, non persistée (E01US023).

        ⚠️ `blason_id` est **fourni par l'appelant** : c'est une **clé étrangère**, et la recopier
        ferait pointer la catégorie du tournoi vers le blason de la *bibliothèque*. Seul le service
        voit les deux collections et sait à quelle copie réattacher le lien (même partage des rôles
        que `BlasonHorsTournoi`). L'`id` repart à `None`, l'`origine` **suit** le modèle.
        """
        return replace(self, tournoi_id=tournoi_id, blason_id=blason_id, id=None)

    def en_bibliotheque(self, blason_id: BlasonId | None) -> Categorie:
        """Détache cette catégorie en **modèle de bibliothèque**, non persisté (**promotion**).

        Miroir de `pour_tournoi`, `blason_id` compris : au retour, le lien doit viser le blason
        **de la bibliothèque**, que seul le service sait résoudre.
        """
        return replace(self, tournoi_id=None, blason_id=blason_id, id=None)

    def modifier(
        self,
        libelle: str,
        arme: str | None = None,
        ages: Iterable[TrancheAge] = (),
        sexe: SexeCategorie | None = None,
        blason_id: BlasonId | None = None,
        hauteur_cm: int = HAUTEUR_CENTRE_DEFAUT,
    ) -> Categorie:
        """Renvoie une copie aux attributs mis à jour (mêmes règles que `creer`).

        L'`id` et le `tournoi_id` sont **préservés** (on ne déplace pas une catégorie d'un
        tournoi à l'autre). `blason_id` remplace le blason par défaut (`None` le retire),
        `hauteur_cm` la hauteur du centre. Lève `LibelleCategorieInvalide` si le libellé est vide,
        `HauteurCentreInvalide` si la hauteur n'est pas un entier strictement positif.
        """
        return replace(
            self,
            libelle=_libelle_valide(libelle),
            arme=_texte_facultatif(arme),
            ages=_ages_valides(ages),
            sexe=sexe,
            blason_id=blason_id,
            hauteur_cm=_hauteur_valide(hauteur_cm),
        )


def _libelle_valide(libelle: str) -> str:
    """Normalise le libellé ; lève `LibelleCategorieInvalide` s'il est vide."""
    libelle_normalise = libelle.strip()
    if not libelle_normalise:
        raise LibelleCategorieInvalide("Le libellé d'une catégorie ne peut pas être vide.")
    return libelle_normalise


def _hauteur_valide(hauteur_cm: int) -> int:
    """Vérifie que la hauteur du centre est un entier strictement positif ; lève sinon.

    On ne borne **pas** par le haut (pas de « ≤ 300 ») : le référentiel ne fixe que deux valeurs
    d'usage (110/130), toute borne serait arbitraire, et une hauteur farfelue est une erreur de
    saisie visible, pas un invariant physique à défendre ici (règle 12). Le **type** (entier) est
    garanti par la frontière (Pydantic, règle 6) comme pour `taille`/`capacite` — on ne le revérifie
    pas ici."""
    if hauteur_cm <= 0:
        raise HauteurCentreInvalide(
            "La hauteur du centre d'une catégorie doit être un entier strictement positif (cm)."
        )
    return hauteur_cm


def _texte_facultatif(valeur: str | None) -> str | None:
    """Normalise un champ texte facultatif ; une valeur vide ou absente devient `None`."""
    if valeur is None:
        return None
    valeur_normalisee = valeur.strip()
    return valeur_normalisee or None


def _ages_valides(ages: Iterable[TrancheAge]) -> tuple[TrancheAge, ...]:
    """Renvoie les tranches **dédoublonnées et ordonnées** par âge canonique (U11 → S3).

    `ages` est un **ensemble** d'éligibilité, pas une séquence significative : deux catégories aux
    mêmes tranches dans un ordre différent sont identiques. La représentation canonique rend
    l'égalité de deux `Categorie` stable et la comparaison d'ensembles directe. Le typage
    `TrancheAge` ferme le vocabulaire — une valeur hors des huit est rejetée à la frontière.
    """
    presentes = set(ages)
    return tuple(tranche for tranche in TrancheAge if tranche in presentes)
