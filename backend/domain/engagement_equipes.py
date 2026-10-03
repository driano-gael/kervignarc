"""Engagement des équipes dans une phase — qui entre, qui est écarté, dans quel ordre (E13US004).

⚠️ **Une dérivation, pas un geste** (ADR-0120 §2) : recalculée à chaque reconstruction du
tableau, comme l'ensemencement individuel. « Refusée à l'engagement » prend donc la forme d'une
équipe **écartée avec ses motifs**, jamais d'une écriture refusée.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from domain.archer import ArcherId
from domain.classement import LigneClassement, StatutClassement
from domain.club import cle_nom
from domain.equipe import (
    EcartComposition,
    Equipe,
    ProfilMembre,
    TypeEquipe,
    ecarts_de_composition,
)

_PROFIL_INCONNU = ProfilMembre(arme=None, sexe=None)


@dataclass(frozen=True)
class EquipeEngagee:
    """Une équipe qui entre au tableau, au rang que lui donne la somme de ses qualifications."""

    equipe: Equipe
    rang: int
    total: int
    nb_dix: int
    nb_neuf: int


@dataclass(frozen=True)
class EquipeEcartee:
    """Une équipe qui n'entre pas, et pourquoi — les deux motifs peuvent se cumuler (CA 2)."""

    equipe: Equipe
    ecarts: tuple[EcartComposition, ...]
    membres_hors_course: tuple[ArcherId, ...]
    """Membres sans ligne **en lice** au classement du départ : inscrits ailleurs, ou forfaits."""


@dataclass(frozen=True)
class Engagement:
    engagees: tuple[EquipeEngagee, ...]
    ecartees: tuple[EquipeEcartee, ...]


def engager_les_equipes(
    type: TypeEquipe,
    equipes: Sequence[Equipe],
    profils: Mapping[ArcherId, ProfilMembre],
    lignes: Mapping[ArcherId, LigneClassement],
) -> Engagement:
    """Les équipes de `type`, engagées (rangées) ou écartées (par nom), au vu du classement.

    `profils` donne l'arme et le sexe de chaque membre ; un membre absent est **inconnu**, jamais
    deviné. `lignes` est le classement de qualification du départ de la phase, par archer.
    """
    engagees: list[EquipeEngagee] = []
    ecartees: list[EquipeEcartee] = []
    for equipe in equipes:
        if equipe.type is not type:
            continue
        ecarts = ecarts_de_composition(
            equipe, [profils.get(membre, _PROFIL_INCONNU) for membre in equipe.membres]
        )
        hors_course = tuple(m for m in equipe.membres if not _en_lice(lignes.get(m)))
        if ecarts or hors_course:
            ecartees.append(EquipeEcartee(equipe, ecarts, hors_course))
            continue
        membres = [lignes[m] for m in equipe.membres]
        engagees.append(
            EquipeEngagee(
                equipe=equipe,
                rang=0,
                total=sum(ligne.total for ligne in membres),
                nb_dix=sum(ligne.nb_dix for ligne in membres),
                nb_neuf=sum(ligne.nb_neuf for ligne in membres),
            )
        )
    # DETTE-121 : à égalité complète, l'ordre alphabétique tranche faute de barrage d'équipes.
    engagees.sort(key=lambda e: (-e.total, -e.nb_dix, -e.nb_neuf, *_cle(e.equipe)))
    return Engagement(
        engagees=tuple(
            EquipeEngagee(e.equipe, rang, e.total, e.nb_dix, e.nb_neuf)
            for rang, e in enumerate(engagees, start=1)
        ),
        ecartees=tuple(sorted(ecartees, key=lambda e: _cle(e.equipe))),
    )


def _en_lice(ligne: LigneClassement | None) -> bool:
    return ligne is not None and ligne.statut is StatutClassement.EN_LICE


def _cle(equipe: Equipe) -> tuple[str, int]:
    # DETTE-006 — `cle_nom` ; l'identifiant départage deux homonymes, pour un ordre total.
    return cle_nom(equipe.nom), equipe.id or 0
