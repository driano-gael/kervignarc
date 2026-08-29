"""Service de **placement** — lit le plan persisté, régénère, déplace, comble la réserve.

La raison d'une mise en réserve est **dérivée**, jamais persistée. Un déplacement invalide est
refusé **en bloc**, l'état restant inchangé.

⚠️ **Un archer sans blason exploitable est un CONFLIT, jamais placé** : la jointure archer →
catégorie → blason nourrit le moteur, elle ne comble pas les trous.
"""

from __future__ import annotations

from dataclasses import dataclass

from application.erreurs import (
    DepartIntrouvable,
    DeplacementInvalide,
    GabaritDuTournoiAbsent,
    InscriptionIntrouvable,
    ReplacementNonConfirme,
    TournoiIntrouvable,
)
from domain.archer import ArcherId
from domain.cloisonnement import Cloisonnement
from domain.depart import DepartId
from domain.entree_audit import ActionAuditee, EntreeAudit
from domain.gabarit_salle import Cible, GabaritSalle
from domain.impact import ImpactRegeneration, NiveauImpact
from domain.inscription import Inscription, InscriptionId
from domain.placement import (
    Affectation,
    ArcherAPlacer,
    CiblePlacee,
    Conflit,
    MotifRefus,
    Placement,
    PlanDeCibles,
    RaisonConflit,
    cible_accepte,
    cible_cloisonnement_non_respecte,
    cible_mixite_non_garantie,
    motif_de_refus,
    placer,
    placer_restants,
)
from domain.ports import (
    ArcherRepository,
    BlasonRepository,
    CategorieRepository,
    DepartRepository,
    GabaritSalleRepository,
    Horloge,
    InscriptionRepository,
    PlacementRepository,
    SerieRepository,
    TournoiRepository,
)
from domain.tournoi import TournoiId

# Auteur de la trace d'audit d'une régénération massive : l'action est **admin**, et l'admin est un
# **secret**, pas une personne nommée (E10US002, `D-13`) — on fige donc le rôle, pas un nom.
# Cohérent
# avec l'agrégat `EntreeAudit` qui exige un auteur non vide (« qui a agi »).
# DETTE-017 : 2ᵉ site de cette constante, dupliquée sur cinq modules applicatifs.
_AUTEUR_ADMIN = "Administrateur"


