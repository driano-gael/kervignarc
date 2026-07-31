"""Politiques injectables du moteur de phases (E05US003, [ADR-0004] / [ADR-0046]).

Un **format** de phase de tableau n'est pas du code mais un **assemblage de stratégies** (règle 2) :
comment on route le perdant, comment on score, comment on ensemence l'arbre, à qui vont les byes,
comment on départage, jusqu'où on classe. ADR-0004 en fait **six familles** de politiques, chacune
une interface du domaine (`Protocol`) avec au moins une implémentation :

| Famille    | Rôle                      | Implémentations livrées |
|------------|---------------------------|-------------------------|
| `routing`  | où va le perdant          | `EliminationSeche`, `PlacementEnCascade`, |
|            |                           | `RoutingRepechage` |
| `scoring`  | calcul du score           | `ScoreCumul`, `ScoreAvecHandicap` |
| `seeding`  | composition de l'arbre    | `SeedingSerpent` |
| `byes`     | exempts si effectif ≠ 2^k | `ByesAuxMieuxClasses` |
| `tiebreak` | départage des égalités    | `TiebreakFftaDefaut`, `TiebreakPoules` |
| `depth`    | jusqu'où classer          | `ProfondeurUnVersN`, `ProfondeurPodium`, |
|            |                           | `AucunClassement` |

**E05US015 peuple ce catalogue** ([ADR-0062]) : le **repêchage** et le **handicap**, que le cahier
des charges rangeait parmi les « types de tournoi » à livrer, ne sont pas des types de phase mais
des **politiques** — le premier décide où va un perdant, le second comment se calcule un score. Ni
l'un ni l'autre n'a de structure propre, donc leur donner une `TypePhase` aurait été une erreur de
maille : c'est l'apport de conception de l'US, pas un détail d'implémentation.

**Portée E05US003.** Ce module livre les **interfaces**, une implémentation **pure et testable**
par famille, et l'**assemblage** d'une `config.policies` en un jeu résolu (`PolitiquesPhase`) via un
`RegistrePolitiques` que la **composition root** peuple (CA « assemblage »). Le *tableau* qui
orchestre ces stratégies (dimensionnement 2^k, génération, progression, podium) est **E05US005**
(élimination directe) et **E05US010** (placement intégral, routing en cascade) : ils **consomment**
ces politiques déjà éprouvées. Les stratégies couplées à la structure d'arbre exposent donc ici leur
méthode **fondatrice** (celle dont la règle est écrite) ; les US consommatrices la **ressignent**
au fil de leurs besoins. **E05US010 a exercé cette clause** sur le `routing` :
`destination_du_perdant()` est devenue `route(contexte)` (ADR-0061), la rupture ayant coûté un
appelant de production et deux
doubles de test — exactement le pari annoncé ici. Le barème par sets fera de même sur le `scoring`.
Ce sont des **ruptures de contrat**, bon marché tant qu'il n'y a **qu'un implémenteur et aucun
consommateur** par famille. C'est le sur-gel prématuré que
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
[ADR-0062]: ../../docs/adr/0062-catalogue-de-types-de-phase.md
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, cast

from domain.erreurs import PolitiqueInconnue, PolitiqueMalFormee
from domain.plage import Plage


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


@dataclass(frozen=True)
class ContexteRoutage:
    """Ce que le routing sait du match dont le perdant est à router (E05US010).

    C'est le `contexte` d'ADR-0004. Il ne porte **pas** le perdant lui-même : le routage est décidé
    à la **construction** de l'arbre, quand les camps sont câblés mais qu'aucun participant n'est
    encore connu (`PerdantDe(m)` est une arête, pas une personne). Router à la construction plutôt
    qu'à chaque match joué est ce qui garde le `Tableau` **reconstructible** (ADR-0049) : la
    structure ne dépend que des politiques, jamais de l'ordre dans lequel les résultats sont
    tombés. Voir [ADR-0061](../../docs/adr/0061-routing-generique-et-placement-en-cascade.md).
    """

    tour: int
    """Le tour perdu, compté **depuis la racine** (1 = premier tour du tableau principal).

    ⚠️ Ce n'est **pas** un compteur local au sous-tableau : la génération propage `tour + 1` dans les
    deux branches, donc le premier tour du sous-tableau des places 5-8 d'un tableau de 8 vaut `2`.
    La distinction comptera pour le repêchage WA (E05US015), dont la règle s'énonce « les perdants
    du 1ᵉʳ tour sont repêchés » : sur un compteur absolu, cela se lit `tour == 1`."""

    plage: Plage
    """La plage de rangs encore atteignable **avant** ce match."""


@dataclass(frozen=True)
class HorsTableau:
    """Le perdant quitte le tableau : aucun match aval ne l'attend (élimination sèche)."""


