"""Forfaits — deux contextes, une seule mécanique (ADR-0050). En qualification le forfait relègue ou
exclut du **classement** ; en duels il fait **passer l'adversaire**. Trace co-écrite dans la même
transaction (ADR-0035).

⚠️ **`declare_par` est un NOM, pour l'audit** : ce service ne vérifie pas que le scoreur officie
dans **ce** tournoi — cette garde vit à l'API, comme pour la validation.
"""

from __future__ import annotations

from application.erreurs import (
    ArcherIntrouvable,
    ForfaitDejaDeclare,
    ForfaitIntrouvable,
    ForfaitTournoiTermine,
    PhaseIntrouvable,
    PhasePasUnTableau,
    PhaseQualificationAbsente,
    TournoiIntrouvable,
)
from application.portee import phase_du_tournoi, qualification_du_tournoi
from application.pose_du_tour import DeclencheurPoseDeTour, PoseurDeTour
from domain.archer import ArcherId
from domain.contrat_phase import TYPES_EN_TABLEAU_JOUE
from domain.entree_audit import ActionAuditee, EntreeAudit
from domain.forfait import Forfait, NatureForfait
from domain.phase import Phase, PhaseId
from domain.ports import (
    ArcherRepository,
    ForfaitRepository,
    Horloge,
    PhaseRepository,
    TournoiRepository,
)
from domain.tournoi import StatutTournoi, TournoiId

# DETTE-017 : 5ᵉ site de la constante `"Administrateur"` (auteur d'un acte admin). Publique
# ici — l'API la lit pour tracer un forfait déclaré depuis l'administration (E16US008).
AUTEUR_ADMIN = "Administrateur"


