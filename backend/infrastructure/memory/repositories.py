"""Adapters in-memory des ports du moteur (E15US002, ADR-0054).

Onze magasins `dict` conformes (structurellement, `Protocol`) aux ports du chemin
qualif → duels → classement : `Tournoi`, `Archer`, `Categorie`, `Blason`, `GabaritSalle`,
`Inscription`, `Phase`, `Serie`, `Forfait`, `Duel`, `PlacementTableau`. Ce sont des **adapters de
production** (règle 2) : `infrastructure/`, dépendances **stdlib + domaine** seulement (le domaine
reste pur, règle 1).

**Pourquoi un jeu distinct des `Faux*Repository` des tests ?** Le code de production ne peut pas
importer `tests/` (dépendance interdite) ; l'inverse (promouvoir les doublures de test) serait un
refactor transverse traité en US dédiée, pas ici (ADR-0054 §2, règle 12). La duplication assumée est
tenue honnête par les **tests de conformité de port** (`test_conformite_ports_memoire.py`).

**Hydratation sans perte d'identifiant.** L'hydratation (SQL → in-memory) **recopie** des entités
qui portent **déjà** leur `id` ; l'intégrité référentielle (`archer.categorie_id`, `phase.source`)
en dépend. Les méthodes d'ajout **préservent** donc l'`id` fourni et n'en attribuent un (auto-inc.)
que s'il est `None` — ce dernier cas sert le bot d'E15US003 qui *crée* des entités simulées.

**No-op d'audit.** Les écritures « avec trace » (`Serie.enregistrer_avec_trace`,
`Forfait.declarer_avec_trace`, `Inscription.definir_paye_avec_trace`) **ignorent** l'audit :
en simulation, rien n'est consigné (ADR-0054). C'est le pendant en mémoire du couplage infra→infra
`consigner_dans` des adapters SQL, ici sans objet.
"""

from __future__ import annotations

import dataclasses
import datetime
from collections.abc import Sequence

from domain.archer import Archer, ArcherId
from domain.blason import Blason, BlasonId
from domain.categorie import Categorie, CategorieId
from domain.club import ClubId
from domain.duel import BaremeDuel, Duel
from domain.entree_audit import EntreeAudit
from domain.forfait import Forfait
from domain.gabarit_salle import GabaritSalle, GabaritSalleId
from domain.inscription import Inscription, InscriptionId
from domain.phase import Phase, PhaseId, TypePhase
from domain.placement import Affectation
from domain.serie import Serie
from domain.tournoi import Tournoi, TournoiId


class _Sequence:
    """Attribue les identifiants auto-incrémentés, en **préservant** un `id` déjà présent.

    Un `id` fourni (hydratation) est conservé et fait avancer la séquence au-delà ; un `id` absent
    (`None`, création par le bot E15US003) reçoit le prochain entier. Ainsi un même magasin sert
    l'hydratation (loss-less) et la création sans collision d'identifiants.
    """

    def __init__(self) -> None:
        self._sequence = 0

    def _identifiant(self, actuel: int | None) -> int:
        if actuel is not None:
            self._sequence = max(self._sequence, actuel)
            return actuel
        self._sequence += 1
        return self._sequence


class InMemoryTournoiRepository(_Sequence):
    """Port `TournoiRepository` en mémoire."""

    def __init__(self) -> None:
        super().__init__()
        self._items: dict[int, Tournoi] = {}

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        identifiant = self._identifiant(tournoi.id)
        persiste = dataclasses.replace(tournoi, id=identifiant)
        self._items[identifiant] = persiste
        return persiste

    def par_id(self, tournoi_id: TournoiId) -> Tournoi | None:
        return self._items.get(tournoi_id)

    def lister(self) -> list[Tournoi]:
        return list(self._items.values())

    def enregistrer(self, tournoi: Tournoi) -> Tournoi:
        assert tournoi.id is not None
        self._items[tournoi.id] = tournoi
        return tournoi

    def supprimer(self, tournoi_id: TournoiId) -> None:
        self._items.pop(tournoi_id, None)


