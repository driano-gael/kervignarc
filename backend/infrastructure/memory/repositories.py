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
from domain.depart import Depart, DepartId
from domain.deroule_etape import EtapeDeroule, EtapeDerouleId
from domain.duel import BaremeDuel, Duel
from domain.entree_audit import EntreeAudit
from domain.forfait import Forfait
from domain.gabarit_salle import GabaritSalle, GabaritSalleId
from domain.inscription import Inscription, InscriptionId
from domain.phase import Phase, PhaseId, TypePhase
from domain.placement import Affectation
from domain.ports import DepartRepository, DerouleRepository
from domain.remboursement import Remboursement
from domain.serie import Serie
from domain.tournoi import Tournoi, TournoiId
from infrastructure.erreurs import InfrastructureError


class _AllocateurId:
    """Attribue les identifiants auto-incrémentés, en **préservant** un `id` déjà présent.

    Un `id` fourni (hydratation) est conservé et fait avancer la séquence au-delà ; un `id` absent
    (`None`, création par le bot E15US003) reçoit le prochain entier. Ainsi un même magasin sert
    l'hydratation (loss-less) et la création sans collision d'identifiants.

    **Piège E15US003 (hors périmètre E15US002).** L'absence de collision suppose que l'hydratation
    (qui préserve les `id`) précède **toute** création à `id=None`. Si le bot crée une entité avant
    d'hydrater, ou dans un magasin où un `id` supérieur sera ensuite hydraté, deux entités peuvent
    partager un `id`. En E15US002 c'est sûr : l'hydratation est complète et préalable, et le rejeu
    ne crée rien. À revoir quand le bot écrira dans le harnais.
    """

    def __init__(self) -> None:
        self._sequence = 0

    def _identifiant(self, actuel: int | None) -> int:
        if actuel is not None:
            self._sequence = max(self._sequence, actuel)
            return actuel
        self._sequence += 1
        return self._sequence


class InMemoryTournoiRepository(_AllocateurId):
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


class InMemoryArcherRepository(_AllocateurId):
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


class InMemoryCategorieRepository(_AllocateurId):
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

    def par_bibliotheque(self) -> list[Categorie]:
        # Modèles de bibliothèque — patrimoine du club, sans tournoi (E01US023).
        return [c for c in self._items.values() if c.tournoi_id is None]

    def par_blason(self, blason_id: BlasonId) -> list[Categorie]:
        return [c for c in self._items.values() if c.blason_id == blason_id]

    def enregistrer(self, categorie: Categorie) -> Categorie:
        assert categorie.id is not None
        self._items[categorie.id] = categorie
        return categorie

    def supprimer(self, categorie_id: CategorieId) -> None:
        self._items.pop(categorie_id, None)


class InMemoryBlasonRepository(_AllocateurId):
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

    def par_bibliotheque(self) -> list[Blason]:
        # Modèles de bibliothèque — patrimoine du club, sans tournoi (E01US023).
        return [b for b in self._items.values() if b.tournoi_id is None]

    def enregistrer(self, blason: Blason) -> Blason:
        assert blason.id is not None
        self._items[blason.id] = blason
        return blason

    def supprimer(self, blason_id: BlasonId) -> None:
        self._items.pop(blason_id, None)


class InMemoryGabaritSalleRepository(_AllocateurId):
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


class InMemoryInscriptionRepository(_AllocateurId):
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

    def supprimer_avec_remboursement(
        self, inscription_id: InscriptionId, remboursement: Remboursement
    ) -> None:
        # Simulation **éphémère** (E15US002, ADR-0054) : rien n'est persisté, le remboursement est
        # ignoré comme `definir_paye_avec_trace` ignore l'audit. Conforme au port (E08US005).
        self._items.pop(inscription_id, None)


