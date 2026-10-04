"""Le verrou du barème de duel au premier tir (E01US011, ADR-0117 §5 et §7).

Le barème n'est pas stocké avec le tir (ADR-0049 §4) : il se relit à chaque lecture, d'après le
réglage de l'étape **et** l'arme de la catégorie. Changer l'un ou l'autre après un tir relirait des
duels validés sous d'autres règles. Une seule définition de « déjà tiré », pour les deux gardes.
"""

from __future__ import annotations

from collections.abc import Iterable

from domain.archer import ArcherId
from domain.depart import DepartId
from domain.deroule_etape import EtapeDeroule, EtapeDerouleId
from domain.duel import BaremeDuel, ResolveurBaremeDuel
from domain.equipe import TypeEquipe
from domain.ports import (
    DepartRepository,
    DerouleRepository,
    DuelRepository,
    InscriptionRepository,
    PhaseRepository,
)
from domain.tournoi import TournoiId


class VerrouBaremeDuel:
    def __init__(
        self,
        departs: DepartRepository,
        phases: PhaseRepository,
        deroules: DerouleRepository,
        duels: DuelRepository,
        resolveur: ResolveurBaremeDuel,
    ) -> None:
        self._departs = departs
        self._phases = phases
        self._deroules = deroules
        self._duels = duels
        # ⚠️ Le **même** défaut que celui de `ServiceSaisieDuels` (composition root) : comparer des
        # barèmes avec un autre résolveur que celui qui relira les duels ne garderait rien.
        self._resolveur = resolveur

    def etape_tiree(self, tournoi_id: TournoiId, etape_id: EtapeDerouleId) -> bool:
        """Une phase de cette étape a-t-elle un tir, **dans n'importe quel créneau** ?

        ⚠️ Tout tir enregistré compte, vestige désynchronisé compris (ADR-0117, Conséquences).
        """
        departs = {d.id for d in self._departs.par_tournoi(tournoi_id) if d.id is not None}
        return self.etape_tiree_dans(etape_id, departs)

    def etape_tiree_dans(self, etape_id: EtapeDerouleId, departs: Iterable[DepartId]) -> bool:
        """Une phase de cette étape a-t-elle un tir dans l'un de ces créneaux (E13US004) ?"""
        return any(
            phase.id is not None and self._duels.numeros_enregistres(phase.id)
            for depart_id in departs
            for phase in self._phases.par_depart(depart_id)
            if phase.etape_id == etape_id
        )

    def arme_figee(self, tournoi_id: TournoiId, ancienne: str | None, nouvelle: str | None) -> bool:
        """Passer de `ancienne` à `nouvelle` change-t-il le barème d'une étape déjà tirée ?

        Réglée ou non : sans réglage, le défaut reconnaît les poulies au libellé, et franchir cette
        frontière relit aussi les duels (arbitrage du 01/10/2026, 2ᵉ passe de revue).
        """
        return any(
            etape.id is not None
            and self._bareme(etape, ancienne) != self._bareme(etape, nouvelle)
            and self.etape_tiree(tournoi_id, etape.id)
            for etape in self._deroules.par_tournoi(tournoi_id)
        )

    def _bareme(self, etape: EtapeDeroule, arme: str | None) -> BaremeDuel:
        if etape.bareme_duel is not None:
            return etape.bareme_duel.pour(arme)
        return self._resolveur.bareme_pour(arme)


class VerrouCompositionEquipes:
    """Une équipe est-elle en jeu : un de ses membres tire-t-il un départ dont le tableau d'équipes
    de ce type a un tir (E13US004, ADR-0120 §7) ?

    ⚠️ **Par départ** (ADR-0075) : un tableau tiré le samedi ne fige pas les équipes du dimanche,
    qu'il n'engage pas.
    """

    def __init__(
        self,
        verrou: VerrouBaremeDuel,
        deroules: DerouleRepository,
        inscriptions: InscriptionRepository,
    ) -> None:
        self._verrou = verrou
        self._deroules = deroules
        self._inscriptions = inscriptions

    def en_jeu(self, tournoi_id: TournoiId, type: TypeEquipe, archers: Iterable[ArcherId]) -> bool:
        departs = {i.depart_id for a in archers for i in self._inscriptions.par_archer(a)}
        return bool(departs) and any(
            etape.id is not None
            and etape.equipes is type
            and self._verrou.etape_tiree_dans(etape.id, departs)
            for etape in self._deroules.par_tournoi(tournoi_id)
        )
