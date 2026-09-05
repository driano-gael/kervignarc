"""Panneau de **routage** — agrège en lecture, ne décide de rien (`D-08`).

Les cibles sont attribuées aux **matchs**, pas aux archers : l'affectation existe donc **avant** le
duel, et rien n'est calculé à la bascule.

⚠️ **Ce qui n'est pas connu est NOMMÉ, jamais masqué** (`P-3`) : un blanc se lit comme une panne,
une phrase se lit comme une attente. Jumeau assumé de `pilotage_tour.py` — `DETTE-019`.
"""

# DETTE-028 — aucun moteur ne consomme encore ces prélèvements.

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from application.big_shoot_off import LecteurEtatBigShootOff
from application.erreurs import (
    ApplicationError,
    DepartIntrouvable,
    GabaritDuTournoiAbsent,
    PhaseIntrouvable,
    PrelevementEnAttente,
)
from application.placement_duels import ServicePlacementDuels
from application.portee import phase_du_depart
from application.saisie_duels import Duelliste, ServiceSaisieDuels
from domain.classement import LigneClassement
from domain.contrat_phase import TYPES_ROUTES, TYPES_ROUTES_IMPLICITEMENT
from domain.depart import DepartId
from domain.erreurs import DomainError, EffectifTableauInvalide
from domain.participant import GenreParticipant, Participant
from domain.phase import (
    IssueTour,
    NatureSource,
    Phase,
    PhaseId,
    StatutPhase,
    TypePhase,
)
from domain.politiques import ContexteRoutage, VersRepechage
from domain.ports import ArcherRepository, DepartRepository, PhaseRepository
from domain.tableau import (
    Match,
    PerdantDe,
    Tableau,
    VainqueurDe,
    fourchette_de_rangs,
    libelle_tour,
)
from domain.tournoi import TournoiId

# Les phrases que le panneau affiche quand l'information n'existe pas encore. Elles vivent ici (et
# non dans le front) pour la même raison que le `blocage` du feu vert : c'est le serveur qui sait
# **pourquoi** la donnée manque, et les quatre canaux de routage doivent dire la même chose.
CIBLE_A_VENIR = "cible attribuée au lancement du tour"
"""Tour ≥ 2 : la cible **existera**, elle n'est simplement pas encore posée (E05US010)."""

CIBLE_NON_ATTRIBUEE = "cible non attribuée"
"""Tour 1 sans pose : aucun plan matérialisé, ou archer en réserve. Rien ne viendra tant que
l'organisateur n'aura pas placé — d'où le libellé **neutre** du feu vert, et non une promesse."""

PLACEMENT_AUTRE_CIBLE = "placement à revoir — votre adversaire est sur la cible {cible}"
"""**Mauvais conseil en vue** : la pose annoncée n'est pas là où le duel se tirera.

Le plan a été matérialisé sur un autre appariement (l'arbre est recalculé à chaque lecture,
ADR-0023, alors que les poses sont persistées), ou les cibles sont trop étroites. On annonce quand
même la pose — c'est bien la ligne de cet archer sur le plan — mais en **nommant la butte de
l'autre** : c'est ce qui fait comprendre qu'il faut aller voir l'organisateur.
"""

PLACEMENT_VOISIN_ELOIGNE = "votre adversaire tire sur la même cible, couloir {position}"
"""Même butte, couloirs **non adjacents** — c'est la disposition nominale d'une cible de salle.

Le duel se tire bien là où on l'annonce : la pose est le **bon** conseil, il n'y a rien à revoir
avant de partir. On le dit quand même, parce qu'E03US009 veut les duellistes **côte à côte** et que
l'intéressé est mieux placé que quiconque pour se décaler d'un couloir. Ton neutre, donc : ce n'est
pas la même situation que `PLACEMENT_AUTRE_CIBLE`, et les confondre — ce que faisait le message
unique — c'était soit alarmer pour rien, soit envoyer quelqu'un sur la mauvaise butte.
"""

PLACEMENT_ADVERSAIRE_NON_PLACE = "placement à revoir — votre adversaire n'est pas placé"
"""L'adversaire est en réserve (pas de blason exploitable, pas d'inscription…) : le duel n'a pas
de lieu tant que l'organisateur ne l'a pas posé."""

RANG_A_VENIR = "rang publié en fin de phase"
_logger = logging.getLogger(__name__)

PHASE_ABSENTE = "phase finale non configurée"
TABLEAU_ABSENT = "tableau non constitué"
HORS_TABLEAU = "non retenu pour le tableau"

REPECHAGE_SANS_DESTINATION = "repêché — phase de repêchage non configurée"
"""Le routing repêche ce battu, mais **aucune phase avale ne le prélève** (E07US008).

`construire_tableau` le dit déjà de son côté : un tableau dont la moitié basse n'est pas engendrée
est structurellement valide, donc « les battus disparaissent sans que rien ne le signale ». Le
routage est le premier endroit où ce trou de composition rencontre un **humain** — l'archer demande
où il tire, et personne ne peut répondre. On le nomme plutôt que de rendre un panneau muet, qu'on
prendrait pour une panne réseau (`P-3`, « ce qui n'est pas connu est nommé »).
"""


class IssueRoutage(str, Enum):
    """Ce que le panneau a à dire d'un archer."""

    PROCHAIN_DUEL = "prochain_duel"
    """Il a un duel devant lui (`prochain` renseigné)."""

    TERMINE = "termine"
    """Il n'a plus de duel : éliminé, ou le tableau est allé à son terme pour lui."""

    REPECHE = "repeche"
    """Il a perdu, mais il **ressort** du tableau au lieu d'y être classé (E07US008).

    Quatrième issue ajoutée par le canal public, et non un sous-cas de `TERMINE` : `VersRepechage`
    ne consomme **aucun rang** (`domain/politiques.py`), donc annoncer « terminé » — même sans rang
    — dirait à quelqu'un d'encore en course qu'il peut rentrer chez lui. `destination` nomme la
    phase qui le reprend.
    """

    PROCHAINE_MANCHE = "prochaine_manche"
    """Il tire une **volée collective** au prochain tour : le Big Shoot Off (E05US028).

    ⚠️ **Cinquième issue, et non un `PROCHAIN_DUEL` déguisé.** Un Big Shoot Off n'oppose personne :
    tous les finalistes sont sur la ligne, et c'est le classement de la manche qui élimine. Faire
    passer ce rendez-vous par `ProchainDuel` aurait annoncé un adversaire absent (`None`) et un
    numéro de match qui n'existe pas — précisément le genre de nom trop étroit qu'ADR-0083 a dû
    corriger sur `monte_les_oppositions`. Le champ `prochaine_manche` porte l'information."""

    EN_ATTENTE = "en_attente"
    """Il est dans la phase, en course, mais **rien à tirer maintenant** (E05US030).

    ⚠️ **Sixième issue, et non un `INDISPONIBLE` motivé** : le front partitionne sur l'issue, et
    sous `INDISPONIBLE` un archer encore en lice sortait du groupe des tireurs en course.

    Deux populations : le porteur du **bye** d'une ronde impaire, et celui dont la rencontre vient
    d'être validée pendant que la ronde s'achève (`domain/suisse.py::_rondes_closes`).
    """

    INDISPONIBLE = "indisponible"
    """On ne sait pas le router (`motif` dit pourquoi)."""


