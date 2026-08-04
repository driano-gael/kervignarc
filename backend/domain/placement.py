"""Moteur de placement des archers sur les cibles (E03US001) — domaine **pur**.

Répartit les archers d'un départ sur les cibles d'un gabarit de salle et produit le **plan de
cibles** (qui tire où), en signalant les archers qu'aucune cible ne peut accueillir. Aucune
dépendance framework ni persistance : le service applicatif (`application/placement.py`) reconstitue
la jointure archer → catégorie → blason depuis les ports, construit la liste des `ArcherAPlacer` et
appelle `placer` ; ici on ne manipule que des valeurs.

**Trois budgets par cible** (CA « capacité & fraction », clarifié depuis le prototype `cible.py`) :

- **espace** : la somme des `taille` (fractions de place, `]0, 1]`) des cartons posés sur une cible
  ne dépasse pas **1,0** — une cible est une face physique unitaire ;
- **positions** : le nombre d'archers d'une cible ne dépasse pas `Cible.capacite` (les lettres
  A/B/C/D) ;
- **partage de carton** : plusieurs archers d'un **même blason** partagent un carton tant que sa
  `capacite` le permet (un triple accueille 3 tireurs sur un seul carton).

**Quatrième contrainte, de 1er rang** (ex-DETTE-002,
[ADR-0022](../../docs/adr/0022-hauteur-de-centre-sur-la-categorie.md)) : tous les archers d'une
**même cible** tirent à la **même hauteur de centre** — une butte n'a qu'une hauteur de montage. Un
U11 (110 cm) ne partage donc jamais une cible avec un adulte (130 cm), quelle que soit la place
restante.

**Stratégie : glouton, cible par cible, sur une liste triée**
([ADR-0023](../../docs/adr/0023-moteur-de-placement-glouton-deterministe.md)). Les archers sont
ordonnés par
`(hauteur, blason, id)`, ce qui rend contigus les tireurs d'une même hauteur puis d'un même blason ;
on remplit la cible courante tant que les budgets tiennent, et l'on passe à la **suivante** dès
qu'un archer n'entre plus (place, position ou hauteur). Un archer qui n'entre nulle part — plus
aucune cible libre — ressort en **conflit** (`RaisonConflit.NON_PLACE`), jamais en échec silencieux
(CA « conflits »). Le résultat est **déterministe** (tri stable, pas d'aléa) — exigence de test
(règle 9). Ce glouton peut laisser de l'espace perdu sur une cible plutôt que de revenir en
arrière : c'est un compromis assumé du MVP, l'ajustement manuel (E03US004) rattrape les cas limites.

**Mixité ≥ 2 clubs** (E03US006, RG-3,
[ADR-0047](../../docs/adr/0047-mixite-clubs-par-reordonnancement-et-signal-derive.md)) : contrainte
**molle**, priorité la plus basse. Elle n'est **pas** câblée dans le glouton — celui-ci reste
inchangé — mais obtenue en **ré-ordonnant l'entrée** : à l'intérieur de chaque groupe
`(hauteur, blason)`, où tous les archers sont interchangeables pour les budgets (même fraction, même
carton, même hauteur), les clubs sont **entrelacés en round-robin** (`_ordonner_pour_mixite`). Une
cible qui puise dans ce groupe reçoit des clubs variés quand ils existent, sans menacer un budget.
Quand la mixité **ne peut pas** être garantie (un seul club, ou clubs inconnus —
`club_id NULL`, *indécidable*, ADR-0014), la cible est **signalée** via `mixite_non_garantie`
(propriété dérivée du prédicat pur `cible_mixite_non_garantie`), jamais un échec.

**Cloisonnement catégorie/blason** (E03US007, RG-4,
[ADR-0071](../../docs/adr/0071-cloisonnement-categorie-blason-active-et-dur.md)) : contrainte
**activable** à quatre positions (`aucun` — défaut, `categorie`, `blason`, `blason_et_categorie`) et
**dure** quand elle est active — au contraire de la mixité, qui est une préférence. Elle se câble
donc *dans* le glouton (`_CibleEnCours`), pas dans l'ordre d'entrée ; l'ordre, lui, groupe en plus
par catégorie quand le réglage la sépare, sans quoi le glouton — qui ne revient jamais en arrière
(ADR-0023) — fermerait une cible à chaque alternance de catégorie. Un archer qu'aucune cible ne peut
accueillir sous cette contrainte ressort en conflit, jamais en silence ; et une cible d'un plan
**déjà posé** qui viole le réglage nouvellement activé est signalée par `cloisonnement_non_respecte`
— dérivée, jamais persistée, même régime que la mixité.

**Ordre de priorité des contraintes** (question ouverte d'EPIC-03, tranchée ici) :
`capacité / espace / hauteur` (dures, structurelles) > `cloisonnement` (dure, mais **réglable**) >
`mixité de club` (molle) > `adjacence des duellistes` (molle). Le cloisonnement ne peut donc que
**retirer** des cohabitations, jamais en autoriser une.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from itertools import groupby

from domain.archer import ArcherId
from domain.blason import BlasonId
from domain.categorie import CategorieId
from domain.cloisonnement import Cloisonnement
from domain.club import ClubId
from domain.gabarit_salle import Cible
from domain.inscription import InscriptionId

# La comparaison d'espace se fait à une tolérance près : `taille` est un flottant (1/3 → 0.333…),
# et trois tiers doivent tenir sur une cible malgré l'arrondi binaire. On accepte donc un carton
# dont la taille dépasse l'espace restant d'au plus `_EPSILON`.
_EPSILON = 1e-9

# Espace physique d'une cible, normalisé à 1,0 (une face unitaire). Les `taille` des blasons en sont
# des fractions ; leur somme sur une cible ne peut pas le dépasser.
_ESPACE_CIBLE = 1.0

# Stratégie d'**ordre d'entrée** du glouton — le point d'injection des contraintes molles (mixité
# E03US006, adjacence E03US009). Elle reçoit le cloisonnement (E03US007) parce que la clé de groupe
# en dépend : ce qui ne doit pas cohabiter doit d'abord être **contigu**, sinon le glouton ferme une
# cible à chaque alternance. Déclaré ici, utilisé par `placer` et `placer_restants`.
Ordonnancement = Callable[["tuple[ArcherAPlacer, ...]", "Cloisonnement"], "list[ArcherAPlacer]"]


@dataclass(frozen=True)
class ArcherAPlacer:
    """Entrée du moteur : un archer inscrit à placer, avec les grandeurs qui pilotent le placement.

    Construit par le service depuis la jointure archer → catégorie → blason. Volontairement
    **découplé** des agrégats `Archer`/`Blason`/`Categorie` : le moteur ne dépend que de ce dont il
    a besoin (fraction, capacité de carton, hauteur), ce qui le rend testable sans monter trois
    agrégats. Un archer dont la catégorie n'a **pas** de blason par défaut n'entre pas ici : c'est
    le service qui le classe en conflit `SANS_BLASON`, faute de pouvoir déterminer sa fraction.
    """

    archer_id: ArcherId
    blason_id: BlasonId
    taille: float  # fraction de place occupée par un carton de ce blason, ]0, 1]
    capacite_blason: int  # nombre d'archers admis sur un même carton, >= 1
    hauteur_cm: int  # hauteur du centre de l'or (via la catégorie), > 0
    # Club de l'archer, pour favoriser la mixité ≥ 2 clubs/cible (E03US006, RG-3). `None` = club
    # **inconnu / indécidable** (ADR-0014), jamais « même club » : deux `None` ne sont pas du même
    # club. Facultatif (défaut `None`) : les entrées qui l'ignorent restent sur l'ordre d'origine
    # (`archer_id`), d'où la non-régression d'E03US001. Ne pilote que l'ordre, jamais un budget.
    club_id: ClubId | None = None
    # Catégorie de l'archer, pour le **cloisonnement** (E03US007, RG-4). `None` = catégorie
    # **indécidable** : jamais réputée identique à une autre (esprit d'ADR-0014), donc refusée par
    # un cloisonnement par catégorie — la contrainte étant dure, l'indécidable se résout en refus.
    # Facultatif (défaut `None`) : les entrées qui l'ignorent ne changent pas de comportement tant
    # que le cloisonnement ne porte pas sur la catégorie (non-régression d'E03US001).
    categorie_id: CategorieId | None = None


class RaisonConflit(str, Enum):
    """Pourquoi un archer n'a pas pu être placé (rapport de faisabilité, CA « conflits »)."""

    NON_PLACE = "non_place"
    """Plus aucune cible ne peut l'accueillir (place, positions ou hauteur épuisées)."""

    EN_RESERVE = "en_reserve"
    """Mis de côté / en attente de placement, mais **plaçable** — au moins une cible l'accepterait.

    Distingue, en réserve (E03US004), l'archer que l'admin a écarté ou pas encore posé de celui
    qu'aucune cible ne peut plus prendre (`NON_PLACE`). Raison **dérivée à la lecture**, jamais
    persistée (ADR-0024)."""

    SANS_BLASON = "sans_blason"
    """Sa catégorie n'a pas de blason par défaut : impossible de connaître sa fraction de place.

    Produit par le **service** (l'archer n'atteint pas le moteur), mais nommé ici pour que le
    rapport de conflits ait un vocabulaire unique."""

    CLOISONNEMENT = "cloisonnement"
    """Le **cloisonnement** actif (E03US007) est ce qui l'empêche de tenir : sans lui, il
    rentrerait.

    Raison **dérivée à la lecture** par le service, qui est seul à pouvoir la distinguer de
    `NON_PLACE` : il rejoue la question « cette cible l'accepterait-elle **sans** le
    cloisonnement ? »
    et ne qualifie ainsi que les archers dont le *réglage* — et non la saturation de la salle — fait
    la réserve. Le moteur pur, lui, ne rend que `NON_PLACE` : il n'a qu'un monde à sa disposition.
    Distinction utile à l'admin : « désactivez le réglage ou ajoutez une cible » n'est pas le même
    geste que « la salle est pleine »."""


