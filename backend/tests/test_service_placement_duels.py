"""Tests du service `ServicePlacementDuels` (E03US009) — repositories factices.

Ici vit la **règle métier de bout en bout** d'E03US009, dérivée du CA (ADR-0048) : à partir d'un
**classement**, l'arbre du 1er tour est construit (serpent) et ses duellistes sont placés **côte à
côte** (positions adjacentes de la même cible) dans la mesure du possible ; les duels qu'on ne peut
pas rapprocher sont **signalés**, jamais bloqués. Le placement pur est couvert par
`test_domain_placement` (adjacence) et `test_domain_tableau` (paires du 1er tour) ; on vérifie ici
l'**orchestration** classement → arbre → paires → placement + les gardes (phase pas un tableau).

Fakes en mémoire conformes aux ports (ni base ni serveur). Le classement est vrai
(`ServiceClassement` sur des séries semées) pour que l'ensemencement soit réaliste et déterministe.
"""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import replace

import pytest

from application.classements import ServiceClassement
from application.erreurs import DeplacementInvalide, PhasePasUnTableau
from application.placement_duels import PlanDeDuels, ServicePlacementDuels
from application.saisie_duels import ServiceSaisieDuels
from domain.archer import Archer, ArcherId
from domain.bareme import BaremeQualification
from domain.blason import Blason, BlasonId, ZoneScore
from domain.categorie import Categorie
from domain.cloisonnement import Cloisonnement
from domain.depart import Depart
from domain.duel import ResolveurBaremeDuelFfta
from domain.entree_audit import EntreeAudit
from domain.gabarit_salle import GabaritSalle, GabaritSalleId
from domain.inscription import Inscription, InscriptionId
from domain.phase import Phase, PhaseId, SourcePhase, TypePhase
from domain.placement import Affectation, RaisonConflit
from domain.politiques import (
    AggregationParQualification,
    ByesAuxMieuxClasses,
    PlacementEnCascade,
    SeedingSerpent,
    registre_par_defaut,
)
from domain.serie import Serie, Volee
from domain.tournoi import Tournoi, TournoiId
from tests.conftest import (
    FauxArcherRepository,
    FauxCategorieRepository,
    FauxDepartRepository,
    FauxDuelRepository,
    FauxForfaitRepository,
    FauxInscriptionRepository,
    FauxPhaseRepository,
)

_DATE = datetime.date(2026, 3, 14)


class FauxTournoiRepository:
    """Double de `TournoiRepository` : seul `par_id` sert (reste = conformité au port).

    `cloisonnement` (E03US007) est porté ici parce que le service le **lit sur le tournoi** : le
    plan de duels est posé dans la même salle que la qualification, sous le même réglage."""

    def __init__(self, ids: set[int], cloisonnement: Cloisonnement = Cloisonnement.AUCUN) -> None:
        self._ids = ids
        self.cloisonnement = cloisonnement

    def par_id(self, tournoi_id: TournoiId) -> Tournoi | None:
        if tournoi_id not in self._ids:
            return None
        return Tournoi.creer("Salle 18m", _DATE).definir_cloisonnement(self.cloisonnement)

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        raise NotImplementedError

    def lister(self) -> list[Tournoi]:
        raise NotImplementedError

    def enregistrer(self, tournoi: Tournoi) -> Tournoi:
        raise NotImplementedError

    def supprimer(self, tournoi_id: TournoiId) -> None:
        raise NotImplementedError


class FauxGabaritRepository:
    """Double de `GabaritSalleRepository` : seul `par_tournoi` sert (reste = conformité)."""

    def __init__(self) -> None:
        self._gabarits: list[GabaritSalle] = []

    def ajouter(self, gabarit: GabaritSalle) -> GabaritSalle:
        self._gabarits.append(gabarit)
        return gabarit

    def par_id(self, gabarit_id: GabaritSalleId) -> GabaritSalle | None:
        raise NotImplementedError

    def lister(self) -> list[GabaritSalle]:
        raise NotImplementedError

    def par_tournoi(self, tournoi_id: TournoiId) -> GabaritSalle | None:
        instances = [g for g in self._gabarits if g.tournoi_id == tournoi_id]
        return instances[-1] if instances else None

    def enregistrer(self, gabarit: GabaritSalle) -> GabaritSalle:
        raise NotImplementedError

    def supprimer(self, gabarit_id: GabaritSalleId) -> None:
        raise NotImplementedError


