"""Politiques injectables du moteur — sept familles (ADR-0004 § « Catalogue livré », ADR-0046).

Un format de phase est un assemblage de stratégies, pas du code (règle 2).

⚠️ Une famille **sans appelant de production est inerte, et rien ne le signale** — c'est le cas de
`scoring`, donc de `ScoreAvecHandicap` (`DETTE-028`). Vérifier qu'une politique est résolue par le
registre avant de la croire active.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Protocol, cast

from domain.archer import ArcherId
from domain.erreurs import PolitiqueInconnue, PolitiqueMalFormee, ProfondeurInvalide
from domain.plage import Plage


class FamillePolitique(str, Enum):
    """Les familles de politiques du moteur — le **catalogue fermé** des clés de `config.policies`.

    Six à ADR-0004, **sept depuis E06US004** (`aggregation`, ADR-0067). Une clé hors de cette
    énumération est une config mal formée (le grain de `validation` en est le cas emblématique : ce
    n'est pas une politique de moteur, ADR-0046).
    """

    ROUTING = "routing"
    SCORING = "scoring"
    SEEDING = "seeding"
    BYES = "byes"
    TIEBREAK = "tiebreak"
    DEPTH = "depth"
    AGGREGATION = "aggregation"
    """Comment fusionner les rangs des phases en un palmarès (E06US004, [ADR-0067]).

    Septième famille — le catalogue d'ADR-0004 en comptait six. Elle ne s'ajoute pas par symétrie
    mais parce qu'une **règle métier sans arbitre** est apparue : deux archers sortis au **même
    tour** n'ont été départagés par aucun match, et il faut bien décider si l'on invente un ordre
    (usage World Archery : le rang de qualification) ou si l'on assume l'*ex æquo*. Les deux
    réponses sont légitimes selon le tournoi — c'est la définition d'une politique (règle 2).
    """


FAMILLES_HORS_CONFIG_PHASE: frozenset[FamillePolitique] = frozenset({FamillePolitique.AGGREGATION})
"""Les familles qui **ne se règlent pas** dans la `config.policies` d'une phase.

`aggregation` fusionne les rangs de **toutes** les phases en un palmarès : elle vaut pour le
tournoi, pas pour l'une d'elles, et s'injecte à la composition root (E06US004).
⚠️ Sans cette liste, ajouter la famille élargissait ce que le serveur accepte : `FamillePolitique`
est le **catalogue fermé** des clés admises, donc `config.policies.aggregation` serait devenue
acceptée, résolue… et silencieusement **ignorée**. Une clé n'est acceptée que si on la consomme.
"""

_FAMILLES_DE_PHASE: tuple[FamillePolitique, ...] = tuple(
    famille for famille in FamillePolitique if famille not in FAMILLES_HORS_CONFIG_PHASE
)
"""Les familles réellement réglables par phase — celles que cite le message d'erreur."""


# --- routing -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class ContexteRoutage:
    """Ce que le routing sait du match dont le perdant est à router (E05US010).

    C'est le `contexte` d'ADR-0004. Il ne porte **pas** le perdant lui-même : le routage est décidé
    à la **construction** de l'arbre, quand les camps sont câblés mais qu'aucun participant n'est
    connu. C'est ce qui garde le `Tableau` **reconstructible** (ADR-0049, ADR-0061) — la structure
    ne dépend que des politiques, jamais de l'ordre dans lequel les résultats sont tombés.
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

    Se distingue de `HorsTableau` par ce qu'elle promet : celui-ci **consomme** un rang, celle-ci
    n'en consomme **aucun** — le repêché peut encore remonter disputer le titre.
    ⚠️ **Cette destination ne construit rien** : la réintégration est un **prélèvement** de la phase
    avale (`SourcePhase.par_issue_de_tour(…, PERDANTS)`). Le routing dit seulement « ces perdants-là
    ne descendent pas dans la cascade » ; qui les récupère est affaire de composition.
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

    def route(self, contexte: ContexteRoutage) -> Destination:
        """Où va le perdant du match décrit par `contexte`.

        ⚠️ **Précondition : jamais appelée sur une plage indivisible** (`largeur < 4`). La *Règle T*
        tranche avant — `construire_tableau` sort dès `plage.est_terminale`, qui ne couvre que la
        largeur **2** ; cela suffit pour un arbre construit (`Plage(1, 2^k)`, divisions par moitiés)
        mais pas pour un appelant qui fabrique ses propres plages, où `PlacementEnCascade` lèverait
        `PlageInvalide`. Le contrat était implicite et son 2ᵉ appelant l'a enfreint (ADR-0065 §2).
        """
        ...


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
    d'y être classés (E05US015, ADR-0062).
    `tours_repeches` liste les tours repêchables, comptés **depuis la racine** — la règle WA « les
    perdants du 1ᵉʳ tour sont repêchés » s'écrit `frozenset({1})`. Tout autre tour est délégué à
    `sinon`. **Décoration plutôt qu'implémentation autonome** : un repêchage ne remplace pas une
    politique de placement, il en **excepte** quelques tours — sans `sinon`, il aurait fallu choisir
    entre « repêcher » et « classer », alors que le classeur réel fait les deux.
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

    Règle du commanditaire (31/07/2026) : le format récompense la **progression**, pas la
    performance absolue.
    ⚠️ **La politique ne calcule pas le handicap, elle l'applique** — sa valeur vient de l'archer et
    transite par `ContexteScore`. La fiabilité du handicap est un problème de **donnée entretenue
    par le club**, pas d'algorithme : coder une table officielle produirait des classements faux.
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

    À chaque doublement, on intercale le complément (`taille+1-tête`) après chaque tête du
    demi-tableau — d'où `(1,8), (4,5), (2,7), (3,6)` pour un tableau de 8. Les têtes au-delà de
    l'effectif réel sont des **places d'exempt**.
    ⚠️ Cet ordre plat donne les **appariements**, **pas** la numérotation des matchs de
    `moteur-placement-lucky-loser.md` : ne pas comparer des *numéros* sans table de correspondance.
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

    §8.1 n'en emploie que deux (`nb_dix`, `nb_neuf`), §10.1 en emploie **cinq** dans un autre ordre.
    C'est la **politique `tiebreak`** qui porte l'ordre ; ce décompte ne porte que les valeurs.
    ⚠️ Les trois champs d'E05US015 ont un défaut à 0, ce qui rend l'élargissement non cassant. Un
    décompte de **qualification** comparé par `TiebreakPoules` retombe donc sur §8.1 — dégradation
    silencieuse mais **juste**, pas une erreur à lever.
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
    """Départage deux tireurs à égalité de score (ADR-0004) — le comparateur (`< 0` si `a` devance).

    **Seconde méthode, ajoutée par E06US003** (ADR-0066) : `barrage_requis`. Elle ne départage rien
    — elle dit si l'ex æquo doit être tranché **au tir** plutôt que partagé. Le comparateur
    constate, le moteur fait tirer.
    Pourquoi ici plutôt que dans une 7ᵉ famille : le seuil et le comparateur doivent rester
    **cohérents entre eux**, et deux familles séparées permettraient de les désaccorder.
    """

    def departager(self, a: DecompteDepartage, b: DecompteDepartage) -> int: ...

    def barrage_requis(self, rang: int) -> bool: ...


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

    def barrage_requis(self, rang: int) -> bool:
        """Jamais : le **défaut** d'E06US001 est l'ex æquo, à tous les rangs (§8.1)."""
        return False


@dataclass(frozen=True)
class TiebreakPoules:
    """Départage **de poule** à cinq critères séquentiels (E05US015, référentiel §10.1).

    Ordre donné par le commanditaire : « points de match, différence de sets, différence de score,
    nombre de 10 / 9, barrage si nécessaire ». Il **précède** §8.1 de trois critères sans s'y
    substituer. Le « barrage si nécessaire » n'est **pas** un sixième critère : c'est ce qui arrive
    **après** que ce comparateur a rendu `0` — au moteur de poule d'en décider.
    """

    def departager(self, a: DecompteDepartage, b: DecompteDepartage) -> int:
        cle_a = (a.points_match, a.diff_sets, a.diff_score, a.nb_dix, a.nb_neuf)
        cle_b = (b.points_match, b.diff_sets, b.diff_score, b.nb_dix, b.nb_neuf)
        if cle_a > cle_b:
            return -1
        if cle_a < cle_b:
            return 1
        return 0

    def barrage_requis(self, rang: int) -> bool:
        """Non — le « barrage si nécessaire » de §10.1 n'est pas *systématique*.

        Le référentiel le cite en fin de cascade sans dire à quelles places il s'applique ; c'est
        `TiebreakAvecBarrage` qui répond à cette question, en enveloppant celui-ci. Renvoyer `True`
        ici ferait retirer pour départager le 27ᵉ d'une poule de qualification.
        """
        return False


@dataclass(frozen=True)
class TiebreakAvecBarrage:
    """Départage **composite** : celui de `sous_jacent`, plus un **barrage** jusqu'au rang réglé.

    Seuil configurable plutôt que règle fixe (cadrage du 02/08/2026) : ce qui fait qu'une place est
    « à enjeu » dépend du tournoi.
    ⚠️ **Le seuil désigne le rang du GROUPE, pas chacune de ses places** : deux ex æquo au rang 8
    avec `jusqu_au=8` se départagent, donc le barrage tranche **aussi** la 9ᵉ place. C'est voulu —
    « départager la dernière place qualificative » est une égalité qui **chevauche** le seuil.
    """

    sous_jacent: Tiebreak
    jusqu_au: int

    def departager(self, a: DecompteDepartage, b: DecompteDepartage) -> int:
        return self.sous_jacent.departager(a, b)

    def barrage_requis(self, rang: int) -> bool:
        return rang <= self.jusqu_au


# --- depth -------------------------------------------------------------------------------------

RANGS_DU_PODIUM = 4
"""Les rangs qu'un tableau à petite finale décerne : 1-2 (finale) et 3-4 (petite finale).

Défaut de `ProfondeurPodium` **et** preset des phases en tableau (`phase.profondeur_par_defaut`) —
un seul 4 pour une seule raison, plutôt qu'un littéral recopié dans chaque module."""


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

    jusqu_au: int = RANGS_DU_PODIUM

    def rangs_a_classer(self, effectif: int) -> tuple[int, ...]:
        return tuple(range(1, min(self.jusqu_au, effectif) + 1))


@dataclass(frozen=True)
class AucunClassement:
    """Profondeur de l'**échauffement** : aucun rang n'est produit (E05US015, §10.1).

    Le cas dégénéré de `Depth`, et il n'est pas artificiel : « sans point sans classement ». Rendre
    `()` plutôt que de laisser `depth` à `None` **dit** quelque chose — la phase a une politique de
    profondeur, et cette politique est « on ne classe rien » ; un `None` se lirait « pas encore
    choisie ». Son pendant côté séquence est `PhaseSansClassementPrelevee`.
    """

    def rangs_a_classer(self, effectif: int) -> tuple[int, ...]:
        return ()


class NomProfondeur(str, Enum):
    """Les profondeurs qu'un **organisateur** choisit — un sous-ensemble du catalogue `depth`.

    `aucun` n'y figure pas : ce n'est pas un choix mais le contenu même du type `échauffement`.
    ⚠️ **`top_n` et non `podium`** (E06US006) : `docs/glossaire.md` réserve **Podium** aux rangs 1-4
    décernés par un match, or ce nom devient ici un **contrat REST et une valeur persistée**. Le
    renommage est gratuit aujourd'hui (aucune base ne porte l'ancien nom) et coûteux dès la
    première base de production. La **classe** garde son nom : elle est interne.
    """

    UN_VERS_N = "un_vers_n"
    TOP_N = "top_n"


@dataclass(frozen=True)
class ProfondeurClassement:
    """Le **choix** de profondeur d'une phase — un descripteur sérialisable, pas la stratégie.

    Distinction d'ADR-0066 : l'agrégat porte de la **donnée**, et c'est le **registre** qui en fait
    une `Depth`. Mettre la stratégie sur la phase ferait entrer un objet non sérialisable dans un
    agrégat et court-circuiterait le point d'injection. `en_config()` rend la forme ADR-0046,
    directement consommable par `assembler_politiques`.
    """

    nom: NomProfondeur
    jusqu_au: int | None = None
    """Le dernier rang départagé — **et seulement** pour un top N.

    Porté par `top_n` uniquement : un classement intégral ne s'arrête à aucun rang, et lui en
    donner un décrirait deux profondeurs à la fois. Le refus est plus utile que la tolérance —
    silencieusement ignoré, le seuil laisserait croire à un top N qui n'aurait jamais lieu.
    """

    def __post_init__(self) -> None:
        if self.nom is NomProfondeur.TOP_N:
            if self.jusqu_au is None or self.jusqu_au < 1:
                raise ProfondeurInvalide(
                    "Un classement en top N s'arrête à un rang entier positif "
                    f"(reçu {self.jusqu_au!r}) ; « classer tout le monde » se dit en choisissant "
                    "le classement intégral."
                )
        elif self.jusqu_au is not None:
            raise ProfondeurInvalide(
                "Un classement intégral va jusqu'au dernier archer : il ne s'arrête à aucun rang "
                f"(reçu {self.jusqu_au!r})."
            )

    @staticmethod
    def integrale() -> ProfondeurClassement:
        """Le mode **1→N** : tous les rangs se jouent, aucun archer n'est laissé en fourchette."""
        return ProfondeurClassement(nom=NomProfondeur.UN_VERS_N)

    @staticmethod
    def top(jusqu_au: int) -> ProfondeurClassement:
        """Le mode **top N** : seuls les `jusqu_au` premiers sont départagés, le reste groupé."""
        return ProfondeurClassement(nom=NomProfondeur.TOP_N, jusqu_au=jusqu_au)

    def en_config(self) -> dict[str, object]:
        """La forme `config.policies.depth` (ADR-0046) — ce qui se persiste et ce qui se résout."""
        config: dict[str, object] = {"nom": self.nom.value}
        if self.jusqu_au is not None:
            config["jusqu_au"] = self.jusqu_au
        return config


# --- aggregation -------------------------------------------------------------------------------


class Aggregation(Protocol):
    """Décide comment ordonner des archers qu'**aucun match n'a départagés** (ADR-0067).

    Les quatre battus des quarts sortent tous sur la plage `[5..8]` (*Règle R*) : leur donner
    l'ordre de la qualification (défaut) ou assumer l'*ex æquo* sont deux réponses défendables.
    ⚠️ **À ne pas confondre avec `tiebreak`**, qui départage sur un **score** commun ; ici il n'y en
    a aucun. ⚠️ **Seule famille typée sur l'archer** (`ArcherId`) : elle départage sur le rang de
    qualification, qu'une équipe n'a pas — le service écarte les participants « équipe » avant.
    """

    def departager(
        self,
        groupe: Sequence[ArcherId],
        rang_qualification: Mapping[ArcherId, int | None],
    ) -> tuple[tuple[ArcherId, ...], ...]:
        """Ordonne `groupe` en paquets, du meilleur au moins bon. Tous les archers en sortent."""
        ...


@dataclass(frozen=True)
class AggregationParQualification:
    """Défaut du projet : les sortis au même tour se rangent sur leur **rang de qualification**.

    L'usage World Archery, qui donne un classement **1→N sans ex æquo** — ce qu'un palmarès affiché
    au mur demande. Deux archers **ex æquo en qualification** ressortent ex æquo ici : la politique
    départage *sur* la qualification, elle ne la contourne pas. Un archer sans rang (disqualifié)
    passe en dernier, et deux archers sans rang restent ensemble.
    """

    def departager(
        self,
        groupe: Sequence[ArcherId],
        rang_qualification: Mapping[ArcherId, int | None],
    ) -> tuple[tuple[ArcherId, ...], ...]:
        ordonne = sorted(
            groupe,
            # Clé totale : les sans-rang en dernier, puis le rang, puis l'identifiant — ce dernier
            # critère **n'ordonne pas** (les ex æquo sont regroupés juste après), il rend seulement
            # deux lectures successives identiques.
            key=lambda archer: (
                rang_qualification.get(archer) is None,
                rang_qualification.get(archer) or 0,
                archer,
            ),
        )
        paquets: list[list[ArcherId]] = []
        for archer in ordonne:
            rang = rang_qualification.get(archer)
            if paquets and rang_qualification.get(paquets[-1][0]) == rang:
                paquets[-1].append(archer)
            else:
                paquets.append([archer])
        return tuple(tuple(paquet) for paquet in paquets)


@dataclass(frozen=True)
class AggregationExAequo:
    """On ne classe **que** ce que la compétition a décidé : les sortis au même tour restent
    *ex æquo*.

    Le cas dégénéré d'`Aggregation` — un seul paquet — et il n'est pas artificiel : dans un tableau
    tronqué au podium, *aucun match n'a été joué* pour départager les quatre battus des quarts. Le
    palmarès affiche alors « 5ᵉ-8ᵉ » pour les quatre, ce qui est le résultat exact du tournoi.
    """

    def departager(
        self,
        groupe: Sequence[ArcherId],
        rang_qualification: Mapping[ArcherId, int | None],
    ) -> tuple[tuple[ArcherId, ...], ...]:
        return (tuple(groupe),)


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

    # Pas de champ `aggregation` : elle ne se regle **pas par phase** (cf.
    # `FAMILLES_HORS_CONFIG_PHASE`). L'exposer ici aurait fait accepter une cle sans
    # consommateur - un reglage sans effet, ce qui est pire que pas de reglage du tout.


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
    # Seconde politique **composite** du catalogue (E06US003) : comme le repêchage, sa fabrique est
    # fermée sur le registre en cours de construction, parce qu'elle doit résoudre le nom du
    # comparateur qu'elle enveloppe.
    registre.enregistrer(
        FamillePolitique.TIEBREAK,
        "barrage",
        lambda params: _fabriquer_barrage(params, registre),
    )
    registre.enregistrer(FamillePolitique.DEPTH, "un_vers_n", lambda _p: ProfondeurUnVersN())
    registre.enregistrer(FamillePolitique.DEPTH, "top_n", _fabriquer_profondeur_podium)
    registre.enregistrer(FamillePolitique.DEPTH, "aucun", lambda _p: AucunClassement())
    registre.enregistrer(
        FamillePolitique.AGGREGATION, "par_qualification", lambda _p: AggregationParQualification()
    )
    registre.enregistrer(FamillePolitique.AGGREGATION, "ex_aequo", lambda _p: AggregationExAequo())
    return registre


PROFONDEUR_MAX_ROUTING = 3
"""Combien de routings peuvent s'envelopper les uns les autres (E05US015).

Le repêchage est une politique **composite** : son `sinon` est résolu par le registre, donc peut
être un repêchage à son tour. La composition est gratuite, la récursion **non bornée** ne l'est pas
— une `config.policies` d'origine client imbriquée un millier de fois donnerait un `RecursionError`,
donc un 500, là où toute config mal formée doit rendre un 422 typé. Trois niveaux dépassent déjà
largement tout besoin réel (repêchage → repêchage → placement)."""


def _fabriquer_repechage(
    params: Mapping[str, object], registre: RegistrePolitiques, profondeur: int = 0
) -> RoutingRepechage:
    """`{"nom": "repechage", "tours": [1], "sinon": {"nom": "placement_cascade"}}` → la politique.

    `tours` est **obligatoire et non vide** : un repêchage qui ne repêche aucun tour est un
    `placement_cascade` déguisé, et l'accepter laisserait croire que le format repêche. `sinon` vaut
    `placement_cascade` par défaut. La récursion passe par le registre, donc un `sinon` lui-même
    « repechage » est résolu sans traitement particulier — la composition le rend gratuit.
    """
    if profondeur >= PROFONDEUR_MAX_ROUTING:
        raise PolitiqueMalFormee(
            f"Les routings de repêchage s'imbriquent au plus {PROFONDEUR_MAX_ROUTING} fois ; "
            "au-delà, la configuration ne décrit plus un format."
        )
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
    # Une seule lecture du `nom` : la relire deux fois obligerait à un `assert` pour convaincre
    # mypy de ce que la garde vient de vérifier — or un `assert` disparaît sous `python -O`.
    if not isinstance(spec_sinon, Mapping) or not isinstance(spec_sinon.get("nom"), str):
        raise PolitiqueMalFormee(
            "Le « sinon » d'un repêchage est un objet portant un « nom » de routing "
            f"(reçu {spec_sinon!r})."
        )
    nom_sinon = spec_sinon["nom"]
    if not isinstance(nom_sinon, str):  # pragma: no cover — garanti par la garde ci-dessus
        raise PolitiqueMalFormee("Le « nom » d'un routing de repêchage doit être une chaîne.")
    params_sinon = {clef: valeur for clef, valeur in spec_sinon.items() if clef != "nom"}
    if nom_sinon == "repechage":
        sinon: Routing = _fabriquer_repechage(params_sinon, registre, profondeur + 1)
    else:
        sinon = cast(
            "Routing", registre.resoudre(FamillePolitique.ROUTING, nom_sinon, params_sinon)
        )
    return RoutingRepechage(tours_repeches=frozenset(tours), sinon=sinon)


def _fabriquer_barrage(
    params: Mapping[str, object], registre: RegistrePolitiques
) -> TiebreakAvecBarrage:
    """`{"nom": "barrage", "jusqu_au": 8, "sinon": {"nom": "ffta_defaut"}}` → la politique.

    `jusqu_au` est **obligatoire** : un barrage sans seuil ne barre rien, c'est un `ffta_defaut`
    déguisé. Même raisonnement que le `tours` du repêchage.
    ⚠️ **Un barrage ne s'enveloppe pas lui-même** — deux seuils imbriqués ne composent rien
    (`barrage_requis` n'étant jamais délégué, le plus interne serait ignoré). C'est ce qui le
    distingue du repêchage, dont l'imbrication a un sens.
    """
    brut = params.get("jusqu_au")
    if not isinstance(brut, int) or isinstance(brut, bool) or brut < 1:
        raise PolitiqueMalFormee(
            "Un barrage attend le rang **jusqu'auquel** il départage, entier positif "
            f"(reçu {brut!r}) ; sans seuil il ne barre rien."
        )
    spec_sinon = params.get("sinon", {"nom": "ffta_defaut"})
    if not isinstance(spec_sinon, Mapping):
        raise PolitiqueMalFormee(
            "Le « sinon » d'un barrage est un objet portant un « nom » de départage "
            f"(reçu {spec_sinon!r})."
        )
    nom_sinon = spec_sinon.get("nom")
    if not isinstance(nom_sinon, str):
        raise PolitiqueMalFormee(
            f"Le « nom » du départage enveloppé par un barrage doit être une chaîne "
            f"(reçu {nom_sinon!r})."
        )
    if nom_sinon == "barrage":
        raise PolitiqueMalFormee(
            "Un barrage ne s'enveloppe pas lui-même : deux seuils imbriqués ne composent pas, "
            "le plus interne serait ignoré."
        )
    params_sinon = {clef: valeur for clef, valeur in spec_sinon.items() if clef != "nom"}
    sous_jacent = cast(
        "Tiebreak", registre.resoudre(FamillePolitique.TIEBREAK, nom_sinon, params_sinon)
    )
    return TiebreakAvecBarrage(sous_jacent=sous_jacent, jusqu_au=brut)


def _fabriquer_profondeur_podium(params: Mapping[str, object]) -> ProfondeurPodium:
    """`{"nom": "top_n", "jusqu_au": 8}` → la profondeur correspondante (4 par défaut).

    Première fabrique **paramétrée** du registre : jusqu'ici toutes les stratégies étaient sans
    état. Un `jusqu_au` non entier ou non positif est une config mal formée — on refuse plutôt que
    de retomber sur le défaut en silence, sans quoi une faute de frappe classerait un top 4 là où
    l'organisateur en demandait 8.
    """
    brut = params.get("jusqu_au", 4)
    if not isinstance(brut, int) or isinstance(brut, bool) or brut < 1:
        raise PolitiqueMalFormee(
            f"La profondeur « top_n » attend un rang entier positif (reçu {brut!r})."
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
                f"({', '.join(f.value for f in _FAMILLES_DE_PHASE)})."
            ) from exc
        if famille in FAMILLES_HORS_CONFIG_PHASE:
            raise PolitiqueMalFormee(
                f"La politique « {famille.value} » ne se règle pas par phase : elle vaut "
                "pour tout le tournoi et s'injecte à la composition root (ADR-0067)."
            )
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
