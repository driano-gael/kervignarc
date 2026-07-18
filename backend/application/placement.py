"""Service applicatif Placement — plan de cibles **matérialisé et ajustable** (E03US004, ADR-0024).

E03US001 recalculait le plan à chaque lecture ; E03US004 le **matérialise** (table `placement`, une
affectation par inscription) pour le rendre ajustable au glisser-déposer. Ce service :

- **lit** le plan persisté (`plan_de_cibles`) et range les inscrits sans affectation en **réserve**,
  avec une **raison dérivée** (sans blason / saturé / en attente) — jamais persistée ;
- **régénère** (`regenerer`) le plan depuis le moteur glouton déterministe — c'est aussi « annuler
  les modifications » (ADR-0024) ;
- **déplace / échange / met en réserve** un archer (`deplacer`), en **validant** contre l'état
  courant (refus en bloc, état inchangé — CA « déplacement invalide ») ;
- **place les restants** (`placer_les_restants`) : comble la réserve sans bouger les placés.

Les écritures passent par la **file** (règle 7) — routage côté API ; le service reste synchrone. La
jointure archer → catégorie → blason par défaut (héritée d'E03US001) nourrit le moteur pur en
`ArcherAPlacer` ; un archer sans blason exploitable est un conflit `SANS_BLASON`, jamais placé.
"""

from __future__ import annotations

from dataclasses import dataclass

from application.erreurs import (
    DepartIntrouvable,
    DeplacementInvalide,
    GabaritDuTournoiAbsent,
    InscriptionIntrouvable,
    TournoiIntrouvable,
)
from domain.archer import ArcherId
from domain.depart import DepartId
from domain.gabarit_salle import Cible, GabaritSalle
from domain.inscription import Inscription, InscriptionId
from domain.placement import (
    Affectation,
    ArcherAPlacer,
    CiblePlacee,
    Conflit,
    Placement,
    PlanDeCibles,
    RaisonConflit,
    cible_accepte,
    placer,
    placer_restants,
)
from domain.ports import (
    ArcherRepository,
    BlasonRepository,
    CategorieRepository,
    DepartRepository,
    GabaritSalleRepository,
    InscriptionRepository,
    PlacementRepository,
    TournoiRepository,
)
from domain.tournoi import TournoiId


@dataclass
class _Contexte:
    """Décor d'un départ, chargé une fois par opération : cibles, inscrits et jointures.

    `donnees` ne contient que les archers **plaçables** (blason exploitable) ; `sans_blason` liste
    les inscriptions dont l'archer n'a pas de fraction connue. Les tables `archer ↔ inscription`
    sont 1:1 sur un départ (contrainte d'unicité), on garde les deux sens."""

    gabarit: GabaritSalle
    inscriptions: list[Inscription]
    donnees: dict[ArcherId, ArcherAPlacer]
    sans_blason: set[InscriptionId]
    archer_par_inscription: dict[InscriptionId, ArcherId]
    inscription_par_archer: dict[ArcherId, InscriptionId]

    def est_placable(self, inscription_id: InscriptionId) -> bool:
        archer_id = self.archer_par_inscription.get(inscription_id)
        return archer_id is not None and archer_id in self.donnees


