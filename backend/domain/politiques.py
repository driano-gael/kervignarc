"""Politiques injectables du moteur de phases (E05US003, [ADR-0004] / [ADR-0046]).

Un **format** de phase de tableau n'est pas du code mais un **assemblage de stratégies** (règle 2) :
comment on route le perdant, comment on score, comment on ensemence l'arbre, à qui vont les byes,
comment on départage, jusqu'où on classe. ADR-0004 en fait **six familles** de politiques, chacune
une interface du domaine (`Protocol`) avec au moins une implémentation :

| Famille    | Rôle                                   | Implémentation de ce socle |
|------------|----------------------------------------|----------------------------|
| `routing`  | destination du perdant                 | `EliminationSeche`         |
| `scoring`  | calcul du score / de la victoire       | `ScoreCumul`               |
| `seeding`  | composition de l'arbre                 | `SeedingSerpent`           |
| `byes`     | exempts si effectif ≠ 2^k              | `ByesAuxMieuxClasses`      |
| `tiebreak` | départage des égalités                 | `TiebreakFftaDefaut`       |
| `depth`    | jusqu'où classer                       | `ProfondeurUnVersN`        |

**Portée E05US003.** Ce module livre les **interfaces**, une implémentation **pure et testable**
par famille, et l'**assemblage** d'une `config.policies` en un jeu résolu (`PolitiquesPhase`) via un
`RegistrePolitiques` que la **composition root** peuple (CA « assemblage »). Le *tableau* qui
orchestre ces stratégies (dimensionnement 2^k, génération, progression, podium) est **E05US005**
(élimination directe) et **E05US010** (placement intégral, routing en cascade) : ils **consomment**
ces politiques déjà éprouvées. Les stratégies couplées à la structure d'arbre exposent donc ici leur
méthode **fondatrice** (celle dont la règle est écrite) ; les US consommatrices la **ressigneront**
au fil de leurs besoins — ADR-0004 décrit déjà `route(perdant, tour, contexte)` là où ce socle
n'expose que `destination_du_perdant()`, et le barème par sets renverra un nombre de sets, pas un
total : ce sont des **ruptures de contrat**, bon marché tant qu'il n'y a **qu'un implémenteur et
aucun consommateur** par famille (la situation d'aujourd'hui). C'est le sur-gel prématuré que
DETTE-003 mettait en garde d'éviter — singulièrement pour le `scoring` : on livre étroit et honnête
plutôt que de figer une signature spéculative.

**Forme de la config (ADR-0046, résorbe DETTE-003).** Chaque politique vit sous `config.policies`,
désignée par un objet `{"nom": <implémentation>, …paramètres}` — un **nom** (l'implémentation
résolue par le registre) **et** des paramètres (le barème de qualif se *paramètre*, il ne se choisit
pas dans un catalogue fermé). Le grain de `validation` **n'est pas** une politique de moteur : il
reste **hors** `policies` (ADR-0046). Agrégats/stratégies de domaine **purs** — immuables, sans
dépendance framework (règle 1).

[ADR-0004]: ../../docs/adr/0004-moteur-de-phases-politiques.md
[ADR-0046]: ../../docs/adr/0046-config-policies-politiques-nommees-parametrees.md
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, cast

from domain.erreurs import PolitiqueInconnue, PolitiqueMalFormee


class FamillePolitique(str, Enum):
    """Les six familles de politiques d'ADR-0004 — le **catalogue fermé** des clés de
    `config.policies`. Une clé hors de cette énumération est une config mal formée (le grain de
    `validation` en est le cas emblématique : ce n'est pas une politique de moteur, ADR-0046)."""

    ROUTING = "routing"
    SCORING = "scoring"
    SEEDING = "seeding"
    BYES = "byes"
    TIEBREAK = "tiebreak"
    DEPTH = "depth"


# --- routing -----------------------------------------------------------------------------------


class DestinationPerdant(str, Enum):
    """Où va le perdant d'un match. Le socle E05US003 n'expose que l'**élimination** ; la
    **cascade** de placement (E05US010) et le **repêchage** WA (E05US016) ajouteront leurs
    destinations quand leur tableau existera — extension du catalogue, pas rupture."""

    ELIMINE = "elimine"


class Routing(Protocol):
    """Décide de la destination du perdant d'un match (ADR-0004). Méthode fondatrice : l'issue en
    élimination sèche. ADR-0004 vise `route(perdant, tour, contexte)` : cascade/repêchage
    (E05US010/E05US016) **ressigneront** cette méthode (rupture bon marché, un implémenteur)."""

    def destination_du_perdant(self) -> DestinationPerdant: ...


@dataclass(frozen=True)
class EliminationSeche:
    """Élimination directe : le perdant quitte le tournoi (ADR-0004, « élimination sèche »)."""

    def destination_du_perdant(self) -> DestinationPerdant:
        return DestinationPerdant.ELIMINE


# --- scoring -----------------------------------------------------------------------------------


class Scoring(Protocol):
    """Calcule le score d'un tireur à partir des points de ses volées (ADR-0004). Méthode
    fondatrice : le **cumul** de qualification. Le barème par sets (duels, E04US013) renverra un
    nombre de sets, pas un total : il **ressignera** cette méthode (rupture bon marché)."""

    def total(self, points_par_volee: Iterable[int]) -> int: ...


@dataclass(frozen=True)
class ScoreCumul:
    """Classement **au cumul** : le score est la somme des points des volées validées (§6.1).

    Stratégie sans état : le barème (nb volées x nb flèches) décrit la *structure* de l'épreuve et
    vit sur `Phase.bareme` — le cumul, lui, n'a besoin que des points à sommer.
    """

    def total(self, points_par_volee: Iterable[int]) -> int:
        return sum(points_par_volee)


# --- seeding -----------------------------------------------------------------------------------


class Seeding(Protocol):
    """Compose l'ordre des têtes de série dans l'arbre (ADR-0004). Méthode fondatrice : l'ordre
    serpent pour un effectif donné, arrondi à la puissance de 2 supérieure."""

    def ordre_des_tetes(self, effectif: int) -> tuple[int, ...]: ...


def _puissance_de_deux_superieure(effectif: int) -> int:
    """La plus petite puissance de 2 `>= effectif` (`>= 2`) — la taille du tableau (CA E05US005)."""
    taille = 1
    while taille < effectif:
        taille *= 2
    return max(taille, 2)


@dataclass(frozen=True)
class SeedingSerpent:
    """Ensemencement **serpent** : la tête `r` affronte `2^k+1-r` (référentiel, CA E05US005).

    Construit récursivement l'ordre des slots du tableau : à chaque doublement, on intercale le
    complément (`taille+1-tête`) après chaque tête du demi-tableau — d'où les paires adjacentes
    `(1,8), (4,5), (2,7), (3,6)` pour un tableau de 8, chacune de somme `2^k+1`. Les têtes de rang
    supérieur à l'effectif réel sont des **places d'exempt** (byes, cf. `ByesAuxMieuxClasses`).

    ⚠️ E05US005/oracle 120 : cet ordre plat donne les **appariements** (et donc la structure
    d'arbre), **pas** la numérotation des matchs de `moteur-placement-lucky-loser.md` — l'ordre
    linéaire des matchs peut différer du doc à structure identique. Ne pas comparer des *numéros* de
    match sans table de correspondance.
    """

    def ordre_des_tetes(self, effectif: int) -> tuple[int, ...]:
        taille = _puissance_de_deux_superieure(effectif)
        ordre = [1]
        largeur = 1
        while largeur < taille:
            largeur *= 2
            ordre = [t for tete in ordre for t in (tete, largeur + 1 - tete)]
        return tuple(ordre)


# --- byes --------------------------------------------------------------------------------------


class Byes(Protocol):
    """Attribue les exempts quand l'effectif n'est pas une puissance de 2 (ADR-0004). Méthode
    fondatrice : l'ensemble des têtes de série qui bénéficient d'un bye."""

    def porteurs_de_bye(self, effectif: int) -> frozenset[int]: ...


@dataclass(frozen=True)
class ByesAuxMieuxClasses:
    """Byes **aux mieux classés**, calcul universel pour tout effectif (ADR-0004, CA E05US005).

    Sur un tableau de taille `2^k`, il y a `2^k - effectif` byes ; ils reviennent aux têtes de série
    les mieux classées (`1..nb_byes`), dont l'adversaire serait une place d'exempt (`> effectif`).
    """

    def porteurs_de_bye(self, effectif: int) -> frozenset[int]:
        taille = _puissance_de_deux_superieure(effectif)
        nb_byes = taille - effectif
        return frozenset(range(1, nb_byes + 1))


# --- tiebreak ----------------------------------------------------------------------------------


@dataclass(frozen=True)
class DecompteDepartage:
    """Ce sur quoi la FFTA départage à total égal : nombre de **10** puis de **9** (§8.1)."""

    nb_dix: int
    nb_neuf: int


class Tiebreak(Protocol):
    """Départage deux tireurs à égalité de score (ADR-0004). Méthode fondatrice : le comparateur
    (`< 0` si `a` devance `b`, `0` si ex æquo). Un barrage de tir (E06US003) sera une autre
    implémentation de cette même interface."""

    def departager(self, a: DecompteDepartage, b: DecompteDepartage) -> int: ...


@dataclass(frozen=True)
class TiebreakFftaDefaut:
    """Départage FFTA **par défaut** : plus de 10, puis plus de 9 ; sinon **ex æquo** (§8.1).

    Critères **séquentiels** (les 9 ne jouent qu'à 10 égaux) et **négatifs** — plus de 10 place en
    tête, donc renvoie une valeur `< 0`. `0` = égalité parfaite au sens FFTA : le défaut laisse
    l'ex æquo (partage de rang), le barrage restant une **option** (E06US003 ; même interface).
    Miroir de `classement._cle_departage`, isolé ici comme la politique `tiebreak` d'ADR-0004.
    """

    def departager(self, a: DecompteDepartage, b: DecompteDepartage) -> int:
        cle_a = (a.nb_dix, a.nb_neuf)
        cle_b = (b.nb_dix, b.nb_neuf)
        if cle_a > cle_b:
            return -1
        if cle_a < cle_b:
            return 1
        return 0


# --- depth -------------------------------------------------------------------------------------


class Depth(Protocol):
    """Décide jusqu'où classer (ADR-0004). Méthode fondatrice : les rangs à produire pour un
    effectif. Un « top N + regroupement » serait une autre implémentation."""

    def rangs_a_classer(self, effectif: int) -> tuple[int, ...]: ...


@dataclass(frozen=True)
class ProfondeurUnVersN:
    """Profondeur **1→N** (défaut ADR-0004) : on classe **tout le monde**, personne n'est retranché
    — c'est le placement intégral du tournoi 120 (`moteur-placement-lucky-loser.md`)."""

    def rangs_a_classer(self, effectif: int) -> tuple[int, ...]:
        return tuple(range(1, effectif + 1))


# --- assemblage --------------------------------------------------------------------------------


@dataclass(frozen=True)
class PolitiquesPhase:
    """Le jeu de politiques **résolu** d'une phase. Chaque famille est facultative : une phase de
    qualification ne porte que `scoring` ; un tableau d'élimination directe porte
    routing/seeding/byes/tiebreak/depth. Le moteur (E05US005+) lit celles dont il a besoin."""

    routing: Routing | None = None
    scoring: Scoring | None = None
    seeding: Seeding | None = None
    byes: Byes | None = None
    tiebreak: Tiebreak | None = None
    depth: Depth | None = None


# Une fabrique construit une politique à partir de ses paramètres (l'objet
# `config.policies[famille]` privé de sa clé `nom`). Renvoie `object` : les fabriques produisent des
# types hétérogènes (un par famille), la cohérence famille→type est garantie par l'enregistrement,
# pas par le typage statique.
Fabrique = Callable[[Mapping[str, object]], object]


class RegistrePolitiques:
    """Catalogue **nom → implémentation** par famille, peuplé par la composition root (règle 2).

    Le domaine définit les stratégies et leurs noms canoniques (`registre_par_defaut`) ; la
    composition root instancie le registre et pourrait y ajouter d'autres implémentations sans
    toucher au domaine — c'est le point d'injection d'ADR-0004 (« un format est de la config »).
    Registre **mutable** par construction (on l'enregistre au démarrage) mais utilisé en lecture
    seule ensuite ; ce n'est pas un agrégat de domaine, juste une table de résolution pure.
    """

    def __init__(self) -> None:
        self._fabriques: dict[FamillePolitique, dict[str, Fabrique]] = {
            famille: {} for famille in FamillePolitique
        }

    def enregistrer(self, famille: FamillePolitique, nom: str, fabrique: Fabrique) -> None:
        """Associe un `nom` d'implémentation à sa `fabrique` pour une `famille` donnée."""
        self._fabriques[famille][nom] = fabrique

    def resoudre(self, famille: FamillePolitique, nom: str, params: Mapping[str, object]) -> object:
        """Construit l'implémentation `nom` de la `famille` avec ses `params`.

        Lève `PolitiqueInconnue` si aucun nom de ce catalogue n'est enregistré — explicite plutôt
        qu'un `KeyError` que la relecture d'une phase confondrait avec « config illisible ».
        """
        fabrique = self._fabriques[famille].get(nom)
        if fabrique is None:
            raise PolitiqueInconnue(
                f"Aucune implémentation « {nom} » n'est enregistrée pour la politique "
                f"« {famille.value} »."
            )
        return fabrique(params)


def registre_par_defaut() -> RegistrePolitiques:
    """Le registre peuplé des implémentations **de ce socle** (une par famille, E05US003).

    Les fabriques ignorent leurs `params` quand la stratégie est sans état (le cumul somme, il n'a
    pas besoin du barème ; les stratégies d'arbre se règlent à l'effectif passé à l'appel). Elles
    les acceptent tout de même pour honorer la forme `{"nom": …, …params}` sans discrimination.
    """
    registre = RegistrePolitiques()
    registre.enregistrer(
        FamillePolitique.ROUTING, "elimination_seche", lambda _p: EliminationSeche()
    )
    registre.enregistrer(FamillePolitique.SCORING, "cumul", lambda _p: ScoreCumul())
    registre.enregistrer(FamillePolitique.SEEDING, "serpent", lambda _p: SeedingSerpent())
    registre.enregistrer(FamillePolitique.BYES, "mieux_classes", lambda _p: ByesAuxMieuxClasses())
    registre.enregistrer(FamillePolitique.TIEBREAK, "ffta_defaut", lambda _p: TiebreakFftaDefaut())
    registre.enregistrer(FamillePolitique.DEPTH, "un_vers_n", lambda _p: ProfondeurUnVersN())
    return registre


def assembler_politiques(
    config_policies: Mapping[str, object], registre: RegistrePolitiques
) -> PolitiquesPhase:
    """Résout la `config.policies` d'une phase en un jeu de politiques (`PolitiquesPhase`).

    `config_policies` = `{famille: {"nom": <implémentation>, …paramètres}}`. Chaque clé doit être
    une **famille du catalogue** ADR-0004 (`PolitiqueMalFormee` sinon — c'est le garde-fou de la
    décision « `validation` hors `policies` », ADR-0046), et chaque valeur un objet portant un
    `nom` (`PolitiqueMalFormee` sinon : on ne devine pas l'implémentation). La résolution du nom
    délègue au registre (`PolitiqueInconnue` s'il est absent du catalogue).
    """
    resolues: dict[FamillePolitique, object] = {}
    for cle, spec in config_policies.items():
        try:
            famille = FamillePolitique(cle)
        except ValueError as exc:
            raise PolitiqueMalFormee(
                f"« {cle} » n'est pas une politique du moteur "
                f"({', '.join(f.value for f in FamillePolitique)})."
            ) from exc
        if not isinstance(spec, Mapping) or "nom" not in spec:
            raise PolitiqueMalFormee(
                f"La politique « {famille.value} » doit être un objet portant un « nom » "
                "d'implémentation."
            )
        nom = spec["nom"]
        if not isinstance(nom, str):
            raise PolitiqueMalFormee(
                f"Le « nom » de la politique « {famille.value} » doit être une chaîne."
            )
        params = {clef: valeur for clef, valeur in spec.items() if clef != "nom"}
        resolues[famille] = registre.resoudre(famille, nom, params)
    # `cast` plutôt que `type: ignore` : le registre renvoie `object` (types hétérogènes par
    # famille), la cohérence famille→type est garantie par l'enregistrement (`registre_par_defaut`),
    # pas statiquement. Le `cast` **exprime** cette intention là où l'`ignore` la masquait.
    return PolitiquesPhase(
        routing=cast("Routing | None", resolues.get(FamillePolitique.ROUTING)),
        scoring=cast("Scoring | None", resolues.get(FamillePolitique.SCORING)),
        seeding=cast("Seeding | None", resolues.get(FamillePolitique.SEEDING)),
        byes=cast("Byes | None", resolues.get(FamillePolitique.BYES)),
        tiebreak=cast("Tiebreak | None", resolues.get(FamillePolitique.TIEBREAK)),
        depth=cast("Depth | None", resolues.get(FamillePolitique.DEPTH)),
    )
