"""Service applicatif du **suivi du déroulé** (E07US004, ADR-0064) — le plan rempli par la réalité.

Compose deux choses qui existent déjà, sans en recalculer aucune :

- la **projection** du format appliqué au tournoi (`domain.deroule.projeter`), c'est-à-dire *le même
  schéma à braquets* qu'à l'atelier — le mot « même » est dans le CA, et il est contraignant : si
  le suivi redessinait, l'organisateur ne reconnaîtrait pas ce qu'il a composé ;
- l'**avancement** (`domain.suivi_deroule`), c'est-à-dire ce qui est joué, dénombré ici depuis les
  tableaux reconstruits.

**Un exempt (bye) n'est pas un duel joué.** C'est le piège central de la composition : dans un
tableau incomplet, les exempts sont gagnés d'office dès la construction. Les compter afficherait
« premier tour terminé » avant que quiconque ait tiré — et surtout, la projection ne les compte pas
non plus (`domain.deroule._braquets` : *« 24 duellistes dans un tableau de 32 → 8 duels, 8
exemptés »*). Les deux comptes doivent parler de la même chose, sans quoi le rapport « joués /
attendus » est faux des deux côtés.

**Robustesse jour J.** Un tableau qu'on ne sait pas reconstruire — format retouché en cours de
route, phase mal câblée — laisse un bloc à zéro joué plutôt qu'une page d'erreur. L'écran de salle
tourne en permanence, souvent sans personne devant pour le relancer : une exception y coûte
l'affichage de toute la journée, un compteur à zéro coûte une ligne inexacte.

Lecture seule et synchrone hors boucle événementielle (règle 7).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from application.erreurs import ApplicationError, TournoiIntrouvable
from domain.deroule import ProjectionDeroule, TourBraquet, projeter
from domain.erreurs import DomainError
from domain.phase import Phase, PhaseId, TypePhase
from domain.ports import (
    DepartRepository,
    InscriptionRepository,
    PhaseRepository,
    TournoiRepository,
)
from domain.suivi_deroule import AvancementDeroule, avancement_bloc
from domain.tableau import Match, Tableau
from domain.tournoi import TournoiId

_TYPES_EN_TABLEAU = frozenset({TypePhase.ELIMINATION_DIRECTE, TypePhase.PLACEMENT})
"""Les types dont on sait reconstruire un arbre — donc dénombrer les duels tranchés.

Volontairement **le même ensemble** que `domain.deroule._TYPES_EN_TABLEAU` : les autres types du
catalogue (E05US015) n'ont pas de braquet projeté, il n'y a donc rien à y remplir (`# DETTE-028`).
"""


class CompteurEngages(Protocol):
    """Port étroit : combien d'archers sont engagés dans ce tournoi.

    C'est l'effectif sur lequel la projection se résout — l'équivalent live du « je simule à N
    archers » de l'atelier. Port étroit plutôt que dépendance à un service entier, même parti que
    `application.supervision.LecteurAvancement`.
    """

    def nb_engages(self, tournoi_id: TournoiId) -> int:
        """Nombre d'archers inscrits au tournoi, tous départs confondus."""
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


def _decalage(braquets: Sequence[TourBraquet]) -> int:
    """De combien décaler les plages du tableau pour les lire dans les rangs **du tournoi**.

    ⚠️ **Deux systèmes de coordonnées, et c'est le piège qui a coûté deux correctifs.**
    `_braquets` (`domain.deroule`) produit des plages **absolues** — sa docstring l'écrit :
    *« un tableau des rangs 33-64 rend des perdants en 49-64 »*. `construire_tableau`, lui,
    engendre ses `Match.plage` **relatives au tableau**, toujours à partir de 1. Comparer
    les deux directement ne pouvait fonctionner que pour un tableau partant du rang 1 — le seul cas
    que montaient les fixtures. Sur un tableau de placement des rangs 9-16, aucune plage ne
    correspondait à aucun tour, et l'écran projeté affichait « 0 duel joué » du début à la fin de la
    journée.

    Le premier tour du braquet donne l'origine : `plage_gagnants[0]` vaut la borne basse de la
    tranche d'entrée (`_braquets` part de `Plage(tranche[0], …)`).
    """
    premier = braquets[0] if braquets else None
    return 0 if premier is None else premier.plage_gagnants[0] - 1


