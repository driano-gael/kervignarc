"""Le verrou du barème de duel au premier tir (E01US011, ADR-0117 §5 et §7).

Le barème n'est pas stocké avec le tir (ADR-0049 §4) : il se relit à chaque lecture, d'après le
réglage de l'étape **et** l'arme de la catégorie. Changer l'un ou l'autre après un tir relirait des
duels validés sous d'autres règles. Une seule définition de « déjà tiré », pour les deux gardes.
"""

from __future__ import annotations

from domain.deroule_etape import EtapeDeroule, EtapeDerouleId
from domain.duel import BaremeDuel, ResolveurBaremeDuel
from domain.ports import DepartRepository, DerouleRepository, DuelRepository, PhaseRepository
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
        return any(
            phase.id is not None and self._duels.numeros_enregistres(phase.id)
            for depart in self._departs.par_tournoi(tournoi_id)
            if depart.id is not None
            for phase in self._phases.par_depart(depart.id)
            if phase.etape_id == etape_id
        )

    def arme_figee(self, tournoi_id: TournoiId, ancienne: str | None, nouvelle: str | None) -> bool:
        """Passer de `ancienne` à `nouvelle` change-t-il le barème d'une étape déjà tirée ?

        Réglée ou non : sans réglage, le défaut reconnaît les poulies au libellé, et franchir cette
        frontière relit aussi les duels (arbitrage du 01/10/2026, 2ᵉ passe de revue).
        """
        return any(
            etape.id is not None
            and self._baremes(etape, ancienne) != self._baremes(etape, nouvelle)
            and self.etape_tiree(tournoi_id, etape.id)
            for etape in self._deroules.par_tournoi(tournoi_id)
        )

    def _baremes(self, etape: EtapeDeroule, arme: str | None) -> tuple[BaremeDuel, ...]:
        """Premiers **et** derniers tours (E01US027) : que l'un change, et des duels se relisent."""
        if etape.bareme_duel is not None:
            return etape.bareme_duel.baremes_pour(arme)
        return (self._resolveur.bareme_pour(arme),)