class InMemoryArcherRepository(_Sequence):
    """Port `ArcherRepository` en mémoire."""

    def __init__(self) -> None:
        super().__init__()
        self._items: dict[int, Archer] = {}

    def ajouter(self, archer: Archer) -> Archer:
        identifiant = self._identifiant(archer.id)
        persiste = dataclasses.replace(archer, id=identifiant)
        self._items[identifiant] = persiste
        return persiste

    def par_id(self, archer_id: ArcherId) -> Archer | None:
        return self._items.get(archer_id)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Archer]:
        return [a for a in self._items.values() if a.tournoi_id == tournoi_id]

    def par_club(self, club_id: ClubId) -> list[Archer]:
        return [a for a in self._items.values() if a.club_id == club_id]

    def enregistrer(self, archer: Archer) -> Archer:
        assert archer.id is not None
        self._items[archer.id] = archer
        return archer

    def supprimer(self, archer_id: ArcherId) -> None:
        self._items.pop(archer_id, None)

    def fusionner(self, gagnant_id: ArcherId, perdant_id: ArcherId) -> None:
        self._items.pop(perdant_id, None)


class InMemoryCategorieRepository(_Sequence):
    """Port `CategorieRepository` en mémoire."""

    def __init__(self) -> None:
        super().__init__()
        self._items: dict[int, Categorie] = {}

    def ajouter(self, categorie: Categorie) -> Categorie:
        identifiant = self._identifiant(categorie.id)
        persiste = dataclasses.replace(categorie, id=identifiant)
        self._items[identifiant] = persiste
        return persiste

    def par_id(self, categorie_id: CategorieId) -> Categorie | None:
        return self._items.get(categorie_id)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Categorie]:
        return [c for c in self._items.values() if c.tournoi_id == tournoi_id]

    def par_blason(self, blason_id: BlasonId) -> list[Categorie]:
        return [c for c in self._items.values() if c.blason_id == blason_id]

    def enregistrer(self, categorie: Categorie) -> Categorie:
        assert categorie.id is not None
        self._items[categorie.id] = categorie
        return categorie

    def supprimer(self, categorie_id: CategorieId) -> None:
        self._items.pop(categorie_id, None)


class InMemoryBlasonRepository(_Sequence):
    """Port `BlasonRepository` en mémoire."""

    def __init__(self) -> None:
        super().__init__()
        self._items: dict[int, Blason] = {}

    def ajouter(self, blason: Blason) -> Blason:
        identifiant = self._identifiant(blason.id)
        persiste = dataclasses.replace(blason, id=identifiant)
        self._items[identifiant] = persiste
        return persiste

    def par_id(self, blason_id: BlasonId) -> Blason | None:
        return self._items.get(blason_id)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Blason]:
        return [b for b in self._items.values() if b.tournoi_id == tournoi_id]

    def enregistrer(self, blason: Blason) -> Blason:
        assert blason.id is not None
        self._items[blason.id] = blason
        return blason

    def supprimer(self, blason_id: BlasonId) -> None:
        self._items.pop(blason_id, None)


class InMemoryGabaritSalleRepository(_Sequence):
    """Port `GabaritSalleRepository` en mémoire.

    `lister` renvoie les **modèles** (`tournoi_id is None`), `par_tournoi` l'**instance** d'un
    tournoi (au plus une), comme l'adapter SQL.
    """

    def __init__(self) -> None:
        super().__init__()
        self._items: dict[int, GabaritSalle] = {}

    def ajouter(self, gabarit: GabaritSalle) -> GabaritSalle:
        identifiant = self._identifiant(gabarit.id)
        persiste = dataclasses.replace(gabarit, id=identifiant)
        self._items[identifiant] = persiste
        return persiste

    def par_id(self, gabarit_id: GabaritSalleId) -> GabaritSalle | None:
        return self._items.get(gabarit_id)

    def lister(self) -> list[GabaritSalle]:
        return [g for g in self._items.values() if g.tournoi_id is None]

    def par_tournoi(self, tournoi_id: TournoiId) -> GabaritSalle | None:
        for gabarit in self._items.values():
            if gabarit.tournoi_id == tournoi_id:
                return gabarit
        return None

    def enregistrer(self, gabarit: GabaritSalle) -> GabaritSalle:
        assert gabarit.id is not None
        self._items[gabarit.id] = gabarit
        return gabarit

    def supprimer(self, gabarit_id: GabaritSalleId) -> None:
        self._items.pop(gabarit_id, None)