class InMemoryDepartRepository(_AllocateurId):
    """Port `DepartRepository` en mémoire (E01US025, ADR-0075).

    Absent jusqu'ici : le harnais de simulation n'avait pas besoin des créneaux, la portée sportive
    étant le tournoi. Elle est devenue le **départ**, donc une simulation qui n'en aurait aucun ne
    pourrait ni composer de phases, ni produire de classement.
    """

    def __init__(self) -> None:
        super().__init__()
        self._items: dict[int, Depart] = {}

    def ajouter(self, depart: Depart) -> Depart:
        identifiant = self._identifiant(depart.id)
        persiste = dataclasses.replace(depart, id=identifiant)
        self._items[identifiant] = persiste
        return persiste

    def par_id(self, depart_id: DepartId) -> Depart | None:
        return self._items.get(depart_id)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Depart]:
        departs = [d for d in self._items.values() if d.tournoi_id == tournoi_id]
        # Tri par numéro **garanti par le port** : le service en dérive le prochain numéro.
        return sorted(departs, key=lambda d: d.numero)

    def enregistrer(self, depart: Depart) -> Depart:
        assert depart.id is not None
        self._items[depart.id] = depart
        return depart

    def supprimer(self, depart_id: DepartId) -> None:
        self._items.pop(depart_id, None)

    def supprimer_avec_remboursements(
        self, depart_id: DepartId, remboursements: Sequence[Remboursement]
    ) -> None:
        """Supprime le créneau ; les remboursements sont **ignorés** en simulation.

        Même parti que les no-op d'audit du module (ADR-0054) : une simulation ne touche à aucune
        caisse. Ignorer n'est pas un raccourci — ouvrir un remboursement fictif serait pire, il
        n'aurait aucun sens à relire.
        """
        self.supprimer(depart_id)


class InMemoryDerouleRepository(_AllocateurId):
    """Port `DerouleRepository` en mémoire — la **définition** du déroulé (ADR-0076)."""

    def __init__(self) -> None:
        super().__init__()
        self._items: dict[int, EtapeDeroule] = {}

    def ajouter(self, etape: EtapeDeroule) -> EtapeDeroule:
        identifiant = self._identifiant(etape.id)
        persiste = dataclasses.replace(etape, id=identifiant)
        self._items[identifiant] = persiste
        return persiste

    def par_tournoi(self, tournoi_id: TournoiId) -> list[EtapeDeroule]:
        etapes = [e for e in self._items.values() if e.tournoi_id == tournoi_id]
        return sorted(etapes, key=lambda e: e.ordre)

    def enregistrer(self, etape: EtapeDeroule) -> EtapeDeroule:
        assert etape.id is not None
        self._items[etape.id] = etape
        return etape

    def reordonner(self, etapes: list[EtapeDeroule]) -> list[EtapeDeroule]:
        """Réécrit le lot d'un coup. Sans contrainte d'unicité à ménager, une passe suffit ici —
        le contrat visible (« ou tout, ou rien ») est le même que celui de l'adapter SQL."""
        for etape in etapes:
            assert etape.id is not None
            self._items[etape.id] = etape
        return list(etapes)

    def supprimer(self, etape_id: EtapeDerouleId) -> None:
        self._items.pop(etape_id, None)