@dataclass(frozen=True)
class Placement:
    """Un archer posé sur une cible : sa position (lettre) et le blason sur lequel il tire.

    `inscription_id` accompagne l'archer pour que la couche API expose **l'inscription** (l'archer
    sur *ce* départ), cible d'un ajustement (`PUT .../inscriptions/{id}`), sans que le client ait à
    reconstituer la correspondance archer → inscription. Le moteur pur (`placer`/`placer_restants`)
    ne connaît pas les inscriptions : il laisse `None` ; c'est le **service** qui la renseigne en
    construisant le plan persisté (E03US004)."""

    position: str  # "A".."D"
    archer_id: ArcherId
    blason_id: BlasonId
    inscription_id: InscriptionId | None = None


@dataclass(frozen=True)
class CiblePlacee:
    """Une cible du plan : son rang (1-based, repris du gabarit) et les archers posés dessus.

    `placements` est vide pour une cible restée libre — le plan liste **toutes** les cibles du
    gabarit, pour donner la vue complète de la salle.

    `mixite_non_garantie` signale (RG-3, E03US006) une cible portant ≥ 2 archers **sans** qu'on
    puisse affirmer ≥ 2 clubs connus distincts (un seul club, ou clubs inconnus — ADR-0014). C'est
    une **propriété dérivée** (`cible_mixite_non_garantie`), jamais persistée : recalculée au moteur
    et à la lecture du plan matérialisé (ADR-0047), comme la raison de réserve (ADR-0024).

    `cloisonnement_non_respecte` signale (E03US007) une cible qui **mêle** ce que le réglage actif
    interdit de mêler. Le placement auto ne peut pas produire cette situation (la contrainte est
    dure) : elle vient d'un plan **posé avant** l'activation du réglage, ou d'un plan importé —
    activer le réglage ne déplace personne. Propriété **dérivée** elle aussi
    (`cible_cloisonnement_non_respecte`), jamais persistée."""

    index: int
    capacite: int
    placements: tuple[Placement, ...] = ()
    mixite_non_garantie: bool = False
    cloisonnement_non_respecte: bool = False