@dataclass
class _Contexte:
    """Décor d'un départ, chargé une fois par opération : cibles, inscrits et jointures.

    `donnees` ne contient que les archers **plaçables** (blason exploitable) ; `sans_blason` liste
    les inscriptions dont l'archer n'a pas de fraction connue. Les tables `archer ↔ inscription`
    sont 1:1 sur un départ (contrainte d'unicité), on garde les deux sens."""

    gabarit: GabaritSalle
    # Réglage de cloisonnement du **tournoi** (E03US007), chargé une fois avec le décor : toutes les
    # opérations du service (générer, déplacer, compléter, lire) doivent parler du même.
    cloisonnement: Cloisonnement
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
        series: SerieRepository,
        horloge: Horloge,
    ) -> None:
        self._tournois = tournois
        self._departs = departs
        self._gabarits = gabarits
        self._inscriptions = inscriptions
        self._archers = archers
        self._categories = categories
        self._blasons = blasons
        self._placements = placements
        # E12US007 : `series` sert au **calcul d'impact** (« quelles cibles ont déjà des scores ») ;
        # `horloge` **date** la trace d'audit d'une régénération massive (le domaine reste pur).
        self._series = series
        self._horloge = horloge

    # --- Lecture -------------------------------------------------------------------------------

    def plan_de_cibles(self, tournoi_id: TournoiId, depart_id: DepartId) -> PlanDeCibles:
        """Renvoie le plan **persisté** d'un départ (cibles remplies + réserve avec sa raison).

        Lève `TournoiIntrouvable` / `DepartIntrouvable` / `GabaritDuTournoiAbsent` (gardes 404
        d'E03US001). Ne recalcule plus : lit la table `placement` ; les inscrits sans affectation
        sont en réserve.
        """
        contexte = self._charger(tournoi_id, depart_id)
        return self._construire_plan(contexte, self._placements.par_depart(depart_id))

    def impact_regeneration(self, tournoi_id: TournoiId, depart_id: DepartId) -> ImpactRegeneration:
        """Calcule l'impact **réel** de régénérer le plan d'un départ (E12US007, ADR-0040).

        Lecture pure (aucune écriture) : c'est la **prévisualisation** que le front interroge avant
        d'agir, pour afficher l'alerte chiffrée — « N archers replacés ; M cibles ont des scores ».
        Mêmes gardes 404 que la lecture du plan (`_charger`).
        """
        contexte = self._charger(tournoi_id, depart_id)
        return self._impact(contexte, tournoi_id, depart_id)

    def cloisonnement(self, tournoi_id: TournoiId) -> Cloisonnement:
        """Réglage de cloisonnement du tournoi (E03US007, RG-4) — `AUCUN` par défaut.

        Lecture **sans départ** : le réglage vaut pour tout le tournoi, l'écran de placement
        l'affiche avant même d'avoir choisi un créneau. `TournoiIntrouvable` (→ 404) si
        l'identifiant est inconnu — un réglage rendu pour un tournoi absent serait un mensonge
        poli."""
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        return tournoi.cloisonnement

    # --- Écritures (via la file, ADR-0005) -----------------------------------------------------

    def definir_cloisonnement(
        self, tournoi_id: TournoiId, cloisonnement: Cloisonnement
    ) -> Cloisonnement:
        """Règle le cloisonnement des cibles du tournoi et renvoie la valeur retenue (E03US007).

        **Ne replace personne** : le plan est matérialisé (ADR-0024) et l'organisateur reste maître
        de ses ajustements. Le réglage s'applique à la prochaine régénération, aux déplacements
        manuels et au **signal** des cibles déjà posées qui le violent
        (`cloisonnement_non_respecte`). Aucune garde de statut : c'est un critère de placement, pas
        une donnée de résultat, et le plan s'ajuste jusqu'au bout (E03US004).
        """
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        enregistre = self._tournois.enregistrer(tournoi.definir_cloisonnement(cloisonnement))
        return enregistre.cloisonnement

    def regenerer(
        self, tournoi_id: TournoiId, depart_id: DepartId, *, confirme: bool = False
    ) -> PlanDeCibles:
        """(Re)génère le plan auto et **écrase** l'existant — sert aussi d'« annuler ».

        Déterministe (ADR-0023) : « annuler » n'a pas besoin d'instantané, c'est cette même
        régénération (ADR-0024). ⚠️ **L'impact est recalculé ici**, dans la file, jamais cru sur
        parole (défaut de DETTE-007) : au niveau `MASSIF` (archers placés **et** scores existants)
        sans `confirme`, on lève `ReplacementNonConfirme` (409 chiffré, état inchangé), et une
        trace d'audit est co-écrite atomiquement avec le plan (ADR-0035).
        """
        contexte = self._charger(tournoi_id, depart_id)
        impact = self._impact(contexte, tournoi_id, depart_id)
        if impact.niveau is NiveauImpact.MASSIF and not confirme:
            raise ReplacementNonConfirme(
                f"Régénérer ce plan replacera {impact.archers_deplaces} archer(s) ; "
                f"{impact.cibles_avec_scores} cible(s) ont déjà des scores (conservés). "
                "Confirmez pour écraser le placement.",
                archers_deplaces=impact.archers_deplaces,
                cibles_avec_scores=impact.cibles_avec_scores,
            )
        plan = placer(
            contexte.gabarit.cibles,
            tuple(contexte.donnees.values()),
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
        if impact.niveau is NiveauImpact.MASSIF:
            self._placements.definir_plan_avec_trace(
                depart_id, affectations, self._trace_replacement(tournoi_id, depart_id, impact)
            )
        else:
            self._placements.definir_plan(depart_id, affectations)
        return self._construire_plan(contexte, affectations)

    def _impact(
        self, contexte: _Contexte, tournoi_id: TournoiId, depart_id: DepartId
    ) -> ImpactRegeneration:
        """Chiffre l'impact d'une régénération : archers placés + cibles avec scores.

        ⚠️ `# DETTE-037` : ne chiffre **pas** la réserve qu'un cloisonnement plus strict (E03US007)
        va créer — l'organisateur confirme, puis la découvre. `cibles_avec_scores` compte les
        cibles dont un archer a **au moins une volée validée** ; « a tiré » = **volée validée**,
        jamais une saisie provisoire (arbitrage du 20/07/2026, `stories/E02-inscriptions.md`),
        cohérent avec `cumul` et le classement. Une seule requête `par_tournoi` (pas de N+1).
        """
        affectations = self._placements.par_depart(depart_id)
        archers_avec_scores = {
            serie.archer_id
            for serie in self._series.par_tournoi(tournoi_id)
            if serie.nb_fleches_validees > 0
        }
        cibles_avec_scores = {
            affectation.cible_index
            for affectation in affectations
            if contexte.archer_par_inscription.get(affectation.inscription_id)
            in archers_avec_scores
        }
        return ImpactRegeneration(
            archers_deplaces=len(affectations),
            cibles_avec_scores=len(cibles_avec_scores),
        )

    def _trace_replacement(
        self, tournoi_id: TournoiId, depart_id: DepartId, impact: ImpactRegeneration
    ) -> EntreeAudit:
        """Construit la trace d'audit d'une régénération massive (datée par le port `Horloge`).

        L'agrégat reste pur : le service **date** (via `Horloge`), le domaine ne lit jamais
        l'horloge. `avant`/`apres` gardent le décompte chiffré au moment de l'acte — la valeur de
        preuve du CA.
        """
        return EntreeAudit.creer(
            tournoi_id=tournoi_id,
            action=ActionAuditee.REPLACEMENT,
            auteur=_AUTEUR_ADMIN,
            horodatage=self._horloge.maintenant(),
            objet=f"Plan de cibles du départ {depart_id}",
            avant=(
                f"{impact.archers_deplaces} archer(s) placé(s), "
                f"{impact.cibles_avec_scores} cible(s) avec scores"
            ),
            apres="plan régénéré",
        )

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
                "Un couloir de tir est requis pour poser un archer sur une cible."
            )
        cible = self._cible(contexte.gabarit, cible_index)
        if position not in cible.positions:
            raise DeplacementInvalide(
                f"Le couloir de tir {position} n'existe pas sur la cible {cible_index}."
            )
        if not contexte.est_placable(inscription_id):
            raise DeplacementInvalide(
                "Cet archer n'a pas de blason : son couloir de tir ne peut pas être déterminé."
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
        # « Placées » = ce que le plan **rend réellement** (après le garde de `_construire_plan`),
        # pas les affectations brutes : un archer dont la cible a disparu du gabarit est retombé en
        # réserve — il doit entrer dans `a_placer` pour être reposé, pas être compté comme placé.
        placees = {
            pose.inscription_id
            for cible in plan_actuel
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
            plan_actuel,
            contexte.donnees,
            a_placer,
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
                "Cette case est occupée : déposez sur un couloir libre, ou échangez deux archers "
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
            # Le motif est demandé au domaine pour **chacune des deux jambes** : un échange met deux
            # cibles en jeu, et celle qui refuse n'est pas forcément celle qu'on regarde. La
            # première qui rend autre chose qu'`AUCUN` explique le refus. Relevé en 2e passe :
            # l'échange gardait le message unique que `_valider_pose` venait d'abandonner, donc
            # accusait de « mêler » deux archers parfois de la **même** catégorie.
            self._refuser_echange(contexte, affectations, cible_cible, candidat, exclus)
            self._refuser_echange(contexte, affectations, cible_source, occupant_candidat, exclus)
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
        """Refuse la pose si la cible ne peut pas accueillir le candidat (déplacement invalide).

        Le message **nomme la cause** : un refus de cloisonnement (E03US007) se corrige en
        desserrant un réglage, pas en libérant de la place. ⚠️ Il distingue **deux** refus de
        cloisonnement : le candidat qui mêlerait, et la cible **déjà** non conforme (plan posé
        avant l'activation du réglage), où même une pose neutre est refusée — accuser le candidat
        serait faux, et l'admin chercherait indéfiniment ce qu'il a mal fait.
        """
        motif = self._motif(contexte, affectations, cible, candidat, exclus)
        if motif is MotifRefus.AUCUN:
            return
        if motif is MotifRefus.CLOISONNEMENT_CIBLE_DEJA_NON_CONFORME:
            raise DeplacementInvalide(
                f"Déplacement refusé : la cible {cible.index} ne respecte déjà pas le "
                "cloisonnement demandé. Régénérez le plan, ou videz-la, avant d'y poser un archer."
            )
        if motif is MotifRefus.CLOISONNEMENT_MELANGE:
            raise DeplacementInvalide(
                "Déplacement refusé : le cloisonnement des cibles interdit de mêler ces archers "
                "sur une même cible."
            )
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
        return cible_accepte(cible, occupants, candidat, cloisonnement=contexte.cloisonnement)

    def _motif(
        self,
        contexte: _Contexte,
        affectations: list[Affectation],
        cible: Cible,
        candidat: ArcherAPlacer,
        exclus: set[InscriptionId],
    ) -> MotifRefus:
        """Pourquoi `cible` refuse `candidat` — la règle est au domaine, ici le seul décor."""
        occupants = self._occupants(contexte, affectations, cible.index, exclus)
        return motif_de_refus(cible, occupants, candidat, cloisonnement=contexte.cloisonnement)

    def _refuser_echange(
        self,
        contexte: _Contexte,
        affectations: list[Affectation],
        cible: Cible,
        candidat: ArcherAPlacer,
        exclus: set[InscriptionId],
    ) -> None:
        """Lève le refus d'échange **nommé** si cette jambe est celle qui bloque ; sinon rend la
        main (l'autre jambe, ou le message générique de l'appelant, prendra le relais)."""
        motif = self._motif(contexte, affectations, cible, candidat, exclus)
        if motif is MotifRefus.CLOISONNEMENT_CIBLE_DEJA_NON_CONFORME:
            raise DeplacementInvalide(
                f"Échange refusé : la cible {cible.index} ne respecte déjà pas le cloisonnement "
                "demandé. Régénérez le plan, ou videz-la, avant d'y échanger un archer."
            )
        if motif is MotifRefus.CLOISONNEMENT_MELANGE:
            raise DeplacementInvalide(
                "Échange refusé : le cloisonnement des cibles interdit de mêler ces archers "
                "sur une même cible."
            )

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

        def _figer(cible: Cible) -> CiblePlacee:
            # Le plan est **matérialisé** (ADR-0024) : la table `placement` ne stocke pas le club,
            # on **recalcule** `mixite_non_garantie` à la lecture depuis la jointure archer → club
            # déjà chargée (`contexte.donnees`), avec le prédicat pur du domaine (ADR-0047). Même
            # régime que la raison de réserve : dérivé, jamais persisté.
            poses = sorted(placements_par_cible.get(cible.index, []), key=lambda p: p.position)
            occupants = [contexte.donnees[pose.archer_id] for pose in poses]
            return CiblePlacee(
                index=cible.index,
                capacite=cible.capacite,
                placements=tuple(poses),
                mixite_non_garantie=cible_mixite_non_garantie([o.club_id for o in occupants]),
                # E03US007 : même régime dérivé. Vrai uniquement sur un plan **posé avant**
                # l'activation du réglage (le placement auto, lui, ne peut pas violer une contrainte
                # dure) — c'est ce qui prévient l'admin qu'il lui reste un plan à régénérer.
                cloisonnement_non_respecte=cible_cloisonnement_non_respecte(
                    contexte.cloisonnement, occupants
                ),
            )

        cibles = tuple(_figer(cible) for cible in contexte.gabarit.cibles)
        return PlanDeCibles(cibles=cibles, conflits=self._reserve(contexte, cibles, placees))

    def _reserve(
        self, contexte: _Contexte, cibles: tuple[CiblePlacee, ...], placees: set[InscriptionId]
    ) -> tuple[Conflit, ...]:
        """Réserve = inscrits non posés, avec leur **raison dérivée** (ADR-0024, non persistée).

        `SANS_BLASON` (donnée), sinon `NON_PLACE` si plus aucune cible ne l'accueille, sinon
        `EN_RESERVE`. Ordre déterministe : celui des inscriptions. **E03US007** : entre les deux,
        `CLOISONNEMENT` quand c'est le *réglage* qui exclut — on le sait en reposant la même
        question **sans** le cloisonnement. Deux gestes différents pour l'admin (desserrer vs.
        ajouter une cible), donc deux raisons distinctes.
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
                # Au moins une cible ne le refuse **que** pour cause de cloisonnement : c'est le
                # réglage qui l'exclut, pas la salle.
                raison = RaisonConflit.CLOISONNEMENT
            else:
                raison = RaisonConflit.NON_PLACE
            conflits.append(
                Conflit(archer_id=archer_id, raison=raison, inscription_id=inscription.id)
            )
        return tuple(conflits)

    def _charger(self, tournoi_id: TournoiId, depart_id: DepartId) -> _Contexte:
        """Valide les gardes 404 et charge le décor du départ (cibles, inscrits, jointures)."""
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
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
            cloisonnement=tournoi.cloisonnement,
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
            # Club propagé pour la mixité ≥ 2 clubs/cible (E03US006). `None` (club inconnu,
            # ADR-0014) traverse tel quel : le moteur le traite comme indécidable, jamais même club.
            club_id=archer.club_id,
            # Catégorie propagée pour le cloisonnement (E03US007) : c'est ici, et nulle part
            # ailleurs, que la jointure archer → catégorie existe.
            categorie_id=archer.categorie_id,
        )
