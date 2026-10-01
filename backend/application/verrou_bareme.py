"""Le verrou du barème de duel au premier tir (E01US011, ADR-0117 §5 et §7).

Le barème n'est pas stocké avec le tir (ADR-0049 §4) : il se relit à chaque lecture, d'après le
réglage de l'étape **et** l'arme de la catégorie. Changer l'un ou l'autre après un tir relirait des
duels validés sous d'autres règles. Une seule définition de « déjà tiré », pour les deux gardes.
"""

from __future__ import annotations

from domain.deroule_etape import EtapeDerouleId
from domain.ports import DepartRepository, DerouleRepository, DuelRepository, PhaseRepository
from domain.tournoi import TournoiId


class VerrouBaremeDuel:
    def __init__(
        self,
        departs: DepartRepository,
        phases: PhaseRepository,
        deroules: DerouleRepository,
        duels: DuelRepository,
    ) -> None:
        self._departs = departs
        self._phases = phases
        self._deroules = deroules
        self._duels = duels

    def etape_tiree(self, tournoi_id: TournoiId, etape_id: EtapeDerouleId) -> bool:
        """Une phase de cette étape a-t-elle un tir, **dans n'importe quel créneau** ?

        ⚠️ Tout tir enregistré compte, vestige désynchronisé compris (ADR-0117, Conséquences).
        """
        return any(
            phase.id is not None and self._duels.numeros_enregistres(phase.id)
            for depart in self._departs.par_tournoi(tournoi_id)
            if depart.id is not None
            for phase in self._phases.par_depart(depart.id)
            if phase.etape_id == etape_id
        )

    def un_bareme_regle_est_tire(self, tournoi_id: TournoiId) -> bool:
        """Une étape **réglée** du tournoi a-t-elle un tir ? Une étape non réglée lit l'arme par
        inclusion (« poulie »), un renommage ne la détache pas : arbitrage du 01/10/2026."""
        return any(
            etape.id is not None
            and etape.bareme_duel is not None
            and self.etape_tiree(tournoi_id, etape.id)
            for etape in self._deroules.par_tournoi(tournoi_id)
        )
