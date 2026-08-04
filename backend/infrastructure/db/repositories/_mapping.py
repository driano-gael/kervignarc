"""Traductions ORM → domaine partagées par **plusieurs** thèmes d'adapters.

Volontairement minuscule : sur les 45 fonctions de mapping de l'ancien module, **une seule**
est utilisée par deux thèmes. Les 44 autres vivent dans le thème qui les emploie — c'est là
qu'on les cherche. Une fonction qui atterrirait ici sans être réellement partagée annulerait
le bénéfice du découpage."""

from __future__ import annotations

import json
from collections.abc import Sequence

from domain.barrage import (
    BarrageDePlaces,
    PorteeBarrage,
    TirBarrage,
)
from domain.participant import Participant
from infrastructure.db.models import (
    BarrageORM,
    BarrageTirORM,
)


def _vers_barrage(ligne: BarrageORM, tirs: Sequence[BarrageTirORM]) -> BarrageDePlaces:
    """Reconstruit l'agrégat depuis sa ligne et ses tirs, **groupés par manche**.

    Les manches sont rendues **triées par numéro** : c'est leur ordre qui porte le sens (la manche 1
    acquiert un ordre que les suivantes ne peuvent pas défaire), et le moteur les consomme dans
    cette séquence. Un trou de numérotation est sans effet — seul l'ordre relatif compte.
    """
    participants = tuple(
        Participant.individuel(int(ref)) for ref in json.loads(ligne.participants_json)
    )
    par_manche: dict[int, list[TirBarrage]] = {}
    for tir in tirs:
        par_manche.setdefault(tir.manche, []).append(
            TirBarrage(
                participant=Participant.individuel(tir.archer_id),
                score=tir.score,
                distance_au_centre=tir.distance_au_centre,
            )
        )
    return BarrageDePlaces(
        tournoi_id=ligne.tournoi_id,
        portee=PorteeBarrage(ligne.portee),
        participants=participants,
        cree_le=ligne.cree_le,
        manches=tuple(tuple(par_manche[numero]) for numero in sorted(par_manche)),
        rang_dispute=ligne.rang_dispute,
        phase_id=ligne.phase_id,
        reference=ligne.reference,
        clos=ligne.clos,
        id=ligne.id,
    )