@dataclass(frozen=True)
class Conflit:
    """Un archer que le placement n'a pas pu poser (il est **en réserve**), et pourquoi.

    `inscription_id` : même rôle que sur `Placement` — l'API expose l'inscription pour que le client
    puisse reposer l'archer (drag depuis la réserve) sans reconstituer la correspondance. Le moteur
    pur laisse `None` ; le service la renseigne."""

    archer_id: ArcherId
    raison: RaisonConflit
    inscription_id: InscriptionId | None = None


@dataclass(frozen=True)
class PlanDeCibles:
    """Résultat du placement : le plan par cible + les conflits (rapport de faisabilité)."""

    cibles: tuple[CiblePlacee, ...]
    conflits: tuple[Conflit, ...] = ()


def cible_mixite_non_garantie(clubs: Sequence[ClubId | None]) -> bool:
    """Dit si une cible est « mixité non garantie » (RG-3, E03US006) d'après les clubs posés dessus.

    Vrai quand la cible a **≥ 2 archers** mais **< 2 clubs connus distincts** — donc impossible
    d'**affirmer** la mixité. `None` = club inconnu, *indécidable* (ADR-0014) : il ne compte jamais
    comme un club (deux `None` ⇒ non garantie ; un connu + un `None` ⇒ non garantie). Une cible à 0
    ou 1 archer est **sans objet** (elle ne peut structurellement pas mêler deux clubs) : on ne la
    signale pas, pour ne pas noyer l'admin sous du bruit. Prédicat **pur** : la même vérité sert le
    moteur (tests domaine) et la lecture du plan matérialisé (ADR-0047)."""
    if len(clubs) < 2:
        return False
    clubs_connus = {club for club in clubs if club is not None}
    return len(clubs_connus) < 2


def cible_cloisonnement_non_respecte(
    cloisonnement: Cloisonnement, archers: Sequence[ArcherAPlacer]
) -> bool:
    """Dit si les `archers` posés sur une cible **violent** le cloisonnement demandé (E03US007).

    Vrai quand la cible mêle deux catégories (resp. deux blasons) que le réglage sépare. Une
    catégorie `None` est **indécidable** (esprit d'ADR-0014) : deux `None` ne sont pas réputés de la
    même catégorie, donc leur cohabitation est une violation — on ne fait jamais l'hypothèse
    favorable sur une donnée manquante. Une cible à 0 ou 1 archer est **sans objet** (elle ne peut
    structurellement rien mêler), tout comme le réglage `AUCUN`.

    Prédicat **pur** et unique : la même vérité sert le glouton (qui l'utilise en négatif pour
    refuser une pose), la validation d'un déplacement manuel et le signal calculé à la lecture d'un
    plan matérialisé — trois chemins, un seul énoncé de la règle."""
    if cloisonnement is Cloisonnement.AUCUN or len(archers) < 2:
        return False
    if cloisonnement.separe_blason and len({archer.blason_id for archer in archers}) > 1:
        return True
    if cloisonnement.separe_categorie:
        categories = {archer.categorie_id for archer in archers}
        # `None` (indécidable) rend la cible non conforme dès qu'un second archer est présent :
        # `{None}` compte pour « autant de catégories distinctes que d'archers ».
        if None in categories or len(categories) > 1:
            return True
    return False


def _cloisonnement_admet(
    cloisonnement: Cloisonnement, occupants: Sequence[ArcherAPlacer], candidat: ArcherAPlacer
) -> bool:
    """Dit si `candidat` peut rejoindre `occupants` sans violer le cloisonnement (négatif du
    signal).

    Défini **à partir** de `cible_cloisonnement_non_respecte` pour qu'il n'existe qu'une seule
    définition de la règle. Conséquence assumée : sur une cible **déjà** non conforme (plan
    antérieur à l'activation du réglage), toute pose est refusée — même « neutre ». L'admin la rend
    conforme en retirant les intrus ou en régénérant ; c'est plus prévisible qu'une règle « ne pas
    aggraver », dont le résultat dépendrait de l'ordre des gestes."""
    return not cible_cloisonnement_non_respecte(cloisonnement, [*occupants, candidat])