class FauxBlasonRepository:
    """Double de `BlasonRepository` : seul `par_id` sert (reste = conformité au port)."""

    def __init__(self) -> None:
        self._blasons: dict[int, Blason] = {}
        self._sequence = 0

    def ajouter(self, blason: Blason) -> Blason:
        self._sequence += 1
        # Même correction que `FauxPhaseRepository` 76 lignes plus haut, et trouvée seulement en
        # revue adversariale : cette reconstruction perdait `origine`. Appliquer le raisonnement à
        # un site et pas à ses voisins immédiats, c'est déplacer le trou, pas le fermer.
        persiste = replace(blason, id=self._sequence)
        self._blasons[self._sequence] = persiste
        return persiste

    def par_id(self, blason_id: BlasonId) -> Blason | None:
        return self._blasons.get(blason_id)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Blason]:
        raise NotImplementedError

    def par_bibliotheque(self) -> list[Blason]:
        # Modèles de bibliothèque (E01US023) : ceux sans tournoi.
        return [x for x in self._blasons.values() if x.tournoi_id is None]

    def enregistrer(self, blason: Blason) -> Blason:
        raise NotImplementedError

    def supprimer(self, blason_id: BlasonId) -> None:
        raise NotImplementedError


class FauxSerieRepository:
    """Double de `SerieRepository` : seul `par_tournoi` sert au classement (reste = conformité)."""

    def __init__(self) -> None:
        self._series: list[Serie] = []

    def semer(self, tournoi_id: int, archer_id: int, valeurs: tuple[ZoneScore, ...]) -> None:
        self._series.append(
            Serie(
                tournoi_id=tournoi_id,
                archer_id=archer_id,
                volees=(Volee(numero=1, valeurs=valeurs, validee_par="Scoreur"),),
            )
        )

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Serie]:
        return [s for s in self._series if s.tournoi_id == tournoi_id]

    def par_archer(self, tournoi_id: TournoiId, archer_id: ArcherId) -> Serie | None:
        raise NotImplementedError

    def horodatages(
        self, tournoi_id: TournoiId, archer_id: ArcherId
    ) -> dict[int, datetime.datetime]:
        raise NotImplementedError

    def enregistrer(self, serie: Serie) -> Serie:
        raise NotImplementedError

    def enregistrer_avec_trace(self, serie: Serie, entree: EntreeAudit) -> Serie:
        raise NotImplementedError


class FauxPlacementTableauRepository:
    """Double en mémoire de `PlacementTableauRepository` (clé composite (phase, inscription))."""

    def __init__(self) -> None:
        self._plan: dict[tuple[int, int], tuple[int, str]] = {}

    def par_phase(self, phase_id: PhaseId) -> list[Affectation]:
        return [
            Affectation(inscription_id=insc, cible_index=cible, position=pos)
            for (phase, insc), (cible, pos) in sorted(self._plan.items())
            if phase == phase_id
        ]

    def definir_plan(self, phase_id: PhaseId, affectations: Sequence[Affectation]) -> None:
        self._plan = {k: v for k, v in self._plan.items() if k[0] != phase_id}
        for a in affectations:
            self._plan[(phase_id, a.inscription_id)] = (a.cible_index, a.position)

    def poser_plusieurs(self, phase_id: PhaseId, affectations: Sequence[Affectation]) -> None:
        for a in affectations:
            self._plan[(phase_id, a.inscription_id)] = (a.cible_index, a.position)

    def retirer(self, phase_id: PhaseId, inscription_id: InscriptionId) -> None:
        self._plan.pop((phase_id, inscription_id), None)


