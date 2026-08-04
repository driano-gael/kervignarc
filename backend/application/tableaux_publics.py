"""Lecture **publique** des tableaux d'un tournoi (E07US005) — « voir les arbres en direct ».

Le CA d'E07US005 dit « rendu de l'arbre (**principal + placement**) mis à jour en live ». Ce
service est le côté serveur de cette phrase : il rend, pour un tournoi, **tous** ses arbres —
élimination directe *et* placement (`TYPES_EN_TABLEAU`, E05US010) — dans l'ordre du déroulé.

**Pourquoi un service à part et non une méthode de `ServiceSaisieDuels`.** `ServiceSaisieDuels` est
le service du **scoreur** : il saisit, il valide, et sa lecture `etat_tableau` est protégée par
`exiger_scoreur`. Y accrocher une lecture publique mêlerait deux audiences dans le même objet, et
c'est le genre de mélange qui finit par exposer au public un champ ajouté pour le scoreur. On suit
donc la forme déjà en place pour les autres lectures publiques dérivées du même arbre —
`ServiceRoutage` (E04US018/E07US008) et `ServiceSuiviDeroule` (E07US004) sont eux aussi des
services de lecture qui **consomment** `ServiceSaisieDuels` sans en faire partie.

⚠️ **La restriction du contenu n'est pas ici, elle est au DTO** (`api/v1/tableaux.py`, règle 6) :
ce service rend l'`EtatTableau` complet, la frontière API choisit ce que le public en voit. Le
partage est volontaire — le domaine et l'application n'ont pas à connaître la notion de « public ».
"""

from __future__ import annotations

from dataclasses import dataclass

from application.erreurs import ApplicationError, TournoiIntrouvable
from application.saisie_duels import EtatTableau, ServiceSaisieDuels
from domain.erreurs import DomainError
from domain.phase import TYPES_EN_TABLEAU, PhaseId, TypePhase
from domain.ports import PhaseRepository, TournoiRepository
from domain.tournoi import TournoiId


@dataclass(frozen=True)
class TableauPublic:
    """Un arbre du tournoi : **quelle** phase (rang et type), et sa photo reconstruite.

    `ordre` et `type` plutôt qu'un libellé : une phase n'a pas de nom (`domain.phase.Phase`), et
    fabriquer « Élimination directe » ici mettrait du texte d'interface dans l'application alors que
    le front en tient déjà le catalogue (`shared/phases/catalogue.ts`). La règle 3 veut le même
    vocabulaire partout — le plus sûr moyen est qu'il n'existe qu'à un endroit.
    """

    phase_id: PhaseId
    ordre: int
    type: TypePhase
    etat: EtatTableau


@dataclass(frozen=True)
class TableauxDuTournoi:
    """Tous les arbres lisibles d'un tournoi, dans l'ordre du déroulé."""

    tournoi_id: TournoiId
    tableaux: tuple[TableauPublic, ...]


class ServiceTableauxPublics:
    """Cas d'usage « voir les arbres du tournoi » — lecture pure, publique, sans identité."""

    def __init__(
        self,
        tournois: TournoiRepository,
        phases: PhaseRepository,
        saisie: ServiceSaisieDuels,
    ) -> None:
        self._tournois = tournois
        self._phases = phases
        self._saisie = saisie

    def pour_tournoi(self, tournoi_id: TournoiId) -> TableauxDuTournoi:
        """Les arbres du tournoi. `TournoiIntrouvable` si le tournoi n'existe pas.

        Un tournoi **sans phase en tableau** rend une liste vide plutôt qu'une erreur : l'onglet
        s'ouvre à 8 h du matin comme à 17 h, et « pas encore de tableau » est une réponse, pas une
        panne.

        # DETTE-031 : chaque appel **reconstruit** intégralement chaque tableau (classement complet
        # du tournoi, arbre rebâti, duels rejoués, forfaits appliqués) — et ici **une fois par
        # phase**, sur un endpoint public non authentifié pollé par autant d'appareils qu'il y a de
        # spectateurs. Régime assumé au contexte mono-club et local ; cf. docs/dette.md.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        phases = sorted(self._phases.par_tournoi(tournoi_id), key=lambda phase: phase.ordre)
        lisibles = []
        for phase in phases:
            if phase.type not in TYPES_EN_TABLEAU or phase.id is None:
                continue
            etat = self._etat_ou_rien(tournoi_id, phase.id)
            if etat is not None:
                lisibles.append(
                    TableauPublic(phase_id=phase.id, ordre=phase.ordre, type=phase.type, etat=etat)
                )
        return TableauxDuTournoi(tournoi_id=tournoi_id, tableaux=tuple(lisibles))

    def _etat_ou_rien(self, tournoi_id: TournoiId, phase_id: PhaseId) -> EtatTableau | None:
        """La photo d'un tableau, ou `None` s'il n'est **pas encore lisible**.

        Le matin, un déroulé composé pour 8 archers porte des phases dont la source ne prélève
        encore personne : le moteur refuse à juste titre de monter un arbre de moins de deux
        participants. Laisser remonter l'erreur donnerait une **page blanche** — sur une surface
        publique et projetée, pour tout le monde, à cause d'une phase qui n'a pas commencé.

        On avale donc l'échec **par phase**, exactement comme `ServiceSuiviDeroule._duels_tranches`
        (E07US004) et pour la même raison. La contrepartie est réelle et assumée : un tableau
        **cassé** est indiscernable d'un tableau **à venir** — les deux disparaissent de la liste.
        C'est le bon arbitrage pour cette surface (le public n'a rien à réparer), pas pour une
        surface d'administration ; le diagnostic de format, lui, vit à l'atelier (E01US024).
        """
        try:
            return self._saisie.etat_tableau(tournoi_id, phase_id)
        except (ApplicationError, DomainError, KeyError):
            return None
