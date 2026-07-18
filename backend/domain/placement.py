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

La **mixité ≥ 2 clubs** (E03US006) et la **séparation catégorie/blason** (E03US007) ne sont **pas**
appliquées ici : ce sont des US ultérieures.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum

from domain.archer import ArcherId
from domain.blason import BlasonId
from domain.gabarit_salle import Cible
from domain.inscription import InscriptionId

# La comparaison d'espace se fait à une tolérance près : `taille` est un flottant (1/3 → 0.333…),
# et trois tiers doivent tenir sur une cible malgré l'arrondi binaire. On accepte donc un carton
# dont la taille dépasse l'espace restant d'au plus `_EPSILON`.
_EPSILON = 1e-9

# Espace physique d'une cible, normalisé à 1,0 (une face unitaire). Les `taille` des blasons en sont
# des fractions ; leur somme sur une cible ne peut pas le dépasser.
_ESPACE_CIBLE = 1.0


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
    gabarit, pour donner la vue complète de la salle."""

    index: int
    capacite: int
    placements: tuple[Placement, ...] = ()


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


@dataclass
class _CibleEnCours:
    """État mutable de la cible en cours de remplissage (interne au glouton)."""

    cible: Cible
    espace_restant: float
    positions: list[Placement] = field(default_factory=list)
    hauteur: int | None = None
    # blason_id → capacité de carton restante (nombre d'archers encore admissibles sur ce carton).
    cartons: dict[BlasonId, int] = field(default_factory=dict)

    @property
    def positions_restantes(self) -> int:
        return self.cible.capacite - len(self.positions)

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
        modifier la cible pour tester, seulement répondre oui/non aux quatre budgets."""
        if self.positions_restantes == 0:
            return False
        if self.hauteur is not None and self.hauteur != archer.hauteur_cm:
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

    def accueille(self, archer: ArcherAPlacer) -> bool:
        """Tente de poser `archer` sur cette cible ; renvoie `True` si posé, `False` sinon.

        On mutualise d'abord un carton déjà présent du même blason (aucun coût d'espace), sinon on
        pose un carton neuf si l'espace, une position **et** la hauteur le permettent."""
        if self.positions_restantes == 0:
            return False
        if self.hauteur is not None and self.hauteur != archer.hauteur_cm:
            return False
        # Partage d'un carton existant du même blason : il reste une place dessus.
        if self.cartons.get(archer.blason_id, 0) > 0:
            self._poser(archer)
            self.cartons[archer.blason_id] -= 1
            return True
        # Carton neuf : il faut de la place physique pour sa fraction.
        if archer.taille <= self.espace_restant + _EPSILON:
            self.espace_restant -= archer.taille
            self.cartons[archer.blason_id] = archer.capacite_blason - 1
            self.hauteur = archer.hauteur_cm
            self._poser(archer)
            return True
        return False

    def _poser(self, archer: ArcherAPlacer) -> None:
        self.positions.append(
            Placement(
                position=self._prochaine_lettre(),
                archer_id=archer.archer_id,
                blason_id=archer.blason_id,
            )
        )

    def figer(self) -> CiblePlacee:
        """Fige la cible en valeur immuable pour le plan."""
        return CiblePlacee(
            index=self.cible.index, capacite=self.cible.capacite, placements=tuple(self.positions)
        )


def placer(cibles: tuple[Cible, ...], archers: tuple[ArcherAPlacer, ...]) -> PlanDeCibles:
    """Place les archers sur les cibles et renvoie le plan de cibles + les conflits.

    Glouton déterministe : archers triés par `(hauteur, blason, id)`, remplissage cible par cible.
    Un archer qui n'entre sur aucune cible restante ressort en conflit `NON_PLACE`. Le plan liste
    **toutes** les cibles du gabarit, y compris celles restées libres.
    """
    ordonnes = sorted(archers, key=lambda a: (a.hauteur_cm, a.blason_id, a.archer_id))
    figees: list[CiblePlacee] = []
    conflits: list[Conflit] = []

    index_cible = 0
    en_cours = _CibleEnCours(cibles[0], _ESPACE_CIBLE) if cibles else None

    for archer in ordonnes:
        while en_cours is not None and not en_cours.accueille(archer):
            # L'archer n'entre pas : on fige la cible courante et on passe à la suivante.
            figees.append(en_cours.figer())
            index_cible += 1
            en_cours = (
                _CibleEnCours(cibles[index_cible], _ESPACE_CIBLE)
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
    cible: Cible, occupants: tuple[ArcherAPlacer, ...], candidat: ArcherAPlacer
) -> bool:
    """Dit si `candidat` peut rejoindre `cible` déjà peuplée par `occupants` (E03US004, ADR-0024).

    Cœur de la règle « déplacement invalide » du CA : on rejoue les occupants pour reconstituer les
    quatre budgets de la cible (espace, positions, partage de carton, hauteur), puis on teste le
    candidat **sans muter**. Un ajout qui violerait un budget est refusé. Les positions exactes des
    occupants n'importent pas pour cette question (seul leur décompte joue), on les rejoue donc
    densément via `accueille`. Un **échange** A↔B se compose de deux appels : A accepté par la cible
    de B *privée de B*, et B accepté par la cible de A *privée de A*."""
    en_cours = _CibleEnCours(cible, _ESPACE_CIBLE)
    for occupant in occupants:
        en_cours.accueille(occupant)
    return en_cours.peut_accueillir(candidat)


def placer_restants(
    cibles: tuple[Cible, ...],
    plan_actuel: tuple[CiblePlacee, ...],
    donnees: Mapping[ArcherId, ArcherAPlacer],
    a_placer: tuple[ArcherAPlacer, ...],
) -> tuple[tuple[PoseCalculee, ...], tuple[Conflit, ...]]:
    """Pose la réserve (`a_placer`) dans les trous du plan **sans déplacer les placés** (E03US004).

    Reconstruit chaque cible depuis `plan_actuel` (occupants à **leur** position, budgets
    consommés via `donnees`), puis pose chaque archer de la réserve sur la **première** cible qui
    l'accepte (premier-trouvé, ordre déterministe `(hauteur, blason, id)` comme `placer`). Un nouvel
    archer prend la 1ʳᵉ lettre libre ; les positions déjà prises sont préservées. Ce
    qu'aucune cible ne peut accueillir ressort en conflit `NON_PLACE` (reste en réserve). Ne renvoie
    que les **nouvelles** poses : les archers déjà placés ne bougent pas."""
    par_index = {cible.index: _CibleEnCours(cible, _ESPACE_CIBLE) for cible in cibles}
    placee_par_index = {cible_placee.index: cible_placee for cible_placee in plan_actuel}
    for cible in cibles:
        en_cours = par_index[cible.index]
        placee = placee_par_index.get(cible.index)
        if placee is not None:
            for pose in placee.placements:
                en_cours.reprendre(donnees[pose.archer_id], pose.position)

    poses: list[PoseCalculee] = []
    conflits: list[Conflit] = []
    for archer in sorted(a_placer, key=lambda a: (a.hauteur_cm, a.blason_id, a.archer_id)):
        for cible in cibles:
            en_cours = par_index[cible.index]
            if en_cours.accueille(archer):
                lettre = en_cours.positions[-1].position
                poses.append(PoseCalculee(archer.archer_id, cible.index, lettre))
                break
        else:
            conflits.append(Conflit(archer_id=archer.archer_id, raison=RaisonConflit.NON_PLACE))
    return tuple(poses), tuple(conflits)
