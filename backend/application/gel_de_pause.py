"""Le **gel** d'une phase en pause et le **signalement** d'une validation (E05US033, [ADR-0091]).

Deux gestes que les **cinq** services qui écrivent un résultat doivent faire, et qui n'appartiennent
à aucun d'eux :

- **refuser** un résultat neuf sur une phase `EN_PAUSE` (`refuser_si_en_pause`) ; - **signaler**
qu'un résultat vient d'être écrit, pour que les arrêts programmés s'évaluent
  (`DeclencheurArrets`).

Les cinq services concernés sont `ServiceSaisie` (qualification), `ServiceSaisieDuels` (élimination
directe), `ServicePoules`, `ServiceSuisse` et `ServiceBigShootOff`.

⚠️ **Module neutre, et c'est un correctif de revue.** La première rédaction définissait le port
`EvaluateurArrets` dans `application.arrets_programmes` — c'est-à-dire chez son **réalisateur** — et
le faisait importer par les services de saisie, donc un service bas dépendait d'un module
d'orchestration qui importe lui-même `ServicePhases`. Le commentaire d'alors posait une fausse
alternative (« le définir chez l'un obligerait l'autre à l'importer de son jumeau, ou à en tenir une
copie ») ; l'axe A a montré qu'il en existe une troisième, **déjà en service** dans le dépôt :
`application.prelevement` héberge `LecteurPopulationPhase`, port à deux consommateurs, dans un
module sans dépendance de service — et sa docstring dit explicitement pourquoi (« cela évite que
`application/saisie.py` importe `application/saisie_duels.py` »). Ce module reprend ce patron.

⚠️ **`DeclencheurArrets` existe pour ne pas écrire cinq fois le même trio.** Chaque service portait
son attribut, son `brancher_evaluateur_arrets` et son `_signaler_validation` — une vingtaine de
lignes identiques. À deux services c'était tolérable ; à cinq, c'est la duplication d'invariant que
le § *Dette* proscrit, et le geste à répliquer est précisément celui dont l'oubli rend l'US
**inerte** (`DETTE-028`). Le collaborateur se construit **sans argument**, donc aucune signature de
service ne change et aucun décor de test existant n'est touché.

[ADR-0091]: ../docs/adr/0091-un-arret-programme-coupe-le-deroule-a-la-fin-d-un-tour.md
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

    ⚠️ **Ce que cette garde couvre, et ce qu'elle ne couvre pas**, est un CA explicite du
    commanditaire (19/08/2026) : la pause gèle ce qui *avance*, jamais ce qui *répare*. Les
    appelants la posent donc sur la **validation** d'un résultat neuf, et **pas** sur la
    rectification d'un score déjà saisi (`ServiceSaisie.corriger_volee`) ni sur la poursuite d'une
    rencontre déjà engagée (`ServiceSaisieDuels.saisir_manche`). C'est précisément pendant la pause
    que l'on relit les feuilles et que l'on découvre les erreurs : l'interdire ferait de chaque
    pause un cul-de-sac, dont la seule issue serait de relancer toute la salle pour corriger une
    flèche.

    ⚠️ **Avant E05US033, `StatutPhase.EN_PAUSE` ne gelait rien du tout** : aucun service d'écriture
    ne lisait le statut de la phase, et la pause n'était qu'un libellé dans le suivi. Cf.
    `DETTE-073` pour le volet **tournoi**, resté cosmétique et hors périmètre (autre maille,
    ADR-0026 §3).
    """
    if phase.statut is StatutPhase.EN_PAUSE:
        raise PhaseEnPause(
            "Cette phase est en pause : la saisie reprendra quand l'organisateur relancera. "
            "La correction d'un score déjà saisi reste possible."
        )


class DeclencheurArrets:
    """Le signalement « un résultat vient d'être validé », branché tardivement.

    Construit **sans argument** par chaque service d'écriture, il reste **inerte** tant que le
    composition root n'y a pas branché d'évaluateur — donc un service non branché se comporte
    exactement comme avant E05US033, ce qui laisse tous les décors de test existants intacts.

    ⚠️ **C'est aussi le mode de panne à connaître** : un branchement oublié rend toute l'US inerte
    sans qu'une seule ligne rougisse. C'est `DETTE-028` (six moteurs livrés, aucun appelé), et c'est
    la raison pour laquelle le composition root le fait en un seul endroit visible, pour les cinq
    services d'un coup.
    """

    def __init__(self) -> None:
        self._evaluateur: EvaluateurArrets | None = None

    def brancher(self, evaluateur: EvaluateurArrets) -> None:
        """Dit à qui signaler. Appelé au composition root, après construction du service
        d'arrêts."""
        self._evaluateur = evaluateur

    def signaler(self, depart_id: DepartId) -> None:
        """Fait évaluer les arrêts programmés du créneau. **Ne lève jamais.**

        ⚠️ **Appelé après l'écriture, jamais avant.** L'arrêt se déclenche sur un tour *achevé* :
        évaluer avant que le résultat soit persisté ferait lire l'avancement d'avant, donc manquer
        la frontière de tour — et le suivant l'attraperait, avec un tour de retard visible en salle.

        ⚠️ **`Exception` et non le triplet typé habituel**, et c'est un choix. Le tuple
        `(ApplicationError, DomainError)` laisserait passer une `InfrastructureError` (SQLite
        occupé, base altérée), et l'attraper nommément demanderait à cette couche d'importer
        `infrastructure`, donc d'inverser le sens des dépendances (règle 2) pour une seule ligne
        d'`except`.

        Le vrai argument est ailleurs : la validation **a réussi et est persistée**. Toute exception
        d'ici est celle d'un *effet de bord*, et la laisser remonter rendrait un 500 à un archer qui
        a bien tiré — qui ressaisirait alors une volée déjà enregistrée. Le déclencheur étant
        idempotent, la validation suivante réévaluera : le pire coût est une pause qui tombe un
        résultat plus tard.
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
