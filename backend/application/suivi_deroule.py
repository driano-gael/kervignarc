"""Suivi du déroulé — compose le **plan** et l'**avancement** sans recalculer aucune règle.

⚠️ **Un exempt (bye) n'est PAS un duel joué**, et c'est le piège central : dans un tableau
incomplet, les exempts sont gagnés d'office dès la construction. Les compter afficherait « premier
tour terminé » avant que quiconque ait tiré — et la projection ne les compte pas non plus. Un
tableau qu'on ne sait pas reconstruire laisse un bloc à zéro plutôt qu'une page d'erreur : l'écran
de salle tourne sans personne devant. Coût de recomposition : `DETTE-031`.
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from application.erreurs import ApplicationError, DepartIntrouvable
from domain.depart import DepartId
from domain.deroule import ProjectionDeroule, TourBraquet, projeter
from domain.erreurs import DomainError
from domain.phase import TYPES_EN_TABLEAU, Phase, PhaseId, TypePhase
from domain.ports import (
    DepartRepository,
    InscriptionRepository,
    PhaseRepository,
    TournoiRepository,
)
from domain.suivi_deroule import (
    STATUTS_DEMARRES,
    AvancementDePhase,
    AvancementDeroule,
    avancement_bloc,
)
from domain.tableau import Match, Tableau
from domain.tournoi import TournoiId

_logger = logging.getLogger(__name__)


class LecteurAvancementDePhase(Protocol):
    """Port étroit : « **où en est** cette phase ? » (ADR-0090 §5).

    Réalisé par les services de format, branché **par type** au composition root (règle 8) : le
    suivi ne connaît aucun de ces services, il connaît **cette question**. ⚠️ Même patron que
    `LecteurClassementDePhase` (ADR-0084) — un second mécanisme de résolution par type aurait été
    la 4ᵉ occurrence de la même idée. Rend `None` quand le service ne sait rien dire : une
    **réponse**, pas une erreur, l'écran de salle tournant en permanence.
    """

    def avancement_de_phase(
        self, tournoi_id: TournoiId, phase_id: PhaseId
    ) -> AvancementDePhase | None:
        """Combien de tours cette phase compte aujourd'hui, et lequel tourne."""
        ...


class CompteurEngages(Protocol):
    """Port étroit : combien d'archers sont engagés dans ce **créneau**.

    L'équivalent live du « je simule à N archers » de l'atelier. ⚠️ **Par départ, et le nom le
    dit** (E01US025, ADR-0075) : la méthode s'appelait `nb_engages` et prenait un `tournoi_id`, si
    bien que quatre créneaux de 100 archers dimensionnaient un tableau pour 400. Le renommage n'est
    pas cosmétique — `TournoiId` et `DepartId` sont le même type pour mypy (`DETTE-044`), donc seul
    un **nom qui change** force la revisite de chaque appel.
    """

    def nb_engages_du_depart(self, depart_id: DepartId) -> int:
        """Nombre d'archers inscrits sur ce créneau."""
        ...


class LecteurTableau(Protocol):
    """Port étroit : reconstruire l'arbre d'une phase (réalisé par `ServiceSaisieDuels`).

    Le suivi ne dépend pas de tout `ServiceSaisieDuels` : juste de sa capacité à rendre le tableau
    reconstruit. On **ne duplique pas** la reconstruction — une seule source de vérité de la
    progression, comme la saisie, le placement et le feu vert la partagent déjà.
    """

    def reconstruire(self, tournoi_id: TournoiId, phase_id: PhaseId) -> tuple[Tableau, object]:
        """Rend le tableau de la phase (et son classement, **ignoré ici**).

        Le second membre est typé `object` et non `dict[int, LigneClassement]` : le suivi n'en fait
        rien, et un `dict` étant **invariant** en typage, l'annoter précisément aurait fait échouer
        la conformité de `ServiceSaisieDuels` au port pour une valeur qu'on jette. Un port étroit ne
        décrit que ce dont il a besoin.
        """
        ...


def _correspondance(tableau: Tableau, braquets: Sequence[TourBraquet]) -> dict[int, TourBraquet]:
    """Quel braquet projeté correspond à quel tour **réel** — alignés **par la fin**.

    ⚠️ Trois passes de revue ici, chaque correctif intermédiaire étant juste sur le cas testé et
    faux sur sa classe : compter tous les matchs d'un tour terminait la phase à la petite finale ;
    filtrer sur l'égalité des plages était impossible (rangs absolus contre relatifs) ; normaliser
    par décalage rendait le compte faux. **Le bon repère est la fin** : les *N* tours projetés sont
    les *N* **derniers** tours réels, quelle que soit la taille d'entrée.
    """
    decalage = tableau.nb_tours - len(braquets)
    return {braquet.tour + decalage: braquet for braquet in braquets}


