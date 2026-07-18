"""Service applicatif Feuille de marque (E09US001).

Compose le document imprimable d'un départ : il lit le **plan de cibles persisté** (E03US001 —
qui tire sur quelle cible, à quelle position), reconstitue la jointure archer → catégorie → blason
(comme `ServicePlacement._archer_a_placer`, via des ports seuls — jamais service→service),
récupère la **grille** depuis le barème de qualification du tournoi, et confie le rendu au port
`GenerateurFeuilleDeMarque` (adapter ReportLab, ADR-0031).

Le service reste synchrone et pur d'infrastructure : il ne connaît ni HTTP, ni SQL, ni ReportLab.
Il fait remonter les mêmes gardes 404 que `ServicePlacement` (`TournoiIntrouvable`,
`DepartIntrouvable`) — même couple tournoi/départ. Un tournoi **sans** barème de qualification
défini n'est pas une erreur : la grille prend le **preset FFTA 18 m** (20 volées de 3), défaut le
plus sûr pour une qualification 18 m (référentiel §6.1, cf. `domain.bareme`).
"""

from __future__ import annotations

from application.erreurs import DepartIntrouvable, TournoiIntrouvable
from domain.bareme import BaremeQualification
from domain.depart import DepartId
from domain.feuille_marque import FeuilleDeMarque, LigneArcher
from domain.phase import TypePhase
from domain.placement import Affectation
from domain.ports import (
    ArcherRepository,
    BlasonRepository,
    CategorieRepository,
    DepartRepository,
    GenerateurFeuilleDeMarque,
    InscriptionRepository,
    PhaseRepository,
    PlacementRepository,
    TournoiRepository,
)
from domain.tournoi import TournoiId


class ServiceFeuilleDeMarque:
    """Cas d'usage : composer et rendre la feuille de marque d'un départ (page par archer placé)."""

    def __init__(
        self,
        tournois: TournoiRepository,
        departs: DepartRepository,
        placements: PlacementRepository,
        inscriptions: InscriptionRepository,
        archers: ArcherRepository,
        categories: CategorieRepository,
        blasons: BlasonRepository,
        phases: PhaseRepository,
        generateur: GenerateurFeuilleDeMarque,
    ) -> None:
        self._tournois = tournois
        self._departs = departs
        self._placements = placements
        self._inscriptions = inscriptions
        self._archers = archers
        self._categories = categories
        self._blasons = blasons
        self._phases = phases
        self._generateur = generateur

    def generer(self, tournoi_id: TournoiId, depart_id: DepartId) -> bytes:
        """Rend en PDF la feuille de marque du départ.

        Lève `TournoiIntrouvable` / `DepartIntrouvable` (gardes 404, même couple que le placement).
        Les archers **placés** figurent seuls (la réserve ne tire pas), ordonnés par cible puis
        position ; la grille de scores dérive du barème de qualification (ou du preset FFTA 18 m).
        """
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        depart = self._departs.par_id(depart_id)
        if depart is None or depart.tournoi_id != tournoi_id:
            raise DepartIntrouvable(
                f"Aucun départ d'identifiant {depart_id} dans le tournoi {tournoi_id}."
            )

        bareme = self._bareme_du_tournoi(tournoi_id)
        lignes = [
            ligne
            for affectation in self._placements.par_depart(depart_id)
            if (ligne := self._ligne(affectation)) is not None
        ]
        lignes.sort(key=lambda ligne: (ligne.cible_index, ligne.position))

        feuille = FeuilleDeMarque(
            tournoi=tournoi.nom,
            depart_numero=depart.numero,
            nb_volees=bareme.nb_volees,
            nb_fleches_par_volee=bareme.nb_fleches_par_volee,
            archers=tuple(lignes),
        )
        return self._generateur.generer(feuille)

    def _bareme_du_tournoi(self, tournoi_id: TournoiId) -> BaremeQualification:
        """Le barème de qualification du tournoi, ou le preset FFTA 18 m s'il n'est pas défini."""
        phase = self._phases.par_tournoi_et_type(tournoi_id, TypePhase.QUALIFICATION)
        return phase.bareme if phase is not None else BaremeQualification.preset_ffta_18m()

    def _ligne(self, affectation: Affectation) -> LigneArcher | None:
        """Reconstitue la ligne d'un archer placé, ou `None` si la chaîne de jointure est rompue.

        `None` ne devrait pas arriver pour un archer **placé** (le placement exige déjà un blason) :
        c'est une garde défensive contre une incohérence de données, pas un cas nominal. Les
        libellés absents (catégorie/blason) retombent sur `""` pour ne jamais **perdre** la feuille
        d'un archer réellement sur une cible.
        """
        inscription = self._inscriptions.par_id(affectation.inscription_id)
        if inscription is None:
            return None
        archer = self._archers.par_id(inscription.archer_id)
        if archer is None:
            return None
        categorie = self._categories.par_id(archer.categorie_id)
        blason = (
            self._blasons.par_id(categorie.blason_id)
            if categorie is not None and categorie.blason_id is not None
            else None
        )
        return LigneArcher(
            cible_index=affectation.cible_index,
            position=affectation.position,
            nom=archer.nom,
            prenom=archer.prenom,
            categorie=categorie.libelle if categorie is not None else "",
            blason=blason.nom if blason is not None else "",
        )
