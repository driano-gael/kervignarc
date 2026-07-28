"""Référentiel FFTA — catégories officielles du Tir à 18 m (salle) pré-chargeables (E01US004).

Source de vérité documentaire : `docs/referentiel-ffta.md` §1 à §3 (règlement sportif FFTA,
édition déc. 2023). Données **pures** (aucune dépendance framework/infrastructure) consommées par
`ServiceCategories.precharger_ffta` pour proposer, à la création d'un tournoi, un jeu de catégories
**modifiable et supprimable**. Une catégorie = division (arme) x catégorie de classement x sexe
(art. A.6.2 / A.7.1.2 / A.7.1.3).

Le jeu encode uniquement les catégories **officielles par division** du §3 (valeurs `✅ FFTA`), et
non le produit cartésien complet arme x âge (qui inventerait des catégories non ouvertes, ex.
poulies U11/U13). L'arme est en texte libre côté domaine (E01US003). Les catégories créées restent
ordinaires : modifiables/supprimables via le CRUD existant.

**E01US022 — blason par défaut du §3.** Chaque catégorie porte le **blason par défaut** prévu par
la FFTA à 18 m (§3) : Classique U11 → 80 cm, U13/U15 → 60 cm, U18 et au-delà → 40 cm ; Poulies →
triples 40 ; Arc Nu « U18 » → 60 cm, « Scratch » → 40 cm. E01US006 a posé le **mécanisme** (une
catégorie porte un `blason_id`), mais ni le pré-chargement des catégories (E01US004) ni celui des
blasons (E01US005 — CRUD seul, aucun jeu FFTA) ne le renseignaient. Ce module décrit donc aussi
les **blasons FFTA** à pré-charger (`blasons_salle_18m`), que `ServiceCategories.precharger_ffta`
crée puis relie à chaque catégorie. Le `blason_id` étant une clé étrangère vers un blason
**existant du tournoi**, le lien n'est possible qu'une fois ces blasons créés — d'où leur présence
ici, aux côtés des catégories. Blasons et liens restent, comme tout le référentiel, un **template
modifiable** (RG-8), pas une contrainte.

**E01US013 — regroupements d'âge.** L'arc nu regroupe plusieurs tranches sous une catégorie de
classement dont le **libellé n'est pas une tranche** (« U18 » = U15+U18 ; « Scratch » = U21..S3,
§3). On modélise donc chaque catégorie d'âge comme un **groupe** `(libellé, tranches)` : hors arc
nu, le groupe est une tranche unique dont le libellé est son propre code ; en arc nu, le libellé est
découplé de la liste `ages`. C'est ce que la bascule `tranche_age` → `Categorie.ages` (liste) rend
enfin exprimable.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.blason import ZoneScore
from domain.categorie import HAUTEUR_CENTRE_DEFAUT, SexeCategorie, TrancheAge

# Divisions (armes) reconnues à 18 m — §1 (art. A.6.2).
_ARC_CLASSIQUE = "Arc Classique"
_ARC_POULIES = "Arc à Poulies"
_ARC_NU = "Arc Nu"

# Hauteur du centre de l'or des U11 : 110 cm (blason 80 cm, art. C.3.1.1 ;
# `docs/referentiel-ffta.md` §5), contre 130 cm pour toutes les autres catégories. C'est la seule
# valeur non-défaut du référentiel ; elle vit ici (donnée FFTA) et non dans le domaine (ADR-0022).
_HAUTEUR_CENTRE_U11 = 110


@dataclass(frozen=True)
class ModeleBlasonFFTA:
    """Gabarit d'un blason FFTA à pré-charger (sans rattachement à un tournoi).

    `taille` est une **fraction de place** occupée sur une cible (`]0, 1]`), **pas un diamètre** —
    le domaine ne connaît pas les « 80/60/40 cm » (cf. `domain/blason.py`). Les fractions retenues
    sont celles que le moteur de placement (EPIC-03) traite déjà comme canoniques : un blason 80 cm
    remplit une butte (`1.0`), un 60 cm en occupe la moitié (`0.5`), un 40 cm (simple ou triple) un
    quart (`0.25`) — soit 1/2/4 archers par butte. `capacite` = 1 : en qualification chaque archer
    a **son** carton (le domaine sait partager un carton, mais le défaut FFTA ne le fait pas). Un
    triple 40 ne se distingue **pas** par sa taille mais par ses `zones` : il exclut 5 → 1 (son
    minimum marquable est le bleu clair = 6, référentiel §4.4). `zones=None` → jeu complet (10 → 1
    + M), défaut du domaine pour un blason simple.
    """

    nom: str
    taille: float
    capacite: int
    zones: tuple[ZoneScore, ...] | None


# Zones d'un triple 40 (§4.4) : pas de 5 → 1 ; `M` (manqué) reste toujours admis — le domaine
# l'exige, et un manqué est physiquement possible sur tout carton.
_ZONES_TRIPLE_40: tuple[ZoneScore, ...] = (
    ZoneScore.DIX,
    ZoneScore.NEUF,
    ZoneScore.HUIT,
    ZoneScore.SEPT,
    ZoneScore.SIX,
    ZoneScore.MANQUE,
)

# Les quatre blasons par défaut du §3 à 18 m. Le `nom` est **canonique** : il sert de clé
# d'idempotence au pré-chargement (comparaison casefold) et de lien catégorie → blason.
_BLASON_80 = ModeleBlasonFFTA("Blason 80 cm", taille=1.0, capacite=1, zones=None)
_BLASON_60 = ModeleBlasonFFTA("Blason 60 cm", taille=0.5, capacite=1, zones=None)
_BLASON_40 = ModeleBlasonFFTA("Blason 40 cm", taille=0.25, capacite=1, zones=None)
_TRIPLE_40 = ModeleBlasonFFTA("Triple 40 cm", taille=0.25, capacite=1, zones=_ZONES_TRIPLE_40)


def blasons_salle_18m() -> list[ModeleBlasonFFTA]:
    """Renvoie les blasons FFTA par défaut à 18 m (§3), ordre 80 → 60 → 40 → triple 40."""
    return [_BLASON_80, _BLASON_60, _BLASON_40, _TRIPLE_40]


# Un « groupe d'âge » d'une division = (libellé affiché, tranches couvertes, **nom du blason par
# défaut §3**). Hors arc nu, un groupe est une tranche unique (libellé = code de la tranche). En arc
# nu, le classement regroupe plusieurs tranches sous un libellé qui n'est PAS une tranche — d'où le
# découplage libellé ↔ `ages`.
GroupeAge = tuple[str, tuple[TrancheAge, ...], str]


# Blason par défaut d'une catégorie d'Arc Classique, par tranche (§3) : U11 → 80 cm, U13/U15 →
# 60 cm, U18 et au-delà → 40 cm. L'ordre du dict fixe l'ordre des catégories créées (U11 → S3).
_BLASON_CLASSIQUE_PAR_TRANCHE: dict[TrancheAge, str] = {
    TrancheAge.U11: _BLASON_80.nom,
    TrancheAge.U13: _BLASON_60.nom,
    TrancheAge.U15: _BLASON_60.nom,
    TrancheAge.U18: _BLASON_40.nom,
    TrancheAge.U21: _BLASON_40.nom,
    TrancheAge.S1: _BLASON_40.nom,
    TrancheAge.S2: _BLASON_40.nom,
    TrancheAge.S3: _BLASON_40.nom,
}

# Catégories d'âge ouvertes par division à 18 m — §3 (art. A.7.1.2 / A.7.1.3) :
# - Arc Classique : toute la plage U11 → S3, blason selon la tranche (ci-dessus) ;
# - Arc à Poulies : U15 → S3 (U15 ouvert depuis la saison 2024/2025), toutes sur triples 40 ;
# - Arc Nu : catégories de classement **regroupées** (« U18 » = U15+U18 → 60 cm ;
#   « Scratch » = U21..S3 → 40 cm).
_GROUPES_CLASSIQUE: tuple[GroupeAge, ...] = tuple(
    (tranche.value, (tranche,), blason) for tranche, blason in _BLASON_CLASSIQUE_PAR_TRANCHE.items()
)
_GROUPES_POULIES: tuple[GroupeAge, ...] = tuple(
    (tranche.value, (tranche,), _TRIPLE_40.nom)
    for tranche in (
        TrancheAge.U15,
        TrancheAge.U18,
        TrancheAge.U21,
        TrancheAge.S1,
        TrancheAge.S2,
        TrancheAge.S3,
    )
)
_GROUPES_NU: tuple[GroupeAge, ...] = (
    ("U18", (TrancheAge.U15, TrancheAge.U18), _BLASON_60.nom),
    ("Scratch", (TrancheAge.U21, TrancheAge.S1, TrancheAge.S2, TrancheAge.S3), _BLASON_40.nom),
)

# Sexes distingués au niveau individuel (Hommes / Femmes) — §2. « Mixte » est réservé aux épreuves
# par équipes et n'entre donc pas dans ce jeu de catégories individuelles.
_SEXES = ((SexeCategorie.HOMME, "Homme"), (SexeCategorie.FEMME, "Femme"))


@dataclass(frozen=True)
class ModeleCategorieFFTA:
    """Gabarit d'une catégorie FFTA à pré-charger (sans rattachement à un tournoi).

    `ages` porte **au moins une** tranche (le regroupement arc nu en porte plusieurs), là où une
    catégorie créée à la main peut n'en porter aucune. `hauteur_cm` est la hauteur du centre de
    l'or (110 pour les U11, 130 sinon — ADR-0022), déduite des `ages`. `blason_nom` est le nom
    canonique du blason par défaut du §3 (E01US022) — `precharger_ffta` le résout en `blason_id`.
    """

    libelle: str
    arme: str
    ages: tuple[TrancheAge, ...]
    sexe: SexeCategorie
    hauteur_cm: int
    blason_nom: str


def _hauteur_du_groupe(ages: tuple[TrancheAge, ...]) -> int:
    """Hauteur du centre d'un groupe d'âge : 110 cm si U11 en fait partie, 130 sinon (§5).

    U11 est un groupe à tranche unique dans le référentiel (jamais mêlé à d'autres tranches), donc
    la présence de `U11` détermine sans ambiguïté la hauteur du blason 80 cm."""
    return _HAUTEUR_CENTRE_U11 if TrancheAge.U11 in ages else HAUTEUR_CENTRE_DEFAUT


def _modeles_division(arme: str, groupes: tuple[GroupeAge, ...]) -> list[ModeleCategorieFFTA]:
    """Décline une division sur ses groupes d'âge et les deux sexes (Homme/Femme)."""
    return [
        ModeleCategorieFFTA(
            libelle=f"{arme} {libelle_age} {libelle_sexe}",
            arme=arme,
            ages=ages,
            sexe=sexe,
            hauteur_cm=_hauteur_du_groupe(ages),
            blason_nom=blason_nom,
        )
        for libelle_age, ages, blason_nom in groupes
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