class ServicePlacement:
    """Cas d'usage du placement : lire, régénérer et ajuster le plan de cibles d'un départ."""

    def __init__(
        self,
        tournois: TournoiRepository,
        departs: DepartRepository,
        gabarits: GabaritSalleRepository,
        inscriptions: InscriptionRepository,
        archers: ArcherRepository,
        categories: CategorieRepository,
        blasons: BlasonRepository,
        placements: PlacementRepository,
    ) -> None:
        self._tournois = tournois
        self._departs = departs
        self._gabarits = gabarits
        self._inscriptions = inscriptions
        self._archers = archers
        self._categories = categories
        self._blasons = blasons
        self._placements = placements

    # --- Lecture -------------------------------------------------------------------------------

    def plan_de_cibles(self, tournoi_id: TournoiId, depart_id: DepartId) -> PlanDeCibles:
        """Renvoie le plan **persisté** d'un départ (cibles remplies + réserve avec sa raison).

        Lève `TournoiIntrouvable` / `DepartIntrouvable` / `GabaritDuTournoiAbsent` (gardes 404
        d'E03US001). Ne recalcule plus : lit la table `placement` ; les inscrits sans affectation
        sont en réserve.
        """
        contexte = self._charger(tournoi_id, depart_id)
        return self._construire_plan(contexte, self._placements.par_depart(depart_id))

    # --- Écritures (via la file, ADR-0005) -----------------------------------------------------

    def regenerer(self, tournoi_id: TournoiId, depart_id: DepartId) -> PlanDeCibles:
        """(Re)génère le plan auto et **écrase** l'existant — sert aussi d'« annuler ».

        Déterministe (ADR-0023) : « annuler les modifications » n'a pas besoin d'instantané, c'est
        cette même régénération (ADR-0024). Les archers que l'auto ne place pas restent en réserve.
        """
        contexte = self._charger(tournoi_id, depart_id)
        plan = placer(contexte.gabarit.cibles, tuple(contexte.donnees.values()))
        affectations = [
            Affectation(
                inscription_id=contexte.inscription_par_archer[pose.archer_id],
                cible_index=cible.index,
                position=pose.position,
            )
            for cible in plan.cibles
            for pose in cible.placements
        ]
        self._placements.definir_plan(depart_id, affectations)
        return self._construire_plan(contexte, affectations)

    def deplacer(
        self,
        tournoi_id: TournoiId,
        depart_id: DepartId,
        inscription_id: InscriptionId,
        cible_index: int | None,
        position: str | None,
    ) -> PlanDeCibles:
        """Déplace un inscrit vers une case, l'échange avec son occupant, ou le met en réserve.

        `cible_index is None` → **mise en réserve** (toujours possible). Sinon, dépôt sur
        `(cible_index, position)` : si la case est **libre**, déplacement simple ; si elle est
        **occupée**, **échange atomique** (les deux valident ensemble, ou refus en bloc).
        Toute violation lève `DeplacementInvalide` (409) **sans** rien écrire — état inchangé.
        """
        contexte = self._charger(tournoi_id, depart_id)
        if inscription_id not in contexte.archer_par_inscription:
            raise InscriptionIntrouvable(
                f"L'inscription {inscription_id} n'appartient pas au départ {depart_id}."
            )

        if cible_index is None:
            self._placements.retirer(inscription_id)
            return self._construire_plan(contexte, self._placements.par_depart(depart_id))

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
                "Cet archer n'a pas de blason : sa place ne peut pas être déterminée."
            )

        affectations = self._placements.par_depart(depart_id)
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
                depart_id,
                [Affectation(inscription_id, cible_index, position)],
            )
        else:
            self._echanger(contexte, affectations, cible, candidat, source, occupant, depart_id)
        return self._construire_plan(contexte, self._placements.par_depart(depart_id))

    def placer_les_restants(self, tournoi_id: TournoiId, depart_id: DepartId) -> PlanDeCibles:
        """Complète la réserve automatiquement dans les trous du plan, **sans bouger les placés**.

        Ce qu'aucune cible ne peut accueillir reste en réserve (CA « placer les restants »).
        """
        contexte = self._charger(tournoi_id, depart_id)
        affectations = self._placements.par_depart(depart_id)
        plan_actuel = self._construire_plan(contexte, affectations).cibles
        placees = {
            a.inscription_id for a in affectations if contexte.est_placable(a.inscription_id)
        }
        a_placer = tuple(
            contexte.donnees[contexte.archer_par_inscription[inscription.id]]
            for inscription in contexte.inscriptions
            if inscription.id is not None
            and inscription.id not in placees
            and inscription.id not in contexte.sans_blason
        )
        poses, _ = placer_restants(contexte.gabarit.cibles, plan_actuel, contexte.donnees, a_placer)
        nouvelles = [
            Affectation(
                inscription_id=contexte.inscription_par_archer[pose.archer_id],
                cible_index=pose.cible_index,
                position=pose.position,
            )
            for pose in poses
        ]
        self._placements.poser_plusieurs(depart_id, nouvelles)
        return self._construire_plan(contexte, self._placements.par_depart(depart_id))

    # --- Interne -------------------------------------------------------------------------------

    def _echanger(
        self,
        contexte: _Contexte,
        affectations: list[Affectation],
        cible_cible: Cible,
        candidat: ArcherAPlacer,
        source: Affectation | None,
        occupant: Affectation,
        depart_id: DepartId,
    ) -> None:
        """Valide et applique l'échange atomique de l'archer déplacé avec l'occupant de la case."""
        if source is None:
            raise DeplacementInvalide(
                "Cette case est occupée : déposez sur une place libre, ou échangez deux archers "
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
                "Échange refusé : l'un des deux archers ne tient pas à la place de l'autre "
                "(capacité, espace ou hauteur)."
            )
        self._placements.poser_plusieurs(
            depart_id,
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
                "Déplacement refusé : la cible ne peut pas accueillir cet archer "
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
        occupants = self._occupants(contexte, affectations, cible.index, exclus)
        return cible_accepte(cible, occupants, candidat)

    def _occupants(
        self,
        contexte: _Contexte,
        affectations: list[Affectation],
        cible_index: int,
        exclus: set[InscriptionId],
    ) -> tuple[ArcherAPlacer, ...]:
        """Données des archers actuellement posés sur une cible, hors inscriptions `exclus`."""
        return tuple(
            contexte.donnees[contexte.archer_par_inscription[affectation.inscription_id]]
            for affectation in affectations
            if affectation.cible_index == cible_index
            and affectation.inscription_id not in exclus
            and contexte.est_placable(affectation.inscription_id)
        )

    def _cible(self, gabarit: GabaritSalle, cible_index: int) -> Cible:
        """Renvoie la cible d'index donné, ou lève `DeplacementInvalide` si elle n'existe pas."""
        for cible in gabarit.cibles:
            if cible.index == cible_index:
                return cible
        raise DeplacementInvalide(f"La cible {cible_index} n'existe pas dans ce départ.")

    def _construire_plan(
        self, contexte: _Contexte, affectations: list[Affectation]
    ) -> PlanDeCibles:
        """Assemble le `PlanDeCibles` depuis les affectations : cibles peuplées + réserve.

        Une affectation dont la cible **ou la position** n'est plus dans le gabarit courant (salle
        réduite après matérialisation — le `ON DELETE CASCADE` ne couvre pas ce cas) retombe en
        **réserve** au lieu de disparaître : elle n'est ni marquée `placees` ni rendue, donc
        `_reserve` la reprend. Sans ce garde, l'archer serait perdu en silence (ni cible ni réserve)
        et la bannière « Plan prêt » mentirait — ligne rouge du CA « aucun archer perdu ».
        """
        cibles_par_index = {cible.index: cible for cible in contexte.gabarit.cibles}
        placements_par_cible: dict[int, list[Placement]] = {}
        placees: set[InscriptionId] = set()
        for affectation in affectations:
            if not contexte.est_placable(affectation.inscription_id):
                continue  # affectation orpheline / archer devenu non plaçable → réserve
            cible = cibles_par_index.get(affectation.cible_index)
            if cible is None or affectation.position not in cible.positions:
                continue  # cible/position disparue du gabarit → réserve (jamais perdu en silence)
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
        cibles = tuple(
            CiblePlacee(
                index=cible.index,
                capacite=cible.capacite,
                placements=tuple(
                    sorted(placements_par_cible.get(cible.index, []), key=lambda p: p.position)
                ),
            )
            for cible in contexte.gabarit.cibles
        )
        return PlanDeCibles(cibles=cibles, conflits=self._reserve(contexte, cibles, placees))

    def _reserve(
        self, contexte: _Contexte, cibles: tuple[CiblePlacee, ...], placees: set[InscriptionId]
    ) -> tuple[Conflit, ...]:
        """Réserve = inscrits non posés, avec leur **raison dérivée** (ADR-0024, non persistée).

        `SANS_BLASON` (donnée), sinon `NON_PLACE` si plus aucune cible ne l'accueille (saturé /
        hauteur), sinon `EN_RESERVE` (plaçable, mis de côté ou en attente). Ordre déterministe :
        celui des inscriptions.
        """
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
                conflits.append(
                    Conflit(
                        archer_id=archer_id,
                        raison=RaisonConflit.SANS_BLASON,
                        inscription_id=inscription.id,
                    )
                )
                continue
            candidat = contexte.donnees[archer_id]
            placable = any(
                cible_accepte(cible_par_index[index], occupants, candidat)
                for index, occupants in occupants_par_index.items()
            )
            raison = RaisonConflit.EN_RESERVE if placable else RaisonConflit.NON_PLACE
            conflits.append(
                Conflit(archer_id=archer_id, raison=raison, inscription_id=inscription.id)
            )
        return tuple(conflits)

    def _charger(self, tournoi_id: TournoiId, depart_id: DepartId) -> _Contexte:
        """Valide les gardes 404 et charge le décor du départ (cibles, inscrits, jointures)."""
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        depart = self._departs.par_id(depart_id)
        if depart is None or depart.tournoi_id != tournoi_id:
            raise DepartIntrouvable(
                f"Aucun départ d'identifiant {depart_id} dans le tournoi {tournoi_id}."
            )
        gabarit = self._gabarits.par_tournoi(tournoi_id)
        if gabarit is None:
            raise GabaritDuTournoiAbsent(
                f"Aucun gabarit de salle n'est appliqué au tournoi {tournoi_id}."
            )

        contexte = _Contexte(
            gabarit=gabarit,
            inscriptions=[],
            donnees={},
            sans_blason=set(),
            archer_par_inscription={},
            inscription_par_archer={},
        )
        for inscription in self._inscriptions.par_depart(depart_id):
            if inscription.id is None:
                continue
            contexte.inscriptions.append(inscription)
            contexte.archer_par_inscription[inscription.id] = inscription.archer_id
            contexte.inscription_par_archer[inscription.archer_id] = inscription.id
            entree = self._archer_a_placer(inscription.archer_id)
            if entree is None:
                contexte.sans_blason.add(inscription.id)
            else:
                contexte.donnees[inscription.archer_id] = entree
        return contexte

    def _archer_a_placer(self, archer_id: ArcherId) -> ArcherAPlacer | None:
        """Reconstruit l'entrée du moteur pour un archer, ou `None` si sa fraction est inconnue.

        `None` = pas de blason exploitable (catégorie sans blason par défaut, ou incohérence de
        données) : l'appelant en fait un conflit `SANS_BLASON`. Chaîne : archer → catégorie →
        blason par défaut, d'où l'on tire fraction (`taille`), capacité de carton et hauteur.
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
        )