def _est_de_la_branche(match: Match, braquet: TourBraquet) -> bool:
    """Ce match est-il celui de la branche des gagnants que ce braquet décrit ?

    Deux conditions, **toutes deux indépendantes du repère** — c'est ce qui rend la comparaison
    robuste là où l'égalité de plages échouait : `plage.debut == 1` (la branche des gagnants part
    du haut du tableau, ce qui écarte la petite finale), et **même largeur** que le braquet (une
    largeur est un nombre de rangs, pas une position, donc elle se compare sans conversion).
    `Match.plage` absente (matchs bâtis à la main dans les tests) → on compte, faute de mieux.
    """
    if match.plage is None:
        return True
    largeur_projetee = braquet.plage_perdants[1] - braquet.plage_gagnants[0] + 1
    return match.plage.debut == 1 and match.plage.fin - match.plage.debut + 1 == largeur_projetee


class CompteurEngagesRepository:
    """Réalisation de `CompteurEngages` sur les repositories : les inscriptions **d'un créneau**.

    C'est l'effectif que la projection doit résoudre — « combien de personnes ce déroulé doit-il
    faire tirer *dans ce créneau* », pas « combien de dossards le tournoi a vendus ». Les archers
    sont **dédoublonnés**. Vit ici plutôt qu'en `infrastructure/` : il ne connaît que des **ports**
    (règle 2), aucune technologie de persistance.
    """

    def __init__(
        self, depart_repository: DepartRepository, inscription_repository: InscriptionRepository
    ) -> None:
        self._departs = depart_repository
        self._inscriptions = inscription_repository

    def nb_engages_du_depart(self, depart_id: DepartId) -> int:
        """Nombre d'archers **distincts** inscrits sur ce créneau."""
        return len({i.archer_id for i in self._inscriptions.par_depart(depart_id)})


@dataclass(frozen=True)
class SuiviDeroule:
    """Le déroulé d'une édition : le dessin (projection) **et** son remplissage (avancement).

    Les deux restent **séparés** plutôt que fusionnés en un objet unique : c'est ce qui garantit que
    le composant de dessin reçoit à l'atelier et au pilotage exactement la même structure, et que le
    suivi n'est qu'un calque par-dessus (la « décision de conception centrale » du CA : un seul
    composant, trois surfaces).
    """

    effectif: int
    projection: ProjectionDeroule
    avancement: AvancementDeroule