@dataclass(frozen=True)
class VersPlage:
    """Le perdant descend dans le sous-tableau de placement de cette `plage` (*Règle R*)."""

    plage: Plage


@dataclass(frozen=True)
class VersRepechage:
    """Le perdant **sort de ce tableau sans être classé** : une phase de repêchage le reprendra.

    C'est la variante annoncée par E05US010, livrée par E05US015. Elle se distingue de
    `HorsTableau` par ce qu'elle promet : `HorsTableau` **consomme** un rang (le perdant a fini sa
    compétition), `VersRepechage` n'en consomme **aucun** — le repêché peut encore remonter
    disputer le titre, donc lui attribuer un rang ici serait faux.

    ⚠️ **Cette destination ne construit rien.** La réintégration n'est pas un lien d'arbre mais un
    **prélèvement** de la phase avale : `SourcePhase.par_issue_de_tour(ordre, tour, PERDANTS)`,
    livrée par E05US010. Le routing dit seulement « ces perdants-là ne descendent pas dans la
    cascade » ; qui les récupère est une affaire de composition. C'est exactement la distinction de
    `moteur-placement-lucky-loser.md` (Q1) entre **placement** (le perdant descend vers un tableau
    de classement, sans retour) et **repêchage** (il ressort du tableau et peut revenir).
    """


type Destination = HorsTableau | VersPlage | VersRepechage
"""Où va le perdant : il a fini (`HorsTableau`), il descend se classer (`VersPlage`), ou il sort
pour être repêché (`VersRepechage`, E05US015)."""


class Routing(Protocol):
    """Décide où va le perdant d'un match (ADR-0004, `route(perdant, tour, contexte)`).

    **Signature ressignée par E05US010**, comme `politiques.py` l'annonçait : la méthode fondatrice
    `destination_du_perdant()` ne prenait aucun argument et ne pouvait donc rendre qu'une réponse
    constante — inapte à exprimer « la moitié basse de *ta* plage ». Rupture bon marché tenue
    (un implémenteur, un appelant en production).
    """

    def route(self, contexte: ContexteRoutage) -> Destination: ...


@dataclass(frozen=True)
class EliminationSeche:
    """Le perdant quitte le tournoi (ADR-0004, « élimination sèche »).

    ⚠️ **Ce n'est pas le format livré par E05US005**, malgré son nom : un tableau à élimination
    directe avec **petite finale** fait rejouer les perdants des demi-finales, donc ne les élimine
    pas. Ce format-là est un `PlacementEnCascade` **tronqué au rang 4** (`ProfondeurPodium`) — c'est
    ce que câble la composition root. `EliminationSeche` décrit le tableau **vraiment** sec, sans
    aucun match de classement (Q6 : « formats simples : élimination directe, top N »).
    """

    def route(self, contexte: ContexteRoutage) -> Destination:
        return HorsTableau()


@dataclass(frozen=True)
class PlacementEnCascade:
    """*Règle R* : le perdant descend dans la **moitié basse** de sa plage (E05US010).

    Le mécanisme de la cascade tient dans cette ligne ; tout le reste est la structure d'arbre qui
    en découle. Q1 du document de formalisation en fait le **défaut** : « Lucky Loser » au sens du
    classeur est un tableau de **consolation**, pas un repêchage — aucun battu ne revient disputer
    le titre.
    """

    def route(self, contexte: ContexteRoutage) -> Destination:
        return VersPlage(contexte.plage.moitie_basse())