class InMemoryPhaseRepository(_AllocateurId):
    """Port `PhaseRepository` en mémoire — l'**avancement** d'une étape (ADR-0076).

    ⚠️ Comme l'adapter SQL, il **assemble** : le magasin ne retient que `(depart_id, ordre, statut)`,
    et la définition vient du déroulé du tournoi de ce créneau. Les deux implémentations doivent
    répondre pareil — c'est ce que vérifient les tests de conformité de port.
    """

    def __init__(
        self,
        departs: DepartRepository | None = None,
        # Le **port**, pas la classe concrète (règle 2) : le paramètre voisin est déjà typé ainsi,
        # et dépendre de `InMemoryDerouleRepository` interdisait d'injecter une autre doublure.
        deroules: DerouleRepository | None = None,
    ) -> None:
        super().__init__()
        self._items: dict[int, Phase] = {}
        # Facultatifs : seules les lectures qui **assemblent** ou remontent au tournoi en ont
        # besoin.
        # Le harnais de simulation les câble ; un décor de test qui ne lit que des statuts non.
        self._departs = departs
        self._deroules = deroules

    @property
    def _assemble(self) -> bool:
        """Vrai quand le magasin sait joindre `phase → départ → tournoi → étape`.

        Faux, il reste en **mode indulgent** : la phase conservée porte déjà sa définition (elle y
        a été mise à l'ajout), on la rend telle quelle. C'est ce qui permet aux décors de test qui
        ne lisent que des statuts de rester simples, sans jamais rendre une phase amputée.

        # DETTE-049 : cette indulgence fait répondre la doublure **autrement que la production**
        # (qui, elle, câble toujours les deux magasins — cf. `bootstrap/composition.py`). Un décor
        # ainsi monté peut donc *consacrer* un bug au lieu de l'attraper, ce qui est exactement le
        # mode de panne rencontré deux fois pendant E01US025. Branche morte au câblage réel, d'où
        # la sévérité mineure ; à supprimer en rendant les deux magasins obligatoires.
        """
        return self._departs is not None and self._deroules is not None

    def _etape(self, phase: Phase) -> EtapeDeroule | None:
        """La définition de cette phase : l'étape de même rang, dans le tournoi de son créneau."""
        if self._departs is None or self._deroules is None:
            return None
        depart = self._departs.par_id(phase.depart_id)
        if depart is None:
            return None
        for etape in self._deroules.par_tournoi(depart.tournoi_id):
            if etape.ordre == phase.ordre:
                return etape
        return None

    def _assembler(self, phases: list[Phase]) -> list[Phase]:
        """Complète chaque phase de sa définition ; une **orpheline** est écartée de la lecture.

        Même règle que l'adapter SQL, et pour la même raison : une phase sans définition ne peut
        rien dire d'utile, mais faire échouer *toute* la lecture pour elle priverait l'organisateur
        du reste de son déroulé le jour J. Les deux adapters doivent répondre pareil — c'est
        l'objet des tests de conformité de port.
        """
        if not self._assemble:
            return phases
        assemblees = []
        for phase in phases:
            etape = self._etape(phase)
            if etape is not None:
                assemblees.append(
                    dataclasses.replace(
                        etape.instancier(phase.depart_id), statut=phase.statut, id=phase.id
                    )
                )
        return assemblees

    def _assembler_une(self, phase: Phase) -> Phase | None:
        assemblees = self._assembler([phase])
        return assemblees[0] if assemblees else None

    def ajouter(self, phase: Phase) -> Phase:
        """Persiste l'**avancement** ; la définition portée par l'objet reçu est ignorée.

        Écrire une instance dont le rang n'existe pas au déroulé du tournoi est une **erreur**, pas
        un cas limite : elle serait invisible à toute lecture (écartée comme orpheline) et le
        service la croirait posée. L'adapter SQL lève ici aussi.
        """
        identifiant = self._identifiant(phase.id)
        persiste = dataclasses.replace(phase, id=identifiant)
        self._items[identifiant] = persiste
        assemblee = self._assembler_une(persiste)
        if assemblee is None:
            del self._items[identifiant]
            raise InfrastructureError(
                "Phase créée sans étape de déroulé de même rang : le tournoi de ce créneau "
                "n'a pas ce rang à son déroulé."
            )
        return assemblee

    def par_id(self, phase_id: PhaseId) -> Phase | None:
        phase = self._items.get(phase_id)
        return None if phase is None else self._assembler_une(phase)

    def par_depart_et_type(self, depart_id: DepartId, type_phase: TypePhase) -> Phase | None:
        trouvees = [p for p in self.par_depart(depart_id) if p.type is type_phase]
        return trouvees[-1] if trouvees else None

    def par_depart(self, depart_id: DepartId) -> list[Phase]:
        phases = [p for p in self._items.values() if p.depart_id == depart_id]
        return self._assembler(sorted(phases, key=lambda p: p.ordre))

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Phase]:
        """Les phases de **tous les départs** du tournoi, triées (départ, ordre) — pas une séquence.

        Le magasin des phases ne connaît que des `depart_id` : remonter au tournoi exige le magasin
        des **départs**, d'où l'injection. Non câblé, cette lecture **lève** au lieu de rendre une
        liste vide : un `[]` silencieux ferait passer « je ne sais pas répondre » pour « ce tournoi
        n'a aucune phase », c'est-à-dire exactement le genre d'écart muet qu'ADR-0075 corrige.
        """
        if self._departs is None:
            raise InfrastructureError(
                "Ce magasin de phases n'a pas de magasin de départs : la lecture transverse "
                "« phases d'un tournoi » exige la jointure phase → départ → tournoi (ADR-0075)."
            )
        departs = {d.id for d in self._departs.par_tournoi(tournoi_id)}
        phases = [p for p in self._items.values() if p.depart_id in departs]
        return self._assembler(sorted(phases, key=lambda p: (p.depart_id, p.ordre)))

    def enregistrer(self, phase: Phase) -> Phase:
        """Met à jour l'**avancement** (statut, rang) ; la définition s'édite sur l'étape.

        ⚠️ **On assemble avant d'écrire**, comme `ajouter` juste au-dessus et comme l'adapter SQL
        depuis la revue E01US025 : écrire puis lever laissait le magasin porter une phase orpheline
        alors que l'appelant venait de recevoir un échec. Les deux adapters doivent répondre pareil
        jusque dans leur comportement en cas d'échec — sans quoi le test de conformité ne prouve
        que le chemin heureux.
        """
        assert phase.id is not None
        assemblee = self._assembler_une(phase)
        if assemblee is None:
            raise InfrastructureError("Phase mise à jour sans étape de déroulé de même rang.")
        self._items[phase.id] = phase
        return assemblee

    def reordonner(self, phases: list[Phase]) -> None:
        """Réaligne les rangs du lot. Seul l'`ordre` bouge, comme dans l'adapter SQL."""
        for phase in phases:
            assert phase.id is not None
            self._items[phase.id] = dataclasses.replace(self._items[phase.id], ordre=phase.ordre)

    def supprimer(self, phase_id: PhaseId) -> None:
        self._items.pop(phase_id, None)