def _positions_adjacentes(a: str, b: str) -> bool:
    """Deux positions sont **voisines** si leurs lettres sont consécutives (A-B, B-C, C-D).

    Les positions d'une cible sont des lettres contiguës A, B, C, D dans l'ordre physique : deux
    tireurs côte à côte occupent donc deux lettres qui se suivent (`abs(ord) == 1`). A et C ne sont
    pas voisins (B les sépare). Définition de « côte à côte » d'E03US009 (ADR-0048)."""
    return abs(ord(a) - ord(b)) == 1


def duels_non_cote_a_cote(
    plan: PlanDeCibles, paires: Sequence[tuple[ArcherId, ArcherId]]
) -> tuple[tuple[ArcherId, ArcherId], ...]:
    """Les duels dont les deux membres ne sont **pas** côte à côte dans `plan` (E03US009, ADR-0048).

    Un duel est côte à côte quand ses deux archers sont posés sur la **même** cible à des positions
    **adjacentes**. Sinon — cibles différentes, positions non adjacentes, ou l'un au moins **non
    placé** (réserve) — le duel est **signalé** (jamais un échec : le placement n'échoue pas, il
    avoue). Propriété **pure et dérivée** du plan + des paires, calculée en post-passe : le glouton
    générique ignore les paires (ADR-0048 §4). Ordre déterministe = celui de `paires`."""
    localisation = {
        pose.archer_id: (cible.index, pose.position)
        for cible in plan.cibles
        for pose in cible.placements
    }
    separes: list[tuple[ArcherId, ArcherId]] = []
    for a, b in paires:
        la = localisation.get(a)
        lb = localisation.get(b)
        if la is None or lb is None or la[0] != lb[0] or not _positions_adjacentes(la[1], lb[1]):
            separes.append((a, b))
    return tuple(separes)


def cibles_avec_duel_separe(
    plan: PlanDeCibles, paires: Sequence[tuple[ArcherId, ArcherId]]
) -> frozenset[int]:
    """Indices des cibles portant un duelliste dont l'adversaire n'est **pas** côte à côte (badge).

    Dérivé de `duels_non_cote_a_cote` : toute cible qui héberge au moins un membre d'un duel séparé
    est **signalée** (`adjacence_non_garantie` côté service/API). Une cible sans duel séparé n'est
    pas signalée — pas de bruit (E03US009, ADR-0048)."""
    localisation = {
        pose.archer_id: cible.index for cible in plan.cibles for pose in cible.placements
    }
    indices: set[int] = set()
    for a, b in duels_non_cote_a_cote(plan, paires):
        for archer_id in (a, b):
            index = localisation.get(archer_id)
            if index is not None:
                indices.add(index)
    return frozenset(indices)