@dataclass(frozen=True)
class RoutingRepechage:
    """*Repêchage World Archery* : les perdants de certains tours **ressortent** du tableau au lieu
    d'y être classés (E05US015, [ADR-0062]).

    `tours_repeches` liste les tours dont le perdant est repêchable, comptés **depuis la racine**
    comme le veut `ContexteRoutage.tour` — la règle WA « les perdants du 1ᵉʳ tour sont repêchés »
    s'écrit donc `frozenset({1})`. Tout autre tour est délégué à `sinon`, ce qui rend le repêchage
    **composable** avec les deux routings existants : repêchage + cascade (le format du club, où le
    « Lucky-Looser » remonte en Grande Finale et où les autres battus descendent se classer), ou
    repêchage + élimination sèche.

    **Décoration plutôt qu'implémentation autonome**, et c'est le point de conception : un
    repêchage ne remplace pas une politique de placement, il en **excepte** quelques tours. Écrire
    `RoutingRepechage` sans `sinon` aurait forcé à choisir entre « repêcher » et « classer », alors
    que le classeur réel fait les deux dans le même tableau.
    """

    tours_repeches: frozenset[int]
    sinon: Routing

    def route(self, contexte: ContexteRoutage) -> Destination:
        if contexte.tour in self.tours_repeches:
            return VersRepechage()
        return self.sinon.route(contexte)


# --- scoring -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class ContexteScore:
    """Ce que le `scoring` sait du **tireur** dont il calcule le score (E05US015).

    Pendant de `ContexteRoutage` pour la famille `scoring`. Il n'existe que parce que le
    **handicap** est une donnée *du tireur*, pas de la phase : `total(points_par_volee)` ne pouvait
    rendre qu'une fonction des seules volées, donc ne pouvait pas exprimer « + son handicap ».
    C'est la **ressignature** que `Scoring` annonçait comme prévue — et elle n'a coûté aucun
    appelant de production (aucun n'existait encore), le pari le moins cher de tout le module.
    """

    handicap: int = 0
    """Points ajoutés au score réalisé — 0 quand la phase ne joue pas au handicap."""


class Scoring(Protocol):
    """Calcule le score d'un tireur à partir des points de ses volées **et de son contexte**
    (ADR-0004, ressignée par E05US015 / [ADR-0062]).

    Méthode fondatrice : le **cumul** de qualification. Le barème par sets (duels, E04US013)
    renverra un nombre de sets, pas un total : il ressignera cette méthode à son tour (rupture bon
    marché tant qu'il n'y a qu'un implémenteur par famille).
    """

    def total(self, points_par_volee: Iterable[int], contexte: ContexteScore) -> int: ...


@dataclass(frozen=True)
class ScoreCumul:
    """Classement **au cumul** : le score est la somme des points des volées validées (§6.1).

    Stratégie sans état : le barème (nb volées x nb flèches) décrit la *structure* de l'épreuve et
    vit sur `Phase.bareme` — le cumul, lui, n'a besoin que des points à sommer. Il **ignore** le
    contexte : un tir scratch ne connaît pas le handicap de qui le tire.
    """

    def total(self, points_par_volee: Iterable[int], contexte: ContexteScore) -> int:
        return sum(points_par_volee)


@dataclass(frozen=True)
class ScoreAvecHandicap:
    """Classement **au handicap** : score réalisé **+** handicap du tireur (E05US015).

    Règle donnée par le commanditaire le 31/07/2026 : « le score final est *score réalisé +
    handicap* », de sorte qu'un débutant qui dépasse son niveau habituel batte un champion en
    performance moyenne. Le format récompense donc la **progression**, pas la performance absolue.

    ⚠️ **La politique ne calcule pas le handicap, elle l'applique.** Sa valeur vient de l'archer
    (`Archer.handicap`, où une surcharge prime un handicap officiel) et transite par
    `ContexteScore`. Ce partage est délibéré : la fiabilité du handicap est le point faible reconnu
    du format (« les nouveaux archers peuvent être avantagés si leur handicap est mal évalué »), et
    c'est un problème de **donnée entretenue par le club**, pas d'algorithme. Aucune table
    officielle n'est codée en dur : le projet n'en a aucune, et en inventer une produirait des
    classements plausibles mais faux.
    """

    def total(self, points_par_volee: Iterable[int], contexte: ContexteScore) -> int:
        return sum(points_par_volee) + contexte.handicap


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
    """Ce sur quoi on départage deux tireurs à égalité — **union** des critères des formats livrés.

    §8.1 (qualification) n'en emploie que deux, `nb_dix` puis `nb_neuf` ; §10.1 (poules) en emploie
    **cinq**, en commençant par trois critères propres au jeu en poule. Les deux ordres sont
    différents et le référentiel avertit de ne pas les confondre : c'est la **politique `tiebreak`**
    qui porte l'ordre, ce décompte ne porte que les **valeurs**.

    ⚠️ **Les trois champs d'E05US015 sont ajoutés avec un défaut à 0, et c'est ce qui rend
    l'élargissement non cassant.** `DecompteDepartage(nb_dix=…, nb_neuf=…)` reste valide tel quel,
    donc `TiebreakFftaDefaut` et tous ses appelants sont intacts — le CA désignait cet
    élargissement comme la rupture de contrat la plus risquée de l'US, elle se réduit à un ajout de
    champs facultatifs. Le corollaire à connaître : un décompte de **qualification** comparé par
    `TiebreakPoules` donnerait trois premiers critères tous nuls, donc retomberait exactement sur
    §8.1 — dégradation silencieuse mais **juste**, pas une erreur à lever.
    """

    nb_dix: int
    nb_neuf: int
    points_match: int = 0
    """Points de match cumulés en poule (victoire / nul / défaite, barème paramétrable)."""

    diff_sets: int = 0
    """Sets gagnés moins sets perdus sur l'ensemble des rencontres de poule."""

    diff_score: int = 0
    """Points de score marqués moins encaissés sur l'ensemble des rencontres de poule."""


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


