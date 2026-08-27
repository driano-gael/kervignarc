"""Plan de duels — **matérialisé** par phase et ajustable, comme le plan de qualification.

⚠️ **L'appariement, lui, n'est JAMAIS persisté** : il est recalculé du classement à chaque
régénération (déterministe, ADR-0023). MVP : ensemencement scratch, tour 1 seulement, gabarit du
tournoi réutilisé. Les participants de genre équipe sont ignorés — pas d'entité `Equipe`.
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
    PrelevementEnAttente,
    TournoiIntrouvable,
)
from application.portee import phase_du_tournoi
from application.prelevement import preleves, profondeur_de
from application.saisie_duels import ServiceSaisieDuels
from domain.archer import ArcherId
from domain.cloisonnement import Cloisonnement
from domain.contrat_phase import TYPES_EN_TABLEAU_JOUE
from domain.gabarit_salle import Cible, GabaritSalle
from domain.inscription import Inscription, InscriptionId
from domain.participant import GenreParticipant, Participant
from domain.phase import PhaseId
from domain.placement import (
    Affectation,
    ArcherAPlacer,
    CiblePlacee,
    Conflit,
    MotifRefus,
    Placement,
    PlanDeCibles,
    RaisonConflit,
    _ordonner_pour_adjacence,
    cible_accepte,
    cible_cloisonnement_non_respecte,
    cibles_avec_duel_separe,
    duels_non_cote_a_cote,
    motif_de_refus,
    placer,
    placer_restants,
)
from domain.politiques import Byes, RegistrePolitiques, Routing, Seeding
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
    # Cloisonnement des cibles réglé sur le tournoi (E03US007) : le plan de duels est posé dans la
    # **même salle** que la qualification, un réglage qui ne vaudrait que pour l'une serait
    # incompréhensible pour l'organisateur.
    cloisonnement: Cloisonnement
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
        registre: RegistrePolitiques,
        saisie_duels: ServiceSaisieDuels,
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
        # La **profondeur** n'est plus injectée ici depuis E06US006 : elle se lit sur la phase
        # (`profondeur_de`), qui la porte enfin. Garder le paramètre aurait laissé deux sources —
        # celle du câblage, celle de l'organisateur — dont l'une aurait silencieusement gagné.
        self._registre = registre
        # E05US024 : **pas** pour saisir, uniquement pour emprunter sa résolution de classement
        # amont — reconstruire un tableau source est son métier, pas celui du plan de cibles. Le
        # sens de dépendance est sûr : `saisie_duels` ne connaît pas le placement, et `palmares`
        # emprunte déjà ce chemin.
        self._saisie_duels = saisie_duels

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
            cloisonnement=contexte.cloisonnement,
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
        lève `DeplacementInvalide` (409) sans rien écrire d'**observable** (l'état inchangé) : la
        purge des poses orphelines (`_poses_a_jour`) peut précéder un refus 409, mais elle ne retire
        que des lignes déjà **invisibles** en lecture — l'état rendu, lui, ne bouge pas.
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
                "Un couloir de tir est requis pour poser un archer sur une cible."
            )
        cible = self._cible(contexte.gabarit, cible_index)
        if position not in cible.positions:
            raise DeplacementInvalide(
                f"Le couloir de tir {position} n'existe pas sur la cible {cible_index}."
            )
        if not contexte.est_placable(inscription_id):
            raise DeplacementInvalide(
                "Ce duelliste n'a pas de blason : son couloir de tir ne peut pas être déterminé."
            )

        affectations = self._poses_a_jour(phase_id, contexte)
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
        affectations = self._poses_a_jour(phase_id, contexte)
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
            cloisonnement=contexte.cloisonnement,
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

    def _poses_a_jour(self, phase_id: PhaseId, contexte: _Contexte) -> list[Affectation]:
        """Lit les poses de la phase après avoir **purgé** celles devenues orphelines (ADR-0048).

        L'appariement est **recalculé** à chaque opération (le classement décide qui est duelliste
        du 1er tour), mais la pose est **persistée**. Une pose dont l'inscription n'est **plus**
        duelliste — un archer classé plus tard décale l'arbre (byes), l'ancien duelliste en sort —
        est **orpheline** : déjà masquée en lecture (`est_placable` l'écarte du plan rendu), elle
        est ici, sur un **chemin d'écriture** (dans la file), **retirée pour de bon**. Sans quoi la
        détection d'occupant d'un déplacement tomberait sur une ligne « fantôme » (case visiblement
        vide mais présente en base) — 500 sur `_echanger`, ou double pose via `placer_les_restants`.
        Le plan de duels fait autorité **après régénération** (qui réécrit tout) ; entre-temps,
        l'orpheline est inerte puis purgée au premier ajustement. Arbitrage tranché à la revue
        d'E03US009 (reversé dans `stories/`).
        """
        a_jour: list[Affectation] = []
        for affectation in self._placements.par_phase(phase_id):
            if affectation.inscription_id in contexte.archer_par_inscription:
                a_jour.append(affectation)
            else:
                self._placements.retirer(phase_id, affectation.inscription_id)
        return a_jour

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
                "Cette case est occupée : déposez sur un couloir libre, ou échangez "
                "deux duellistes déjà placés."
            )
        occupant_archer = contexte.archer_par_inscription[occupant.inscription_id]
        occupant_candidat = contexte.donnees[occupant_archer]
        cible_source = self._cible(contexte.gabarit, source.cible_index)
        exclus = {source.inscription_id, occupant.inscription_id}
        tient = self._accepte(
            contexte, affectations, cible_cible, candidat, exclus
        ) and self._accepte(contexte, affectations, cible_source, occupant_candidat, exclus)
        if not tient:
            # Motif demandé au domaine pour **chacune des deux jambes** (jumeau de
            # `ServicePlacement._echanger`) : celle qui refuse n'est pas forcément celle qu'on
            # regarde. Relevé en 2e passe — l'échange gardait le message unique que `_valider_pose`
            # venait d'abandonner.
            self._refuser_echange(contexte, affectations, cible_cible, candidat, exclus)
            self._refuser_echange(contexte, affectations, cible_source, occupant_candidat, exclus)
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
        """Refuse la pose si la cible ne peut pas accueillir le candidat (déplacement invalide).

        Le message **nomme la cause**, comme en qualification (E03US007) : un refus dû au
        cloisonnement se corrige en desserrant un réglage, pas en libérant de la place — et sur une
        cible **déjà** non conforme, ce n'est pas le candidat qui mêle quoi que ce soit."""
        motif = self._motif(contexte, affectations, cible, candidat, exclus)
        if motif is MotifRefus.AUCUN:
            return
        if motif is MotifRefus.CLOISONNEMENT_CIBLE_DEJA_NON_CONFORME:
            raise DeplacementInvalide(
                f"Déplacement refusé : la cible {cible.index} ne respecte déjà pas le "
                "cloisonnement demandé. Régénérez le plan de duels, ou videz-la, avant d'y poser "
                "un duelliste."
            )
        if motif is MotifRefus.CLOISONNEMENT_MELANGE:
            raise DeplacementInvalide(
                "Déplacement refusé : le cloisonnement des cibles interdit de mêler ces duellistes "
                "sur une même cible."
            )
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
        return cible_accepte(
            cible,
            self._occupants(contexte, affectations, cible, exclus),
            candidat,
            cloisonnement=contexte.cloisonnement,
        )

    def _motif(
        self,
        contexte: _Contexte,
        affectations: list[Affectation],
        cible: Cible,
        candidat: ArcherAPlacer,
        exclus: set[InscriptionId],
    ) -> MotifRefus:
        """Pourquoi `cible` refuse `candidat` — la règle est au domaine, ici le seul décor.

        La 1ʳᵉ passe de revue avait fait recopier ici l'enchaînement « accepte ? accepte sans
        réglage ? cible déjà non conforme ? » du service jumeau — 4ᵉ occurrence d'un même
        raisonnement, dans deux fichiers qu'ADR-0048 signale déjà comme dupliqués. La 2ᵉ passe l'a
        relevé : la règle est remontée en `domain.placement.motif_de_refus`, il ne reste ici que le
        **vocabulaire** (« duelliste » et non « archer »)."""
        return motif_de_refus(
            cible,
            self._occupants(contexte, affectations, cible, exclus),
            candidat,
            cloisonnement=contexte.cloisonnement,
        )

    def _refuser_echange(
        self,
        contexte: _Contexte,
        affectations: list[Affectation],
        cible: Cible,
        candidat: ArcherAPlacer,
        exclus: set[InscriptionId],
    ) -> None:
        """Lève le refus d'échange **nommé** si cette jambe bloque ; sinon rend la main."""
        motif = self._motif(contexte, affectations, cible, candidat, exclus)
        if motif is MotifRefus.CLOISONNEMENT_CIBLE_DEJA_NON_CONFORME:
            raise DeplacementInvalide(
                f"Échange refusé : la cible {cible.index} ne respecte déjà pas le cloisonnement "
                "demandé. Régénérez le plan de duels, ou videz-la, avant d'y échanger un duelliste."
            )
        if motif is MotifRefus.CLOISONNEMENT_MELANGE:
            raise DeplacementInvalide(
                "Échange refusé : le cloisonnement des cibles interdit de mêler ces duellistes "
                "sur une même cible."
            )

    def _occupants(
        self,
        contexte: _Contexte,
        affectations: list[Affectation],
        cible: Cible,
        exclus: set[InscriptionId],
    ) -> tuple[ArcherAPlacer, ...]:
        """Duellistes actuellement posés sur une cible, hors inscriptions `exclus`.

        Prend la `Cible` et non son index, contrairement au jumeau de `ServicePlacement` : tous les
        appelants d'ici ont l'objet en main. Divergence de signature relevée en revue et **assumée**
        — l'aligner pour l'alignement ferait passer par `cible.index` puis re-résoudre la cible."""
        return tuple(
            contexte.donnees[contexte.archer_par_inscription[affectation.inscription_id]]
            for affectation in affectations
            if affectation.cible_index == cible.index
            and affectation.inscription_id not in exclus
            and contexte.est_placable(affectation.inscription_id)
        )

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
            # `cloisonnement_non_respecte` (E03US007) se recalcule ici comme en qualification : le
            # plan de duels est posé dans la **même salle**, sous le **même** réglage. L'omettre
            # laissait un plan de duels antérieur au réglage muet là où le plan de cibles, lui,
            # affichait badge et bannière — la contrainte y était dure à l'écriture et invisible à
            # la lecture. `mixite_non_garantie` reste, elle, hors sujet ici (préférence de
            # qualification, E03US006).
            poses = sorted(placements_par_cible.get(cible.index, []), key=lambda p: p.position)
            occupants = [contexte.donnees[pose.archer_id] for pose in poses]
            return CiblePlacee(
                index=cible.index,
                capacite=cible.capacite,
                placements=tuple(poses),
                cloisonnement_non_respecte=cible_cloisonnement_non_respecte(
                    contexte.cloisonnement, occupants
                ),
            )

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
                cible_accepte(
                    cible_par_index[index],
                    occupants,
                    candidat,
                    cloisonnement=contexte.cloisonnement,
                )
                for index, occupants in occupants_par_index.items()
            )
            if placable:
                raison = RaisonConflit.EN_RESERVE
            elif any(
                motif_de_refus(
                    cible_par_index[index],
                    occupants,
                    candidat,
                    cloisonnement=contexte.cloisonnement,
                )
                is not MotifRefus.BUDGETS
                for index, occupants in occupants_par_index.items()
            ):
                # Même distinction qu'en qualification : c'est le **réglage** qui exclut, pas la
                # salle (E03US007) — deux gestes différents pour l'organisateur.
                raison = RaisonConflit.CLOISONNEMENT
            else:
                raison = RaisonConflit.NON_PLACE
            conflits.append(Conflit(archer_id, raison, inscription.id))
        return tuple(conflits)

    # --- Interne : chargement du décor (classement → arbre → duellistes) -----------------------

    def _charger(self, tournoi_id: TournoiId, phase_id: PhaseId) -> _Contexte:
        """Valide les gardes et assemble le décor : classement → arbre → duellistes du 1er tour."""
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        phase = phase_du_tournoi(self._phases, tournoi_id, phase_id)
        if phase is None:
            raise PhaseIntrouvable(f"Aucune phase {phase_id} dans le tournoi {tournoi_id}.")
        # Filtre **dérivé** du contrat de phase (ADR-0083) : un arbre de duels, monté par un
        # service. Une phase de poules produit bien un plan de cibles, mais `par_bloc_de_poule` —
        # c'est `ServicePoules` qui le pose, pas ce service-ci.
        if phase.type not in TYPES_EN_TABLEAU_JOUE:
            raise PhasePasUnTableau(
                f"La phase {phase_id} n'est pas une élimination directe : pas de plan de duels."
            )
        gabarit = self._gabarits.par_tournoi(tournoi_id)
        if gabarit is None:
            raise GabaritDuTournoiAbsent(
                f"Aucun gabarit de salle n'est appliqué au tournoi {tournoi_id}."
            )

        contexte = _Contexte(
            phase_id=phase_id, gabarit=gabarit, cloisonnement=tournoi.cloisonnement
        )
        # Le classement **du départ de cette phase** (ADR-0075) — même ensemencement que la
        # reconstruction, donc même portée : le plan pose les duellistes que le tableau jouera.
        classement = self._classements.pour_depart(phase.depart_id)
        # ⚠️ **Même ensemencement que la reconstruction, par la même fonction** (E05US020) : le
        # plan pose les duellistes que le tableau fera jouer. Les deux règles étaient **recopiées**,
        # avec un commentaire affirmant leur parité ; la recopie a lâché à la première évolution —
        # E05US020 a fait consommer les prélèvements d'un seul côté, et la revue a mesuré un plan de
        # 8 placements pour un tableau de 4. Un archer posté sur une butte sans duel, un autre en
        # face du mauvais adversaire, invisibles jusqu'au jour J.
        # E05US024 : le résolveur vient de `ServiceSaisieDuels` — c'est **lui** qui sait
        # reconstruire
        # un tableau amont pour le lire comme un classement. Le prendre ici plutôt que de le
        # réimplémenter est ce qui garantit que le plan pose les duellistes que l'arbre fait jouer :
        # deux résolutions distinctes rouvriraient l'écart mesuré à E05US020 (plan de 8, tableau
        # de 4), un cran plus loin dans la chaîne.
        try:
            participants = [
                Participant.individuel(ligne.archer_id)
                for ligne in preleves(
                    phase,
                    classement,
                    self._saisie_duels.resolveur_de_classement(tournoi_id, phase.depart_id),
                )
            ]
        except PrelevementEnAttente:
            # La source n'a pas encore départagé les places prélevées (ADR-0081). On retombe sur le
            # chemin **gracieux** déjà prévu ci-dessous pour « pas assez de participants » : un plan
            # vide, pas un écran en erreur. Laisser remonter donnerait un 409 sur le plan de cibles
            # pendant que l'écran public, lui, dit poliment « en attente » — trois surfaces, trois
            # comportements pour le même état (relevé en revue, axes C2 et adversarial).
            return contexte
        if len(participants) < 2:
            return contexte  # pas de tableau possible : plan vide, sans duel

        tableau = construire_tableau(
            participants,
            self._seeding,
            self._byes,
            self._routing,
            profondeur_de(phase, self._registre),
        )
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
            categorie_id=archer.categorie_id,
        )