@dataclass
class _CibleEnCours:
    """État mutable de la cible en cours de remplissage (interne au glouton)."""

    cible: Cible
    espace_restant: float
    positions: list[Placement] = field(default_factory=list)
    hauteur: int | None = None
    # blason_id → capacité de carton restante (nombre d'archers encore admissibles sur ce carton).
    cartons: dict[BlasonId, int] = field(default_factory=dict)
    # Archers posés, dans l'ordre — `Placement` ne porte ni le club ni la catégorie (il n'en a pas
    # besoin), et les deux signaux dérivés en ont besoin au moment de figer : la mixité (E03US006)
    # lit les clubs, le cloisonnement (E03US007) la catégorie et le blason. On garde donc l'entrée
    # complète plutôt que deux listes parallèles à tenir synchronisées.
    archers_poses: list[ArcherAPlacer] = field(default_factory=list)
    # Ce que cette cible n'a pas le droit de mêler (E03US007) — `AUCUN` = comportement d'E03US001.
    cloisonnement: Cloisonnement = Cloisonnement.AUCUN

    @property
    def positions_restantes(self) -> int:
        return self.cible.capacite - len(self.positions)

    @property
    def clubs_poses(self) -> list[ClubId | None]:
        """Clubs des archers posés, dans l'ordre (entrée du signal de mixité, E03US006)."""
        return [archer.club_id for archer in self.archers_poses]

    def _prochaine_lettre(self) -> str:
        """Première position **libre** de la cible (A, puis B, …), en sautant les trous.

        Sur une cible remplie à partir de zéro (cas de `placer`), c'est la position suivante par
        décompte — comportement identique à avant. Après `reprendre` (reconstruction depuis un plan
        persisté où des lettres peuvent manquer, E03US004), c'est la première lettre non occupée."""
        occupees = {p.position for p in self.positions}
        for lettre in self.cible.positions:
            if lettre not in occupees:
                return lettre
        raise AssertionError("Aucune position libre : appelée alors que la cible est pleine.")

    def peut_accueillir(self, archer: ArcherAPlacer) -> bool:
        """Dit si `archer` **pourrait** être posé, sans muter l'état — même règle qu'`accueille`.

        Sert à valider un déplacement manuel (E03US004) avant de l'appliquer : on ne veut pas
        modifier la cible pour tester, seulement répondre oui/non aux quatre budgets — et, depuis
        E03US007, au cloisonnement actif.

        `accueille` **en dérive** (il pose ce que celle-ci autorise) : les gardes ne sont écrites
        qu'ici. Elles l'étaient en double jusqu'à E03US007, qui a ajouté la même ligne de
        cloisonnement aux deux — c'est précisément la duplication qu'ADR-0023 §2 guettait, et le
        remède tient en une délégation, pas en un registre de contraintes (ADR-0071 §6)."""
        if self.positions_restantes == 0:
            return False
        if self.hauteur is not None and self.hauteur != archer.hauteur_cm:
            return False
        if not _cloisonnement_admet(self.cloisonnement, self.archers_poses, archer):
            return False
        if self.cartons.get(archer.blason_id, 0) > 0:
            return True
        return archer.taille <= self.espace_restant + _EPSILON

    def reprendre(self, archer: ArcherAPlacer, position: str) -> None:
        """Réintègre un occupant **déjà placé** à sa position exacte (reconstruction, E03US004).

        Consomme les budgets comme `accueille` (partage de carton, sinon carton neuf : espace,
        carton, hauteur) mais **impose** `position` au lieu d'en prendre une neuve : on reconstruit
        une cible depuis le plan persisté avant d'y poser la réserve. L'appelant garantit que
        l'occupant tient (état persisté déjà valide)."""
        if self.cartons.get(archer.blason_id, 0) > 0:
            self.cartons[archer.blason_id] -= 1
        else:
            self.espace_restant -= archer.taille
            self.cartons[archer.blason_id] = archer.capacite_blason - 1
            self.hauteur = archer.hauteur_cm
        self.positions.append(
            Placement(position=position, archer_id=archer.archer_id, blason_id=archer.blason_id)
        )
        self.archers_poses.append(archer)

    def accueille(self, archer: ArcherAPlacer) -> bool:
        """Tente de poser `archer` sur cette cible ; renvoie `True` si posé, `False` sinon.

        **Ni les gardes ni la consommation ne sont réécrites ici** : la première vit dans
        `peut_accueillir`, la seconde dans `reprendre`. Cette méthode n'est que leur composition —
        « si c'est autorisé, alors pose à la première lettre libre ».

        C'est ce qui rend vraie l'affirmation d'ADR-0071 §6 : une contrainte de plus ne s'écrit
        qu'**à un seul endroit**. Elle ne l'était qu'à moitié après la première correction de revue,
        qui n'avait dédupliqué que les gardes — `reprendre` recopiait encore mot pour mot le bloc
        carton/espace/hauteur, si bien qu'une contrainte **consommant un budget** aurait dû être
        écrite trois fois. Relevé par deux axes en seconde passe."""
        if not self.peut_accueillir(archer):
            return False
        self.reprendre(archer, self._prochaine_lettre())
        return True

    def figer(self) -> CiblePlacee:
        """Fige la cible en valeur immuable pour le plan, drapeaux dérivés compris.

        Mixité de club (E03US006) et cloisonnement (E03US007) sont calculés ici depuis les archers
        posés. Le second est toujours `False` sur un plan **fraîchement généré** (la contrainte est
        dure : le glouton n'a pas pu la violer) — il ne devient vrai qu'à la relecture d'un plan
        matérialisé antérieur au réglage, où le service refait le même calcul."""
        return CiblePlacee(
            index=self.cible.index,
            capacite=self.cible.capacite,
            placements=tuple(self.positions),
            mixite_non_garantie=cible_mixite_non_garantie(self.clubs_poses),
            cloisonnement_non_respecte=cible_cloisonnement_non_respecte(
                self.cloisonnement, self.archers_poses
            ),
        )


def _entrelacer_clubs(groupe: list[ArcherAPlacer]) -> list[ArcherAPlacer]:
    """Entrelace les clubs d'un groupe `(hauteur, blason)` déjà trié par `archer_id` (E03US006).

    Round-robin **déterministe** : on répartit les archers en files par club (clubs connus d'abord,
    par `id` croissant, puis le paquet des inconnus `None` en dernier), puis on tire tour à tour une
    tête de chaque file non vide. Résultat : dans le groupe, deux archers consécutifs tendent à
    venir de clubs différents — la cible les prenant est mixée. Avec un seul club (ou que `None`)
    il n'y a qu'une file : le round-robin est l'**identité**, l'ordre reste celui d'`archer_id`
    (non-régression d'E03US001). Ne réordonne qu'à l'intérieur du groupe, où tous les archers sont
    interchangeables pour les budgets (même fraction, carton, hauteur) — les contraintes de rang
    supérieur sont donc intactes (ADR-0047)."""
    files: dict[ClubId | None, list[ArcherAPlacer]] = {}
    for archer in groupe:
        files.setdefault(archer.club_id, []).append(archer)
    connus = sorted(club for club in files if club is not None)
    # Clubs connus d'abord (par id croissant), puis le paquet des inconnus (`None`) en dernier.
    ordre: list[ClubId | None] = [*connus, None] if None in files else [*connus]
    restants = [files[club] for club in ordre]
    entrelaces: list[ArcherAPlacer] = []
    while any(restants):
        for file in restants:
            if file:
                entrelaces.append(file.pop(0))
    return entrelaces