@dataclass(frozen=True)
class TiebreakPoules:
    """Départage **de poule** à cinq critères séquentiels (E05US015, référentiel §10.1).

    Ordre donné par le commanditaire, verbatim : « points de match, différence de sets, différence
    de score, nombre de 10 / 9, barrage si nécessaire ». Il **précède** §8.1 de trois critères et ne
    s'y substitue pas — le référentiel avertit explicitement de ne pas confondre les deux ordres.

    Le « barrage si nécessaire » n'est **pas** un sixième critère de comparaison : c'est ce qui
    arrive **après** que ce comparateur a rendu `0`. Un comparateur pur ne peut pas faire tirer des
    flèches ; il constate l'ex æquo, et c'est au moteur de poule (`poule.py`) de décider s'il
    organise un barrage ou laisse le rang partagé. Même partage des rôles que
    `TiebreakFftaDefaut`, dont le `0` laisse déjà l'ex æquo.
    """

    def departager(self, a: DecompteDepartage, b: DecompteDepartage) -> int:
        cle_a = (a.points_match, a.diff_sets, a.diff_score, a.nb_dix, a.nb_neuf)
        cle_b = (b.points_match, b.diff_sets, b.diff_score, b.nb_dix, b.nb_neuf)
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


@dataclass(frozen=True)
class ProfondeurPodium:
    """Profondeur **top N** (Q2) : on ne départage que les `jusqu_au` premiers, 4 par défaut.

    C'est la profondeur du tableau à élimination directe livré par E05US005 : finale (rangs 1-2) et
    petite finale (rangs 3-4), les battus des tours antérieurs restant **non classés entre eux**.
    Combinée à `PlacementEnCascade`, elle reproduit exactement cette structure — un tableau de 8
    rend ses 8 matchs. C'est le sens de Q2 : « l'organisateur peut choisir de s'arrêter à un top ».
    """

    jusqu_au: int = 4

    def rangs_a_classer(self, effectif: int) -> tuple[int, ...]:
        return tuple(range(1, min(self.jusqu_au, effectif) + 1))