@dataclass(frozen=True)
class ProchainDuel:
    """Le rendez-vous suivant d'un archer : où, quand dans l'arbre, et contre qui.

    `cible` / `position` sont `None` au-delà du tour 1 (placement intégral : E05US010) ;
    `adversaire` est `None` tant que le duel amont n'est pas tranché.

    ⚠️ `manque` = « je n'ai pas l'information » ; `alerte` = « je l'ai, mais quelque chose cloche ».
    Pas d'heure non plus : aucun horaire n'existe par tour de tableau (E12US002 fait foi).
    """

    numero: int
    tour: int
    libelle: str
    cible: int | None
    position: str | None
    adversaire: Duelliste | None
    sources_en_attente: tuple[int, ...]
    manque: str | None
    alerte: str | None = None


@dataclass(frozen=True)
class ProchaineManche:
    """Le rendez-vous suivant d'un finaliste de Big Shoot Off : quelle manche, et combien sortent.

    Pas d'adversaire ni de numéro de match : la manche est **collective**. `elimine` dit combien
    d'archers sortiront à l'issue du tour.

    ⚠️ `cible` et `position` sont **toujours** `None` : ce service ne lit pas le plan de cibles du
    créneau. Nommé par `manque` (`P-3`), tracé par `# DETTE-059`.
    """

    numero: int
    elimine: int
    cible: int | None = None
    position: str | None = None
    manque: str | None = None


@dataclass(frozen=True)
class DestinationRepechage:
    """La phase avale qui **reprend** un repêché (E07US008).

    Elle ne se lit pas dans le tableau : la réintégration est un **prélèvement** de la phase
    avale (`SourcePhase.par_issue_de_tour(…, PERDANTS)`), lu dans les sources de la séquence.

    `type` porte l'**énumération** et non une chaîne libre : c'est ce qui la publie fermée au
    schéma OpenAPI. Le front sait déjà nommer un type de phase (`LIBELLE_TYPE`).
    """

    phase_id: int
    ordre: int
    type: TypePhase


@dataclass(frozen=True)
class RencontreARouter:
    """Une rencontre **à tirer**, réduite à ce dont le panneau de routage a besoin (E05US026).

    Volontairement pauvre : ni pavé, ni tir, ni barème — le routage répond à « où je tire ensuite »,
    pas « comment je saisis ».

    `couloirs` porte les deux couloirs `(haut, bas)`, ou `None` si le plan n'est pas posé. C'est la
    différence de fond avec le Big Shoot Off (`DETTE-059`) : ici la cible **est** connue.
    """

    numero: int
    tour: int
    libelle: str
    haut: int
    bas: int
    couloirs: tuple[tuple[int, str], tuple[int, str]] | None = None

    def couloir_de(self, archer_id: int) -> tuple[int, str] | None:
        """Le couloir de **cet** archer — `None` si le plan n'est pas posé."""
        if self.couloirs is None:
            return None
        return self.couloirs[0] if archer_id == self.haut else self.couloirs[1]


@dataclass(frozen=True)
class RencontresARouter:
    """Ce qu'une phase à rencontres dit au routage : qui elle contient, quoi tirer, où en elle est.

    ⚠️ **Les trois champs sont nécessaires** (deux bloquants de revue, E05US026). Sans
    `participants`, un archer absent des `rencontres` passait pour fini — vrai en poule, faux en
    suisse, dont seule la ronde courante existe. Sans `termines`, le correctif inverse disait
    « attends » à qui pouvait partir. `epuisee` = plus aucune rencontre, pour personne.
    """

    rencontres: tuple[RencontreARouter, ...]
    participants: tuple[int, ...]
    epuisee: bool
    termines: frozenset[int] = frozenset()


class LecteurRencontresARouter(Protocol):
    """Port étroit : « quelles rencontres restent à tirer dans cette phase ? » (ADR-0083).

    Réalisé par `ServiceSuisse` et `ServicePoules`, **déclaré chez le consommateur** — ils sont
    deux, et le port doit vivre là où la question se pose (à la différence de
    `LecteurEtatBigShootOff`, qui n'a qu'un réalisateur).

    ⚠️ L'ordre compte : la **première** rencontre non tirée d'un archer est celle qui vient.
    """

    def rencontres_a_tirer(self, tournoi_id: TournoiId, phase_id: PhaseId) -> RencontresARouter:
        """Les rencontres encore à tirer, la population de la phase, et si elle est épuisée."""
        ...


@dataclass(frozen=True)
class RoutageArcher:
    """Ce que le panneau affiche pour **un** archer : son issue et ce qui la détaille.

    Trois champs disent un rang sans être redondants (E07US008) : `rang_final` est le rang **exact**
    décerné par un match terminal ; `rang_min`/`rang_max` la **fourchette acquise**, qui vaut aussi
    quand le tableau est tronqué au podium (le battu d'un quart est 5ᵉ-8ᵉ *ex æquo*). Quand le rang
    exact existe, la fourchette s'y referme. ⚠️ Un archer **en lice** n'a ni l'un ni l'autre.
    """

    archer_id: int
    nom: str
    prenom: str
    issue: IssueRoutage
    prochain: ProchainDuel | None = None
    prochaine_manche: ProchaineManche | None = None
    """Le rendez-vous d'un finaliste de Big Shoot Off (E05US028) — exclusif de `prochain`.

    Deux champs plutôt qu'un champ polymorphe : le client sait déjà lire `prochain` et n'a pas à
    deviner lequel des deux sens s'applique. Un archer n'a jamais les deux — son issue le dit."""

    rang_final: int | None = None
    rang_min: int | None = None
    rang_max: int | None = None
    tour_sortie: str | None = None
    destination: DestinationRepechage | None = None
    motif: str | None = None


@dataclass(frozen=True)
class _PlanLu:
    """Ce que le routage retient du plan de duels : les poses, et **qui n'est pas côte à côte**.

    `separes` vient de `PlanDeDuels.duels_separes`, dérivé par le domaine des paires du tableau
    **d'aujourd'hui** confrontées aux poses **persistées** : le recalculer à la main (« même index
    de cible ») en serait une 3ᵉ écriture, plus faible — elle raterait « même cible, positions non
    adjacentes ». `tour` = le tour de ces poses (`None` = plan indisponible), ADR-0106 §1.
    """

    tour: int | None
    poses: dict[int, tuple[int, str]]
    separes: frozenset[int]


@dataclass(frozen=True)
class Routage:
    """La réponse du panneau : la phase de tableau visée, et une ligne par archer.

    `phase_id` est `None` quand aucune phase d'élimination n'est configurée — l'écran le dit au lieu
    de rendre une liste vide qu'on prendrait pour une panne.

    ⚠️ Même type pour les deux lectures (`routage`, `affectations`) : les quatre canaux doivent dire
    **la même chose**, et deux formes de réponse finiraient par diverger.
    """

    phase_id: int | None
    archers: tuple[RoutageArcher, ...]