def _cle_de_groupe(
    cloisonnement: Cloisonnement,
) -> Callable[[ArcherAPlacer], tuple[int, int, int]]:
    """Clé de **groupe** du tri d'entrée : ce qui rend contigus des archers interchangeables.

    `(hauteur, blason)` depuis E03US001 ; s'y ajoute la **catégorie** quand le cloisonnement la
    sépare (E03US007). Sans cet ajout, deux catégories partageant un blason s'entrelaceraient par
    `archer_id` et le glouton — qui ne revient jamais en arrière (ADR-0023) — fermerait une cible à
    chaque alternance : le réglage coûterait des cibles sans rien apporter. La catégorie n'entre
    **pas** dans la clé quand le réglage ne la sépare pas : le plan par défaut reste alors
    exactement celui d'avant l'US (non-régression stricte).

    `categorie_id` à `None` est trié comme `-1` : une valeur fixe, pour que le tri reste **total et
    déterministe** (règle 9) — `None` n'est pas comparable à un `int`. Le refus des indécidables est
    la responsabilité du prédicat de cloisonnement, pas du tri. Le test est `is not None` et non la
    véracité : une catégorie d'identifiant `0` est une catégorie **connue**, et la ranger avec les
    inconnues ferait diverger le tri du prédicat, qui la traite bien comme décidable."""
    if cloisonnement.separe_categorie:
        return lambda a: (
            a.hauteur_cm,
            a.blason_id,
            a.categorie_id if a.categorie_id is not None else -1,
        )
    return lambda a: (a.hauteur_cm, a.blason_id, 0)


def _ordonner_pour_mixite(
    archers: tuple[ArcherAPlacer, ...], cloisonnement: Cloisonnement = Cloisonnement.AUCUN
) -> list[ArcherAPlacer]:
    """Ordre d'entrée du glouton, mixité comprise (E03US006, ADR-0047).

    Tri de base identique à E03US001 — `(hauteur, blason, id)`, enrichi de la **catégorie** quand le
    cloisonnement la sépare (E03US007) —, qui fixe les **groupes** contigus, puis entrelacement des
    clubs **à l'intérieur** de chaque groupe. Le glouton lui-même n'est pas touché par la mixité :
    il consomme simplement une liste dont l'ordre la favorise."""
    groupe_de = _cle_de_groupe(cloisonnement)
    base = sorted(archers, key=lambda a: (*groupe_de(a), a.archer_id))
    ordonnes: list[ArcherAPlacer] = []
    for _, groupe in groupby(base, key=groupe_de):
        ordonnes.extend(_entrelacer_clubs(list(groupe)))
    return ordonnes


def _grouper_paires(
    groupe: list[ArcherAPlacer], partenaire: Mapping[ArcherId, ArcherId]
) -> list[ArcherAPlacer]:
    """Émet les deux membres d'un duel **consécutivement** dans un groupe trié par `archer_id`.

    Le groupe est déjà trié par `archer_id`. On le parcourt dans cet ordre ; dès qu'un archer non
    encore émis a son **partenaire** dans le même groupe et pas encore émis, on émet les deux à la
    suite. Résultat : chaque paire est clusterisée à la tête de son membre de plus petit
    `archer_id`, ses deux archers adjacents — le glouton les posera alors sur deux positions
    voisines de la cible courante. Déterministe (parcours par `archer_id`, aucune ambiguïté). Un
    archer sans partenaire dans le groupe (bye, effectif impair, adversaire d'un autre groupe) reste
    **en place**."""
    par_id = {a.archer_id: a for a in groupe}
    emis: set[ArcherId] = set()
    resultat: list[ArcherAPlacer] = []
    for archer in groupe:
        if archer.archer_id in emis:
            continue
        resultat.append(archer)
        emis.add(archer.archer_id)
        conjoint = partenaire.get(archer.archer_id)
        if conjoint is not None and conjoint in par_id and conjoint not in emis:
            resultat.append(par_id[conjoint])
            emis.add(conjoint)
    return resultat


def _ordonner_pour_adjacence(
    archers: tuple[ArcherAPlacer, ...],
    cloisonnement: Cloisonnement = Cloisonnement.AUCUN,
    *,
    partenaire: Mapping[ArcherId, ArcherId],
) -> list[ArcherAPlacer]:
    """Ordre d'entrée du glouton favorisant le côte à côte des duellistes (E03US009, ADR-0048).

    Tri de base identique à E03US001 — `(hauteur, blason, id)`, qui fixe les **groupes** contigus —
    puis regroupement des paires **à l'intérieur** de chaque groupe `(hauteur, blason)`. Deux
    duellistes partagent la catégorie → même blason/hauteur → **même groupe**, donc le clustering
    est naturel. Le glouton n'est pas touché (ADR-0048 §4) : il consomme une liste dont l'ordre
    favorise l'adjacence. `partenaire` associe chaque archer à son adversaire (relation symétrique).

    ⚠️ Sous **cloisonnement par catégorie** (E03US007), un tableau ensemencé au scratch peut opposer
    deux catégories (ADR-0028 : `construire_tableau` ignore les catégories) : les duellistes tombent
    alors dans deux groupes distincts et le côte à côte devient **impossible**. C'est l'ordre de
    priorité assumé — la contrainte dure gagne sur la molle —, et le duel est signalé
    `adjacence_non_garantie` comme n'importe quel autre duel séparé."""
    groupe_de = _cle_de_groupe(cloisonnement)
    base = sorted(archers, key=lambda a: (*groupe_de(a), a.archer_id))
    ordonnes: list[ArcherAPlacer] = []
    for _, groupe in groupby(base, key=groupe_de):
        ordonnes.extend(_grouper_paires(list(groupe), partenaire))
    return ordonnes