class ServiceSuiviDeroule:
    """Cas d'usage : « où en est ce **créneau** ? », pour le pilotage et pour l'écran de salle."""

    def __init__(
        self,
        tournoi_repository: TournoiRepository,
        depart_repository: DepartRepository,
        phase_repository: PhaseRepository,
        engages: CompteurEngages,
        tableaux: LecteurTableau,
    ) -> None:
        self._tournois = tournoi_repository
        self._departs = depart_repository
        self._phases = phase_repository
        self._engages = engages
        self._tableaux = tableaux
        self._avancements: dict[TypePhase, LecteurAvancementDePhase] = {}

    def brancher_lecteur_avancement(
        self, type_phase: TypePhase, lecteur: LecteurAvancementDePhase
    ) -> None:
        """Dit qui sait répondre « où en est cette phase ? » pour ce type ([ADR-0090] §5).

        Branchement **tardif et visible** au composition root, comme celui de
        `ServiceSaisieDuels.brancher_lecteur` (ADR-0084) : les services de format sont construits
        après le suivi, et un cycle qu'on ne voit pas est un cycle qu'on réintroduit.

        [ADR-0090]: ../../docs/adr/0090-une-phase-avance-par-tours-un-tour-n-est-pas-un-braquet.md
        """
        self._avancements[type_phase] = lecteur

    def pour_depart(self, depart_id: DepartId) -> SuiviDeroule:
        """Le suivi complet d'un **créneau**. `DepartIntrouvable` si le créneau n'existe pas.

        ⚠️ **La maille est le départ, pas le tournoi** (E01US025, ADR-0075) : `par_tournoi` n'est
        pas une séquence mais la concaténation de N suites 1..M, si bien que sur deux créneaux le
        déroulé était dessiné en double, l'avancement du dernier écrasait les autres et l'effectif
        était fusionné. Un créneau **sans phase** rend un suivi vide. `# DETTE-031` — tout est
        recalculé à chaque appel, sur une route publique pollée toutes les 10 s.
        """
        depart = self._departs.par_id(depart_id)
        if depart is None:
            raise DepartIntrouvable(f"Aucun départ d'identifiant {depart_id}.")
        tournoi_id = depart.tournoi_id
        phases = sorted(self._phases.par_depart(depart_id), key=lambda phase: phase.ordre)
        effectif = self._engages.nb_engages_du_depart(depart_id)
        projection = projeter(phases, effectif)
        par_ordre = {phase.ordre: phase for phase in phases}
        blocs = tuple(
            avancement_bloc(
                ordre=bloc.ordre,
                statut=par_ordre[bloc.ordre].statut,
                tours=bloc.tours,
                joues_par_tour=self._duels_tranches(tournoi_id, par_ordre[bloc.ordre], bloc.tours),
                avancement_lu=self._avancement_lu(tournoi_id, par_ordre[bloc.ordre]),
            )
            for bloc in projection.blocs
        )
        return SuiviDeroule(
            effectif=effectif,
            projection=projection,
            avancement=AvancementDeroule(blocs=blocs),
        )

    def avancement_par_phase(self, depart_id: DepartId) -> dict[PhaseId, AvancementDePhase]:
        """Où en est chaque phase de ce créneau, **par identifiant de phase** (E05US033).

        Réalise `LecteurAvancementDuDepart`. Cette couture vit **ici** parce que c'est le seul
        endroit qui sache répondre pour **tous** les formats : l'élimination directe n'a aucun
        lecteur branché, si bien qu'un consommateur interrogeant le port par phase laisserait les
        tableaux hors du mécanisme d'arrêt sans que rien ne rougisse. ⚠️ **La clé change de nature
        au passage** — `ordre` contre `PhaseId`, trois alias d'`int` (`DETTE-044`).
        """
        suivi = self.pour_depart(depart_id)
        par_ordre = {
            phase.ordre: phase.id
            for phase in self._phases.par_depart(depart_id)
            if phase.id is not None
        }
        avancements: dict[PhaseId, AvancementDePhase] = {}
        for bloc in suivi.avancement.blocs:
            phase_id = par_ordre.get(bloc.ordre)
            if phase_id is None:
                continue
            avancements[phase_id] = AvancementDePhase(
                nb_tours=bloc.nb_tours, tour_courant=bloc.tour_courant
            )
        return avancements

    def _avancement_lu(self, tournoi_id: TournoiId, phase: Phase) -> AvancementDePhase | None:
        """Ce que le service du format dit de l'avancement de cette phase, ou `None`.

        ⚠️ **Aucune exception ne remonte d'ici** : cette méthode alimente un endpoint **public**
        pollé toutes les 10 s, et une phase mal réglée ferait tomber tout le schéma. Le tuple
        rattrapé inclut `KeyError`, que `contrat_de` lève par conception, et **chaque cas est
        journalisé** — sinon « pourquoi la ronde ne s'affiche pas ? » serait indébogable. `#
        DETTE-031` — les `etat()` recomposent intégralement leur phase.
        """
        lecteur = self._avancements.get(phase.type)
        if lecteur is None or phase.id is None or phase.statut not in STATUTS_DEMARRES:
            return None
        try:
            return lecteur.avancement_de_phase(tournoi_id, phase.id)
        except (ApplicationError, DomainError) as exc:
            _logger.info("Avancement de la phase %s non lisible : %s", phase.id, exc)
            return None
        except KeyError as exc:
            _logger.warning("Défaut interne sur la phase %s, avancement écarté : %r", phase.id, exc)
            return None

    def _duels_tranches(
        self, tournoi_id: TournoiId, phase: Phase, braquets: Sequence[TourBraquet]
    ) -> dict[int, int]:
        """Les duels **réellement disputés et tranchés**, par numéro de tour.

        Trois filtres : `vainqueur is not None` ; `not est_bye` ; et **même branche que le
        braquet** — au dernier tour il y en a **deux**, la finale et la petite finale, et les
        compter ensemble affichait la phase **terminée pendant que la finale se tirait**, sur
        l'écran projeté. On filtre la **réalité** plutôt que de corriger la projection : le CA
        impose le **même** schéma qu'à l'atelier. Résultat indexé par **numéro de braquet**.
        """

        # Sans braquet, il n'y a rien à remplir : on évite la reconstruction, l'opération la plus
        # coûteuse du service (`# DETTE-031`) — cas d'une phase à plusieurs sources.
        if phase.type not in TYPES_EN_TABLEAU or phase.id is None or not braquets:
            return {}
        try:
            tableau, _ = self._tableaux.reconstruire(tournoi_id, phase.id)
        except (ApplicationError, DomainError, KeyError):
            return {}
        par_tour_reel = _correspondance(tableau, braquets)
        comptes: Counter[int] = Counter()
        for match in tableau.matchs:
            if match.vainqueur is None or match.est_bye:
                continue
            braquet = par_tour_reel.get(match.tour)
            if braquet is not None and _est_de_la_branche(match, braquet):
                comptes[braquet.tour] += 1
        return comptes