class ServiceForfait:
    """Cas d'usage du forfait : déclarer / annuler un abandon ou une DSQ, en qualif ou en duels."""

    def __init__(
        self,
        forfaits: ForfaitRepository,
        tournois: TournoiRepository,
        archers: ArcherRepository,
        phases: PhaseRepository,
        horloge: Horloge,
    ) -> None:
        self._forfaits = forfaits
        self._tournois = tournois
        self._archers = archers
        self._phases = phases
        self._horloge = horloge
        self._pose_de_tour = DeclencheurPoseDeTour()

    def brancher_poseur_de_tour(self, poseur: PoseurDeTour) -> None:
        """Dit à qui signaler qu'un walkover vient de trancher un duel (E03US012)."""
        self._pose_de_tour.brancher(poseur)

    # --- Qualification (phase résolue par le service) ------------------------------------------

    def declarer_en_qualification(
        self,
        tournoi_id: TournoiId,
        archer_id: ArcherId,
        nature: NatureForfait,
        declare_par: str,
        motif: str | None = None,
    ) -> Forfait:
        """Déclare un forfait en **qualification** : archer relégué (abandon) / exclu (DSQ)."""
        phase = self._phase_qualification(tournoi_id)
        return self._declarer(tournoi_id, phase, archer_id, nature, declare_par, motif)

    def annuler_en_qualification(
        self, tournoi_id: TournoiId, archer_id: ArcherId, annule_par: str
    ) -> None:
        """Annule le forfait de qualification d'un archer (réversibilité, `D-15`)."""
        phase = self._phase_qualification(tournoi_id)
        assert phase.id is not None, "Une phase persistée porte un id."
        self._annuler(tournoi_id, phase.id, archer_id, annule_par)

    # --- Duels (phase de tableau fournie) ------------------------------------------------------

    def declarer_en_duel(
        self,
        tournoi_id: TournoiId,
        phase_id: PhaseId,
        archer_id: ArcherId,
        nature: NatureForfait,
        declare_par: str,
        motif: str | None = None,
    ) -> Forfait:
        """Déclare un forfait dans une **phase de tableau** : l'adversaire passera (walkover)."""
        phase = self._exiger_phase_de_tableau(tournoi_id, phase_id)
        forfait = self._declarer(tournoi_id, phase, archer_id, nature, declare_par, motif)
        # Un walkover **tranche** un duel sans qu'aucun score soit saisi : c'est le second chemin
        # par lequel un tour s'achève (E03US012). L'oublier rendait la pose automatique muette dès
        # qu'un tour se finissait sur un forfait.
        self._pose_de_tour.signaler(tournoi_id, phase_id)
        return forfait

    def annuler_en_duel(
        self, tournoi_id: TournoiId, phase_id: PhaseId, archer_id: ArcherId, annule_par: str
    ) -> None:
        """Annule un forfait de duel : à la reconstruction suivante, le walkover disparaît."""
        self._exiger_phase_de_tableau(tournoi_id, phase_id)
        self._annuler(tournoi_id, phase_id, archer_id, annule_par)
        # L'annulation défait un walkover : le tour redevient indéterminé et ses poses orphelines.
        # Signaler ici les fait purger au prochain chargement plutôt qu'au prochain hasard.
        self._pose_de_tour.signaler(tournoi_id, phase_id)

    # --- Interne -------------------------------------------------------------------------------

    def _declarer(
        self,
        tournoi_id: TournoiId,
        phase: Phase,
        archer_id: ArcherId,
        nature: NatureForfait,
        declare_par: str,
        motif: str | None,
    ) -> Forfait:
        assert phase.id is not None, "Une phase persistée porte un id."
        self._exiger_tournoi_ouvrable(tournoi_id)
        self._exiger_archer(tournoi_id, archer_id)
        if self._forfaits.par_archer_et_phase(tournoi_id, archer_id, phase.id) is not None:
            raise ForfaitDejaDeclare(
                f"L'archer {archer_id} est déjà déclaré forfait dans cette phase."
            )
        maintenant = self._horloge.maintenant()
        forfait = Forfait.creer(
            tournoi_id=tournoi_id,
            archer_id=archer_id,
            phase_id=phase.id,
            nature=nature,
            declare_par=declare_par,
            declare_le=maintenant,
            motif=motif,
        )
        entree = EntreeAudit.creer(
            tournoi_id=tournoi_id,
            action=ActionAuditee.FORFAIT,
            auteur=declare_par,
            horodatage=maintenant,
            objet=f"forfait de l'archer {archer_id} (phase {phase.id})",
            apres=forfait.nature.value
            if forfait.motif is None
            else f"{forfait.nature.value} — {forfait.motif}",
        )
        return self._forfaits.declarer_avec_trace(forfait, entree)

    def _annuler(
        self, tournoi_id: TournoiId, phase_id: PhaseId, archer_id: ArcherId, annule_par: str
    ) -> None:
        self._exiger_tournoi_ouvrable(tournoi_id)
        forfait = self._forfaits.par_archer_et_phase(tournoi_id, archer_id, phase_id)
        if forfait is None:
            raise ForfaitIntrouvable(
                f"Aucun forfait de l'archer {archer_id} à annuler dans cette phase."
            )
        entree = EntreeAudit.creer(
            tournoi_id=tournoi_id,
            action=ActionAuditee.FORFAIT,
            auteur=annule_par,
            horodatage=self._horloge.maintenant(),
            objet=f"forfait de l'archer {archer_id} (phase {phase_id})",
            avant=forfait.nature.value,
            apres="annulé",
        )
        self._forfaits.annuler_avec_trace(forfait, entree)

    def _exiger_tournoi_ouvrable(self, tournoi_id: TournoiId) -> None:
        """Le tournoi existe et n'est **pas terminé** (`D-15`) — sinon 404 / 409."""
        tournoi = self._tournois.par_id(tournoi_id)
        if tournoi is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        if tournoi.statut is StatutTournoi.TERMINE:
            raise ForfaitTournoiTermine(
                "Le tournoi est terminé : ses forfaits ne sont plus modifiables."
            )

    def _exiger_archer(self, tournoi_id: TournoiId, archer_id: ArcherId) -> None:
        archer = self._archers.par_id(archer_id)
        if archer is None or archer.tournoi_id != tournoi_id:
            raise ArcherIntrouvable(f"Aucun archer d'identifiant {archer_id} dans ce tournoi.")

    def _phase_qualification(self, tournoi_id: TournoiId) -> Phase:
        # DETTE-047 : le forfait est écrit sur la qualification du **premier** créneau, quel que
        # soit celui où l'archer tire — `ServiceClassement._forfaits_qualif` le relit par le même
        # chemin, d'où un affichage juste *par accident*. Deux conséquences réelles : supprimer le
        # premier créneau efface (cascade) les forfaits de tous les autres, et un archer engagé sur
        # deux créneaux déclaré forfait sur l'un est relégué sur les deux. Résorption : porter un
        # `depart_id` jusqu'ici — change la route et le front, donc une US à part entière.
        phase = qualification_du_tournoi(self._phases, tournoi_id)
        if phase is None:
            raise PhaseQualificationAbsente(
                "La qualification n'est pas encore configurée pour ce tournoi."
            )
        return phase

    def _exiger_phase_de_tableau(self, tournoi_id: TournoiId, phase_id: PhaseId) -> Phase:
        phase = phase_du_tournoi(self._phases, tournoi_id, phase_id)
        if phase is None:
            raise PhaseIntrouvable(f"Aucune phase {phase_id} dans le tournoi {tournoi_id}.")
        # ⚠️ Le `phase_id` vient du client. Sans ce filtre, la route des duels écrit un forfait de
        # QUALIFICATION relu par `_forfaits_qualif`. Miroir exact de la LECTURE
        # (`_appliquer_forfaits`) : écrire hors de cet
        # ensemble poserait une ligne fantôme — invisible, puis `ForfaitDejaDeclare` au geste
        # suivant, et `ServiceFormats` la compte. Allowlist, pas denylist : un type neuf déclare
        # son décor en un seul endroit (ADR-0083) et le filtre suit.
        if phase.type not in TYPES_EN_TABLEAU_JOUE:
            raise PhasePasUnTableau(
                f"La phase {phase_id} n'est pas une élimination directe : pas de forfait de duel."
            )
        return phase