@dataclass(frozen=True)
class _Grille:
    """Ce qu'une lecture de tableau prépare **une fois** pour tous les archers à router.

    Tout ici coûte une reconstruction d'arbre ou une lecture de plan : le calculer par archer
    tiendrait encore à quatre (la tablette), pas à cent vingt (l'écran de salle).
    """

    tableau: Tableau
    lignes: dict[int, LigneClassement]
    plan: _PlanLu
    rangs: dict[Participant, int]
    identites: dict[int, tuple[str, str]]
    repechages: dict[int, DestinationRepechage]


class ServiceRoutage:
    """Cas d'usage du panneau de routage : router des archers vers leur suite (lecture pure)."""

    def __init__(
        self,
        saisie_duels: ServiceSaisieDuels,
        placement_duels: ServicePlacementDuels,
        archers: ArcherRepository,
        phases: PhaseRepository,
        departs: DepartRepository,
        big_shoot_off: LecteurEtatBigShootOff | None = None,
        suisse: LecteurRencontresARouter | None = None,
        poules: LecteurRencontresARouter | None = None,
        colline: LecteurRencontresARouter | None = None,
    ) -> None:
        # E05US028 : de quoi router un finaliste de Big Shoot Off. Au **constructeur** et non par un
        # `brancher_…` : il n'y a aucun cycle (`big_shoot_off` n'importe pas `routage`), donc rien
        # ne justifie de perdre le contrôle du compilateur. `None` reste licite — c'est le régime de
        # tout montage sans Big Shoot Off, et il se lit dans la signature.
        self._big_shoot_off = big_shoot_off
        # E05US026 : de quoi router une rencontre de **ronde** ou de **groupe**. Même régime que
        # ci-dessus — au constructeur, aucun cycle, `None` licite pour un montage sans ce format.
        #
        # ⚠️ **Ces deux-là donnent leur cible**, à la différence du Big Shoot Off : leur plan de
        # cibles est posé (`PAR_BLOC_DE_COULOIRS`), donc `ProchainDuel.cible` est renseigné et
        # `manque` reste `None`. C'est ce que `DETTE-059` attend encore pour la finale.
        self._suisse = suisse
        self._poules = poules
        # E05US027 : la colline, 3ᵉ format à rencontres. Même régime — au constructeur, aucun cycle,
        # `None` licite pour un montage sans ce format, et sa cible est connue (elle déclare elle
        # aussi `PAR_BLOC_DE_COULOIRS`).
        self._colline = colline
        # ⚠️ **La table remplace un ternaire**, et c'est le moment où il fallait la faire : à deux
        # formats, `a if type is X else b` restait lisible ; à trois, il devient un `elif` déguisé
        # dont l'oubli d'une branche est silencieux (le format tomberait sur le lecteur d'un autre,
        # donc sur `PhasePasUn…` attrapé plus bas — un « ce montage ne sait pas dérouler ce
        # format » parfaitement trompeur). Une table se lit d'un coup d'œil et se complète sans
        # relire la condition.
        self._lecteurs_par_rencontres: dict[TypePhase, LecteurRencontresARouter | None] = {
            TypePhase.SUISSE: suisse,
            TypePhase.POULES: poules,
            TypePhase.COLLINE: colline,
        }
        self._saisie_duels = saisie_duels
        self._placement_duels = placement_duels
        self._archers = archers
        self._phases = phases
        # `DepartRepository` depuis E01US025 : la maille d'entrée est le créneau (ADR-0075), et les
        # lectures internes (identités, plan, arbre) restent au tournoi — il faut donc remonter.
        self._departs = departs

    def _tournoi_du_depart(self, depart_id: DepartId) -> TournoiId:
        """Le tournoi de ce créneau. `DepartIntrouvable` (404) s'il n'existe pas.

        Garde d'existence **et** conversion de maille : les lectures internes (archers du tournoi,
        plan de duels, reconstruction) travaillent au tournoi, l'entrée publique au créneau.
        """
        depart = self._departs.par_id(depart_id)
        if depart is None:
            raise DepartIntrouvable(f"Aucun départ d'identifiant {depart_id}.")
        return depart.tournoi_id

    def routage(
        self,
        depart_id: DepartId,
        archer_ids: tuple[int, ...],
        phase_id: PhaseId | None = None,
    ) -> Routage:
        """Route chaque archer demandé, **dans l'ordre demandé** (positions A→D).

        La maille est le **créneau** (E01US025, ADR-0075) : c'est ce que la tablette connaît.
        `phase_id` non fourni ⇒ le tableau qui vient (`_phase_de_tableau`) ; fourni, il est
        **validé** (`PhaseIntrouvable` s'il est inconnu ou d'un autre créneau). ⚠️ Aucune erreur
        n'est levée pour un archer : une ligne motivée vaut mieux qu'un panneau qui échoue.
        """
        tournoi_id = self._tournoi_du_depart(depart_id)
        # ⚠️ **Superposition, pas substitution** (revue d'E05US028). En résolution implicite, une
        # phase à population restreinte route ceux qu'elle contient **sans déposséder les autres** :
        # pendant une finale à 8, les 112 archers du plateau doivent continuer à lire leur rang
        # final du tableau, pas « cet archer ne fait pas partie de ce Big Shoot Off ». Choisir *une*
        # phase pour tout le monde était le défaut ; on choisit donc par archer.
        restreinte = self._phase_restreinte_en_cours(depart_id) if phase_id is None else None
        if restreinte is not None and restreinte.id is not None:
            finalistes = self._archers_de_la_phase_restreinte(tournoi_id, restreinte)
            vises = tuple(a for a in archer_ids if a in finalistes)
            if vises:
                # Même garde que ci-dessous, et il faut les deux : cette voie **court-circuite** la
                # résolution principale, donc une finale en pause aurait continué à router ses huit
                # finalistes vers leur cible. Le repli des autres archers reste inchangé — ils
                # dépendent de *leur* phase, pas de celle-ci.
                routage_restreint = (
                    self._en_pause(tournoi_id, restreinte.id, vises)
                    if restreinte.statut is StatutPhase.EN_PAUSE
                    else self._routage_big_shoot_off(tournoi_id, restreinte, vises)
                )
                autres = tuple(a for a in archer_ids if a not in finalistes)
                if not autres:
                    return routage_restreint
                repli = self.routage(depart_id, autres, phase_id=None)
                par_archer = {ligne.archer_id: ligne for ligne in routage_restreint.archers}
                par_archer.update({ligne.archer_id: ligne for ligne in repli.archers})
                return Routage(
                    phase_id=restreinte.id,
                    archers=tuple(par_archer[a] for a in archer_ids if a in par_archer),
                )
        phase = self._phase_de_tableau(depart_id, phase_id)
        if phase is None or phase.id is None:
            return self._tous_indisponibles(tournoi_id, None, archer_ids, PHASE_ABSENTE)
        if phase.statut is StatutPhase.EN_PAUSE:
            return self._en_pause(tournoi_id, phase.id, archer_ids)
        if phase.type is TypePhase.BIG_SHOOT_OFF:
            # Bifurcation **avant** `_grille` : un Big Shoot Off n'a pas d'arbre à reconstruire, et
            # l'y envoyer léverait `PhasePasUnTableau` sur un panneau qui doit rester consultable.
            return self._routage_big_shoot_off(tournoi_id, phase, archer_ids)
        if phase.type in self._lecteurs_par_rencontres:
            # Même bifurcation, et même motif : aucun de ces trois formats n'a d'arbre (E05US026,
            # la colline s'y ajoutant en E05US027).
            return self._routage_par_rencontres(tournoi_id, phase, archer_ids)
        grille = self._grille(tournoi_id, phase, phase.id)
        if grille is None:
            # Moins de deux archers en lice : il n'y a pas d'arbre. Comme le feu vert, on rend un
            # panneau **motivé** plutôt qu'une erreur — l'écran est consultable avant la clôture.
            return self._tous_indisponibles(tournoi_id, phase.id, archer_ids, TABLEAU_ABSENT)
        return Routage(
            phase_id=phase.id,
            archers=tuple(self._router(archer_id, grille) for archer_id in archer_ids),
        )

    def affectations(self, depart_id: DepartId, phase_id: PhaseId | None = None) -> Routage:
        """**Tout** le tableau, dans l'ordre du pas de tir — le canal n°2 (E07US008).

        Différence de fond avec `routage` : l'appelant ne fournit **aucun** identifiant ; l'écran de
        salle ne sait rien du tableau, le reconstituer est le travail de ce service.

        ⚠️ Les archers **hors tableau** n'y figurent pas (contrairement à `routage`), et les
        participants **équipe** (E13US002) sont écartés — une équipe n'a pas de nom d'archer.
        """
        tournoi_id = self._tournoi_du_depart(depart_id)
        # ⚠️ **Pas de garde de pause ici, et c'est délibéré** (ADR-0091 §6). `affectations` est une
        # **lecture publique** (`VueEcran.AFFECTATIONS`, E07US008), pas un ordre de tir : le CA veut
        # qu'on voie où en est la salle *pendant* la pause.
        #
        # La mention publique de pause est livrée ailleurs — `EcranSalle.MentionDePause`, monté
        # **hors de la rotation** des vues, donc visible quelle que soit la vue affichée.
        phase = self._phase_de_tableau(depart_id, phase_id)
        if phase is None or phase.id is None:
            return Routage(phase_id=None, archers=())
        if phase.type is TypePhase.BIG_SHOOT_OFF:
            # `affectations` ne reçoit **aucun** identifiant : la population est celle de la phase.
            return self._routage_big_shoot_off(tournoi_id, phase, archer_ids=None)
        if phase.type in self._lecteurs_par_rencontres:
            # ⚠️ **Bifurcation jumelle de celle de `routage()`, et son absence était un bloquant.**
            # Faire entrer ces deux types dans `TYPES_ROUTES` les rend cibles implicites de
            # `_phase_de_tableau` : sans cette ligne, `affectations` tombait dans `_grille` et
            # remontait `PhasePasUnTableau` — un **409 sur une route publique non authentifiée**,
            # pour tout créneau portant une phase de poules, donc en régression sur E05US023.
            # Le canal n°2 (écran de salle, table d'organisation) s'éteignait exactement pendant la
            # phase qu'il sert. Reproduit par deux axes de revue.
            return self._routage_par_rencontres(tournoi_id, phase, archer_ids=None)
        grille = self._grille(tournoi_id, phase, phase.id)
        if grille is None:
            return Routage(phase_id=phase.id, archers=())
        lignes = [self._router(a, grille) for a in _archers_du_tableau(grille.tableau)]
        return Routage(
            phase_id=phase.id,
            archers=tuple(sorted(lignes, key=_ordre_du_pas_de_tir)),
        )

    def _phase_restreinte_en_cours(self, depart_id: DepartId) -> Phase | None:
        """La phase à **population restreinte** encore en cours de ce créneau, s'il y en a une.

        Elle ne peut pas être la cible implicite du panneau (elle ne concerne pas le plateau), mais
        elle doit rester atteignable **sans que la tablette la nomme** : c'est le régime par défaut
        de `useRoutage`, donc le seul que la plupart des postes emprunteront le jour J.
        """
        restreintes = [
            p
            for p in self._phases.par_depart(depart_id)
            if p.type in TYPES_ROUTES and p.type not in TYPES_ROUTES_IMPLICITEMENT
        ]
        en_cours = [p for p in restreintes if p.statut is not StatutPhase.TERMINEE]
        return en_cours[0] if en_cours else None

    def _archers_de_la_phase_restreinte(
        self, tournoi_id: TournoiId, phase: Phase
    ) -> frozenset[int]:
        """Qui cette phase restreinte contient — vide si on ne peut pas le savoir.

        Le vide est **volontairement indistinguable** d'une phase sans participants : dans les deux
        cas la superposition ne s'applique pas et le panneau retombe sur le tableau, ce qui est la
        bonne dégradation. Un Big Shoot Off pas encore réglé passe donc ici sans bruit.
        """
        if self._big_shoot_off is None or phase.id is None:
            return frozenset()
        try:
            etat = self._big_shoot_off.etat(tournoi_id, phase.id)
        except ApplicationError:
            return frozenset()
        return frozenset(tireur.archer_id for tireur in etat.tireurs)

    def _routage_par_rencontres(
        self, tournoi_id: TournoiId, phase: Phase, archer_ids: tuple[int, ...] | None
    ) -> Routage:
        """Route un tireur de **ronde** (suisse), de **groupe** (poules) ou de **manche** (colline).

        Les trois partagent ce chemin parce que leurs rencontres **sont des duels** (ADR-0083 §7) :
        `ProchainDuel` convient tel quel, et leur plan étant posé (`PAR_BLOC_DE_COULOIRS`), `cible`
        et `position` sont renseignés — contrairement au Big Shoot Off (`DETTE-059`).
        Quatre issues : `PROCHAIN_DUEL`, `TERMINE`, `EN_ATTENTE` (bye, ou rencontre validée pendant
        que la ronde s'achève — **régime ordinaire** de la colline), `INDISPONIBLE`.
        """

        # `# DETTE-031` — `rencontres_a_tirer` rejoue l'état complet de la phase à chaque poll.
        assert phase.id is not None, "L'appelant a déjà refusé une phase sans identité."
        lecteur = self._lecteurs_par_rencontres.get(phase.type)
        if lecteur is None:
            return self._tous_indisponibles(
                tournoi_id,
                phase.id,
                archer_ids or (),
                "Ce montage ne sait pas dérouler ce format.",
            )
        try:
            lecture = lecteur.rencontres_a_tirer(tournoi_id, phase.id)
        except (ApplicationError, DomainError) as exc:
            # ⚠️ **`DomainError` est ici pour une raison mesurée.** La borne du système suisse
            # (« à N participants, M rondes au plus ») est levée par `apparier_ronde` en
            # `ConfigurationSuisseInvalide`, une erreur de **domaine** : n'attraper qu'
            # `ApplicationError` laissait un 422 sortir sur cette route **publique**.
            # Journalisé — une phase muette le jour J doit rester débogable.
            _logger.info("Phase à rencontres %s écartée du routage : %s", phase.id, exc)
            return self._tous_indisponibles(
                tournoi_id,
                phase.id,
                archer_ids or (),
                "Les rencontres de cette phase ne sont pas connues pour l'instant.",
            )
        attendues: dict[int, RencontreARouter] = {}
        for rencontre in lecture.rencontres:
            for archer_id in (rencontre.haut, rencontre.bas):
                # La **première** rencontre non tirée dans l'ordre : c'est celle qui vient. Les
                # suivantes ne se promettent pas — l'appariement d'une ronde ultérieure n'existe
                # même pas tant que celle-ci n'est pas close.
                attendues.setdefault(archer_id, rencontre)
        # ⚠️ **La population vient de la phase, pas des rencontres restantes.** `tuple(attendues)`
        # omettait tout archer dont les rencontres sont déjà validées — donc l'écran de salle, qui
        # n'envoie aucun identifiant, perdait des lignes au fil de la ronde.
        demandes = archer_ids if archer_ids is not None else lecture.participants
        inscrits = set(lecture.participants)
        identites = self._identites(tournoi_id)
        lignes: list[RoutageArcher] = []
        for archer_id in demandes:
            nom, prenom = identites.get(archer_id, ("", ""))
            attendue = attendues.get(archer_id)
            if attendue is None:
                lignes.append(
                    self._sans_rencontre(archer_id, nom, prenom, archer_id in inscrits, lecture)
                )
                continue
            adverse = attendue.bas if attendue.haut == archer_id else attendue.haut
            couloir = attendue.couloir_de(archer_id)
            nom_adverse, prenom_adverse = identites.get(adverse, ("", ""))
            lignes.append(
                RoutageArcher(
                    archer_id=archer_id,
                    nom=nom,
                    prenom=prenom,
                    issue=IssueRoutage.PROCHAIN_DUEL,
                    prochain=ProchainDuel(
                        numero=attendue.numero,
                        tour=attendue.tour,
                        libelle=attendue.libelle,
                        cible=None if couloir is None else couloir[0],
                        position=None if couloir is None else couloir[1],
                        adversaire=Duelliste(
                            archer_id=adverse, nom=nom_adverse, prenom=prenom_adverse
                        ),
                        sources_en_attente=(),
                        manque=None
                        if couloir is not None
                        else "Le plan de cibles de cette phase n'est pas encore posé.",
                    ),
                )
            )
        if archer_ids is None:
            # ⚠️ **`affectations` promet « dans l'ordre du pas de tir »**, et la branche tableau le
            # tient (`_ordre_du_pas_de_tir`). Sans ce tri, l'écran de salle recevait l'ordre du
            # **classement de phase** — sans rapport avec la salle —, ce que la fiche de recette
            # démentait elle aussi. Le tri n'a de sens que sur ce canal : `routage` doit rendre les
            # lignes **dans l'ordre demandé** par la tablette.
            lignes.sort(key=_ordre_du_pas_de_tir)
        return Routage(phase_id=phase.id, archers=tuple(lignes))

    def _sans_rencontre(
        self, archer_id: int, nom: str, prenom: str, inscrit: bool, lecture: RencontresARouter
    ) -> RoutageArcher:
        """Ce qu'on dit à un archer sans rencontre en attente — **trois cas, pas un** (E05US026).

        1. il n'est pas dans cette phase → `INDISPONIBLE` ;
        2. la phase est épuisée, **ou** lui a fini (un format à groupes connus d'avance laisse un
           membre finir avant les autres) → `TERMINE` ;
        3. il y est, mais rien à tirer maintenant → `EN_ATTENTE` (E05US030). ⚠️ Jamais « c'est
           fini » : un archer à qui l'on dit terminé range son arc.
        """
        if not inscrit:
            return RoutageArcher(
                archer_id=archer_id,
                nom=nom,
                prenom=prenom,
                issue=IssueRoutage.INDISPONIBLE,
                motif="Cet archer ne fait pas partie de cette phase.",
            )
        if lecture.epuisee or archer_id in lecture.termines:
            return RoutageArcher(
                archer_id=archer_id,
                nom=nom,
                prenom=prenom,
                issue=IssueRoutage.TERMINE,
                motif="Plus aucune rencontre à tirer dans cette phase.",
            )
        return RoutageArcher(
            archer_id=archer_id,
            nom=nom,
            prenom=prenom,
            issue=IssueRoutage.EN_ATTENTE,
            motif="Rien à tirer pour l'instant : sa prochaine rencontre n'est pas encore appariée.",
        )

    def _routage_big_shoot_off(
        self, tournoi_id: TournoiId, phase: Phase, archer_ids: tuple[int, ...] | None
    ) -> Routage:
        """Route les finalistes d'un Big Shoot Off (E05US028) — le 5ᵉ canal du panneau.

        `archer_ids` à `None` (appel d'`affectations`) ⇒ **tous** les finalistes, dans l'ordre du
        classement ; fourni (`routage`), une ligne par archer demandé. Trois issues :
        `PROCHAINE_MANCHE`, `TERMINE` (sorti avec son rang, ou rescapé — rang 1 partagé),
        `INDISPONIBLE`. ⚠️ **Aucune cible n'est donnée** : ce service ne lit pas le plan du
        créneau — nommé par `manque`, tracé par `# DETTE-059`.
        """
        assert phase.id is not None, "L'appelant a déjà refusé une phase sans identité."
        if self._big_shoot_off is None:
            motif = "Ce montage ne sait pas dérouler un Big Shoot Off."
            return self._tous_indisponibles(tournoi_id, phase.id, archer_ids or (), motif)
        try:
            etat = self._big_shoot_off.etat(tournoi_id, phase.id)
        except ApplicationError:
            # ⚠️ **Le panneau dégrade, il ne tombe pas** (revue d'E05US028) — même point de
            # tolérance que `_grille`. Un Big Shoot Off composé mais **pas encore réglé** est un
            # état licite (brouillon d'ADR-0063) sur lequel `etat()` lève `PhasePasReglee` ; sans
            # cette garde, une route **publique non authentifiée** rendrait 4xx.
            #
            # Le motif est écrit ici et non repris de l'exception : `P-3` demande de nommer ce qui
            # n'est pas connu, et la règle 5 interdit qu'un message interne parte au client.
            return self._tous_indisponibles(
                tournoi_id,
                phase.id,
                archer_ids or (),
                "Ce Big Shoot Off n'est pas encore réglé : sa première manche n'est pas connue.",
            )
        par_archer = {tireur.archer_id: tireur for tireur in etat.tireurs}
        demandes = archer_ids if archer_ids is not None else tuple(par_archer)
        prochaine = next((manche for manche in etat.manches if not manche.jouee), None)
        lignes: list[RoutageArcher] = []
        for archer_id in demandes:
            tireur = par_archer.get(archer_id)
            if tireur is None:
                identite = self._identites(tournoi_id).get(archer_id, ("", ""))
                lignes.append(
                    RoutageArcher(
                        archer_id=archer_id,
                        nom=identite[0],
                        prenom=identite[1],
                        issue=IssueRoutage.INDISPONIBLE,
                        motif="Cet archer ne fait pas partie de ce Big Shoot Off.",
                    )
                )
                continue
            if not tireur.en_lice or etat.termine or prochaine is None:
                lignes.append(
                    RoutageArcher(
                        archer_id=archer_id,
                        nom=tireur.nom,
                        prenom=tireur.prenom,
                        issue=IssueRoutage.TERMINE,
                        # Un rescapé d'une phase achevée n'a pas de `rang` porté par le moteur : il
                        # partage le rang 1 avec les autres restants (règle du 31/07). On le pose
                        # ici plutôt que de laisser un `None` que l'écran lirait « pas de rang ».
                        rang_final=tireur.rang if tireur.rang is not None else 1,
                        rang_min=tireur.rang if tireur.rang is not None else 1,
                        rang_max=tireur.rang if tireur.rang is not None else 1,
                    )
                )
                continue
            lignes.append(
                RoutageArcher(
                    archer_id=archer_id,
                    nom=tireur.nom,
                    prenom=tireur.prenom,
                    issue=IssueRoutage.PROCHAINE_MANCHE,
                    prochaine_manche=ProchaineManche(
                        numero=prochaine.numero,
                        elimine=prochaine.elimine,
                        manque="votre cible n'est pas encore connue pour cette phase",
                    ),
                )
            )
        return Routage(phase_id=phase.id, archers=tuple(lignes))

    # --- Lecture de la grille --------------------------------------------------------------------

    # DETTE-031 : cette lecture appelle `ServiceSaisieDuels.reconstruire` — tout le classement du
    # tournoi, l'arbre rebâti, les duels rejoués — sans cache et sans plafond, sur deux routes
    # **publiques non authentifiées**. E07US008 y ajoute un second endpoint et deux surfaces de
    # polling ; la ligne du registre a été élargie en conséquence.
    def _grille(self, tournoi_id: TournoiId, phase: Phase, phase_id: PhaseId) -> _Grille | None:
        """Tout ce qu'il faut pour router, lu **une fois** — `None` si le tableau n'existe pas.

        `classement()` plutôt que `podium()` (E07US008) : le podium n'en est que la restriction aux
        rangs ≤ 4, et sous placement intégral (E05US010) tous les rangs sont terminaux. ⚠️ Mais
        `jusqu_au` est un **paramètre** : au défaut (4, la production) la sortie est celle d'hier ;
        sous `ProfondeurPodium(jusqu_au=8)` le service gagne les rangs 5-8 que `podium()` jetait.
        """
        try:
            tableau, lignes = self._saisie_duels.reconstruire(tournoi_id, phase_id)
        # PrelevementEnAttente rejoint la garde (E05US024, ADR-0081) : « la source n'a pas encore
        # départagé les places prélevées » est le **même** cas métier qu'« effectif insuffisant »
        # — il est trop tôt. Sans cet élargissement, la nouvelle exception traversait ce point de
        # tolérance et faisait échouer en bloc ce que le site s'engage à dégrader (relevé par
        # trois axes de revue : régression introduite par le refus typé lui-même).
        except (EffectifTableauInvalide, PrelevementEnAttente):
            return None
        return _Grille(
            tableau=tableau,
            lignes=lignes,
            plan=self._plan_lu(tournoi_id, phase_id),
            rangs={place.participant: place.rang for place in tableau.classement()},
            identites=self._identites(tournoi_id),
            repechages=self._repechages(phase),
        )

    def _repechages(self, phase: Phase) -> dict[int, DestinationRepechage]:
        """`tour perdu → phase qui reprend ses battus`, lu dans les **sources de la séquence**.

        `VersRepechage` « ne construit rien » : la réintégration est un **prélèvement** de la phase
        avale (`SourcePhase.par_issue_de_tour(ordre, tour, PERDANTS)`), donc absente du tableau.
        ⚠️ Lecture `par_depart`, et le tri en dépend (ADR-0075) : sous `par_tournoi`, qui trie par
        `(départ, ordre)`, un repêché de l'après-midi partait vers un tableau du matin.
        """
        destinations: dict[int, DestinationRepechage] = {}
        for autre in self._phases.par_depart(phase.depart_id):
            if autre.id is None or autre.ordre <= phase.ordre:
                continue
            for source in autre.sources:
                if (
                    source.nature is NatureSource.ISSUE_DE_TOUR
                    and source.ordre_source == phase.ordre
                    and source.issue is IssueTour.PERDANTS
                    and source.tour is not None
                ):
                    destinations.setdefault(
                        source.tour,
                        DestinationRepechage(autre.id, autre.ordre, autre.type),
                    )
        return destinations

    # --- Résolution de la phase ----------------------------------------------------------------

    def _phase_de_tableau(self, depart_id: DepartId, phase_id: PhaseId | None) -> Phase | None:
        """La phase visée : celle **imposée** par le client, sinon celle du créneau qui **vient**.

        `phase_id` imposé est **validé** (`PhaseIntrouvable` 404 s'il est inconnu ou d'un autre
        créneau) ; sinon, résolution implicite best-effort sur la 1ʳᵉ ED non terminée du créneau.

        ⚠️ Lecture **par créneau** (ADR-0075) : sous `par_tournoi`, les archers de l'après-midi
        partaient vers le tableau du matin — sur les quatre canaux de routage à la fois.
        """
        if phase_id is not None:
            phase = phase_du_depart(self._phases, depart_id, phase_id)
            if phase is None:
                raise PhaseIntrouvable(f"Aucune phase {phase_id} pour le départ {depart_id}.")
            return phase
        # Filtre **dérivé** du contrat de phase (ADR-0083, capacité `route_l_archer`) : élimination
        # directe, Big Shoot Off, poules et système suisse.
        #
        # ⚠️ Toute bascule de `route_l_archer` doit passer par ici **et** par `affectations()` —
        # les deux canaux lisent ce filtre, et n'en câbler qu'un rendait 409 sur une route publique.
        # ⚠️ `TYPES_ROUTES_IMPLICITEMENT` et non `TYPES_ROUTES` : on est dans la résolution
        # implicite, et une phase à population restreinte y capterait des archers qu'elle ne
        # contient pas — `_phase_restreinte_en_cours` les rattrape archer par archer.
        tableaux = [
            p for p in self._phases.par_depart(depart_id) if p.type in TYPES_ROUTES_IMPLICITEMENT
        ]
        en_cours = [p for p in tableaux if p.statut is not StatutPhase.TERMINEE]
        if en_cours:
            return en_cours[0]
        # Tous terminés : on vise le **dernier** de ce créneau, pas le premier. C'est celui où se
        # trouve le dénouement — router vers le premier rendrait « non retenu pour le tableau » à
        # tout archer qui n'a joué que le second, alors qu'il a un rang à afficher.
        return tableaux[-1] if tableaux else None

    def _tous_indisponibles(
        self,
        tournoi_id: TournoiId,
        phase_id: int | None,
        archer_ids: tuple[int, ...],
        motif: str,
        issue: IssueRoutage = IssueRoutage.INDISPONIBLE,
    ) -> Routage:
        """Le panneau dégradé — mais **nominatif**.

        C'est l'état le plus fréquent de la journée (la phase finale n'est configurée qu'une fois la
        qualification close) : quatre lignes anonymes seraient illisibles. Les noms viennent des
        **archers du tournoi**, lisibles indépendamment de toute phase. ⚠️ `issue` est un paramètre
        (E05US033), défaut `INDISPONIBLE` — la pause veut `EN_ATTENTE` : « attendez » ≠ « partez ».
        """
        identites = self._identites(tournoi_id)
        return Routage(
            phase_id=phase_id,
            archers=tuple(
                RoutageArcher(
                    archer_id=archer_id,
                    nom=identites.get(archer_id, ("", ""))[0],
                    prenom=identites.get(archer_id, ("", ""))[1],
                    issue=issue,
                    motif=motif,
                )
                for archer_id in archer_ids
            ),
        )

    def _en_pause(
        self, tournoi_id: TournoiId, phase_id: int, archer_ids: tuple[int, ...]
    ) -> Routage:
        """La phase est en pause : l'archer doit **savoir pourquoi** (E05US033).

        ⚠️ Avant cette US la pause était **cosmétique** ici : le filtre de sélection est
        `statut is not TERMINEE`, donc une phase en pause routait normalement (`DETTE-073`).
        La garde est posée **ici** et non dans `_phase_de_tableau` — écarter les phases en pause de
        la *sélection* ferait tomber le routage sur une autre phase, donc enverrait l'archer tirer
        ailleurs au lieu de lui dire d'attendre. L'issue `EN_ATTENTE` (E05US030) est réutilisée.
        """
        return self._tous_indisponibles(
            tournoi_id,
            phase_id,
            archer_ids,
            "Tir suspendu : l'organisateur a mis cette phase en pause. Restez à disposition.",
            issue=IssueRoutage.EN_ATTENTE,
        )

    def _identites(self, tournoi_id: TournoiId) -> dict[int, tuple[str, str]]:
        """`archer_id → (nom, prénom)`, lus **directement** sur les archers du tournoi.

        On veut un nom, pas un rang : passer par le classement coûterait toutes les séries du
        tournoi plus le calcul complet, sur la branche que le panneau emprunte le plus souvent (la
        phase finale n'est configurée qu'une fois la qualification close) et depuis ~30 tablettes.
        `ArcherRepository.par_tournoi` suffit, et il couvre **tout le monde** — y compris un archer
        sans une flèche tirée, qu'un classement n'aurait pas forcément classé.
        """
        return {
            archer.id: (archer.nom, archer.prenom)
            for archer in self._archers.par_tournoi(tournoi_id)
            if archer.id is not None
        }

    # --- Routage d'un archer -------------------------------------------------------------------

    def _router(self, archer_id: int, grille: _Grille) -> RoutageArcher:
        """L'issue d'un archer : prochain duel, repêchage, sortie, ou l'aveu qu'on ne sait pas.

        **Son prochain duel est le match non tranché qu'il occupe** : le tableau reconstruit a déjà
        propagé les vainqueurs et résolu les byes, et l'arbre interdit d'en occuper deux à la fois.
        Plus de match devant lui ⇒ il a perdu son dernier — deux sorties (E07US008) : `TERMINE`
        (classé ici, avec son rang) et `REPECHE` (sans rang, il peut remonter).
        """
        tableau = grille.tableau
        moi = Participant.individuel(archer_id)
        # Les noms viennent des **archers**, pas du classement : un abandon y est relégué et une
        # disqualification en est **sortie** (ADR-0050), or ce sont précisément les archers qu'on
        # route encore (ils restent dans la grille). Les lire du classement rendait leur ligne
        # **anonyme** — la moitié du trou que le panneau dégradé avait déjà fermée de son côté.
        nom, prenom = grille.identites.get(archer_id, ("", ""))
        siens = [m for m in tableau.matchs if moi in (m.haut, m.bas)]
        if not siens:
            return RoutageArcher(
                archer_id=archer_id,
                nom=nom,
                prenom=prenom,
                issue=IssueRoutage.INDISPONIBLE,
                motif=HORS_TABLEAU,
            )
        prochain = next((m for m in siens if m.vainqueur is None), None)
        if prochain is not None:
            return RoutageArcher(
                archer_id=archer_id,
                nom=nom,
                prenom=prenom,
                issue=IssueRoutage.PROCHAIN_DUEL,
                prochain=self._prochain_duel(prochain, grille, moi),
            )
        dernier = max(siens, key=lambda m: m.tour)
        tour_sortie = libelle_tour(
            dernier.tour, tableau.nb_tours, dernier.place_en_jeu, dernier.plage
        )
        a_perdu = dernier.vainqueur != moi
        if a_perdu and _est_repeche(tableau, dernier):
            destination = grille.repechages.get(dernier.tour)
            return RoutageArcher(
                archer_id=archer_id,
                nom=nom,
                prenom=prenom,
                issue=IssueRoutage.REPECHE,
                tour_sortie=tour_sortie,
                destination=destination,
                motif=REPECHAGE_SANS_DESTINATION if destination is None else None,
            )
        rang = grille.rangs.get(moi)
        fourchette = fourchette_de_rangs(rang, dernier if a_perdu else None, tableau.effectif)
        return RoutageArcher(
            archer_id=archer_id,
            nom=nom,
            prenom=prenom,
            issue=IssueRoutage.TERMINE,
            rang_final=rang,
            rang_min=fourchette[0] if fourchette is not None else None,
            rang_max=fourchette[1] if fourchette is not None else None,
            tour_sortie=tour_sortie,
            # ⚠️ **`# DETTE-033` — un battu repris par la *séquence* n'est pas annoncé ici.**
            #
            # Les deux moitiés du repêchage se lisent à deux sources : le **routing**
            # (`_est_repeche`, match par match — la branche ci-dessus) et les **sources de la
            # séquence** (`grille.repechages`, indexées par tour). Annoncer la seconde ici est
            # impossible en l'état : `dernier` est le dernier match *joué* (sous cascade, le battu
            # des demies a `tour == 3`), et un tour couvre plusieurs plages dès qu'il y a des
            # sous-tableaux. La sémantique de `SourcePhase.par_issue_de_tour` n'est pas tranchée.
            destination=None,
            # `RANG_A_VENIR` ne subsiste que là où **rien** n'est acquis : ni rang exact, ni
            # fourchette (plage absente d'un `Match` bâti à la main). Avant E07US008 il couvrait
            # tout le hors-podium, ce qui n'apprenait rien à quelqu'un qui venait de perdre.
            motif=RANG_A_VENIR if fourchette is None else None,
        )

    def _prochain_duel(self, match: Match, grille: _Grille, moi: Participant) -> ProchainDuel:
        """Le rendez-vous : sa cible (si elle est **valide**), son libellé de tour, l'adversaire."""
        adversaire_participant = match.bas if match.haut == moi else match.haut
        adversaire = self._saisie_duels.duelliste(adversaire_participant, grille.lignes)
        pose, manque, alerte = self._pose_a_annoncer(
            match, moi, adversaire_participant, grille.plan
        )
        return ProchainDuel(
            numero=match.numero,
            tour=match.tour,
            libelle=libelle_tour(
                match.tour, grille.tableau.nb_tours, match.place_en_jeu, match.plage
            ),
            cible=pose[0] if pose is not None else None,
            position=pose[1] if pose is not None else None,
            adversaire=adversaire,
            sources_en_attente=self._sources_en_attente(match),
            manque=manque,
            alerte=alerte,
        )

    # DETTE-019 : jumelle de `ServicePilotageTour._duel_a_venir`.
    @staticmethod
    def _pose_a_annoncer(
        match: Match, moi: Participant, adversaire: Participant | None, plan: _PlanLu
    ) -> tuple[tuple[int, str] | None, str | None, str | None]:
        """La pose à annoncer, le **manque** s'il n'y en a pas, l'**alerte** si elle est douteuse.

        1. **tour non encore posé** → aucune cible (ADR-0106 §2 : le plan pose un tour à la fois) ;
        2. **pose absente au tour posé** → aucune cible, libellé **neutre** ;
        3. **duel non côte à côte** → cible annoncée **et** alerte qualifiée : même butte (se
           décaler d'une place) ou buttes différentes (on nomme alors l'autre butte).
        """
        if match.tour != plan.tour:
            return None, CIBLE_A_VENIR, None
        pose = plan.poses.get(moi.ref_id)
        if pose is None:
            return None, CIBLE_NON_ATTRIBUEE, None
        if moi.ref_id not in plan.separes:
            return pose, None, None
        pose_adverse = plan.poses.get(adversaire.ref_id) if adversaire is not None else None
        if pose_adverse is None:
            return pose, None, PLACEMENT_ADVERSAIRE_NON_PLACE
        if pose_adverse[0] == pose[0]:
            return pose, None, PLACEMENT_VOISIN_ELOIGNE.format(position=pose_adverse[1])
        return pose, None, PLACEMENT_AUTRE_CIBLE.format(cible=pose_adverse[0])

    # --- Lectures best-effort ------------------------------------------------------------------

    # DETTE-019 : jumelle de `ServicePilotageTour._cibles_par_archer`.
    def _plan_lu(self, tournoi_id: TournoiId, phase_id: PhaseId) -> _PlanLu:
        """Le plan de duels **persisté**, réduit à ce que le routage en fait.

        Jumeau de `ServicePilotageTour._cibles_par_archer` (2ᵉ occurrence) à deux choses près : on
        garde la **position**, et on **conserve** `duels_separes` — le signal qui dit que la pose ne
        correspond plus au duel du jour, et que le pilotage, lui, jette.

        Sans gabarit appliqué, plan **vide** — d'où « cible non attribuée », jamais un échec.
        """
        try:
            plan = self._placement_duels.plan_de_duels(tournoi_id, phase_id)
        except GabaritDuTournoiAbsent:
            return _PlanLu(tour=None, poses={}, separes=frozenset())
        return _PlanLu(
            tour=plan.tour,
            poses={
                pose.archer_id: (cible.index, pose.position)
                for cible in plan.cibles
                for pose in cible.placements
            },
            separes=frozenset(archer for paire in plan.duels_separes for archer in paire),
        )

    # DETTE-019 : corps identique à `ServicePilotageTour._sources_en_attente`.
    @staticmethod
    def _sources_en_attente(match: Match) -> tuple[int, ...]:
        """Les duels amont dont ce match attend encore l'issue — pour **nommer** qui l'on attend.

        Jumeau de `ServicePilotageTour._sources_en_attente` (2ᵉ occurrence). Un camp `VainqueurDe`
        / `PerdantDe` **sans occupant** signale un duel amont non tranché : « en attente du duel
        n°2 » plutôt qu'un adversaire vide.
        """
        pending: list[int] = []
        for source, occupant in (
            (match.source_haut, match.haut),
            (match.source_bas, match.bas),
        ):
            if occupant is None and isinstance(source, VainqueurDe | PerdantDe):
                pending.append(source.numero)
        return tuple(pending)


