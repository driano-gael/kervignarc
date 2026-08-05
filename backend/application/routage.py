"""Service applicatif Routage — « où est-ce que je tire ensuite ? » (E04US018).

C'est le **canal n°1 des quatre canaux de routage** (`D-09`) : celui qui suit l'archer encore
présent sur la cible. Il valide, range ses flèches et part — l'information doit partir avec lui. Les
trois autres canaux (public E07US008, écran de salle E07US004, et la tablette elle-même en mode
public) liront la **même** projection.

**Rien n'est calculé au moment de la bascule** (`D-08`) : c'est tout l'intérêt du modèle. Les cibles
sont attribuées aux **matchs** (positions de tableau), pas aux archers — « le match n°3 des 1/8ᵉ se
tire sur la cible 4, quel que soit son vainqueur » — donc l'affectation existe **avant** le duel
(E03US009). Ce service ne fait donc qu'**agréger en lecture** ce que le tableau reconstruit
(`ServiceSaisieDuels`) et le plan de duels persisté (`ServicePlacementDuels`) tiennent déjà : aucune
écriture, aucun placement, aucune trace d'audit — un panneau de routage ne *décide* de rien.

**Ce qui n'est pas encore connu est nommé, jamais masqué** (`P-3`, arbitré au cadrage du
30/07/2026) — même parti pris que le `blocage` du feu vert d'E12US002 : la cible d'un tour ≥ 2
(E05US010 non livrée), l'adversaire pas encore sorti de son duel amont, le rang intermédiaire
(E06US004 non livrée). Un blanc se lit comme une panne ; une phrase se lit comme une attente.

*Jumeau assumé de `pilotage_tour.py`* (**`# DETTE-019`**) : la lecture « archer → pose du plan » et
la règle « pas de cible au-delà du tour 1 » y existent déjà, sous un autre angle (le duel, pas
l'archer). **2ᵉ** occurrence : on duplique et on attend la 3ᵉ pour extraire (règle « remède
structurel sur preuve »). La garde tour-1 est celle qu'**E05US010 devra lever aux deux endroits** —
c'est pour ça qu'elle est tracée au registre plutôt que seulement commentée.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from application.erreurs import GabaritDuTournoiAbsent, PhaseIntrouvable
from application.placement_duels import ServicePlacementDuels
from application.saisie_duels import Duelliste, ServiceSaisieDuels
from domain.classement import LigneClassement
from domain.erreurs import EffectifTableauInvalide
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
from domain.ports import ArcherRepository, PhaseRepository
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

Le plan a été matérialisé sur un **autre appariement** (le classement a bougé — une correction de
score suffit, E04US013 — et l'arbre est recalculé à chaque lecture, ADR-0023, alors que les poses
sont persistées), ou les cibles sont trop étroites pour rapprocher les duellistes. On annonce quand
même la pose — c'est la ligne de cet archer sur le plan, et la taire ne dirait rien de plus
utile — mais on **nomme la butte de l'autre** : c'est ce qui permet de comprendre en deux
secondes qu'il faut aller voir l'organisateur plutôt que de s'installer.
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

    INDISPONIBLE = "indisponible"
    """On ne sait pas le router (`motif` dit pourquoi)."""


@dataclass(frozen=True)
class ProchainDuel:
    """Le rendez-vous suivant d'un archer : où, quand dans l'arbre, et contre qui.

    `cible` / `position` sont `None` au-delà du tour 1 (le placement intégral est E05US010) ;
    `adversaire` est `None` tant que le duel amont n'est pas tranché, et `sources_en_attente` en
    **nomme** alors le numéro. `manque` résume en clair ce qui reste inconnu (`None` si tout y est).

    `manque` et `alerte` ne disent pas la même chose et ne se remplacent pas : `manque` = « je n'ai
    pas l'information » (pas de cible à donner) ; `alerte` = « je l'ai, mais quelque chose cloche »
    (la cible est là, le duel n'est pas côte à côte). Confondre les deux, c'est soit taire une
    information juste, soit rassurer à tort.

    Il n'y a **pas d'heure** : le CA en demandait une, mais aucun horaire n'existe par tour de
    tableau (les horaires vivent sur les `Depart`, côté qualification). On ne fabrique pas une heure
    qu'on ne sait pas tenir — c'est le lancement du tour (E12US002) qui fait foi.
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
class DestinationRepechage:
    """La phase avale qui **reprend** un repêché (E07US008).

    Elle ne se lit pas dans le tableau : la réintégration n'est pas un lien d'arbre mais un
    **prélèvement** de la phase suivante (`SourcePhase.par_issue_de_tour(…, PERDANTS)`, cf.
    `VersRepechage`). Le routage la retrouve donc dans les **sources de la séquence** — c'est la
    seule lecture qui la connaisse.

    On rend `ordre` et `type` plutôt qu'un libellé tout fait : le front sait déjà nommer un type de
    phase (`LIBELLE_TYPE`), et une phase n'a pas de nom propre dans le modèle.

    `type` porte l'**énumération**, pas une chaîne libre (correctif de revue, axe A) : c'est ce que
    font tous les autres DTO de phase du projet, et c'est ce qui permet de la publier fermée au
    schéma OpenAPI — donc de faire disparaître le `as TypePhase` que le front devait écrire.
    """

    phase_id: int
    ordre: int
    type: TypePhase


@dataclass(frozen=True)
class RoutageArcher:
    """Ce que le panneau affiche pour **un** archer : son issue et ce qui la détaille.

    Trois champs disent un rang, et ils ne sont pas redondants (E07US008) :

    - `rang_final` — le rang **exact**, décerné par un match terminal (`Tableau.classement`) ;
    - `rang_min`/`rang_max` — la **fourchette acquise**, qui vaut aussi quand le tableau est tronqué
      au podium : le battu d'un quart est 5ᵉ-8ᵉ *ex æquo*, et aucun match n'a été joué pour le
      départager. Quand le rang exact existe, la fourchette s'y referme (`min == max == rang_final`)
      — c'est la même notion à deux profondeurs, pas deux calculs concurrents.

    Un archer **encore en lice** n'a ni l'un ni l'autre : un rang annoncé avant la fin serait un
    faux départ.
    """

    archer_id: int
    nom: str
    prenom: str
    issue: IssueRoutage
    prochain: ProchainDuel | None = None
    rang_final: int | None = None
    rang_min: int | None = None
    rang_max: int | None = None
    tour_sortie: str | None = None
    destination: DestinationRepechage | None = None
    motif: str | None = None


@dataclass(frozen=True)
class _PlanLu:
    """Ce que le routage retient du plan de duels : les poses, et **qui n'est pas côte à côte**.

    `separes` vient de `PlanDeDuels.duels_separes`, dérivé par le domaine
    (`duels_non_cote_a_cote`) des paires du tableau **d'aujourd'hui** confrontées aux poses
    **persistées**. C'est exactement l'oracle qu'il faut ici, et il existait déjà : le recalculer à
    la main (« même index de cible ») en serait une 3ᵉ écriture, plus faible — elle raterait le cas
    « même cible, positions non adjacentes ».
    """

    poses: dict[int, tuple[int, str]]
    separes: frozenset[int]


@dataclass(frozen=True)
class Routage:
    """La réponse du panneau : la phase de tableau visée, et une ligne par archer.

    `phase_id` est `None` quand aucune phase d'élimination n'est configurée — l'écran le dit au lieu
    de rendre une liste vide qu'on prendrait pour une panne. C'est la seule chose qui distingue
    « il n'y a pas encore de tableau » de « le tableau ne route personne ».

    Même type pour les deux lectures (`routage` par identifiants, `affectations` pour tout le
    tableau) : les quatre canaux de routage doivent dire **la même chose**, et deux formes de
    réponse finiraient par diverger sur un détail — la butte annoncée, par exemple.
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
    ) -> None:
        self._saisie_duels = saisie_duels
        self._placement_duels = placement_duels
        self._archers = archers
        self._phases = phases

    def routage(
        self,
        tournoi_id: TournoiId,
        archer_ids: tuple[int, ...],
        phase_id: PhaseId | None = None,
    ) -> Routage:
        """Route chaque archer demandé, **dans l'ordre demandé** (l'ordre des positions A→D).

        `phase_id` non fourni ⇒ on vise le **tableau qui vient** (cf. `_phase_de_tableau`) : la
        tablette de qualification ne connaît que sa cible et son départ, pas l'arbre. Fourni (écran
        de duels), il est **validé** — `PhaseIntrouvable` (404) s'il est inconnu ou relève d'un
        autre
        tournoi ; `PhasePasUnTableau` remonte ensuite du service de saisie, comme partout ailleurs.

        Aucune erreur n'est levée pour un archer : une ligne **indisponible** motivée vaut mieux
        qu'un panneau qui échoue en bloc parce qu'un seul des quatre n'est pas dans le tableau.
        """
        phase = self._phase_de_tableau(tournoi_id, phase_id)
        if phase is None or phase.id is None:
            return self._tous_indisponibles(tournoi_id, None, archer_ids, PHASE_ABSENTE)
        grille = self._grille(tournoi_id, phase, phase.id)
        if grille is None:
            # Moins de deux archers en lice : il n'y a pas d'arbre. Comme le feu vert, on rend un
            # panneau **motivé** plutôt qu'une erreur — l'écran est consultable avant la clôture.
            return self._tous_indisponibles(tournoi_id, phase.id, archer_ids, TABLEAU_ABSENT)
        return Routage(
            phase_id=phase.id,
            archers=tuple(self._router(archer_id, grille) for archer_id in archer_ids),
        )

    def affectations(self, tournoi_id: TournoiId, phase_id: PhaseId | None = None) -> Routage:
        """**Tout** le tableau, dans l'ordre du pas de tir — le canal n°2 (E07US008).

        Différence de fond avec `routage`, et non de commodité : l'appelant ne fournit **aucun**
        identifiant. La tablette sait qui sont ses quatre archers ; l'écran de salle et la table de
        l'organisation ne savent rien du tout. Leur faire reconstituer la liste d'abord, ce serait
        leur faire connaître le tableau — c'est le travail de ce service.

        Les archers **hors tableau** n'y figurent pas, et c'est le contraire de `routage` : là on a
        *demandé* cet archer, donc on lui doit une ligne motivée ; ici personne ne l'a nommé, et
        l'afficher ferait chercher une butte à quelqu'un qui n'en a pas.

        Les participants **équipe** (E13US002) sont écartés : le routage résout un `Participant` en
        archer (`_identites`), et une équipe n'a pas de nom d'archer. Les afficher rendrait des
        lignes anonymes — la résolution `Participant → équipe` viendra avec les équipes elles-mêmes.
        """
        phase = self._phase_de_tableau(tournoi_id, phase_id)
        if phase is None or phase.id is None:
            return Routage(phase_id=None, archers=())
        grille = self._grille(tournoi_id, phase, phase.id)
        if grille is None:
            return Routage(phase_id=phase.id, archers=())
        lignes = [self._router(a, grille) for a in _archers_du_tableau(grille.tableau)]
        return Routage(
            phase_id=phase.id,
            archers=tuple(sorted(lignes, key=_ordre_du_pas_de_tir)),
        )

    # --- Lecture de la grille --------------------------------------------------------------------

    # DETTE-031 : cette lecture appelle `ServiceSaisieDuels.reconstruire` — tout le classement du
    # tournoi, l'arbre rebâti, les duels rejoués — sans cache et sans plafond, sur deux routes
    # **publiques non authentifiées**. E07US008 y ajoute un second endpoint et deux surfaces de
    # polling ; la ligne du registre a été élargie en conséquence.
    def _grille(self, tournoi_id: TournoiId, phase: Phase, phase_id: PhaseId) -> _Grille | None:
        """Tout ce qu'il faut pour router, lu **une fois** — `None` si le tableau n'existe pas.

        `classement()` plutôt que `podium()` (E07US008) : le podium n'est que sa restriction aux
        rangs ≤ 4. Sous placement intégral (E05US010), tous les rangs sont décernés par des matchs
        terminaux, et les lire donne le rang **exact** de chacun sans autre calcul.

        Sous `ProfondeurPodium()` **par défaut** (`jusqu_au=4`, le câblage de production), la sortie
        est identique à celle d'hier : seules `[1..2]` et `[3..4]` sont terminales, donc
        `classement()` ne rend jamais de rang > 4. ⚠️ Mais `jusqu_au` est un **paramètre** — sous
        `ProfondeurPodium(jusqu_au=8)`, le service gagne les rangs 5-8 exacts que `podium()`
        jetait. C'est donc bien un changement de comportement dans cette configuration, et il est
        **voulu** ; la formulation « ce n'est pas un changement de comportement » d'un premier jet
        était fausse et la revue l'a rattrapée.
        """
        try:
            tableau, lignes = self._saisie_duels.reconstruire(tournoi_id, phase_id)
        except EffectifTableauInvalide:
            return None
        return _Grille(
            tableau=tableau,
            lignes=lignes,
            plan=self._plan_lu(tournoi_id, phase_id),
            rangs={place.participant: place.rang for place in tableau.classement()},
            identites=self._identites(tournoi_id),
            repechages=self._repechages(tournoi_id, phase),
        )

    def _repechages(self, tournoi_id: TournoiId, phase: Phase) -> dict[int, DestinationRepechage]:
        """`tour perdu → phase qui reprend ses battus`, lu dans les **sources de la séquence**.

        `VersRepechage` « ne construit rien » (`domain/politiques.py`) : la réintégration est un
        **prélèvement** de la phase avale, `SourcePhase.par_issue_de_tour(ordre, tour, PERDANTS)`.
        La destination d'un repêché n'est donc pas dans son tableau — elle est dans le déroulé, et
        c'est la seule lecture qui puisse la donner.

        `par_tournoi` trie par ordre (E05US001) : `setdefault` retient donc la phase **la plus
        proche**, celle qui reprendra effectivement ces battus si deux la déclarent.
        """
        destinations: dict[int, DestinationRepechage] = {}
        for autre in self._phases.par_tournoi(tournoi_id):
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

    def _phase_de_tableau(self, tournoi_id: TournoiId, phase_id: PhaseId | None) -> Phase | None:
        """La phase visée : celle **imposée** par le client, sinon celle du tournoi qui **vient**.

        Deux contrats distincts, et c'est volontaire :

        - `phase_id` **imposé** (écran de duels) : un identifiant fourni par le client est
          **validé**, comme partout ailleurs — inconnu, ou relevant d'un autre tournoi ⇒
          `PhaseIntrouvable` (404). Sans cette garde, un `phase_id` périmé (phase supprimée
          entre-temps) rendrait un placide « phase finale non configurée » au lieu d'un vrai
          refus : l'écran mentirait.
        - **résolution implicite** (tablette de qualification, qui ne connaît que sa cible et son
          départ) : best-effort, `None` si le tournoi n'a pas de tableau — l'écran le dit.

        « Celle qui vient » = la première élimination directe **non terminée**, dans l'ordre de la
        séquence (`par_tournoi` garantit le tri, E05US001). Prendre la première tout court
        épinglerait un tournoi à deux tableaux sur le premier **à jamais**, et router tout le monde
        en « terminé ».
        """
        if phase_id is not None:
            phase = self._phases.par_id(phase_id)
            if phase is None or phase.tournoi_id != tournoi_id:
                raise PhaseIntrouvable(f"Aucune phase {phase_id} pour le tournoi {tournoi_id}.")
            return phase
        tableaux = [
            p
            for p in self._phases.par_tournoi(tournoi_id)
            if p.type is TypePhase.ELIMINATION_DIRECTE
        ]
        en_cours = [p for p in tableaux if p.statut is not StatutPhase.TERMINEE]
        if en_cours:
            return en_cours[0]
        # Tous terminés : on vise le **dernier**, pas le premier. C'est celui où se trouve le
        # dénouement — router vers le premier rendrait « non retenu pour le tableau » à tout archer
        # qui n'a joué que le second, alors qu'il a un rang à afficher.
        return tableaux[-1] if tableaux else None

    def _tous_indisponibles(
        self,
        tournoi_id: TournoiId,
        phase_id: int | None,
        archer_ids: tuple[int, ...],
        motif: str,
    ) -> Routage:
        """Le panneau dégradé — mais **nominatif**.

        C'est l'état le plus fréquent de la journée (la phase finale n'est configurée qu'une fois la
        qualification close), donc pas un cas limite : quatre lignes anonymes et identiques seraient
        illisibles, et un panneau qui ne sait plus dire *qui* est qui a perdu sa raison d'être. Les
        noms viennent des **archers du tournoi**, lisibles indépendamment de toute phase de tableau
        — c'est justement ce que les deux branches dégradées n'ont pas.
        """
        identites = self._identites(tournoi_id)
        return Routage(
            phase_id=phase_id,
            archers=tuple(
                RoutageArcher(
                    archer_id=archer_id,
                    nom=identites.get(archer_id, ("", ""))[0],
                    prenom=identites.get(archer_id, ("", ""))[1],
                    issue=IssueRoutage.INDISPONIBLE,
                    motif=motif,
                )
                for archer_id in archer_ids
            ),
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

        La règle tient en une phrase : **son prochain duel est le match non tranché qu'il occupe**.
        Le tableau reconstruit a déjà propagé les vainqueurs et résolu les byes — un exempt du 1er
        tour occupe donc déjà son match du tour 2, et c'est celui-là qu'on trouve. Un participant
        n'occupe au plus qu'un match non tranché à la fois : l'arbre l'interdit.

        Plus de match devant lui ⇒ il a **perdu son dernier match** (ou gagné le dernier du
        tableau). Deux sorties très différentes s'y cachent, et E07US008 les sépare : le battu qui
        est **classé ici** (`TERMINE`, avec son rang) et celui que le routing **fait ressortir**
        (`REPECHE`, sans rang — il peut encore remonter).
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
            # Les deux moitiés du repêchage se lisent à deux sources indépendantes : le **routing**
            # (`_est_repeche`, décidé match par match — c'est la branche ci-dessus) et les
            # **sources de la séquence** (`grille.repechages`, indexées par **tour**). Un premier
            # correctif de revue a voulu annoncer la seconde ici aussi ; deux relecteurs l'ont
            # démoli, et de deux façons **opposées** :
            #
            # - `dernier` est le **dernier match joué**, pas le match perdu : sous cascade, le battu
            #   des demies redescend en petite finale, donc son `dernier.tour` vaut 3 et l'on rate
            #   précisément les archers que « perdants du tour 2 » désigne ;
            # - un **tour couvre plusieurs plages** dès qu'il y a des sous-tableaux : finale et
            #   petite finale sont toutes deux au tour 3, si bien qu'une source « perdants du
            #   tour 3 » décorerait aussi le 4ᵉ du podium.
            #
            # Les deux correctifs proposés étaient **incompatibles** (restreindre au braquet
            # principal / élargir à tous les tours perdus), et pour cause : la sémantique de
            # `SourcePhase.par_issue_de_tour` n'est **pas tranchée** — `# DETTE-028` acte qu'aucun
            # moteur ne consomme encore ces prélèvements. La figer ici, dans un canal d'affichage,
            # serait décider une règle métier au mauvais endroit. On s'abstient donc, et la lacune
            # est inscrite au registre plutôt que devinée.
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

    # DETTE-019 : garde tour-1, jumelle de `ServicePilotageTour._duel_a_venir`.
    @staticmethod
    def _pose_a_annoncer(
        match: Match, moi: Participant, adversaire: Participant | None, plan: _PlanLu
    ) -> tuple[tuple[int, str] | None, str | None, str | None]:
        """La pose à annoncer, le **manque** s'il n'y en a pas, l'**alerte** si elle est douteuse.

        Trois issues, et elles ne se disent pas de la même façon — c'est tout l'objet de cette
        méthode, qui est la **seule** à décider d'une cible :

        1. **Tour ≥ 2 → aucune cible.** Le plan ne pose que le 1ᵉʳ tour (ADR-0048 ; l'intégral 1→N
           est E05US010). L'archer garde bien une ligne dans `placement_tableau`, mais c'est **celle
           de son tour 1** : elle serait périmée et enverrait un finaliste sur son ancienne butte.
           La cible existera (« attribuée au lancement du tour »). Jumeau de
           `ServicePilotageTour._duel_a_venir`.
        2. **Pose absente au tour 1 → aucune cible.** Aucun plan matérialisé, pas de gabarit, ou
           archer en réserve. Rien ne viendra tant que l'organisateur n'aura pas placé : libellé
           **neutre**, pas une promesse. *(Le jumeau dit « cible non attribuée », même raison.)*
        3. **Pose présente mais duel non côte à côte → cible annoncée + alerte qualifiée.** Le
           **déclenchement** vient du domaine (`duels_non_cote_a_cote`, via
           `PlanDeDuels.duels_separes`), confronté aux paires du tableau **d'aujourd'hui**. On
           **n'efface pas** la cible : c'est la ligne de cet archer sur le plan, et la lui retirer
           échangerait une information contre un vide.

           Mais « non côte à côte » recouvre **deux situations qui appellent des conseils
           opposés**, et les confondre sous un message unique, c'était forcément se tromper sur
           l'une des deux :
           - **même butte, places éloignées** (la disposition nominale — quatre archers sur une
             cible) : la pose est le **bon** conseil, il n'y a qu'à se décaler d'une place ;
           - **buttes différentes** : la pose est le **mauvais** conseil — le duel ne s'y tirera
             pas, l'organisateur va régénérer le plan. Il faut le dire, et nommer l'autre butte.

           D'où trois messages, et non un. La donnée est déjà en main (`plan.poses`) : aucune
           lecture supplémentaire.
        """
        if match.tour != 1:
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

        Jumeau de `ServicePilotageTour._cibles_par_archer` (2ᵉ occurrence), à deux choses près : le
        routage garde la **position** (le pilotage ne compte que des cibles) et il **conserve** le
        signal `duels_separes` — que le pilotage, lui, jette. C'est précisément l'information qui
        dit
        que la pose ne correspond plus au duel du jour ; la recalculer ici en serait une écriture de
        plus, et plus faible.

        Même tolérance : sans gabarit appliqué, plan **vide** — d'où « cible non attribuée », jamais
        un échec du panneau.
        """
        try:
            plan = self._placement_duels.plan_de_duels(tournoi_id, phase_id)
        except GabaritDuTournoiAbsent:
            return _PlanLu(poses={}, separes=frozenset())
        return _PlanLu(
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
        # ⚠️ **Le routing ne s'interroge pas sur une plage indivisible**, et ce n'est pas une
        # optimisation : `construire_tableau` sort *avant* de l'appeler dans ce cas (*Règle T* —
        # « l'issue fixe les deux rangs, il n'y a plus rien à diviser »), si bien que
        # `PlacementEnCascade` y appelle `moitie_basse()` et lève `PlageInvalide`. Le contrat est
        # désormais écrit à sa source (`Routing.route`, ADR-0065 §2) ; on le redonde ici parce
        # qu'on est le deuxième appelant — et le premier à l'avoir enfreint.
        #
        # `largeur < 4` et non `est_terminale` (largeur 2) : c'est la borne exacte que
        # `Plage._demi_largeur` refuse (correctif de revue). Métier, la garde est vraie de toute
        # façon : un match terminal **décerne** les deux rangs, son perdant est classé ici.
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

    Cible croissante, puis position A→D. L'écran de salle n'a **aucune interaction** (CA E07US004) :
    l'ordre rendu par le serveur est le seul qu'il aura, et l'ordre naturel d'une boucle sur l'arbre
    (par numéro de match) ne veut rien dire pour quelqu'un qui cherche sa butte de loin.

    Ceux qui n'ont plus de pose — sortis, repêchés, pas encore placés — passent **après**, jamais
    intercalés : une ligne sans cible au milieu du pas de tir fait sauter une butte à l'œil qui
    descend la liste. Entre eux, le nom, seul ordre stable dont on dispose alors.
    """
    prochain = ligne.prochain
    if prochain is not None and prochain.cible is not None:
        return (0, prochain.cible, prochain.position or "", ligne.nom, ligne.prenom)
    return (1, 0, "", ligne.nom, ligne.prenom)