class InMemorySerieRepository(_AllocateurId):
    """Port `SerieRepository` en mémoire (`enregistrer_avec_trace` = no-op d'audit).

    `horodatages` renvoie `{}` : le `created_at` d'une volée est une **métadonnée de persistance**
    (hors agrégat) que la simulation ne suit pas — sans effet sur le classement, qui l'ignore.
    """

    def __init__(self) -> None:
        super().__init__()
        self._items: dict[int, Serie] = {}

    def par_archer(self, phase_id: PhaseId, archer_id: ArcherId) -> Serie | None:
        for serie in self._items.values():
            if serie.phase_id == phase_id and serie.archer_id == archer_id:
                return serie
        return None

    def par_phase(self, phase_id: PhaseId) -> list[Serie]:
        return [s for s in self._items.values() if s.phase_id == phase_id]

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Serie]:
        return [s for s in self._items.values() if s.tournoi_id == tournoi_id]

    def horodatages(self, phase_id: PhaseId, archer_id: ArcherId) -> dict[int, datetime.datetime]:
        return {}

    def enregistrer(self, serie: Serie) -> Serie:
        identifiant = self._identifiant(serie.id)
        persiste = dataclasses.replace(serie, id=identifiant)
        self._items[identifiant] = persiste
        return persiste

    def enregistrer_avec_trace(self, serie: Serie, entree: EntreeAudit) -> Serie:
        return self.enregistrer(serie)


class InMemoryForfaitRepository(_AllocateurId):
    """Port `ForfaitRepository` en mémoire (`*_avec_trace` = no-op d'audit).

    `semer` (hors port) factorise l'ajout **sans trace** en préservant l'`id` ; il sert
    `declarer_avec_trace` (et servira le bot d'E15US003 qui *crée* des forfaits simulés). Les
    forfaits ne sont **pas** hydratés (ADR-0054 §3 : un tournoi avant démarrage n'en a pas).
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