def placer(
    cibles: tuple[Cible, ...],
    archers: tuple[ArcherAPlacer, ...],
    *,
    ordonner: Ordonnancement = _ordonner_pour_mixite,
    cloisonnement: Cloisonnement = Cloisonnement.AUCUN,
) -> PlanDeCibles:
    """Place les archers sur les cibles et renvoie le plan de cibles + les conflits.

    Glouton déterministe : archers ordonnés par la stratégie `ordonner` (défaut : tri
    `(hauteur, blason, id)` **entrelacé par club** pour la mixité, E03US006/ADR-0047) ; remplissage
    cible par cible. Un archer qui n'entre sur aucune cible restante ressort en conflit `NON_PLACE`.
    Le plan liste **toutes** les cibles du gabarit, y compris celles restées libres.

    `ordonner` est le **point d'injection** des contraintes molles portées par l'ordre d'entrée : la
    mixité (défaut) pour la qualification, l'adjacence des duellistes (`_ordonner_pour_adjacence`)
    pour un plan de duels (E03US009, ADR-0048). Le glouton reste inchangé quel que soit l'ordre —
    seule change l'identité de qui occupe quelle position, jamais les budgets (ADR-0047 §1).

    `cloisonnement`, lui, **change** les budgets : c'est une contrainte **dure** (E03US007), passée
    à chaque cible et à la stratégie d'ordre (qui groupe alors par catégorie). `AUCUN` (défaut) rend
    le plan d'avant l'US, à l'identique.
    """
    ordonnes = ordonner(archers, cloisonnement)
    figees: list[CiblePlacee] = []
    conflits: list[Conflit] = []

    index_cible = 0
    en_cours = (
        _CibleEnCours(cibles[0], _ESPACE_CIBLE, cloisonnement=cloisonnement) if cibles else None
    )

    for archer in ordonnes:
        while en_cours is not None and not en_cours.accueille(archer):
            # L'archer n'entre pas : on fige la cible courante et on passe à la suivante.
            figees.append(en_cours.figer())
            index_cible += 1
            en_cours = (
                _CibleEnCours(cibles[index_cible], _ESPACE_CIBLE, cloisonnement=cloisonnement)
                if index_cible < len(cibles)
                else None
            )
        if en_cours is None:
            # Plus aucune cible : cet archer et tous les suivants sont en conflit.
            conflits.append(Conflit(archer_id=archer.archer_id, raison=RaisonConflit.NON_PLACE))

    # Fige la dernière cible en cours, puis liste les cibles restées libres après le curseur.
    if en_cours is not None:
        figees.append(en_cours.figer())
        for cible in cibles[index_cible + 1 :]:
            figees.append(CiblePlacee(index=cible.index, capacite=cible.capacite))

    return PlanDeCibles(cibles=tuple(figees), conflits=tuple(conflits))


@dataclass(frozen=True)
class Affectation:
    """Affectation **persistée** d'un inscrit sur une case (E03US004, ADR-0024).

    Là où E03US001 recalculait le plan à chaque lecture, E03US004 le **matérialise** : une
    affectation par **inscription** (l'archer sur *ce* départ). `cible_index` reprend l'index
    1-based du gabarit, `position` la lettre (A..D). Un inscrit **sans** affectation = réserve —
    l'absence de ligne *est* l'information, on ne persiste pas la réserve."""

    inscription_id: InscriptionId
    cible_index: int
    position: str


@dataclass(frozen=True)
class PoseCalculee:
    """Une pose **décidée** par le placement des restants : archer → (cible, position) (E03US004).

    Distincte d'`Affectation` (clé archer, pas inscription) : le moteur pur raisonne en `archer_id`,
    le service traduit ensuite en inscription pour persister."""

    archer_id: ArcherId
    cible_index: int
    position: str


def cible_accepte(
    cible: Cible,
    occupants: tuple[ArcherAPlacer, ...],
    candidat: ArcherAPlacer,
    *,
    cloisonnement: Cloisonnement = Cloisonnement.AUCUN,
) -> bool:
    """Dit si `candidat` peut rejoindre `cible` déjà peuplée par `occupants` (E03US004, ADR-0024).

    Cœur de la règle « déplacement invalide » du CA : on rejoue les occupants pour reconstituer les
    quatre budgets de la cible (espace, positions, partage de carton, hauteur), puis on teste le
    candidat **sans muter**. Un ajout qui violerait un budget est refusé. Les positions exactes des
    occupants n'importent pas pour cette question (seul leur décompte joue), on les rejoue donc
    densément. Un **échange** A↔B se compose de deux appels : A accepté par la cible de B *privée de
    B*, et B accepté par la cible de A *privée de A*.

    ⚠️ **Les occupants sont repris par `reprendre`, jamais par `accueille`** — correction de revue,
    en deux temps. `accueille` **valide** avant de poser : un occupant que l'état persisté rend
    aujourd'hui invalide (hauteur de catégorie ou taille de blason éditée **après** placement, ce
    qu'aucune garde n'interdit) est silencieusement **perdu** au rejeu, son retour n'étant pas lu.
    On jugeait alors le candidat contre une cible **plus vide que la vraie** : d'abord sur le
    cloisonnement (première passe de revue), puis — la correction ne fermant qu'une moitié — sur les
    budgets eux-mêmes, au point d'accepter une pose sur une cible physiquement pleine (mesuré par
    l'axe adversarial en seconde passe). `reprendre` ne consulte aucune garde : il **reconstitue**
    l'état réel, conforme ou non, ce qui est exactement ce qu'on veut d'une reconstruction. Le
    cloisonnement peut dès lors être posé au constructeur comme partout ailleurs."""
    en_cours = _CibleEnCours(cible, _ESPACE_CIBLE, cloisonnement=cloisonnement)
    for occupant, position in zip(occupants, cible.positions, strict=False):
        en_cours.reprendre(occupant, position)
    return en_cours.peut_accueillir(candidat)


