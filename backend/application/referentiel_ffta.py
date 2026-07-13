"""Référentiel FFTA — catégories officielles du Tir à 18 m (salle) pré-chargeables (E01US004).

Source de vérité documentaire : `docs/referentiel-ffta.md` §1 à §3 (règlement sportif FFTA,
édition déc. 2023). Données **pures** (aucune dépendance framework/infrastructure) consommées par
`ServiceCategories.precharger_ffta` pour proposer, à la création d'un tournoi, un jeu de catégories
**modifiable et supprimable**. Une catégorie = division (arme) x catégorie d'âge x sexe
(art. A.6.2 / A.7.1.2 / A.7.1.3).

Le jeu encode uniquement les catégories **officielles par division** du §3 (valeurs `✅ FFTA`), et
non le produit cartésien complet arme x âge (qui inventerait des catégories non ouvertes, ex.
poulies U11/U13). L'arme est en texte libre côté domaine (E01US003) ; l'association d'un blason par
défaut viendra en E01US006. Les catégories créées restent ordinaires : modifiables/supprimables via
le CRUD existant.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.categorie import SexeCategorie

# Divisions (armes) reconnues à 18 m — §1 (art. A.6.2).
_ARC_CLASSIQUE = "Arc Classique"
_ARC_POULIES = "Arc à Poulies"
_ARC_NU = "Arc Nu"

# Catégories d'âge ouvertes par division à 18 m — §3 (art. A.7.1.2 / A.7.1.3) :
# - Arc Classique : toute la plage U11 → S3 ;
# - Arc à Poulies : U15 → S3 (U15 ouvert depuis la saison 2024/2025) ;
# - Arc Nu : catégories de classement **regroupées** (U18 = U15+U18 ; Scratch = U21+S1+S2+S3).
_AGES_CLASSIQUE = ("U11", "U13", "U15", "U18", "U21", "S1", "S2", "S3")
_AGES_POULIES = ("U15", "U18", "U21", "S1", "S2", "S3")
_AGES_NU = ("U18", "Scratch")

# Sexes distingués au niveau individuel (Hommes / Femmes) — §2. « Mixte » est réservé aux épreuves
# par équipes et n'entre donc pas dans ce jeu de catégories individuelles.
_SEXES = ((SexeCategorie.HOMME, "Homme"), (SexeCategorie.FEMME, "Femme"))


@dataclass(frozen=True)
class ModeleCategorieFFTA:
    """Gabarit d'une catégorie FFTA à pré-charger (sans rattachement à un tournoi)."""

    libelle: str
    arme: str
    tranche_age: str
    sexe: SexeCategorie


def _modeles_division(arme: str, ages: tuple[str, ...]) -> list[ModeleCategorieFFTA]:
    """Décline une division sur ses catégories d'âge et les deux sexes (Homme/Femme)."""
    return [
        ModeleCategorieFFTA(
            libelle=f"{arme} {age} {libelle_sexe}",
            arme=arme,
            tranche_age=age,
            sexe=sexe,
        )
        for age in ages
        for sexe, libelle_sexe in _SEXES
    ]


def categories_salle_18m() -> list[ModeleCategorieFFTA]:
    """Renvoie le jeu ordonné des catégories FFTA officielles à 18 m (32 catégories).

    Ordre : Arc Classique, puis Arc à Poulies, puis Arc Nu ; à l'intérieur d'une division, par
    catégorie d'âge croissante puis Homme avant Femme. Le libellé (ex. « Arc Classique U18 Homme »)
    reprend division + âge + sexe pour rester lisible dans la liste des catégories.
    """
    return [
        *_modeles_division(_ARC_CLASSIQUE, _AGES_CLASSIQUE),
        *_modeles_division(_ARC_POULIES, _AGES_POULIES),
        *_modeles_division(_ARC_NU, _AGES_NU),
    ]
