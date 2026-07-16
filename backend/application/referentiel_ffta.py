"""Référentiel FFTA — catégories officielles du Tir à 18 m (salle) pré-chargeables (E01US004).

Source de vérité documentaire : `docs/referentiel-ffta.md` §1 à §3 (règlement sportif FFTA,
édition déc. 2023). Données **pures** (aucune dépendance framework/infrastructure) consommées par
`ServiceCategories.precharger_ffta` pour proposer, à la création d'un tournoi, un jeu de catégories
**modifiable et supprimable**. Une catégorie = division (arme) x catégorie de classement x sexe
(art. A.6.2 / A.7.1.2 / A.7.1.3).

Le jeu encode uniquement les catégories **officielles par division** du §3 (valeurs `✅ FFTA`), et
non le produit cartésien complet arme x âge (qui inventerait des catégories non ouvertes, ex.
poulies U11/U13). L'arme est en texte libre côté domaine (E01US003) ; l'association d'un blason par
défaut viendra en E01US006. Les catégories créées restent ordinaires : modifiables/supprimables via
le CRUD existant.

**E01US013 — regroupements d'âge.** L'arc nu regroupe plusieurs tranches sous une catégorie de
classement dont le **libellé n'est pas une tranche** (« U18 » = U15+U18 ; « Scratch » = U21..S3,
§3). On modélise donc chaque catégorie d'âge comme un **groupe** `(libellé, tranches)` : hors arc
nu, le groupe est une tranche unique dont le libellé est son propre code ; en arc nu, le libellé est
découplé de la liste `ages`. C'est ce que la bascule `tranche_age` → `Categorie.ages` (liste) rend
enfin exprimable.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.categorie import SexeCategorie, TrancheAge

# Divisions (armes) reconnues à 18 m — §1 (art. A.6.2).
_ARC_CLASSIQUE = "Arc Classique"
_ARC_POULIES = "Arc à Poulies"
_ARC_NU = "Arc Nu"

# Un « groupe d'âge » d'une division = (libellé affiché, tranches couvertes). Hors arc nu, un groupe
# est une tranche unique (libellé = code de la tranche). En arc nu, le classement regroupe plusieurs
# tranches sous un libellé qui n'est PAS une tranche — d'où le découplage libellé ↔ `ages`.
GroupeAge = tuple[str, tuple[TrancheAge, ...]]


def _tranches_seules(*tranches: TrancheAge) -> tuple[GroupeAge, ...]:
    """Un groupe par tranche, libellé = code de la tranche (cas Arc Classique / Arc à Poulies)."""
    return tuple((tranche.value, (tranche,)) for tranche in tranches)


# Catégories d'âge ouvertes par division à 18 m — §3 (art. A.7.1.2 / A.7.1.3) :
# - Arc Classique : toute la plage U11 → S3 ;
# - Arc à Poulies : U15 → S3 (U15 ouvert depuis la saison 2024/2025) ;
# - Arc Nu : catégories de classement **regroupées** (« U18 » = U15+U18 ; « Scratch » = U21..S3).
_GROUPES_CLASSIQUE = _tranches_seules(
    TrancheAge.U11,
    TrancheAge.U13,
    TrancheAge.U15,
    TrancheAge.U18,
    TrancheAge.U21,
    TrancheAge.S1,
    TrancheAge.S2,
    TrancheAge.S3,
)
_GROUPES_POULIES = _tranches_seules(
    TrancheAge.U15,
    TrancheAge.U18,
    TrancheAge.U21,
    TrancheAge.S1,
    TrancheAge.S2,
    TrancheAge.S3,
)
_GROUPES_NU: tuple[GroupeAge, ...] = (
    ("U18", (TrancheAge.U15, TrancheAge.U18)),
    ("Scratch", (TrancheAge.U21, TrancheAge.S1, TrancheAge.S2, TrancheAge.S3)),
)

# Sexes distingués au niveau individuel (Hommes / Femmes) — §2. « Mixte » est réservé aux épreuves
# par équipes et n'entre donc pas dans ce jeu de catégories individuelles.
_SEXES = ((SexeCategorie.HOMME, "Homme"), (SexeCategorie.FEMME, "Femme"))


@dataclass(frozen=True)
class ModeleCategorieFFTA:
    """Gabarit d'une catégorie FFTA à pré-charger (sans rattachement à un tournoi).

    `ages` porte **au moins une** tranche (le regroupement arc nu en porte plusieurs), là où une
    catégorie créée à la main peut n'en porter aucune.
    """

    libelle: str
    arme: str
    ages: tuple[TrancheAge, ...]
    sexe: SexeCategorie


def _modeles_division(arme: str, groupes: tuple[GroupeAge, ...]) -> list[ModeleCategorieFFTA]:
    """Décline une division sur ses groupes d'âge et les deux sexes (Homme/Femme)."""
    return [
        ModeleCategorieFFTA(
            libelle=f"{arme} {libelle_age} {libelle_sexe}",
            arme=arme,
            ages=ages,
            sexe=sexe,
        )
        for libelle_age, ages in groupes
        for sexe, libelle_sexe in _SEXES
    ]


def categories_salle_18m() -> list[ModeleCategorieFFTA]:
    """Renvoie le jeu ordonné des catégories FFTA officielles à 18 m (32 catégories).

    Ordre : Arc Classique, puis Arc à Poulies, puis Arc Nu ; à l'intérieur d'une division, par
    groupe d'âge croissant puis Homme avant Femme. Le libellé (ex. « Arc Classique U18 Homme »,
    « Arc Nu Scratch Femme ») reprend division + libellé d'âge + sexe pour rester lisible dans la
    liste des catégories, indépendamment des tranches réellement couvertes par `ages`.
    """
    return [
        *_modeles_division(_ARC_CLASSIQUE, _GROUPES_CLASSIQUE),
        *_modeles_division(_ARC_POULIES, _GROUPES_POULIES),
        *_modeles_division(_ARC_NU, _GROUPES_NU),
    ]
