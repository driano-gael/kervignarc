"""Port et collaborateur **neutres** partagés par les cinq services de saisie (ADR-0091).

⚠️ **Module sans dépendance de service, délibérément** : définir le port chez son réalisateur ferait
dépendre un service bas d'un module d'orchestration. Patron déjà employé par
`application.prelevement`. `DeclencheurArrets` évite d'écrire cinq fois le même trio — et c'est
précisément le geste dont l'oubli rend l'US **inerte** (`DETTE-028`). Il se construit **sans
argument** : aucune signature de service ne change.
"""

from __future__ import annotations

import logging
from typing import Protocol

from application.erreurs import PhaseEnPause
from domain.depart import DepartId
from domain.phase import Phase, PhaseId, StatutPhase

_logger = logging.getLogger(__name__)

__all__ = ["DeclencheurArrets", "EvaluateurArrets", "refuser_si_en_pause"]


class EvaluateurArrets(Protocol):
    """Port étroit : « quelque chose vient d'être validé dans ce créneau ».

    Réalisé par `application.arrets_programmes.ServiceArretsProgrammes`, consommé par les services
    d'écriture — qui sont les seuls à savoir qu'un résultat vient d'être persisté. Un port plutôt
    qu'une dépendance au service entier : la saisie n'a pas à connaître les arrêts, seulement à
    **signaler**. Même parti que `DiffusionSimulation` (ADR-0055 §5).
    """

    def evaluer(self, depart_id: DepartId) -> tuple[PhaseId, ...]:
        """Applique les arrêts devenus dus et renvoie les phases mises en pause."""
        ...


def refuser_si_en_pause(phase: Phase) -> None:
    """Refuse un résultat **neuf** sur une phase en pause — `PhaseEnPause` (409).

    ⚠️ **Ce que cette garde couvre et ne couvre pas** est un CA explicite du commanditaire
    (19/08/2026) : la pause gèle ce qui *avance*, jamais ce qui *répare*. Elle n'est donc pas posée
    sur `ServiceSaisie.corriger_volee` ni sur `ServiceSaisieDuels.saisir_manche` — c'est pendant la
    pause qu'on relit les feuilles. ⚠️ Avant E05US033, `EN_PAUSE` ne gelait **rien** ; cf.
    `DETTE-073` pour le volet **tournoi**, resté cosmétique.
    """
    if phase.statut is StatutPhase.EN_PAUSE:
        raise PhaseEnPause(
            "Cette phase est en pause : la saisie reprendra quand l'organisateur relancera. "
            "La correction d'un score déjà saisi reste possible."
        )


class DeclencheurArrets:
    """Le signalement « un résultat vient d'être validé », branché tardivement.

    Construit **sans argument**, il reste **inerte** tant que le composition root n'y a pas branché
    d'évaluateur — un service non branché se comporte donc comme avant E05US033, ce qui laisse les
    décors de test intacts. ⚠️ **C'est aussi le mode de panne** : un branchement oublié rend toute
    l'US inerte sans qu'une ligne rougisse (c'est `DETTE-028`), d'où un câblage en **un seul
    endroit visible** pour les cinq services.
    """

    def __init__(self) -> None:
        self._evaluateur: EvaluateurArrets | None = None

    def brancher(self, evaluateur: EvaluateurArrets) -> None:
        """Dit à qui signaler. Appelé au composition root, après construction du service
        d'arrêts."""
        self._evaluateur = evaluateur

    def signaler(self, depart_id: DepartId) -> None:
        """Fait évaluer les arrêts programmés du créneau. **Ne lève jamais.**

        ⚠️ **Appelé après l'écriture, jamais avant** : l'arrêt se déclenche sur un tour *achevé*.
        ⚠️ **`Exception` et non le triplet typé** : le tuple laisserait passer une
        `InfrastructureError`, l'attraper nommément inverserait le sens des dépendances (règle 2),
        et la validation est **déjà persistée** — un 500 ici ferait ressaisir une volée
        enregistrée. Le déclencheur est idempotent.
        """
        if self._evaluateur is None:
            return
        try:
            self._evaluateur.evaluer(depart_id)
        except Exception as exc:
            _logger.warning(
                "Arrêts programmés non évalués après validation sur le créneau %s : %r",
                depart_id,
                exc,
            )