class _Monde:
    """Décor : un tournoi, un gabarit, une catégorie (blason), N archers classés, une phase tableau.

    Les archers reçoivent des scores **décroissants** dans l'ordre de création → rang scratch 1..N
    dans cet ordre. La phase d'élimination directe porte l'id `phase_id`.
    """

    def __init__(self, capacites: tuple[int, ...] = (4,), *, taille: float = 0.25) -> None:
        self.tournoi_id = 1
        self.tournois = FauxTournoiRepository({1})
        self.departs = FauxDepartRepository()
        _depart = self.departs.ajouter(
            Depart.creer(tournoi_id=1, numero=1, tarif_centimes=800, horaire="09:00")
        )
        assert _depart.id is not None
        self.depart_id = _depart.id
        self.phases = FauxPhaseRepository(self.departs)
        self.gabarits = FauxGabaritRepository()
        self.inscriptions = FauxInscriptionRepository()
        self.archers = FauxArcherRepository()
        self.categories = FauxCategorieRepository()
        self.blasons = FauxBlasonRepository()
        self.series = FauxSerieRepository()
        self.forfaits = FauxForfaitRepository()
        self.placements = FauxPlacementTableauRepository()
        self.gabarits.ajouter(
            GabaritSalle(nom="Salle", capacites=capacites, tournoi_id=self.tournoi_id)
        )
        blason = self.blasons.ajouter(Blason.creer(self.tournoi_id, "B", taille=taille, capacite=1))
        categorie = self.categories.ajouter(
            Categorie.creer(self.tournoi_id, "Cat", blason_id=blason.id, hauteur_cm=130)
        )
        assert categorie.id is not None
        self.categorie_id = categorie.id
        # Seconde catégorie sur le **même** blason (E03US007) : c'est le cas qui distingue un
        # cloisonnement par catégorie d'un cloisonnement par blason.
        autre = self.categories.ajouter(
            Categorie.creer(self.tournoi_id, "Cat2", blason_id=blason.id, hauteur_cm=130)
        )
        assert autre.id is not None
        self.autre_categorie_id = autre.id
        depart = 1  # un seul « départ » logique ; l'inscription suffit (pas de repo départ ici)
        self.depart_id = depart
        phase = self.phases.ajouter(Phase.creer(self.depart_id, 2, TypePhase.ELIMINATION_DIRECTE))
        assert phase.id is not None
        self.phase_id = phase.id
        self.inscription_par_archer: dict[int, int] = {}

    def regler_cloisonnement(self, cloisonnement: Cloisonnement) -> None:
        """Règle le cloisonnement du tournoi (E03US007) — lu par le service à chaque opération."""
        self.tournois.cloisonnement = cloisonnement

    def inscrire_classe(
        self, valeurs: tuple[ZoneScore, ...], *, categorie_id: int | None = None
    ) -> int:
        """Crée un archer inscrit avec un score (une volée validée) ; renvoie son `archer_id`."""
        archer = self.archers.ajouter(
            Archer(
                nom="N",
                prenom="P",
                tournoi_id=self.tournoi_id,
                categorie_id=categorie_id if categorie_id is not None else self.categorie_id,
            )
        )
        assert archer.id is not None
        inscription = self.inscriptions.ajouter(
            Inscription(archer_id=archer.id, depart_id=self.depart_id)
        )
        assert inscription.id is not None
        self.inscription_par_archer[archer.id] = inscription.id
        self.series.semer(self.tournoi_id, archer.id, valeurs)
        return archer.id

    @property
    def saisie_duels(self) -> ServiceSaisieDuels:
        """Le service jumeau, construit **comme** le plan le construit (E05US024).

        Exposé pour que la parité plan ↔ arbre soit vérifiable de l'extérieur : c'est l'écart entre
        ces deux-là qu'E05US020 avait laissé passer, et une assertion croisée vaut mieux qu'un
        commentaire affirmant qu'ils partagent la règle.
        """
        return self._saisie_duels(
            ServiceClassement(
                self.tournois,
                self.archers,
                self.series,
                self.categories,
                self.phases,
                self.forfaits,
                self.departs,
                self.inscriptions,
            )
        )

    @property
    def service(self) -> ServicePlacementDuels:
        classement = ServiceClassement(
            self.tournois,
            self.archers,
            self.series,
            self.categories,
            self.phases,
            self.forfaits,
            self.departs,
            self.inscriptions,
        )
        return ServicePlacementDuels(
            self.tournois,
            self.phases,
            self.gabarits,
            self.inscriptions,
            self.archers,
            self.categories,
            self.blasons,
            self.placements,
            classement,
            SeedingSerpent(),
            ByesAuxMieuxClasses(),
            PlacementEnCascade(),
            registre_par_defaut(),
            self._saisie_duels(classement),
        )

    def _saisie_duels(self, classement: ServiceClassement) -> ServiceSaisieDuels:
        """Le jumeau dont le plan emprunte la résolution de classement amont (E05US024).

        **Mêmes politiques que le plan** : les deux montent le même arbre, et les faire diverger ici
        ferait mentir le décor avant même le test.
        """
        return ServiceSaisieDuels(
            self.tournois,
            self.phases,
            self.categories,
            self.blasons,
            FauxDuelRepository(),
            self.forfaits,
            classement,
            ResolveurBaremeDuelFfta(),
            SeedingSerpent(),
            ByesAuxMieuxClasses(),
            PlacementEnCascade(),
            registre_par_defaut(),
            AggregationParQualification(),
        )


def _quatre_archers(monde: _Monde) -> list[int]:
    """Quatre archers aux scores décroissants → rangs scratch 1, 2, 3, 4 dans l'ordre rendu."""
    return [
        monde.inscrire_classe((ZoneScore.DIX, ZoneScore.DIX)),  # 20 → rang 1
        monde.inscrire_classe((ZoneScore.NEUF, ZoneScore.NEUF)),  # 18 → rang 2
        monde.inscrire_classe((ZoneScore.HUIT, ZoneScore.HUIT)),  # 16 → rang 3
        monde.inscrire_classe((ZoneScore.SEPT, ZoneScore.SEPT)),  # 14 → rang 4
    ]


def _positions(monde: _Monde, plan: PlanDeDuels, archer_id: int) -> tuple[int, str] | None:
    for cible in plan.cibles:
        for pose in cible.placements:
            if pose.archer_id == archer_id:
                return (cible.index, pose.position)
    return None