# --- lectures dérivées du tableau ----------------------------------------------------------------


def _est_repeche(tableau: Tableau, match: Match) -> bool:
    """Le perdant de ce match **ressort** du tableau au lieu d'y être classé (E07US008).

    On **redemande au routing** plutôt que de deviner à la structure de l'arbre. C'est la même
    question que `construire_tableau` a posée en engendrant l'arbre, à la même politique, avec le
    même contexte : la réponse ne peut donc pas diverger. Déduire « pas de sous-tableau aval ⇒
    repêché » serait faux — un match dont la plage aval est **élaguée par la profondeur**
    (`ProfondeurPodium`) n'a pas non plus d'aval, et son battu est bel et bien éliminé.
    """
    if match.plage is None or match.plage.largeur < 4:
        # ⚠️ **Le routing ne s'interroge pas sur une plage indivisible** : `construire_tableau` sort
        # *avant* de l'appeler dans ce cas (*Règle T*, ADR-0065 §2), sans quoi `PlacementEnCascade`
        # y appelle `moitie_basse()` et lève `PlageInvalide`. On redonde le contrat ici parce qu'on
        # est le deuxième appelant — et le premier à l'avoir enfreint.
        #
        # `largeur < 4` et non `est_terminale` : c'est la borne exacte que `Plage._demi_largeur`
        # refuse. Métier, un match terminal **décerne** les deux rangs, son perdant est classé ici.
        return False
    destination = tableau.routing.route(ContexteRoutage(tour=match.tour, plage=match.plage))
    return isinstance(destination, VersRepechage)