class InMemoryInscriptionRepository(_Sequence):
    """Port `InscriptionRepository` en mémoire (`definir_paye_avec_trace` = no-op d'audit)."""

    def __init__(self) -> None:
        super().__init__()
        self._items: dict[int, Inscription] = {}

    def ajouter(self, inscription: Inscription) -> Inscription:
        identifiant = self._identifiant(inscription.id)
        persiste = dataclasses.replace(inscription, id=identifiant)
        self._items[identifiant] = persiste
        return persiste

    def par_id(self, inscription_id: InscriptionId) -> Inscription | None:
        return self._items.get(inscription_id)

    def par_archer(self, archer_id: ArcherId) -> list[Inscription]:
        return [i for i in self._items.values() if i.archer_id == archer_id]

    def par_depart(self, depart_id: int) -> list[Inscription]:
        return [i for i in self._items.values() if i.depart_id == depart_id]

    def par_archer_et_depart(self, archer_id: ArcherId, depart_id: int) -> Inscription | None:
        for inscription in self._items.values():
            if inscription.archer_id == archer_id and inscription.depart_id == depart_id:
                return inscription
        return None

    def enregistrer(self, inscription: Inscription) -> Inscription:
        assert inscription.id is not None
        self._items[inscription.id] = inscription
        return inscription

    def definir_paye_avec_trace(
        self, inscription_ids: Sequence[InscriptionId], paye: bool, entree: EntreeAudit
    ) -> list[Inscription]:
        maj: list[Inscription] = []
        for inscription_id in inscription_ids:
            inscription = dataclasses.replace(self._items[inscription_id], paye=paye)
            self._items[inscription_id] = inscription
            maj.append(inscription)
        return maj

    def supprimer(self, inscription_id: InscriptionId) -> None:
        self._items.pop(inscription_id, None)


class InMemoryPhaseRepository(_Sequence):
    """Port `PhaseRepository` en mémoire (`par_tournoi` **ordonné par `ordre`**, comme SQL)."""

    def __init__(self) -> None:
        super().__init__()
        self._items: dict[int, Phase] = {}

    def ajouter(self, phase: Phase) -> Phase:
        identifiant = self._identifiant(phase.id)
        persiste = dataclasses.replace(phase, id=identifiant)
        self._items[identifiant] = persiste
        return persiste

    def par_id(self, phase_id: PhaseId) -> Phase | None:
        return self._items.get(phase_id)

    def par_tournoi_et_type(self, tournoi_id: TournoiId, type_phase: TypePhase) -> Phase | None:
        for phase in self._items.values():
            if phase.tournoi_id == tournoi_id and phase.type == type_phase:
                return phase
        return None

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Phase]:
        phases = [p for p in self._items.values() if p.tournoi_id == tournoi_id]
        return sorted(phases, key=lambda p: p.ordre)

    def enregistrer(self, phase: Phase) -> Phase:
        assert phase.id is not None
        self._items[phase.id] = phase
        return phase

    def supprimer(self, phase_id: PhaseId) -> None:
        self._items.pop(phase_id, None)


class InMemorySerieRepository(_Sequence):
    """Port `SerieRepository` en mémoire (`enregistrer_avec_trace` = no-op d'audit).

    `horodatages` renvoie `{}` : le `created_at` d'une volée est une **métadonnée de persistance**
    (hors agrégat) que la simulation ne suit pas — sans effet sur le classement, qui l'ignore.
    """

    def __init__(self) -> None:
        super().__init__()
        self._items: dict[int, Serie] = {}

    def par_archer(self, tournoi_id: TournoiId, archer_id: ArcherId) -> Serie | None:
        for serie in self._items.values():
            if serie.tournoi_id == tournoi_id and serie.archer_id == archer_id:
                return serie
        return None

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Serie]:
        return [s for s in self._items.values() if s.tournoi_id == tournoi_id]

    def horodatages(
        self, tournoi_id: TournoiId, archer_id: ArcherId
    ) -> dict[int, datetime.datetime]:
        return {}

    def enregistrer(self, serie: Serie) -> Serie:
        identifiant = self._identifiant(serie.id)
        persiste = dataclasses.replace(serie, id=identifiant)
        self._items[identifiant] = persiste
        return persiste

    def enregistrer_avec_trace(self, serie: Serie, entree: EntreeAudit) -> Serie:
        return self.enregistrer(serie)


