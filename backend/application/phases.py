"""Service applicatif Phases — compose et fait vivre la séquence de phases d'un tournoi (E05US001).

Use cases : lister, ajouter, éditer (type/source/effectif), réordonner, supprimer, et faire
avancer le **cycle de vie** de chaque phase (`a_venir → en_cours ⇄ en_pause → terminee`).

Répartition des responsabilités (ADR-0045, ADR-0007) :

- **La cohérence de la séquence** (ordres contigus, sources bien formées : source vide / rangs
  inexistants / effectif incompatible) est une **règle du domaine** : le service assemble les phases
  en `SequencePhases`, dont la **construction** rejette une séquence incohérente (→ `DomainError`,
  traduite en 422). Le service n'en réimplémente rien.
- **Les conflits d'état** (transition de statut illégale, suppression d'une phase qui en alimente
  une autre, existence d'une phase dans *ce* tournoi) sont arbitrés **ici** (`ApplicationError`,
  409/404), comme `ServiceTournois` pour le cycle de vie du tournoi.

Le service ignore HTTP, SQL et la file d'écriture (sérialisation assurée en amont, côté API) : il
reste synchrone et pur d'infrastructure.

**Le peuplement (source) est une amorce minimale** (DETTE-015) : une source unique « par rangs ».
Le réordonnancement et la suppression **remappent** les références de source (portées par l'`ordre`
de la phase source) pour qu'elles suivent la phase qu'elles désignaient — un artefact de ce modèle
provisoire qu'E05US010 simplifiera en référençant autrement.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from application.erreurs import (
    PhaseIntrouvable,
    PhaseQualificationNonSupprimable,
    PhaseSourceReferencee,
    ReordonnancementPhasesInvalide,
    TournoiIntrouvable,
    TransitionStatutInvalide,
)
from domain.phase import (
    Phase,
    PhaseId,
    SequencePhases,
    SourcePhase,
    StatutPhase,
    TypePhase,
)
from domain.ports import PhaseRepository, TournoiRepository
from domain.tournoi import TournoiId


class ServicePhases:
    """Cas d'usage de la séquence de phases : composer, éditer, ordonner, cycle de vie."""

    def __init__(self, tournois: TournoiRepository, phases: PhaseRepository) -> None:
        self._tournois = tournois
        self._phases = phases

    # --- Lecture -------------------------------------------------------------------------------

    def lister(self, tournoi_id: TournoiId) -> list[Phase]:
        """Renvoie les phases du tournoi, ordonnées (liste éventuellement vide).

        Lève `TournoiIntrouvable` si le tournoi n'existe pas.
        """
        self._exiger_tournoi(tournoi_id)
        return self._phases.par_tournoi(tournoi_id)

    # --- Composition & édition -----------------------------------------------------------------

    def ajouter(
        self,
        tournoi_id: TournoiId,
        type: TypePhase,
        source: SourcePhase | None = None,
        effectif: int | None = None,
    ) -> Phase:
        """Ajoute une phase **en fin de séquence** (ordre = N+1) et la persiste.

        Lève `TournoiIntrouvable` si le tournoi n'existe pas, une `DomainError` (→ 422) si la phase
        ou la séquence obtenue est incohérente (ex. barème manquant pour une qualification, source
        mal formée). Rien n'est persisté si la validation échoue.
        """
        self._exiger_tournoi(tournoi_id)
        existantes = self._phases.par_tournoi(tournoi_id)
        nouvelle = Phase.creer(
            tournoi_id, ordre=len(existantes) + 1, type=type, source=source, effectif=effectif
        )
        # Valide la séquence complète (la nouvelle incluse) avant d'écrire.
        SequencePhases(phases=(*existantes, nouvelle))
        return self._phases.ajouter(nouvelle)

    def modifier(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        type: TypePhase,
        source: SourcePhase | None,
        effectif: int | None,
    ) -> Phase:
        """Édite le type, la source et l'effectif d'une phase (édition **totale** de sa config de
        séquence — `ordre`, `statut`, barème/grain sont préservés).

        Lève `PhaseIntrouvable` si la phase n'est pas dans ce tournoi, une `DomainError` (→ 422) si
        le résultat est incohérent (ex. retyper en `qualification` sans barème, source hors bornes).
        """
        phase = self._exiger_phase(tournoi_id, phase_id)
        modifiee = replace(phase, type=type, source=source, effectif=effectif)
        autres = [p for p in self._phases.par_tournoi(tournoi_id) if p.id != phase_id]
        SequencePhases(phases=(*autres, modifiee))
        return self._phases.enregistrer(modifiee)

    def reordonner(self, tournoi_id: TournoiId, phases_ordonnees: list[PhaseId]) -> list[Phase]:
        """Réordonne **l'ensemble** des phases du tournoi selon la liste d'identifiants fournie.

        Chaque phase reçoit un nouvel `ordre` (position dans la liste) ; les références de source
        sont **remappées** pour suivre la phase qu'elles désignaient. Lève
        `ReordonnancementPhasesInvalide` (→ 409) si la liste ne recouvre pas exactement les phases
        du tournoi, et une `DomainError` (→ 422) si l'ordre demandé rend la séquence incohérente
        (ex. une source se retrouve **après** la phase qu'elle alimente).
        """
        self._exiger_tournoi(tournoi_id)
        actuelles = self._phases.par_tournoi(tournoi_id)
        if not actuelles and not phases_ordonnees:
            return []
        par_id: dict[int, Phase] = {}
        for phase in actuelles:
            assert phase.id is not None, "Une phase listée est persistée."
            par_id[phase.id] = phase
        if sorted(phases_ordonnees) != sorted(par_id):
            raise ReordonnancementPhasesInvalide(
                "Réordonner exige la liste complète des phases du tournoi, chacune une seule fois."
            )
        # Ancien ordre → nouvel ordre (position dans la liste, 1-indexée).
        ancien_vers_nouveau = {
            par_id[phase_id].ordre: rang for rang, phase_id in enumerate(phases_ordonnees, start=1)
        }
        reordonnees = [
            self._remapper(
                par_id[phase_id], nouvel_ordre=rang, ancien_vers_nouveau=ancien_vers_nouveau
            )
            for rang, phase_id in enumerate(phases_ordonnees, start=1)
        ]
        SequencePhases(phases=tuple(reordonnees))  # valide l'ordre demandé
        return [self._phases.enregistrer(phase) for phase in reordonnees]

    def supprimer(self, tournoi_id: TournoiId, phase_id: PhaseId) -> None:
        """Retire une phase de la séquence et **recompacte** les ordres (1..N sans trou).

        Lève `PhaseIntrouvable` si la phase n'est pas dans ce tournoi, `PhaseSourceReferencee`
        (→ 409) si une **autre** phase tire d'elle ses participants (il faut d'abord la réaffecter).
        Les références de source des phases restantes sont remappées après recompactage.
        """
        cible = self._exiger_phase(tournoi_id, phase_id)
        if cible.type is TypePhase.QUALIFICATION:
            raise PhaseQualificationNonSupprimable(
                "La phase de qualification se gère via le barème ; elle ne se supprime pas ici."
            )
        restantes = [p for p in self._phases.par_tournoi(tournoi_id) if p.id != phase_id]
        if any(p.source is not None and p.source.ordre_source == cible.ordre for p in restantes):
            raise PhaseSourceReferencee(
                "Cette phase alimente une autre phase de la séquence ; réaffectez-la d'abord."
            )
        # Recompactage : les ordres au-delà de la phase retirée descendent d'un cran.
        ancien_vers_nouveau = {
            p.ordre: (p.ordre if p.ordre < cible.ordre else p.ordre - 1) for p in restantes
        }
        recompactees = [
            self._remapper(
                p,
                nouvel_ordre=ancien_vers_nouveau[p.ordre],
                ancien_vers_nouveau=ancien_vers_nouveau,
            )
            for p in restantes
        ]
        SequencePhases(phases=tuple(recompactees))
        for phase in recompactees:
            self._phases.enregistrer(phase)
        assert cible.id is not None, "Une phase consultée est persistée."
        self._phases.supprimer(cible.id)

    # --- Cycle de vie (transitions gardées, patron ServiceTournois) ----------------------------

    def demarrer(self, tournoi_id: TournoiId, phase_id: PhaseId) -> Phase:
        """`a_venir → en_cours`. Lève `TransitionStatutInvalide` (→ 409) hors de `a_venir`."""
        return self._transition(
            tournoi_id, phase_id, StatutPhase.A_VENIR, Phase.demarrer, "à venir"
        )

    def mettre_en_pause(self, tournoi_id: TournoiId, phase_id: PhaseId) -> Phase:
        """`en_cours → en_pause`. Lève `TransitionStatutInvalide` (→ 409) hors de `en_cours`."""
        return self._transition(
            tournoi_id, phase_id, StatutPhase.EN_COURS, Phase.mettre_en_pause, "en cours"
        )

    def reprendre(self, tournoi_id: TournoiId, phase_id: PhaseId) -> Phase:
        """`en_pause → en_cours`. Lève `TransitionStatutInvalide` (→ 409) hors de `en_pause`."""
        return self._transition(
            tournoi_id, phase_id, StatutPhase.EN_PAUSE, Phase.reprendre, "en pause"
        )

    def terminer(self, tournoi_id: TournoiId, phase_id: PhaseId) -> Phase:
        """`en_cours → terminee`. Lève `TransitionStatutInvalide` (→ 409) hors de `en_cours`."""
        return self._transition(
            tournoi_id, phase_id, StatutPhase.EN_COURS, Phase.terminer, "en cours"
        )

    # --- Internes ------------------------------------------------------------------------------

    def _transition(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        attendu: StatutPhase,
        muter: Callable[[Phase], Phase],
        libelle_attendu: str,
    ) -> Phase:
        phase = self._exiger_phase(tournoi_id, phase_id)
        if phase.statut is not attendu:
            raise TransitionStatutInvalide(
                f"Cette transition n'est possible que sur une phase {libelle_attendu}."
            )
        return self._phases.enregistrer(muter(phase))

    @staticmethod
    def _remapper(phase: Phase, *, nouvel_ordre: int, ancien_vers_nouveau: dict[int, int]) -> Phase:
        """Renvoie la phase à son nouvel ordre, sa source remappée sur le nouvel ordre de la phase
        qu'elle désignait (les ancres de source sont des `ordre`, non des id — DETTE-015)."""
        deplacee = phase.avec_ordre(nouvel_ordre)
        if phase.source is None:
            return deplacee
        nouvelle_source = replace(
            phase.source, ordre_source=ancien_vers_nouveau[phase.source.ordre_source]
        )
        return deplacee.avec_source(nouvelle_source)

    def _exiger_tournoi(self, tournoi_id: TournoiId) -> None:
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")

    def _exiger_phase(self, tournoi_id: TournoiId, phase_id: PhaseId) -> Phase:
        phase = self._phases.par_id(phase_id)
        if phase is None or phase.tournoi_id != tournoi_id:
            raise PhaseIntrouvable(
                f"Aucune phase d'identifiant {phase_id} dans le tournoi {tournoi_id}."
            )
        return phase