def test_regenerer_place_les_duellistes_cote_a_cote() -> None:
    """CA : sur une cible qui a la place, les 2 adversaires d'un duel du 1er tour sont adjacents.

    Serpent sur 4 : rang 1 affronte rang 4, rang 2 affronte rang 3. Chaque duel tombe sur deux
    positions voisines de la même cible ; aucun duel n'est signalé.
    """
    monde = _Monde(capacites=(4,))
    r1, r2, r3, r4 = _quatre_archers(monde)
    plan = monde.service.regenerer(monde.tournoi_id, monde.phase_id)

    assert plan.duels_separes == ()  # tout le monde côte à côte
    assert plan.adjacence_non_garantie == frozenset()
    # le duel (r1, r4) et le duel (r2, r3) occupent chacun deux positions adjacentes d'une cible
    for a, b in ((r1, r4), (r2, r3)):
        pa, pb = _positions(monde, plan, a), _positions(monde, plan, b)
        assert pa is not None and pb is not None
        assert pa[0] == pb[0]  # même cible
        assert abs(ord(pa[1]) - ord(pb[1])) == 1  # positions voisines


def test_plan_de_duels_relit_le_plan_persiste() -> None:
    """Après régénération, `plan_de_duels` relit le plan matérialisé (les 4 duellistes posés)."""
    monde = _Monde(capacites=(4,))
    _quatre_archers(monde)
    monde.service.regenerer(monde.tournoi_id, monde.phase_id)
    plan = monde.service.plan_de_duels(monde.tournoi_id, monde.phase_id)
    poses = [pose for cible in plan.cibles for pose in cible.placements]
    assert len(poses) == 4
    assert plan.conflits == ()  # personne en réserve


def test_duel_signale_quand_les_cibles_ne_prennent_qu_un_archer() -> None:
    """CA « signalé si impossible » : des cibles de capacité 1 séparent chaque duelliste.

    Aucun blocage — les 4 sont placés (une cible chacun) — mais les deux duels sont signalés (leurs
    membres ne sont pas côte à côte), et les cibles concernées portent le drapeau d'adjacence.
    """
    monde = _Monde(capacites=(1, 1, 1, 1), taille=1.0)
    r1, r2, r3, r4 = _quatre_archers(monde)
    plan = monde.service.regenerer(monde.tournoi_id, monde.phase_id)

    assert plan.conflits == ()  # tous placés, aucun bloqué
    duels = {frozenset(paire) for paire in plan.duels_separes}
    assert duels == {frozenset((r1, r4)), frozenset((r2, r3))}
    assert plan.adjacence_non_garantie != frozenset()


def test_mettre_un_duelliste_en_reserve() -> None:
    """Ajustement : déplacer un duelliste en réserve (cible None) le retire du plan (persisté)."""
    monde = _Monde(capacites=(4,))
    r1, _r2, _r3, _r4 = _quatre_archers(monde)
    monde.service.regenerer(monde.tournoi_id, monde.phase_id)
    inscription_r1 = monde.inscription_par_archer[r1]
    plan = monde.service.deplacer(monde.tournoi_id, monde.phase_id, inscription_r1, None, None)
    assert _positions(monde, plan, r1) is None  # r1 n'est plus posé
    assert any(c.archer_id == r1 for c in plan.conflits)  # il est en réserve


def test_phase_qui_n_est_pas_un_tableau_est_refusee() -> None:
    """Garde : demander le plan de duels sur une phase de qualification lève `PhasePasUnTableau`."""
    monde = _Monde(capacites=(4,))
    _quatre_archers(monde)
    qualif = monde.phases.ajouter(
        Phase.qualification(monde.tournoi_id, BaremeQualification.creer(2, 3))
    )
    assert qualif.id is not None
    with pytest.raises(PhasePasUnTableau):
        monde.service.plan_de_duels(monde.tournoi_id, qualif.id)


# --- Surface d'ajustement (glisser-déposer) — CA E03US009, ADR-0048 ------------------------------


def test_deplacer_case_libre_puis_refus_position_invalide() -> None:
    """Déplacement sur une case libre ; une position inexistante est refusée (409), sans écrire."""
    monde = _Monde(capacites=(4, 4))
    r1, _r2, _r3, _r4 = _quatre_archers(monde)
    monde.service.regenerer(monde.tournoi_id, monde.phase_id)
    insc_r1 = monde.inscription_par_archer[r1]

    # Case libre (cible 2, position A) → déplacement accepté.
    plan = monde.service.deplacer(monde.tournoi_id, monde.phase_id, insc_r1, 2, "A")
    assert _positions(monde, plan, r1) == (2, "A")

    # Position inexistante → refus 409, état inchangé.
    with pytest.raises(DeplacementInvalide):
        monde.service.deplacer(monde.tournoi_id, monde.phase_id, insc_r1, 1, "Z")
    apres = monde.service.plan_de_duels(monde.tournoi_id, monde.phase_id)
    assert _positions(monde, apres, r1) == (2, "A")  # rien n'a bougé


