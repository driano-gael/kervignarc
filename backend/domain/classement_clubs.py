"""Le classement des **clubs entre eux**, au décompte de médailles (E16US017).

⚠️ **Module à part, et non une méthode de `Palmares`** : `ADR-0103` §8 qualifie ce classement de
**neuf**, par opposition au rang « dans son club » d'E16US014 qui est un regroupement. Il **lit**
les podiums décernés et ne rejoue aucun rang : les deux barèmes ne peuvent donc pas diverger.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.club import ClubId
from domain.palmares import BlocPodium, Palmares
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
    portees_comptees: tuple[PorteePodium, ...]
    """Les portées du réglage qui alimentent le décompte — **vide** = aucune base de comparaison.

    ⚠️ Dérivé du **réglage**, pas des blocs rendus : sans quoi un tournoi qui n'a encore décerné
    aucune médaille se dirait « sans base », ce qui est faux et ne se corrigerait jamais à l'écran.
    """

    provisoire: bool = False
    """Un podium compté attend-il encore ? On ne promet pas un trophée pendant que ça se tire."""


def classer_clubs(palmares: Palmares, reglage: ReglagePodiums) -> ClassementClubs:
    """Classe les clubs à l'or, puis à l'argent, puis au bronze (ordre olympique).

    Le décompte porte sur les médailles que le tournoi **décerne** : un archer médaillé dans deux
    portées cumulées en rapporte deux à son club (arbitrage du 04/09/2026). ⚠️ Un archer **sans
    club** n'en rapporte à personne et ne crée aucune ligne — « club inconnu » est une anomalie à
    signaler, pas un club de rattachement (ADR-0014).
    """
    portees = tuple(portee for portee in reglage.portees_actives() if portee in PORTEES_INTER_CLUBS)
    if not portees:
        return ClassementClubs(lignes=(), portees_comptees=())

    blocs = tuple(bloc for bloc in palmares.podiums(reglage) if bloc.portee in PORTEES_INTER_CLUBS)
    libelles = _libelles(palmares)
    decomptes = _decompter(blocs, libelles)
    return ClassementClubs(
        lignes=_ranger(decomptes, libelles),
        portees_comptees=portees,
        provisoire=any(bloc.en_attente for bloc in blocs),
    )


def _libelles(palmares: Palmares) -> dict[ClubId, str]:
    """Tous les clubs **présents au tournoi**, dans l'ordre du palmarès.

    Aucun effectif minimum (arbitrage du 31/08/2026) : un seuil masquerait des clubs en silence.
    ⚠️ Le repli doit rester **identique** à celui de `Palmares._groupes`, sinon le même club
    s'appellerait autrement selon qu'on lit son podium ou son rang.
    """
    libelles: dict[ClubId, str] = {}
    for ligne in palmares.lignes:
        if ligne.club_id is not None:
            libelles.setdefault(ligne.club_id, ligne.club_libelle or f"Club {ligne.club_id}")
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

    # DETTE-029 — 5ᵉ site de l'arithmétique « rang partagé à clé égale, avec sauts (1-2-2-4) »
    # (avec `classement._ranger`, `poule`, `suisse`, `palmares._numeroter`). La clé est ici un
    # triplet de médailles et non un score : le remède attendu (`attribuer_rangs(ordonnes,
    # meme_rang)`) l'accommode, il ne demande qu'un prédicat d'égalité.
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
