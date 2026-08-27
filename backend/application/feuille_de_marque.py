"""Feuille de marque — reconstitue le placement par **ports seuls**, jamais service→service.

⚠️ **Un tournoi sans barème défini n'est PAS une erreur** : la grille prend le preset FFTA 18 m
(20 volées de 3), défaut le plus sûr pour une qualification (référentiel §6.1).
"""

from __future__ import annotations

import logging

from application.erreurs import DepartIntrouvable, TournoiIntrouvable
from application.portee import qualification_courante
from domain.bareme import BaremeQualification
from domain.depart import DepartId
from domain.feuille_marque import FeuilleDeMarque, LigneArcher
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

_logger = logging.getLogger(__name__)


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

        bareme = self._bareme_du_creneau(depart_id)
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

    def _bareme_du_creneau(self, depart_id: DepartId) -> BaremeQualification:
        """Le barème de la qualification **qui se tire dans ce créneau**, ou le preset FFTA 18 m.

        ⚠️ **Correctif de revue E05US025.** Cette méthode lisait `qualification_du_tournoi`, qui
        rend depuis cette US le barème de la **première** qualification — alors que `generer` tient
        déjà le `depart_id` sous la main. Sur le déroulé de référence (3x20 puis *haute* et *basse*
        à 3x15), on imprimait donc des feuilles à **20 volées** pour un tour qui s'en tire 15 : du
        papier faux distribué au pas de tir, que le jour J ne rattrape pas. Le site avait échappé
        au tri écrit en tête de `application/portee.py` — il y est désormais énuméré.
        """
        phase = qualification_courante(self._phases, depart_id)
        # `bareme` est optionnel depuis E05US001 (ADR-0045 §2) mais toujours présent sur une
        # qualification ; à défaut (données incohérentes), on retombe sur le preset FFTA.
        if phase is None or phase.bareme is None:
            return BaremeQualification.preset_ffta_18m()
        return phase.bareme

    def _ligne(self, affectation: Affectation) -> LigneArcher | None:
        """Reconstitue la ligne d'un archer placé, ou `None` si la chaîne de jointure est rompue.

        **Deux niveaux, à ne pas confondre.** Un **libellé** manquant (catégorie ou blason) retombe
        sur `""` : la feuille de l'archer part quand même, un intitulé vide n'est pas un motif de la
        lui retirer. Mais si l'**identité** manque — l'affectation pointe vers une inscription ou un
        archer introuvable — on ne peut rien imprimer d'utile : la ligne est **omise**, et le fait
        est **journalisé** (jamais un retrait muet — plan incohérent, pas un cas nominal).

        Cette omission ne devrait **pas** se produire pour un archer réellement placé : la FK
        `placement.inscription_id` est en `ON DELETE CASCADE` (pas de placement orphelin) et
        `ServiceArchers.supprimer` refuse (`ArcherEngage`) ou purge le placement. La garde reste
        défensive : le jour où l'un de ces invariants saute, l'anomalie se voit dans les logs plutôt
        que de faire disparaître un archer de sa feuille en silence.
        """
        inscription = self._inscriptions.par_id(affectation.inscription_id)
        if inscription is None:
            _logger.warning(
                "Feuille de marque — plan incohérent : affectation (cible %s, pos %s) vers "
                "inscription %s introuvable ; archer omis.",
                affectation.cible_index,
                affectation.position,
                affectation.inscription_id,
            )
            return None
        archer = self._archers.par_id(inscription.archer_id)
        if archer is None:
            _logger.warning(
                "Feuille de marque — plan incohérent : inscription %s sans archer %s ; omis.",
                inscription.id,
                inscription.archer_id,
            )
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