# `_fourchette_de_rangs` a **remonté dans le domaine** en E06US004 (`domain.tableau`) : le
# palmarès en est le second consommateur, et deux services s'important une fonction privée
# l'un de l'autre auraient inversé le sens des dépendances (règle 2) pour une règle métier.


def _archers_du_tableau(tableau: Tableau) -> tuple[int, ...]:
    """Les archers qui occupent au moins un camp du tableau, **sans doublon**, dans l'ordre des
    matchs — la liste que l'écran de salle ne peut pas fournir lui-même.

    Un `dict` plutôt qu'un `set` : l'ordre d'insertion est stable, donc deux lectures successives
    d'un même tableau rendent la même liste. Le tri final du pas de tir s'appuie dessus pour être
    déterministe jusque dans les ex æquo.
    """
    vus: dict[int, None] = {}
    for match in tableau.matchs:
        for camp in (match.haut, match.bas):
            if camp is not None and camp.genre is GenreParticipant.INDIVIDUEL:
                vus.setdefault(camp.ref_id, None)
    return tuple(vus)


def _ordre_du_pas_de_tir(ligne: RoutageArcher) -> tuple[int, int, str, str, str]:
    """L'ordre de lecture d'un panneau d'affectations : **la salle telle qu'elle est disposée**.

    Cible croissante, puis position A→D. L'écran de salle n'a aucune interaction (CA E07US004) :
    l'ordre du serveur est le seul qu'il aura, et l'ordre naturel de l'arbre ne veut rien dire pour
    qui cherche sa butte de loin. ⚠️ Ceux qui n'ont plus de pose passent **après**, jamais
    intercalés — une ligne sans cible au milieu du pas de tir fait sauter une butte à l'œil.
    """
    prochain = ligne.prochain
    if prochain is not None and prochain.cible is not None:
        return (0, prochain.cible, prochain.position or "", ligne.nom, ligne.prenom)
    return (1, 0, "", ligne.nom, ligne.prenom)