class InMemoryForfaitRepository(_Sequence):
    """Port `ForfaitRepository` en mémoire (`*_avec_trace` = no-op d'audit).

    `semer` (hors port) sert l'hydratation : recopie un forfait en préservant son `id`, sans trace.
    """

    def __init__(self) -> None:
        super().__init__()
        self._items: dict[int, Forfait] = {}

    def semer(self, forfait: Forfait) -> Forfait:
        identifiant = self._identifiant(forfait.id)
        persiste = dataclasses.replace(forfait, id=identifiant)
        self._items[identifiant] = persiste
        return persiste

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Forfait]:
        return [f for f in self._items.values() if f.tournoi_id == tournoi_id]

    def par_phase(self, phase_id: PhaseId) -> list[Forfait]:
        return [f for f in self._items.values() if f.phase_id == phase_id]

    def par_archer_et_phase(
        self, tournoi_id: TournoiId, archer_id: ArcherId, phase_id: PhaseId
    ) -> Forfait | None:
        for forfait in self._items.values():
            if (
                forfait.tournoi_id == tournoi_id
                and forfait.archer_id == archer_id
                and forfait.phase_id == phase_id
            ):
                return forfait
        return None

    def declarer_avec_trace(self, forfait: Forfait, entree: EntreeAudit) -> Forfait:
        return self.semer(forfait)

    def annuler_avec_trace(self, forfait: Forfait, entree: EntreeAudit) -> None:
        assert forfait.id is not None
        self._items.pop(forfait.id, None)


class InMemoryDuelRepository:
    """Port `DuelRepository` en mémoire, keyé `(phase_id, match_numero)`.

    `charger` renvoie le duel stocké tel quel : contrairement à l'adapter SQL (qui ré-injecte le
    `bareme` non stocké), le magasin garde l'agrégat complet — le paramètre `bareme`, requis par le
    port, est accepté sans être ré-appliqué (il sert les *opérations* du service, pas la relecture).
    """

    def __init__(self) -> None:
        self._items: dict[tuple[int, int], Duel] = {}

    def numeros_enregistres(self, phase_id: PhaseId) -> frozenset[int]:
        return frozenset(match for (phase, match) in self._items if phase == phase_id)

    def charger(self, phase_id: PhaseId, match_numero: int, *, bareme: BaremeDuel) -> Duel | None:
        return self._items.get((phase_id, match_numero))

    def enregistrer(self, phase_id: PhaseId, match_numero: int, duel: Duel) -> Duel:
        self._items[(phase_id, match_numero)] = duel
        return duel


class InMemoryPlacementTableauRepository:
    """Port `PlacementTableauRepository` en mémoire (plan par phase, clé composite)."""

    def __init__(self) -> None:
        # phase_id -> {inscription_id -> Affectation}
        self._plans: dict[int, dict[int, Affectation]] = {}

    def par_phase(self, phase_id: PhaseId) -> list[Affectation]:
        return list(self._plans.get(phase_id, {}).values())

    def definir_plan(self, phase_id: PhaseId, affectations: Sequence[Affectation]) -> None:
        self._plans[phase_id] = {a.inscription_id: a for a in affectations}

    def poser_plusieurs(self, phase_id: PhaseId, affectations: Sequence[Affectation]) -> None:
        plan = self._plans.setdefault(phase_id, {})
        for affectation in affectations:
            plan[affectation.inscription_id] = affectation

    def retirer(self, phase_id: PhaseId, inscription_id: InscriptionId) -> None:
        self._plans.get(phase_id, {}).pop(inscription_id, None)