def test_echange_atomique_de_deux_duellistes() -> None:
    """Déposer un duelliste sur une case occupée **permute** les deux (tout ou rien)."""
    monde = _Monde(capacites=(4,))
    r1, r2, r3, r4 = _quatre_archers(monde)
    plan = monde.service.regenerer(monde.tournoi_id, monde.phase_id)
    pos_r1, pos_r4 = _positions(monde, plan, r1), _positions(monde, plan, r4)
    assert pos_r1 is not None and pos_r4 is not None

    # Déposer r1 sur la case de r4 → ils échangent leurs positions.
    echange = monde.service.deplacer(
        monde.tournoi_id, monde.phase_id, monde.inscription_par_archer[r1], pos_r4[0], pos_r4[1]
    )
    assert _positions(monde, echange, r1) == pos_r4
    assert _positions(monde, echange, r4) == pos_r1
    # Personne perdu, personne en réserve.
    places = {p.archer_id for cible in echange.cibles for p in cible.placements}
    assert places == {r1, r2, r3, r4}
    assert echange.conflits == ()


def test_placer_les_restants_rapproche_un_duel() -> None:
    """« Placer les restants » repose une paire mise en réserve, côte à côte (ordre d'adjacence)."""
    monde = _Monde(capacites=(4,))
    r1, _r2, _r3, r4 = _quatre_archers(monde)
    monde.service.regenerer(monde.tournoi_id, monde.phase_id)
    # r1 et r4 sont adversaires (serpent : rang 1 vs rang 4). On les met tous deux en réserve.
    for archer in (r1, r4):
        monde.service.deplacer(
            monde.tournoi_id, monde.phase_id, monde.inscription_par_archer[archer], None, None
        )
    plan = monde.service.placer_les_restants(monde.tournoi_id, monde.phase_id)
    # Ils reviennent posés, et côte à côte (leur duel n'est pas signalé séparé).
    pr1, pr4 = _positions(monde, plan, r1), _positions(monde, plan, r4)
    assert pr1 is not None and pr4 is not None
    assert pr1[0] == pr4[0] and abs(ord(pr1[1]) - ord(pr4[1])) == 1
    assert frozenset((r1, r4)) not in {frozenset(p) for p in plan.duels_separes}


def test_effectif_inferieur_a_deux_donne_un_plan_vide() -> None:
    """Un seul archer classé : pas de tableau possible → plan vide, sans duel, sans erreur 500."""
    monde = _Monde(capacites=(4,))
    monde.inscrire_classe((ZoneScore.DIX, ZoneScore.DIX))
    plan = monde.service.regenerer(monde.tournoi_id, monde.phase_id)
    assert all(cible.placements == () for cible in plan.cibles)
    assert plan.conflits == ()
    assert plan.duels_separes == ()


def _monde_avec_orphelines() -> tuple[_Monde, list[int], tuple[int, str]]:
    """Décor où r1/r2/r3 ont des poses **orphelines**, et renvoie (monde, [r1..r5], case de r1).

    On régénère à 4 archers (les 4 posés), puis on inscrit un 5ᵉ moins bien classé : l'arbre passe à
    8, les rangs 1-3 sont exemptés (byes), seul le duel (rang 4, rang 5) subsiste au 1er tour. Les
    duellistes courants sont donc {r4, r5} ; les poses de r1/r2/r3 sont **orphelines** (masquées en
    lecture). C'est le scénario exact du bloquant trouvé à la revue (axe D).
    """
    monde = _Monde(capacites=(4,))
    r1, r2, r3, r4 = _quatre_archers(monde)
    plan = monde.service.regenerer(monde.tournoi_id, monde.phase_id)
    case_r1 = _positions(monde, plan, r1)
    assert case_r1 is not None
    r5 = monde.inscrire_classe((ZoneScore.UN, ZoneScore.UN))  # moins bien classé → décale l'arbre
    lecture = monde.service.plan_de_duels(monde.tournoi_id, monde.phase_id)
    assert _positions(monde, lecture, r1) is None  # pose de r1 masquée (orpheline)
    return monde, [r1, r2, r3, r4, r5], case_r1


def test_deplacer_un_place_sur_une_case_orpheline_ne_provoque_pas_500() -> None:
    """Régression (revue E03US009, axe D) : déplacer un duelliste **déjà placé** sur une case
    portant une pose **orpheline** ne lève plus de KeyError/500.

    C'est le chemin exact du bloquant : `deplacer` détectait l'orpheline comme **occupant**, puis
    `_echanger` indexait `archer_par_inscription[orpheline]` → `KeyError` → 500. La purge
    (`_poses_a_jour`) retire l'orpheline avant : la case est alors libre, le déplacement passe.
    """
    monde, (r1, _r2, _r3, r4, _r5), case_r1 = _monde_avec_orphelines()
    apres = monde.service.deplacer(
        monde.tournoi_id, monde.phase_id, monde.inscription_par_archer[r4], case_r1[0], case_r1[1]
    )
    assert _positions(monde, apres, r4) == case_r1  # r4 posé sur l'ancienne case de r1, sans 500
    assert _positions(monde, apres, r1) is None  # l'orpheline est purgée, jamais réapparue


