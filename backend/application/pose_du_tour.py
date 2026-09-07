"""Port et déclencheur **neutres** de la pose automatique d'un tour (E03US012, ADR-0106).

⚠️ **Module sans dépendance de service, délibérément** : `ServicePlacementDuels` dépend déjà de
`ServiceSaisieDuels`, et faire dépendre la saisie du placement fermerait le cycle. Le port vit donc
chez personne — 2ᵉ occurrence du patron de `application.gel_de_pause`, recopié plutôt qu'abstrait
(le remède structurel attend une 3ᵉ occurrence réelle).
"""

from __future__ import annotations

import logging
from typing import Protocol

from domain.phase import PhaseId
from domain.tournoi import TournoiId

_logger = logging.getLogger(__name__)

__all__ = ["DeclencheurPoseDeTour", "PoseurDeTour"]


class PoseurDeTour(Protocol):
    """Port étroit : « un duel vient d'être tranché dans cette phase ».

    Réalisé par `application.placement_duels.ServicePlacementDuels`, consommé par les services qui
    peuvent trancher un duel — seuls à savoir qu'un résultat vient d'être persisté.
    """

    def poser_le_tour_courant(self, tournoi_id: TournoiId, phase_id: PhaseId) -> None:
        """Donne une cible aux duellistes du tour à poser qui n'en ont pas encore."""
        ...


class DeclencheurPoseDeTour:
    """Le signalement « un duel vient d'être tranché », branché tardivement.

    Construit **sans argument**, inerte tant que le composition root n'y a branché personne : un
    service non branché se comporte comme avant E03US012, ce qui laisse les décors de test intacts.
    ⚠️ **C'est aussi le mode de panne** (`DETTE-028`) : un branchement oublié rend la pose
    automatique muette sans qu'une ligne rougisse — d'où un câblage en **un seul endroit visible**.
    """

    def __init__(self) -> None:
        self._poseur: PoseurDeTour | None = None

    def brancher(self, poseur: PoseurDeTour) -> None:
        """Dit à qui signaler. Appelé au composition root, après construction du placement."""
        self._poseur = poseur

    def signaler(self, tournoi_id: TournoiId, phase_id: PhaseId) -> None:
        """Fait poser le tour devenu déterminé. **Ne lève jamais.**

        ⚠️ **Appelé après l'écriture, jamais avant** : le tour suivant n'est déterminé qu'une fois
        le résultat persisté. ⚠️ **`Exception` et non un triplet typé** : le résultat est **déjà**
        enregistré, et un 500 ici ferait ressaisir un duel validé — une cible manquante se rattrape
        d'un clic, pas une feuille de marque.
        """
        if self._poseur is None:
            return
        try:
            self._poseur.poser_le_tour_courant(tournoi_id, phase_id)
        except Exception as exc:
            _logger.warning(
                "Pose automatique du tour non effectuée sur la phase %s : %r", phase_id, exc
            )