def _branches_reconnues(
    tableau: Tableau, braquets: Sequence[TourBraquet], decalage: int
) -> dict[int, tuple[int, int]]:
    """Les branches projetées que le tableau reconstruit **contient réellement**, par tour.

    Deuxième garde, après la normalisation des coordonnées : **le filtre ne s'applique que si les
    deux structures parlent du même arbre**. Les tailles peuvent différer même à origine commune —
    `# DETTE-028` fait que `ServiceSaisieDuels._decor` ensemence l'arbre avec *tous* les archers en
    lice, sans lire `Phase.sources`, quand `_braquets` compte l'effectif **déclaré**. Une phase
    déclarant « rangs 1..8 » mais jouée à 12 donne des plages réelles `(1,16)`, `(1,8)`, `(1,4)`…
    face à des branches `(1,8)`, `(1,4)`, `(1,2)`.

    Le critère juste n'est pas *combien* on a compté — un tour dont seule la petite finale est jouée
    compte légitimement zéro — mais si la branche projetée **existe** parmi les matchs de ce tour,
    joués ou non. Si elle existe, on filtre (la petite finale est écartée) ; sinon on ne filtre pas,
    et on retombe sur le comptage d'avant, plafonné par `avancement_bloc`. Un compte approximatif
    vaut mieux qu'un compteur bloqué à zéro.
    """
    presentes: dict[int, set[tuple[int, int]]] = {}
    for match in tableau.matchs:
        if match.plage is not None:
            presentes.setdefault(match.tour, set()).add(
                (match.plage.debut + decalage, match.plage.fin + decalage)
            )
    reconnues: dict[int, tuple[int, int]] = {}
    for braquet in braquets:
        attendue = (braquet.plage_gagnants[0], braquet.plage_perdants[1])
        if attendue in presentes.get(braquet.tour, set()):
            reconnues[braquet.tour] = attendue
    return reconnues


def _dans_la_branche(match: Match, branche: tuple[int, int] | None, decalage: int) -> bool:
    """Ce match appartient-il à la branche que décrit le braquet de son tour ?

    `Match.plage` est la tranche de rangs que ce match départage, **relative au tableau** ; on la
    ramène dans les rangs du tournoi (`decalage`) avant de comparer. Au dernier tour, la finale
    porte alors la branche du braquet et la petite finale une autre — deux branches distinctes à la
    même profondeur.

    **Compte par défaut** quand l'information manque : branche non reconnue (cf.
    `_branches_reconnues`), tour sans braquet, ou `Match.plage` non renseignée (les `Match` bâtis à
    la main dans les tests). Mieux vaut un compte plafonné qu'un compteur bloqué à zéro.
    """
    if branche is None or match.plage is None:
        return True
    return (match.plage.debut + decalage, match.plage.fin + decalage) == branche