class MotifRefus(str, Enum):
    """Pourquoi une cible refuse un archer — la question que pose un **ajustement manuel**.

    `cible_accepte` répond oui/non ; ceci répond *pourquoi*, parce que les trois « non » n'appellent
    pas le même geste de l'organisateur : libérer de la place, desserrer un réglage, ou remettre une
    cible en ordre. Les deux services (qualification et duels) traduisaient chacun cette question en
    enchaînant deux appels à `cible_accepte` et un prédicat — quatre recopies d'un même
    raisonnement, dans deux fichiers jumeaux qu'ADR-0048 signale déjà comme dupliqués. La **règle**
    vit ici ; il ne reste aux services que le **vocabulaire** (« archers », « duellistes »).
    """

    AUCUN = "aucun"
    """La cible accepte l'archer : rien à refuser."""

    BUDGETS = "budgets"
    """Capacité, espace, partage de carton ou hauteur — la **physique** de la cible."""

    CLOISONNEMENT_MELANGE = "cloisonnement_melange"
    """Le candidat mêlerait ce que le réglage sépare. Desserrer le réglage, ou viser ailleurs."""

    CLOISONNEMENT_CIBLE_DEJA_NON_CONFORME = "cloisonnement_cible_deja_non_conforme"
    """La cible viole **déjà** le réglage sans le candidat (plan antérieur à son activation).

    Distinct du précédent : ici le candidat ne mêle rien — l'accuser enverrait l'organisateur
    chercher une faute qu'il n'a pas commise, alors que le geste utile est de régénérer ou de vider
    la cible."""


def motif_de_refus(
    cible: Cible,
    occupants: tuple[ArcherAPlacer, ...],
    candidat: ArcherAPlacer,
    *,
    cloisonnement: Cloisonnement = Cloisonnement.AUCUN,
) -> MotifRefus:
    """Dit **pourquoi** `cible` refuse `candidat`, ou `AUCUN` si elle l'accepte (E03US007).

    Fonction pure, dérivée des deux prédicats existants — aucune règle nouvelle : `cible_accepte`
    sous réglage donne le verdict, `cible_accepte` **sans** réglage dit si le réglage en est la
    cause, et `cible_cloisonnement_non_respecte` sur les seuls occupants distingue « le candidat
    mêlerait » de « la cible est déjà en faute »."""
    if cible_accepte(cible, occupants, candidat, cloisonnement=cloisonnement):
        return MotifRefus.AUCUN
    if cloisonnement is Cloisonnement.AUCUN or not cible_accepte(cible, occupants, candidat):
        return MotifRefus.BUDGETS
    if cible_cloisonnement_non_respecte(cloisonnement, occupants):
        return MotifRefus.CLOISONNEMENT_CIBLE_DEJA_NON_CONFORME
    return MotifRefus.CLOISONNEMENT_MELANGE


def placer_restants(
    cibles: tuple[Cible, ...],
    plan_actuel: tuple[CiblePlacee, ...],
    donnees: Mapping[ArcherId, ArcherAPlacer],
    a_placer: tuple[ArcherAPlacer, ...],
    *,
    ordonner: Ordonnancement = _ordonner_pour_mixite,
    cloisonnement: Cloisonnement = Cloisonnement.AUCUN,
) -> tuple[tuple[PoseCalculee, ...], tuple[Conflit, ...]]:
    """Pose la réserve (`a_placer`) dans les trous du plan **sans déplacer les placés** (E03US004).

    Reconstruit chaque cible depuis `plan_actuel` (occupants à **leur** position, budgets
    consommés via `donnees`), puis pose chaque archer de la réserve sur la **première** cible qui
    l'accepte (premier-trouvé, ordre déterministe `(hauteur, blason, id)` comme `placer`). Un nouvel
    archer prend la 1ʳᵉ lettre libre ; les positions déjà prises sont préservées. Ce
    qu'aucune cible ne peut accueillir ressort en conflit `NON_PLACE` (reste en réserve). Ne renvoie
    que les **nouvelles** poses : les archers déjà placés ne bougent pas.

    Le `cloisonnement` (E03US007) ne s'applique qu'aux **nouvelles** poses : les occupants sont
    repris par `reprendre`, qui ne consulte aucune garde — l'état persisté existe déjà, conforme ou
    non, il n'y a rien à valider. La contrainte est donc posée **au constructeur** et ne gêne pas la
    reprise. Un archer qu'elle exclut de partout reste en réserve, comme un archer que la salle ne
    peut plus prendre."""
    par_index = {
        cible.index: _CibleEnCours(cible, _ESPACE_CIBLE, cloisonnement=cloisonnement)
        for cible in cibles
    }
    placee_par_index = {cible_placee.index: cible_placee for cible_placee in plan_actuel}
    for cible in cibles:
        en_cours = par_index[cible.index]
        placee = placee_par_index.get(cible.index)
        if placee is not None:
            for pose in placee.placements:
                en_cours.reprendre(donnees[pose.archer_id], pose.position)

    poses: list[PoseCalculee] = []
    conflits: list[Conflit] = []
    for archer in ordonner(a_placer, cloisonnement):
        for cible in cibles:
            en_cours = par_index[cible.index]
            if en_cours.accueille(archer):
                lettre = en_cours.positions[-1].position
                poses.append(PoseCalculee(archer.archer_id, cible.index, lettre))
                break
        else:
            conflits.append(Conflit(archer_id=archer.archer_id, raison=RaisonConflit.NON_PLACE))
    return tuple(poses), tuple(conflits)