def test_deposer_sur_une_case_orpheline_visiblement_vide_est_traite_comme_libre() -> None:
    """Une case portant une orpheline **paraît vide** : y déposer un duelliste en réserve doit poser
    (case libre après purge), pas refuser « case occupée » (409, garde `source is None`)."""
    monde, (_r1, _r2, _r3, _r4, r5), case_r1 = _monde_avec_orphelines()
    apres = monde.service.deplacer(
        monde.tournoi_id, monde.phase_id, monde.inscription_par_archer[r5], case_r1[0], case_r1[1]
    )
    assert _positions(monde, apres, r5) == case_r1  # r5 (réserve) posé, pas de faux « occupé »


def test_placer_les_restants_ignore_les_poses_orphelines() -> None:
    """`placer_les_restants` purge les orphelines : jamais deux archers sur une même case (variante
    « double pose » du bloquant, axe D)."""
    monde, (_r1, _r2, _r3, _r4, r5), _case = _monde_avec_orphelines()
    plan = monde.service.placer_les_restants(monde.tournoi_id, monde.phase_id)
    cases = [(cible.index, pose.position) for cible in plan.cibles for pose in cible.placements]
    assert len(cases) == len(set(cases))  # aucune case doublement occupée (orpheline purgée)
    places = {pose.archer_id for cible in plan.cibles for pose in cible.placements}
    assert r5 in places  # le seul restant plaçable est bien reposé


# --- Cloisonnement des cibles (E03US007) --------------------------------------------------------
#
# Le plan de duels est posé dans la **même salle** que la qualification, sous le **même** réglage de
# tournoi : la story et l'ADR-0071 l'affirment tous deux. Ces tests fixent ce que cette affirmation
# veut dire — sans eux, la propagation du réglage à ce service n'était couverte par rien, et c'est
# précisément ce qui a laissé passer trois défauts à la revue d'E03US007.


def test_cloisonnement_par_categorie_separe_les_duellistes_sur_le_plan_de_duels() -> None:
    """Deux catégories partageant un blason ne se retrouvent pas sur la même cible.

    Vérifie du même coup que le service **propage la catégorie** jusqu'au moteur : sans
    `categorie_id` dans `ArcherAPlacer`, tous les duellistes seraient indécidables et chacun
    occuperait sa propre cible — un plan très différent de celui qu'on attend ici."""
    monde = _Monde(capacites=(4, 4))
    monde.regler_cloisonnement(Cloisonnement.CATEGORIE)
    a1 = monde.inscrire_classe((ZoneScore.DIX, ZoneScore.DIX))
    a2 = monde.inscrire_classe((ZoneScore.NEUF, ZoneScore.NEUF))
    b1 = monde.inscrire_classe(
        (ZoneScore.HUIT, ZoneScore.HUIT), categorie_id=monde.autre_categorie_id
    )
    b2 = monde.inscrire_classe(
        (ZoneScore.SEPT, ZoneScore.SEPT), categorie_id=monde.autre_categorie_id
    )

    plan = monde.service.regenerer(monde.tournoi_id, monde.phase_id)

    cible_de = {pose.archer_id: cible.index for cible in plan.cibles for pose in cible.placements}
    assert cible_de[a1] == cible_de[a2]
    assert cible_de[b1] == cible_de[b2]
    assert cible_de[a1] != cible_de[b1]


def test_sans_reglage_les_duellistes_de_deux_categories_partagent_la_cible() -> None:
    """Non-régression : sans réglage, le plan de duels est celui d'E03US009 (une seule cible)."""
    monde = _Monde(capacites=(4, 4))
    a1 = monde.inscrire_classe((ZoneScore.DIX, ZoneScore.DIX))
    b1 = monde.inscrire_classe(
        (ZoneScore.SEPT, ZoneScore.SEPT), categorie_id=monde.autre_categorie_id
    )

    plan = monde.service.regenerer(monde.tournoi_id, monde.phase_id)

    cible_de = {pose.archer_id: cible.index for cible in plan.cibles for pose in cible.placements}
    assert cible_de[a1] == cible_de[b1]


