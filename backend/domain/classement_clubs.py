"""Le classement des **clubs entre eux**, au décompte de médailles (E16US017).

⚠️ **Module à part, et non une méthode de `Palmares`** : `ADR-0103` §8 qualifie ce classement de
**neuf**, par opposition au rang « dans son club » d'E16US014 qui est un regroupement. Il **lit**
les podiums décernés et ne rejoue aucun rang : les deux barèmes ne peuvent donc pas diverger.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.club import ClubId
from domain.palmares import BlocPodium, Palmares, libelle_de_club
from domain.podium import PorteePodium, ReglagePodiums

PORTEES_INTER_CLUBS = frozenset({PorteePodium.SCRATCH, PorteePodium.CATEGORIE})
"""Les portées qui comparent des archers **de clubs différents**.

⚠️ La portée *club* en est exclue (arbitrage du 04/09/2026) : elle décerne un or à l'intérieur de
**chaque** club, donc à tous. La compter aurait classé les clubs à l'effectif — exactement ce que
les Notes d'E16US017 excluent du barème retenu.
"""

_METAUX = 3
"""Or, argent, bronze — le barème n'en connaît pas d'autre.

⚠️ Une place de podium n'est **pas** une médaille au-delà : la profondeur par défaut est 4
(ADR-0103 §4) et monte à 64, donc le cas est nominal, pas marginal.
"""


@dataclass(frozen=True)
class LigneClassementClubs:
    """Un club et son décompte. Le rang est **partagé** à décompte égal, sans départage inventé."""

    rang: int
    club_id: ClubId
    club_libelle: str
    medailles_or: int
    medailles_argent: int
    medailles_bronze: int


@dataclass(frozen=True)
class ClassementClubs:
    """Le classement des clubs, et de quoi dire **sur quoi il repose** — ou pourquoi il est absent.

    ⚠️ L'état est **porté**, jamais déduit par l'appelant d'une liste vide : c'est la leçon des
    trois passes de revue d'ADR-0103 §6, où l'énoncé d'un bloc portait chaque fois sur une autre
    population que son contenu.
    """

    lignes: tuple[LigneClassementClubs, ...]
    """Les clubs classés — **vide** tant qu'aucun d'eux n'a de médaille (décision 8 d'ADR-0104).

    ⚠️ **Ne pas ranger un champ de zéros** : à décompte égal le rang est partagé, donc tous les
    clubs sortaient **1ᵉʳˢ** toute la matinée — l'état que le CA interdit, atteint par la porte du
    décompte au lieu de celle de la portée (relevé en revue, axe C1).
    """

    portees_comptees: tuple[PorteePodium, ...]
    """Les portées du réglage qui alimentent le décompte — **vide** = aucune base de comparaison.

    ⚠️ Dérivé du **réglage**, pas des blocs rendus : sans quoi un tournoi qui n'a encore décerné
    aucune médaille se dirait « sans base », ce qui est faux et ne se corrigerait jamais à l'écran.
    """

    portees_reglees: tuple[PorteePodium, ...]
    """Tout ce que le tournoi récompense, portée *club* **comprise** — **vide** = il ne récompense
    rien, et la surface n'a alors aucune question à traiter (ADR-0104 §3).

    ⚠️ **Sans valeur par défaut, délibérément** : `()` fait disparaître la section des quatre
    surfaces, donc un constructeur qui l'oublierait supprimerait la fonctionnalité en silence.
    """

    provisoire: bool = False
    """Un podium compté attend-il encore ? On ne promet pas un trophée pendant que ça se tire."""


def classer_clubs(palmares: Palmares, reglage: ReglagePodiums) -> ClassementClubs:
    """Classe les clubs à l'or, puis à l'argent, puis au bronze (ordre olympique).

    Le décompte porte sur les médailles que le tournoi **décerne** : un archer médaillé dans deux
    portées cumulées en rapporte deux à son club (ADR-0104 §4, dont la limite mono-catégorie).
    ⚠️ Un archer **sans club** n'en rapporte à personne et ne crée aucune ligne (ADR-0014).
    ⚠️ `DETTE-045` — ce classement **agrège** et désigne un **lauréat unique**, sur la donnée du
    seul premier créneau : un club qui tire l'après-midi n'apporte rien.
    """
    reglees = reglage.portees_actives()
    portees = tuple(portee for portee in reglees if portee in PORTEES_INTER_CLUBS)
    if not portees:
        return ClassementClubs(lignes=(), portees_comptees=(), portees_reglees=reglees)

    blocs = tuple(bloc for bloc in palmares.podiums(reglage) if bloc.portee in PORTEES_INTER_CLUBS)
    libelles = _libelles(palmares)
    decomptes = _decompter(blocs, libelles)
    # Tant que personne n'a rien gagné, il n'y a pas de classement — pas un classement de zéros.
    # Le ranger donnerait le **même** rang à tous (clé égale), donc « 1ᵉʳ » à chaque club, ce que
    # le CA interdit et que trois surfaces auraient affiché toute la matinée.
    aucune = not any(decompte != (0, 0, 0) for decompte in decomptes.values())
    return ClassementClubs(
        lignes=() if aucune else _ranger(decomptes, libelles),
        portees_comptees=portees,
        portees_reglees=reglees,
        # ⚠️ **Le créneau prime, comme au bloc** (ADR-0103 §6) : tant qu'une phase à duels ouverte
        # n'a rien livré, elle peut encore renuméroter tout le monde — quels que soient les métaux
        # déjà décernés. Ce n'est qu'à l'intérieur de ce cas que l'attente s'affine, archer par
        # archer.
        provisoire=palmares.duels_non_commences
        or any(_reste_une_medaille(bloc, reglage.profondeur) for bloc in blocs),
    )


def _reste_une_medaille(bloc: BlocPodium, profondeur: int) -> bool:
    """Ce bloc peut-il encore **changer le décompte** ? — pas « attend-il quelqu'un ».

    ⚠️ **La nuance décide d'un trophée** (relevé en revue, axe D). `bloc.en_attente` est vrai dès
    qu'un archer du groupe est en lice, **fût-ce pour la 5ᵉ place** : le classement annonçait alors
    « décompte provisoire » sous des podiums qui, eux, n'affichaient aucune réserve — les trois
    métaux étant décernés. L'organisateur retenait le trophée sans savoir pourquoi.
    """
    decernees = sum(1 for place in bloc.places if place.rang <= _METAUX)
    return bloc.en_attente and decernees < min(_METAUX, profondeur, bloc.effectif)


def _libelles(palmares: Palmares) -> dict[ClubId, str]:
    """Tous les clubs **présents au tournoi**, dans l'ordre du palmarès.

    Aucun effectif minimum (arbitrage du 31/08/2026) : un seuil masquerait des clubs en silence.
    Le repli de nom vient de `libelle_de_club`, partagé avec `Palmares._groupes` : le même club
    doit s'appeler pareil selon qu'on lit son podium ou le classement.
    """
    libelles: dict[ClubId, str] = {}
    for ligne in palmares.lignes:
        if ligne.club_id is not None:
            libelles.setdefault(ligne.club_id, libelle_de_club(ligne))
    return libelles


def _decompter(
    blocs: tuple[BlocPodium, ...], libelles: dict[ClubId, str]
) -> dict[ClubId, tuple[int, int, int]]:
    """Les médailles de chaque club — un club bredouille reste dans la table, à zéro."""
    cumuls: dict[ClubId, list[int]] = {club_id: [0, 0, 0] for club_id in libelles}
    for bloc in blocs:
        for place in bloc.places:
            club_id = place.ligne.club_id
            if club_id is not None and place.rang <= _METAUX:
                cumuls[club_id][place.rang - 1] += 1
    return {club_id: (cumul[0], cumul[1], cumul[2]) for club_id, cumul in cumuls.items()}


def _ranger(
    decomptes: dict[ClubId, tuple[int, int, int]], libelles: dict[ClubId, str]
) -> tuple[LigneClassementClubs, ...]:
    """Ordonne les clubs et leur attribue un rang **partagé à décompte égal**.

    ⚠️ Le libellé n'est **pas** un départage : il n'entre dans la clé de tri que pour rendre
    l'ordre d'affichage déterministe entre *ex æquo* (règle 9). Deux clubs à décompte identique
    partagent le rang quel que soit leur nom.
    """
    ordonnes = sorted(
        libelles,
        key=lambda club_id: (
            -decomptes[club_id][0],
            -decomptes[club_id][1],
            -decomptes[club_id][2],
            libelles[club_id],
        ),
    )

    # DETTE-029 — site de l'arithmétique « rang partagé à clé égale, avec sauts (1-2-2-4) ».
    # Le compte des sites vit au registre, pas ici : l'écrire en dur périme le commentaire au
    # prochain ajout, ce qui est le défaut même que ce marqueur sert à retrouver. La clé est un
    # triplet de médailles et non un score ; le remède attendu ne demande qu'un prédicat d'égalité.
    lignes: list[LigneClassementClubs] = []
    rang = 0
    precedent: tuple[int, int, int] | None = None
    for position, club_id in enumerate(ordonnes, start=1):
        decompte = decomptes[club_id]
        if decompte != precedent:
            rang, precedent = position, decompte
        lignes.append(
            LigneClassementClubs(
                rang=rang,
                club_id=club_id,
                club_libelle=libelles[club_id],
                medailles_or=decompte[0],
                medailles_argent=decompte[1],
                medailles_bronze=decompte[2],
            )
        )
    return tuple(lignes)