class CompteurEngagesRepository:
    """Réalisation de `CompteurEngages` sur les repositories : les inscriptions de tous les départs.

    Un archer inscrit à **deux** créneaux (cas rare mais légal) serait compté deux fois par une
    simple somme : on dénombre donc les **archers distincts**. C'est l'effectif que la projection
    doit résoudre — « combien de personnes ce format doit-il faire tirer », pas « combien de
    dossards ont été vendus ».

    Vit ici plutôt qu'en `infrastructure/` : il ne connaît que des **ports** (règle 2), aucune
    technologie de persistance.
    """

    def __init__(
        self, depart_repository: DepartRepository, inscription_repository: InscriptionRepository
    ) -> None:
        self._departs = depart_repository
        self._inscriptions = inscription_repository

    def nb_engages(self, tournoi_id: TournoiId) -> int:
        """Nombre d'archers **distincts** inscrits au tournoi, tous départs confondus."""
        archers: set[int] = set()
        for depart in self._departs.par_tournoi(tournoi_id):
            if depart.id is None:
                continue
            archers.update(
                inscription.archer_id for inscription in self._inscriptions.par_depart(depart.id)
            )
        return len(archers)


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
    """Cas d'usage : « où en est le tournoi ? », pour le pilotage et pour l'écran de salle."""

    def __init__(
        self,
        tournoi_repository: TournoiRepository,
        phase_repository: PhaseRepository,
        engages: CompteurEngages,
        tableaux: LecteurTableau,
    ) -> None:
        self._tournois = tournoi_repository
        self._phases = phase_repository
        self._engages = engages
        self._tableaux = tableaux

    def pour_tournoi(self, tournoi_id: TournoiId) -> SuiviDeroule:
        """Le suivi complet d'un tournoi. `TournoiIntrouvable` si le tournoi n'existe pas.

        Un tournoi **sans phase** rend un suivi vide plutôt qu'une erreur : avant qu'un format soit
        appliqué, l'écran doit afficher « rien à suivre », pas une page cassée.

        # DETTE-031 : tout est **recalculé à chaque appel** — le compte des engagés, et surtout la
        # reconstruction de chaque phase en tableau (qui rejoue le classement complet du tournoi).
        # Endpoint public, pollé toutes les 10 s par deux surfaces. Assumé au contexte mono-club et
        # local ; le remède est borné (mémoïsation par version, invalidée par donnees_modifiees),
        # mais aucune mesure ne le réclame aujourd'hui. Cf. docs/dette.md.
        """
        if self._tournois.par_id(tournoi_id) is None:
            raise TournoiIntrouvable(f"Aucun tournoi d'identifiant {tournoi_id}.")
        phases = sorted(self._phases.par_tournoi(tournoi_id), key=lambda phase: phase.ordre)
        effectif = self._engages.nb_engages(tournoi_id)
        projection = projeter(phases, effectif)
        par_ordre = {phase.ordre: phase for phase in phases}
        blocs = tuple(
            avancement_bloc(
                ordre=bloc.ordre,
                statut=par_ordre[bloc.ordre].statut,
                tours=bloc.tours,
                joues_par_tour=self._duels_tranches(tournoi_id, par_ordre[bloc.ordre], bloc.tours),
            )
            for bloc in projection.blocs
        )
        return SuiviDeroule(
            effectif=effectif,
            projection=projection,
            avancement=AvancementDeroule(blocs=blocs),
        )

    def _duels_tranches(
        self, tournoi_id: TournoiId, phase: Phase, braquets: Sequence[TourBraquet]
    ) -> dict[int, int]:
        """Les duels **réellement disputés et tranchés**, par numéro de tour.

        Trois filtres. Les deux premiers sont évidents une fois écrits ; le troisième est celui que
        la revue a dû trouver, et c'est le seul qui produisait un affichage **faux devant le
        public** :

        - `vainqueur is not None` : le duel est allé au bout ;
        - `not est_bye` : un exempt occupe une place du braquet mais **n'est pas un duel** — la
          projection ne le compte pas davantage ;
        - **même branche que le braquet** : un braquet décrit *une* branche à une profondeur donnée
          (`[plage_gagnants.debut … plage_perdants.fin]`), pas tous les matchs de ce rang. Au
          dernier tour d'une élimination directe, il y en a **deux** : la finale (places 1-2) et la
          **petite finale** (places 3-4), que `PlacementEnCascade` fait jouer aux perdants des
          demies. Les compter ensemble donnait « 2 joués sur 1 attendu », plafonné à 1 : dès que la
          petite finale tombait — souvent avant la finale, ou en parallèle — la phase s'affichait
          **terminée pendant que la finale se tirait**, sur l'écran projeté, au moment de la journée
          où il est le plus regardé.

        On filtre donc la **réalité** plutôt que de corriger la projection : le CA impose « le
        **même** schéma » qu'à l'atelier, et `_braquets` (E01US024) ne suit délibérément que la
        branche des gagnants. Corriger le dessin ici, c'est le faire diverger de ce que
        l'organisateur a composé.

        Rend un dictionnaire vide dès que le tableau n'est pas lisible : phase non persistée, type
        sans arbre, ou reconstruction en échec (voir la note de robustesse jour J).
        """
        if phase.type not in _TYPES_EN_TABLEAU or phase.id is None:
            return {}
        try:
            tableau, _ = self._tableaux.reconstruire(tournoi_id, phase.id)
        except (ApplicationError, DomainError, KeyError):
            return {}
        decalage = _decalage(braquets)
        branches = _branches_reconnues(tableau, braquets, decalage)
        return Counter(
            match.tour
            for match in tableau.matchs
            if match.vainqueur is not None
            and not match.est_bye
            and _dans_la_branche(match, branches.get(match.tour), decalage)
        )