def test_duelliste_exclu_par_le_reglage_porte_la_raison_cloisonnement() -> None:
    """En réserve **pour cause de réglage**, la raison le dit — sinon l'écran reste muet.

    Une seule cible, largement assez grande : ce n'est pas la salle qui refuse le second duelliste,
    c'est le cloisonnement. La distinction commande le geste correctif de l'organisateur."""
    monde = _Monde(capacites=(4,))
    monde.regler_cloisonnement(Cloisonnement.CATEGORIE)
    monde.inscrire_classe((ZoneScore.DIX, ZoneScore.DIX))
    exclu = monde.inscrire_classe(
        (ZoneScore.SEPT, ZoneScore.SEPT), categorie_id=monde.autre_categorie_id
    )

    plan = monde.service.regenerer(monde.tournoi_id, monde.phase_id)

    raisons = {conflit.archer_id: conflit.raison for conflit in plan.conflits}
    assert raisons[exclu] is RaisonConflit.CLOISONNEMENT


def test_deplacement_manuel_refuse_nomme_le_cloisonnement_sur_le_plan_de_duels() -> None:
    """Le message de refus **nomme la cause** — dire « capacité, espace ou hauteur » enverrait
    l'organisateur libérer des places, ce qui n'y changerait rien."""
    monde = _Monde(capacites=(4, 4))
    monde.regler_cloisonnement(Cloisonnement.CATEGORIE)
    monde.inscrire_classe((ZoneScore.DIX, ZoneScore.DIX))
    intrus = monde.inscrire_classe(
        (ZoneScore.SEPT, ZoneScore.SEPT), categorie_id=monde.autre_categorie_id
    )
    monde.service.regenerer(monde.tournoi_id, monde.phase_id)
    avant = monde.service.plan_de_duels(monde.tournoi_id, monde.phase_id)

    with pytest.raises(DeplacementInvalide) as refus:
        monde.service.deplacer(
            monde.tournoi_id,
            monde.phase_id,
            monde.inscription_par_archer[intrus],
            1,
            "B",
        )

    assert "cloisonnement" in str(refus.value).lower()
    assert monde.service.plan_de_duels(monde.tournoi_id, monde.phase_id) == avant


def test_plan_de_duels_pose_avant_le_reglage_est_signale_non_conforme() -> None:
    """Activer le réglage ne déplace personne : la cible devenue non conforme est **signalée**.

    Sans ce signal, le plan de duels restait muet là où le plan de cibles affichait badge et
    bannière — la contrainte y était dure à l'écriture et invisible à la lecture."""
    monde = _Monde(capacites=(4,))
    monde.inscrire_classe((ZoneScore.DIX, ZoneScore.DIX))
    monde.inscrire_classe((ZoneScore.SEPT, ZoneScore.SEPT), categorie_id=monde.autre_categorie_id)
    monde.service.regenerer(monde.tournoi_id, monde.phase_id)  # posé **sans** réglage

    monde.regler_cloisonnement(Cloisonnement.CATEGORIE)
    plan = monde.service.plan_de_duels(monde.tournoi_id, monde.phase_id)

    assert len(plan.cibles[0].placements) == 2  # personne n'a bougé
    assert plan.cibles[0].cloisonnement_non_respecte is True


def _deux_par_categorie(monde: _Monde) -> tuple[int, int, int, int]:
    """Quatre duellistes, deux par catégorie, aux rangs 1 à 4 (tous duellistes au tour 1).

    Quatre et non trois : sur un tableau de 4, un effectif impair donne un **bye** au premier
    classé, qui n'est alors duelliste d'aucun match du tour 1 — il n'apparaît donc pas au plan
    (piège rencontré en écrivant ces tests)."""
    return (
        monde.inscrire_classe((ZoneScore.DIX, ZoneScore.DIX)),
        monde.inscrire_classe((ZoneScore.NEUF, ZoneScore.NEUF)),
        monde.inscrire_classe(
            (ZoneScore.HUIT, ZoneScore.HUIT), categorie_id=monde.autre_categorie_id
        ),
        monde.inscrire_classe(
            (ZoneScore.SEPT, ZoneScore.SEPT), categorie_id=monde.autre_categorie_id
        ),
    )


def _cible_de(plan: PlanDeDuels) -> dict[int, int]:
    return {pose.archer_id: cible.index for cible in plan.cibles for pose in cible.placements}


