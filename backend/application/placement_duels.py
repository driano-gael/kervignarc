"""Service applicatif Plan de duels — placer les duellistes côte à côte (E03US009, ADR-0048).

Assemble ce que le domaine tient séparé : le **classement** (source d'ensemencement), l'**arbre**
d'élimination (`construire_tableau`, qui produit les duels du 1er tour) et le **moteur de
placement** (qui pose les archers, réordonnés pour l'adjacence). Le plan de duels est
**matérialisé** par phase (table `placement_tableau`) et **ajustable** au glisser-déposer, à l'image
de la qualification (`ServicePlacement`, ADR-0024) — mais l'**appariement** n'est jamais persisté :
il est **recalculé** du classement à chaque régénération (déterministe, ADR-0023).

MVP (ADR-0048) : **ensemencement scratch** (au `rang_scratch`), **tour 1** uniquement (seuls duels
aux adversaires connus), **gabarit du tournoi** réutilisé. Les `Participant` de genre **équipe**
sont ignorés (pas d'entité `Equipe` avant E13US002). Le pont `Participant → inscription` vit ici
(couche haute, ADR-0028) : en individuel `ref_id` est l'`ArcherId`, résolu vers son inscription.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import partial

from application.classements import ServiceClassement
from application.erreurs import (
    DeplacementInvalide,
    GabaritDuTournoiAbsent,
    InscriptionIntrouvable,
    PhaseIntrouvable,
    PhasePasUnTableau,
    TournoiIntrouvable,
)
from domain.archer import ArcherId
from domain.gabarit_salle import Cible, GabaritSalle
from domain.inscription import Inscription, InscriptionId
from domain.participant import GenreParticipant, Participant
from domain.phase import PhaseId, TypePhase
from domain.placement import (
    Affectation,
    ArcherAPlacer,
    CiblePlacee,
    Conflit,
    Placement,
    PlanDeCibles,
    RaisonConflit,
    _ordonner_pour_adjacence,
    cible_accepte,
    cibles_avec_duel_separe,
    duels_non_cote_a_cote,
    placer,
    placer_restants,
)
from domain.politiques import Byes, Routing, Seeding
from domain.ports import (
    ArcherRepository,
    BlasonRepository,
    CategorieRepository,
    GabaritSalleRepository,
    InscriptionRepository,
    PhaseRepository,
    PlacementTableauRepository,
    TournoiRepository,
)
from domain.tableau import construire_tableau, paires_du_premier_tour
from domain.tournoi import TournoiId


@dataclass(frozen=True)
class PlanDeDuels:
    """Plan de duels rendu : le plan de cibles + le signal **côte à côte** dérivé (ADR-0048).

    `adjacence_non_garantie` = index des cibles portant un duelliste dont l'adversaire n'est pas
    côte à côte (badge par cible). `duels_separes` = les paires d'`ArcherId` non côte à côte
    (bannière récapitulative). Les deux sont **dérivés**, jamais persistés (comme la mixité).
    """

    cibles: tuple[CiblePlacee, ...]
    conflits: tuple[Conflit, ...]
    adjacence_non_garantie: frozenset[int]
    duels_separes: tuple[tuple[ArcherId, ArcherId], ...]


@dataclass
class _Contexte:
    """Décor d'une phase de tableau : gabarit, duellistes du 1er tour et leurs jointures.

    `donnees` ne contient que les duellistes **plaçables** (blason exploitable) ; `partenaire`
    associe chaque archer à son adversaire (pour l'ordre d'adjacence) ; `paires` liste les duels en
    `ArcherId` (pour le signal). Un archer sans inscription n'atteint pas ce décor.
    """

    phase_id: PhaseId
    gabarit: GabaritSalle
    inscriptions: list[Inscription] = field(default_factory=list)
    donnees: dict[ArcherId, ArcherAPlacer] = field(default_factory=dict)
    sans_blason: set[InscriptionId] = field(default_factory=set)
    archer_par_inscription: dict[InscriptionId, ArcherId] = field(default_factory=dict)
    inscription_par_archer: dict[ArcherId, InscriptionId] = field(default_factory=dict)
    partenaire: dict[ArcherId, ArcherId] = field(default_factory=dict)
    paires: list[tuple[ArcherId, ArcherId]] = field(default_factory=list)

    def est_placable(self, inscription_id: InscriptionId) -> bool:
        archer_id = self.archer_par_inscription.get(inscription_id)
        return archer_id is not None and archer_id in self.donnees


class ServicePlacementDuels:
    """Cas d'usage du plan de duels : lire, régénérer et ajuster le placement des duellistes."""

    def __init__(
        self,
        tournois: TournoiRepository,
        phases: PhaseRepository,
        gabarits: GabaritSalleRepository,
        inscriptions: InscriptionRepository,
        archers: ArcherRepository,
        categories: CategorieRepository,
        blasons: BlasonRepository,
        placements: PlacementTableauRepository,
        classements: ServiceClassement,
        seeding: Seeding,
        byes: Byes,
        routing: Routing,
    ) -> None:
        self._tournois = tournois
        self._phases = phases
        self._gabarits = gabarits
        self._inscriptions = inscriptions
        self._archers = archers
        self._categories = categories
        self._blasons = blasons
        self._placements = placements
        self._classements = classements
        # Politiques du tableau (E05US003) : le format est de la configuration (règle 2). MVP =
        # défauts (serpent / byes aux mieux classés / élimination sèche) — ADR-0048.
        self._seeding = seeding
        self._byes = byes
        self._routing = routing

    # --- Lecture -------------------------------------------------------------------------------

    def plan_de_duels(self, tournoi_id: TournoiId, phase_id: PhaseId) -> PlanDeDuels:
        """Renvoie le plan de duels **persisté** d'une phase (cibles + réserve + signal adjacence).

        Lève `TournoiIntrouvable` / `PhaseIntrouvable` (404), `PhasePasUnTableau` (409, la phase
        n'est pas une élimination directe) ou `GabaritDuTournoiAbsent`.
        """
        contexte = self._charger(tournoi_id, phase_id)
        return self._construire_plan(contexte, self._placements.par_phase(phase_id))

    # --- Écritures (via la file) ---------------------------------------------------------------

    def regenerer(self, tournoi_id: TournoiId, phase_id: PhaseId) -> PlanDeDuels:
        """(Re)génère le plan de duels auto et **écrase** l'existant — sert aussi d'« annuler ».

        Déterministe (ADR-0023) : recalcule l'arbre du classement, réordonne l'entrée pour
        l'adjacence (`_ordonner_pour_adjacence`), place, matérialise. Pas d'alerte d'impact
        (E12US007) : au tour 1 aucun score de duel n'existe, jamais de régénération « massive ».
        """
        contexte = self._charger(tournoi_id, phase_id)
        plan = placer(
            contexte.gabarit.cibles,
            tuple(contexte.donnees.values()),
            ordonner=partial(_ordonner_pour_adjacence, partenaire=contexte.partenaire),
        )
        affectations = [
            Affectation(
                inscription_id=contexte.inscription_par_archer[pose.archer_id],
                cible_index=cible.index,
                position=pose.position,
            )
            for cible in plan.cibles
            for pose in cible.placements
        ]
        self._placements.definir_plan(phase_id, affectations)
        return self._construire_plan(contexte, affectations)

    def deplacer(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        inscription_id: InscriptionId,
        cible_index: int | None,
        position: str | None,
    ) -> PlanDeDuels:
        """Déplace un duelliste vers une case, l'échange avec son occupant, ou le met en réserve.

        `cible_index is None` → **mise en réserve** (toujours possible). Sinon dépôt : case libre →
        déplacement simple ; case occupée → **échange atomique** (tout ou rien). Toute violation
        lève `DeplacementInvalide` (409) **sans** rien écrire (état inchangé).
        """
        contexte = self._charger(tournoi_id, phase_id)
        if inscription_id not in contexte.archer_par_inscription:
            raise InscriptionIntrouvable(
                f"L'inscription {inscription_id} ne dispute pas la phase {phase_id}."
            )

        if cible_index is None:
            self._placements.retirer(phase_id, inscription_id)
            return self._construire_plan(contexte, self._placements.par_phase(phase_id))

        if position is None:
            raise DeplacementInvalide(
                "Une position est requise pour poser un archer sur une cible."
            )
        cible = self._cible(contexte.gabarit, cible_index)
        if position not in cible.positions:
            raise DeplacementInvalide(
                f"La position {position} n'existe pas sur la cible {cible_index}."
            )
        if not contexte.est_placable(inscription_id):
            raise DeplacementInvalide(
                "Ce duelliste n'a pas de blason : sa place ne peut pas être déterminée."
            )

        affectations = self._placements.par_phase(phase_id)
        source = next((a for a in affectations if a.inscription_id == inscription_id), None)
        occupant = next(
            (
                a
                for a in affectations
                if a.cible_index == cible_index
                and a.position == position
                and a.inscription_id != inscription_id
            ),
            None,
        )
        candidat = contexte.donnees[contexte.archer_par_inscription[inscription_id]]

        if occupant is None:
            self._valider_pose(contexte, affectations, cible, candidat, {inscription_id})
            self._placements.poser_plusieurs(
                phase_id, [Affectation(inscription_id, cible_index, position)]
            )
        else:
            self._echanger(contexte, affectations, cible, candidat, source, occupant, phase_id)
        return self._construire_plan(contexte, self._placements.par_phase(phase_id))

    def placer_les_restants(self, tournoi_id: TournoiId, phase_id: PhaseId) -> PlanDeDuels:
        """Complète la réserve automatiquement dans les trous du plan, **sans bouger les placés**.

        Ce qu'aucune cible ne peut accueillir reste en réserve. Réordonne les restants pour
        l'adjacence (un duel encore entier tombe côte à côte quand la place le permet).
        """
        contexte = self._charger(tournoi_id, phase_id)
        affectations = self._placements.par_phase(phase_id)
        plan_actuel = self._plan_de_cibles(contexte, affectations)
        placees = {
            pose.inscription_id
            for cible in plan_actuel.cibles
            for pose in cible.placements
            if pose.inscription_id is not None
        }
        a_placer = tuple(
            contexte.donnees[contexte.archer_par_inscription[inscription.id]]
            for inscription in contexte.inscriptions
            if inscription.id is not None
            and inscription.id not in placees
            and inscription.id not in contexte.sans_blason
        )
        poses, _ = placer_restants(
            contexte.gabarit.cibles,
            plan_actuel.cibles,
            contexte.donnees,
            a_placer,
            ordonner=partial(_ordonner_pour_adjacence, partenaire=contexte.partenaire),
        )
        nouvelles = [
            Affectation(
                inscription_id=contexte.inscription_par_archer[pose.archer_id],
                cible_index=pose.cible_index,
                position=pose.position,
            )
            for pose in poses
        ]
        self._placements.poser_plusieurs(phase_id, nouvelles)
        return self._construire_plan(contexte, self._placements.par_phase(phase_id))

    # --- Interne : validation d'un déplacement (calqué sur ServicePlacement, ADR-0048) ---------

    def _echanger(
        self,
        contexte: _Contexte,
        affectations: list[Affectation],
        cible_cible: Cible,
        candidat: ArcherAPlacer,
        source: Affectation | None,
        occupant: Affectation,
        phase_id: PhaseId,
    ) -> None:
        """Valide et applique l'échange atomique du duelliste déplacé avec l'occupant de la case."""
        if source is None:
            raise DeplacementInvalide(
                "Cette case est occupée : déposez sur une place libre, ou échangez deux duellistes "
                "déjà placés."
            )
        occupant_archer = contexte.archer_par_inscription[occupant.inscription_id]
        occupant_candidat = contexte.donnees[occupant_archer]
        cible_source = self._cible(contexte.gabarit, source.cible_index)
        exclus = {source.inscription_id, occupant.inscription_id}
        tient = self._accepte(
            contexte, affectations, cible_cible, candidat, exclus
        ) and self._accepte(contexte, affectations, cible_source, occupant_candidat, exclus)
        if not tient:
            raise DeplacementInvalide(
                "Échange refusé : l'un des deux ne tient pas à la place de l'autre "
                "(capacité, espace ou hauteur)."
            )
        self._placements.poser_plusieurs(
            phase_id,
            [
                Affectation(source.inscription_id, cible_cible.index, occupant.position),
                Affectation(occupant.inscription_id, source.cible_index, source.position),
            ],
        )

    def _valider_pose(
        self,
        contexte: _Contexte,
        affectations: list[Affectation],
        cible: Cible,
        candidat: ArcherAPlacer,
        exclus: set[InscriptionId],
    ) -> None:
        """Refuse la pose si la cible ne peut pas accueillir le candidat (déplacement invalide)."""
        if not self._accepte(contexte, affectations, cible, candidat, exclus):
            raise DeplacementInvalide(
                "Déplacement refusé : la cible ne peut pas accueillir ce duelliste "
                "(capacité, espace ou hauteur)."
            )

    def _accepte(
        self,
        contexte: _Contexte,
        affectations: list[Affectation],
        cible: Cible,
        candidat: ArcherAPlacer,
        exclus: set[InscriptionId],
    ) -> bool:
        """Vrai si `candidat` tient sur `cible` (occupants actuels lus des affectations)."""
        occupants = tuple(
            contexte.donnees[contexte.archer_par_inscription[affectation.inscription_id]]
            for affectation in affectations
            if affectation.cible_index == cible.index
            and affectation.inscription_id not in exclus
            and contexte.est_placable(affectation.inscription_id)
        )
        return cible_accepte(cible, occupants, candidat)

    def _cible(self, gabarit: GabaritSalle, cible_index: int) -> Cible:
        """Renvoie la cible d'index donné, ou lève `DeplacementInvalide` si elle n'existe pas."""
        for cible in gabarit.cibles:
            if cible.index == cible_index:
                return cible
        raise DeplacementInvalide(f"La cible {cible_index} n'existe pas dans ce tournoi.")

    # --- Interne : construction du plan rendu --------------------------------------------------

    def _construire_plan(self, contexte: _Contexte, affectations: list[Affectation]) -> PlanDeDuels:
        """Assemble le plan de cibles depuis les affectations, puis dérive le signal côte à côte."""
        plan = self._plan_de_cibles(contexte, affectations)
        return PlanDeDuels(
            cibles=plan.cibles,
            conflits=plan.conflits,
            adjacence_non_garantie=cibles_avec_duel_separe(plan, contexte.paires),
            duels_separes=duels_non_cote_a_cote(plan, contexte.paires),
        )

    def _plan_de_cibles(self, contexte: _Contexte, affectations: list[Affectation]) -> PlanDeCibles:
        """Cibles peuplées + réserve (jumeau de `ServicePlacement._construire_plan`, sans mixité).

        Une affectation dont la cible/position n'est plus dans le gabarit retombe en **réserve** au
        lieu de disparaître (jamais d'archer perdu en silence — ligne rouge du CA).
        """
        cibles_par_index = {cible.index: cible for cible in contexte.gabarit.cibles}
        placements_par_cible: dict[int, list[Placement]] = {}
        placees: set[InscriptionId] = set()
        for affectation in affectations:
            if not contexte.est_placable(affectation.inscription_id):
                continue
            cible = cibles_par_index.get(affectation.cible_index)
            if cible is None or affectation.position not in cible.positions:
                continue
            archer_id = contexte.archer_par_inscription[affectation.inscription_id]
            placees.add(affectation.inscription_id)
            placements_par_cible.setdefault(affectation.cible_index, []).append(
                Placement(
                    position=affectation.position,
                    archer_id=archer_id,
                    blason_id=contexte.donnees[archer_id].blason_id,
                    inscription_id=affectation.inscription_id,
                )
            )

        def _figer(cible: Cible) -> CiblePlacee:
            poses = sorted(placements_par_cible.get(cible.index, []), key=lambda p: p.position)
            return CiblePlacee(index=cible.index, capacite=cible.capacite, placements=tuple(poses))

        cibles = tuple(_figer(cible) for cible in contexte.gabarit.cibles)
        return PlanDeCibles(cibles=cibles, conflits=self._reserve(contexte, cibles, placees))

    def _reserve(
        self, contexte: _Contexte, cibles: tuple[CiblePlacee, ...], placees: set[InscriptionId]
    ) -> tuple[Conflit, ...]:
        """Réserve = duellistes non posés, avec leur **raison dérivée** (non persistée)."""
        cible_par_index = {cible.index: cible for cible in contexte.gabarit.cibles}
        occupants_par_index = {
            cible.index: tuple(contexte.donnees[p.archer_id] for p in cible.placements)
            for cible in cibles
        }
        conflits: list[Conflit] = []
        for inscription in contexte.inscriptions:
            if inscription.id is None or inscription.id in placees:
                continue
            archer_id = inscription.archer_id
            if inscription.id in contexte.sans_blason:
                conflits.append(Conflit(archer_id, RaisonConflit.SANS_BLASON, inscription.id))
                continue
            candidat = contexte.donnees[archer_id]
            placable = any(
                cible_accepte(cible_par_index[index], occupants, candidat)
                for index, occupants in occupants_par_index.items()
            )
            raison = RaisonConflit.EN_RESERVE if placable else RaisonConflit.NON_PLACE
            conflits.append(Conflit(archer_id, raison, inscription.id))
        return tuple(conflits)

    # --- Interne : chargement du décor (classement → arbre → duellistes) -----------------------

    def _charger(self, tournoi_id: TournoiId, phase_id: PhaseId) -> _Contexte:
        """Valide les gardes et assemble le décor : classement → arbre → duellistes du 1er tour."""
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        phase = self._phases.par_id(phase_id)
        if phase is None or phase.tournoi_id != tournoi_id:
            raise PhaseIntrouvable(f"Aucune phase {phase_id} dans le tournoi {tournoi_id}.")
        if phase.type is not TypePhase.ELIMINATION_DIRECTE:
            raise PhasePasUnTableau(
                f"La phase {phase_id} n'est pas une élimination directe : pas de plan de duels."
            )
        gabarit = self._gabarits.par_tournoi(tournoi_id)
        if gabarit is None:
            raise GabaritDuTournoiAbsent(
                f"Aucun gabarit de salle n'est appliqué au tournoi {tournoi_id}."
            )

        contexte = _Contexte(phase_id=phase_id, gabarit=gabarit)
        classement = self._classements.pour_tournoi(tournoi_id)
        participants = [
            Participant.individuel(ligne.archer_id)
            for ligne in sorted(classement.lignes, key=lambda ligne: ligne.rang_scratch)
        ]
        if len(participants) < 2:
            return contexte  # pas de tableau possible : plan vide, sans duel

        tableau = construire_tableau(participants, self._seeding, self._byes, self._routing)
        for haut, bas in paires_du_premier_tour(tableau):
            self._enregistrer_duel(contexte, haut, bas)
        return contexte

    def _enregistrer_duel(self, contexte: _Contexte, haut: Participant, bas: Participant) -> None:
        """Résout un duel (Participant → archer → inscription) et l'inscrit au décor.

        Les `Participant` de genre **équipe** sont ignorés (hors périmètre, E13US002). Un archer
        sans inscription au tournoi n'est pas plaçable (rien à persister) : le duel est alors
        incomplet et ressortira **signalé** (un membre non posé) — jamais un plantage.
        """
        archer_haut = self._archer_du(haut)
        archer_bas = self._archer_du(bas)
        if archer_haut is None or archer_bas is None:
            return
        inscription_haut = self._inscrire_au_decor(contexte, archer_haut)
        inscription_bas = self._inscrire_au_decor(contexte, archer_bas)
        contexte.paires.append((archer_haut, archer_bas))
        if inscription_haut is not None and inscription_bas is not None:
            contexte.partenaire[archer_haut] = archer_bas
            contexte.partenaire[archer_bas] = archer_haut

    @staticmethod
    def _archer_du(participant: Participant) -> ArcherId | None:
        """L'`ArcherId` d'un participant individuel, ou `None` pour une équipe (hors périmètre)."""
        if participant.genre is not GenreParticipant.INDIVIDUEL:
            return None
        return participant.ref_id

    def _inscrire_au_decor(self, contexte: _Contexte, archer_id: ArcherId) -> InscriptionId | None:
        """Rattache un archer duelliste au décor (inscription + `ArcherAPlacer`), une fois.

        Résout l'inscription du tournoi de façon **déterministe** (la plus petite `id` parmi les
        inscriptions de l'archer — MVP mono-départ, ADR-0048). Renvoie l'inscription, ou `None` si
        l'archer n'a aucune inscription (non plaçable). Idempotent : un archer déjà enregistré n'est
        pas rechargé.
        """
        if archer_id in contexte.inscription_par_archer:
            return contexte.inscription_par_archer[archer_id]
        inscriptions = [i for i in self._inscriptions.par_archer(archer_id) if i.id is not None]
        if not inscriptions:
            return None
        inscription = min(inscriptions, key=lambda i: i.id or 0)
        assert inscription.id is not None
        contexte.inscriptions.append(inscription)
        contexte.archer_par_inscription[inscription.id] = archer_id
        contexte.inscription_par_archer[archer_id] = inscription.id
        entree = self._archer_a_placer(archer_id)
        if entree is None:
            contexte.sans_blason.add(inscription.id)
        else:
            contexte.donnees[archer_id] = entree
        return inscription.id

    def _archer_a_placer(self, archer_id: ArcherId) -> ArcherAPlacer | None:
        """Reconstruit l'entrée du moteur pour un archer, ou `None` si sa fraction est inconnue.

        Jointure archer → catégorie → blason par défaut (2ᵉ occurrence de celle de
        `ServicePlacement` — extraction reportée au 3ᵉ cas, règle 12 / ADR-0048).
        """
        archer = self._archers.par_id(archer_id)
        if archer is None:
            return None
        categorie = self._categories.par_id(archer.categorie_id)
        if categorie is None:
            return None
        blason_id = categorie.blason_id
        if blason_id is None:
            return None
        blason = self._blasons.par_id(blason_id)
        if blason is None:
            return None
        return ArcherAPlacer(
            archer_id=archer_id,
            blason_id=blason_id,
            taille=blason.taille,
            capacite_blason=blason.capacite,
            hauteur_cm=categorie.hauteur_cm,
            club_id=archer.club_id,
        )
