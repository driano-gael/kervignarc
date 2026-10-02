"""L'**horaire prévu** d'un déroulé — calculé par départ depuis les durées d'étape (E03US010).

Rien n'est saisi en heures : l'étape porte une durée, le départ une heure de début, et le reste se
déduit du **graphe des sources** (ADR-0118). ⚠️ Pas de l'`ordre`, qui est topologique et non
chronologique (ADR-0082) : deux étapes nourries des mêmes sources se jouent en même temps.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from domain.erreurs import DureePrevueInvalide

if TYPE_CHECKING:
    from domain.deroule_etape import EtapeDeroule, EtapeDerouleId

DUREE_PREVUE_MAX = 24 * 60
"""Une journée : au-delà, ce n'est plus une étape mais une faute de frappe."""

_MINUTES_PAR_JOUR = 24 * 60


def verifier_duree_prevue(duree: int | None) -> None:
    """Le refus commun aux deux portes d'entrée de la durée, `EtapeDeroule` et `ModelePhase`."""
    if duree is not None and not 1 <= duree <= DUREE_PREVUE_MAX:
        raise DureePrevueInvalide(
            f"La durée prévue d'une étape va de 1 à {DUREE_PREVUE_MAX} minutes ; "
            f"{duree} a été demandée."
        )


@dataclass(frozen=True, order=True)
class HeurePrevue:
    """Une heure comptée **en minutes depuis minuit du jour du départ** — elle peut passer 24 h."""

    minutes: int

    @property
    def libelle(self) -> str:
        """`HH:MM` sur 24 h, le format de `Depart.horaire` ; le jour se lit sur `jours_apres`."""
        heures, minutes = divmod(self.minutes % _MINUTES_PAR_JOUR, 60)
        return f"{heures:02d}:{minutes:02d}"

    @property
    def jours_apres(self) -> int:
        """0 le jour même, 1 le lendemain (CA 5)."""
        return self.minutes // _MINUTES_PAR_JOUR

    def plus(self, duree: int) -> HeurePrevue:
        return HeurePrevue(self.minutes + duree)


@dataclass(frozen=True)
class HorairePrevu:
    """Début et fin prévus d'une étape dans un départ ; `None` = inconnu, jamais deviné (CA 3)."""

    etape_id: EtapeDerouleId
    ordre: int
    debut: HeurePrevue | None
    fin: HeurePrevue | None


def heure_du_jour(horaire: str) -> HeurePrevue:
    """Lit un `HH:MM` déjà validé par `Depart` (E02US010)."""
    heures, minutes = horaire.split(":")
    return HeurePrevue(int(heures) * 60 + int(minutes))


def horaires_prevus(heure_depart: str, etapes: Sequence[EtapeDeroule]) -> tuple[HorairePrevu, ...]:
    """Un horaire par étape persistée, dans l'ordre du déroulé (CA 2 à 4)."""
    depart = heure_du_jour(heure_depart)
    par_id = {etape.id: etape for etape in etapes if etape.id is not None}
    fins: dict[EtapeDerouleId, HeurePrevue | None] = {}
    debuts: dict[EtapeDerouleId, HeurePrevue | None] = {}
    for etape_id in par_id:
        _calculer(etape_id, par_id, depart, debuts, fins, en_cours=set())
    return tuple(
        HorairePrevu(
            etape_id=etape.id, ordre=etape.ordre, debut=debuts[etape.id], fin=fins[etape.id]
        )
        for etape in sorted(par_id.values(), key=lambda etape: etape.ordre)
        if etape.id is not None
    )


def _calculer(
    etape_id: EtapeDerouleId,
    par_id: Mapping[EtapeDerouleId, EtapeDeroule],
    depart: HeurePrevue,
    debuts: dict[EtapeDerouleId, HeurePrevue | None],
    fins: dict[EtapeDerouleId, HeurePrevue | None],
    en_cours: set[EtapeDerouleId],
) -> HeurePrevue | None:
    """Renvoie la fin prévue de l'étape, en mémorisant début et fin au passage.

    ⚠️ `en_cours` coupe un cycle de sources — le déroulé n'en admet aucun, mais une boucle infinie
    sur une donnée altérée ferait tomber l'écran au lieu d'afficher « inconnu ».
    """
    if etape_id in fins:
        return fins[etape_id]
    etape = par_id.get(etape_id)
    if etape is None or etape_id in en_cours:
        return None
    en_cours.add(etape_id)
    debut: HeurePrevue | None = depart
    if etape.sources:
        fins_amont = [
            _calculer(source.etape_source_id, par_id, depart, debuts, fins, en_cours)
            for source in etape.sources
        ]
        debut = None if None in fins_amont else max(f for f in fins_amont if f is not None)
    fin = None if debut is None or etape.duree_prevue is None else debut.plus(etape.duree_prevue)
    debuts[etape_id] = debut
    fins[etape_id] = fin
    return fin