def test_echange_refuse_par_le_cloisonnement_le_dit_sur_le_plan_de_duels() -> None:
    """L'**échange** aussi nomme le cloisonnement (jumeau du test de qualification).

    Relevé en 2ᵉ passe : la branche existait sans test — la supprimer laissait la suite verte, et
    l'écran des duels redisait « capacité, espace ou hauteur » sur un refus de réglage, c'est-à-dire
    le défaut même que la 1ʳᵉ passe avait fait corriger."""
    monde = _Monde(capacites=(4, 4))
    monde.regler_cloisonnement(Cloisonnement.CATEGORIE)
    a1, a2, b1, _ = _deux_par_categorie(monde)
    plan = monde.service.regenerer(monde.tournoi_id, monde.phase_id)
    cible_de = _cible_de(plan)
    # Le réglage a séparé les catégories : `a2` **reste** derrière `a1`, c'est lui qui rend
    # l'échange illégal (échanger deux cibles autrement vides serait conforme).
    assert cible_de[a1] == cible_de[a2] != cible_de[b1]
    avant = monde.service.plan_de_duels(monde.tournoi_id, monde.phase_id)
    position_a1 = next(
        pose.position for cible in plan.cibles for pose in cible.placements if pose.archer_id == a1
    )

    with pytest.raises(DeplacementInvalide) as refus:
        monde.service.deplacer(
            monde.tournoi_id,
            monde.phase_id,
            monde.inscription_par_archer[b1],
            cible_de[a1],
            position_a1,
        )

    assert "cloisonnement" in str(refus.value).lower()
    assert monde.service.plan_de_duels(monde.tournoi_id, monde.phase_id) == avant


def test_pose_sur_une_cible_de_duels_deja_non_conforme_dit_de_regenerer() -> None:
    """Sur une cible de duels déjà non conforme, le refus **n'accuse pas le candidat**.

    Second jumeau manquant relevé en 2ᵉ passe : le décor existait (plan posé avant le réglage) mais
    aucun test n'y tentait de pose, donc le message n'était jamais exécuté."""
    monde = _Monde(capacites=(4, 4))
    _, _, _, b2 = _deux_par_categorie(monde)
    monde.service.regenerer(
        monde.tournoi_id, monde.phase_id
    )  # posé **sans** réglage : tous cible 1
    monde.regler_cloisonnement(Cloisonnement.CATEGORIE)
    # On libère une place sur la cible non conforme en écartant un duelliste, puis on tente de l'y
    # reposer : la cible reste mêlée sans lui, ce n'est donc pas *lui* qui mêle quoi que ce soit.
    monde.service.deplacer(
        monde.tournoi_id, monde.phase_id, monde.inscription_par_archer[b2], 2, "A"
    )
    plan = monde.service.plan_de_duels(monde.tournoi_id, monde.phase_id)
    assert plan.cibles[0].cloisonnement_non_respecte is True
    occupees = {pose.position for pose in plan.cibles[0].placements}
    libre = next(lettre for lettre in ("A", "B", "C", "D") if lettre not in occupees)

    with pytest.raises(DeplacementInvalide) as refus:
        monde.service.deplacer(
            monde.tournoi_id, monde.phase_id, monde.inscription_par_archer[b2], 1, libre
        )

    message = str(refus.value).lower()
    assert "ne respecte déjà pas" in message
    assert "régénérez" in message


def test_le_plan_de_cibles_honore_les_prelevements_comme_l_arbre() -> None:
    """**CA — plan de cibles et arbre ensemencés à l'identique**, testé là où il avait cassé.

    Correctif de revue (axe B). La parité est censée venir du **partage** de
    `application/prelevement.py` : les deux services appellent la même fonction. Mais le défaut
    d'E05US020 — plan de 8 placements pour un tableau de 4 — n'était pas dans la règle, il était
    dans le **câblage** : le plan ne l'appelait pas. Tester la fonction pure ne dit donc rien du
    fait que les deux services l'appellent, ce qui est précisément ce qui avait manqué.

    Aucun des dix-neuf tests de ce module ne déclarait de `SourcePhase` avant celui-ci : le nouveau
    chemin — le plan emprunte `resolveur_de_classement` à la saisie — était livré sans couverture.
    """
    monde = _Monde(capacites=(4,))
    _quatre_archers(monde)
    # La qualification est la phase d'ordre 1 : sans elle, la source ne viserait rien, retomberait
    # sur « tous les archers en lice », et le test passerait pour la mauvaise raison.
    monde.phases.ajouter(Phase.qualification(monde.depart_id, BaremeQualification.creer(2, 3)))
    phase = monde.phases.par_id(monde.phase_id)
    assert phase is not None
    # Le tableau ne prend que les deux premiers : le plan doit poser deux archers, pas quatre.
    monde.phases._phases[monde.phase_id] = replace(
        phase, sources=(SourcePhase.par_rangs(ordre_source=1, rang_debut=1, rang_fin=2),)
    )

    plan = monde.service.regenerer(monde.tournoi_id, monde.phase_id)

    poses = [pose.archer_id for cible in plan.cibles for pose in cible.placements]
    assert len(poses) == 2
    # …et ce sont **exactement** ceux que l'arbre fera jouer : c'est la parité, pas juste le compte.
    tableau, _ = monde.saisie_duels.reconstruire(monde.tournoi_id, monde.phase_id)
    duellistes = {
        camp.ref_id for match in tableau.matchs for camp in (match.haut, match.bas) if camp
    }
    assert set(poses) == duellistes