@dataclass(frozen=True)
class AucunClassement:
    """Profondeur de l'**échauffement** : aucun rang n'est produit (E05US015, §10.1).

    Le cas dégénéré de `Depth` — et il n'est pas artificiel, c'est littéralement la demande du
    commanditaire (« sans point sans classement »). Rendre `()` plutôt que de laisser `depth` à
    `None` **dit** quelque chose : la phase a une politique de profondeur, et cette politique est
    « on ne classe rien ». Un `None` se lirait « la profondeur n'a pas encore été choisie ».

    Son pendant côté séquence est `PhaseSansClassementPrelevee` : ce qui ne produit aucun rang ne
    peut pas être prélevé par rangs.
    """

    def rangs_a_classer(self, effectif: int) -> tuple[int, ...]:
        return ()


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
    registre.enregistrer(
        FamillePolitique.ROUTING, "placement_cascade", lambda _p: PlacementEnCascade()
    )
    # Fabrique **fermée sur le registre en cours de construction** : c'est la première politique
    # **composite** du catalogue (elle en enveloppe une autre), donc la seule qui ait besoin de
    # résoudre un nom à son tour. La clôture est ce qui évite d'élargir la signature `Fabrique` de
    # toutes les autres pour le besoin d'une seule.
    registre.enregistrer(
        FamillePolitique.ROUTING,
        "repechage",
        lambda params: _fabriquer_repechage(params, registre),
    )
    registre.enregistrer(FamillePolitique.SCORING, "cumul", lambda _p: ScoreCumul())
    registre.enregistrer(FamillePolitique.SCORING, "handicap", lambda _p: ScoreAvecHandicap())
    registre.enregistrer(FamillePolitique.SEEDING, "serpent", lambda _p: SeedingSerpent())
    registre.enregistrer(FamillePolitique.BYES, "mieux_classes", lambda _p: ByesAuxMieuxClasses())
    registre.enregistrer(FamillePolitique.TIEBREAK, "ffta_defaut", lambda _p: TiebreakFftaDefaut())
    registre.enregistrer(FamillePolitique.TIEBREAK, "poules", lambda _p: TiebreakPoules())
    registre.enregistrer(FamillePolitique.DEPTH, "un_vers_n", lambda _p: ProfondeurUnVersN())
    registre.enregistrer(FamillePolitique.DEPTH, "podium", _fabriquer_profondeur_podium)
    registre.enregistrer(FamillePolitique.DEPTH, "aucun", lambda _p: AucunClassement())
    return registre


def _fabriquer_repechage(
    params: Mapping[str, object], registre: RegistrePolitiques
) -> RoutingRepechage:
    """`{"nom": "repechage", "tours": [1], "sinon": {"nom": "placement_cascade"}}` → la politique.

    `tours` est **obligatoire et non vide** : un repêchage qui ne repêche aucun tour est un
    `placement_cascade` déguisé, et l'accepter laisserait croire à l'organisateur que son format
    repêche alors qu'il n'en fait rien. `sinon` est facultatif et vaut `placement_cascade` par
    défaut — le cas du format club, où les battus non repêchés descendent malgré tout se classer.

    La récursion sur `sinon` passe par le registre, donc un `sinon` lui-même « repechage » est
    résolu sans traitement particulier. Ce n'est pas un cas d'usage connu ; c'est simplement ce que
    la composition rend gratuit.
    """
    tours_bruts = params.get("tours")
    if not isinstance(tours_bruts, list) or not tours_bruts:
        raise PolitiqueMalFormee(
            "Le repêchage attend la liste non vide des tours dont le perdant est repêché "
            f"(reçu {tours_bruts!r})."
        )
    tours: set[int] = set()
    for tour in tours_bruts:
        if not isinstance(tour, int) or isinstance(tour, bool) or tour < 1:
            raise PolitiqueMalFormee(
                f"Un tour repêché est un entier ≥ 1, compté depuis la racine (reçu {tour!r})."
            )
        tours.add(tour)
    spec_sinon = params.get("sinon", {"nom": "placement_cascade"})
    if not isinstance(spec_sinon, Mapping) or not isinstance(spec_sinon.get("nom"), str):
        raise PolitiqueMalFormee(
            "Le « sinon » d'un repêchage est un objet portant un « nom » de routing "
            f"(reçu {spec_sinon!r})."
        )
    nom_sinon = spec_sinon["nom"]
    assert isinstance(nom_sinon, str)
    params_sinon = {clef: valeur for clef, valeur in spec_sinon.items() if clef != "nom"}
    sinon = cast("Routing", registre.resoudre(FamillePolitique.ROUTING, nom_sinon, params_sinon))
    return RoutingRepechage(tours_repeches=frozenset(tours), sinon=sinon)


def _fabriquer_profondeur_podium(params: Mapping[str, object]) -> ProfondeurPodium:
    """`{"nom": "podium", "jusqu_au": 8}` → la profondeur correspondante (4 par défaut).

    Première fabrique **paramétrée** du registre : jusqu'ici toutes les stratégies étaient sans
    état. Un `jusqu_au` non entier ou non positif est une config mal formée — on refuse plutôt que
    de retomber sur le défaut en silence, sans quoi une faute de frappe classerait un top 4 là où
    l'organisateur en demandait 8.
    """
    brut = params.get("jusqu_au", 4)
    if not isinstance(brut, int) or isinstance(brut, bool) or brut < 1:
        raise PolitiqueMalFormee(
            f"La profondeur « podium » attend un rang entier positif (reçu {brut!r})."
        )
    return ProfondeurPodium(jusqu_au=brut)


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
