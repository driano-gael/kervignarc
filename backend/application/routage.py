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

from application.classements import ServiceClassement
from application.erreurs import GabaritDuTournoiAbsent, PhaseIntrouvable, TournoiIntrouvable
from application.placement_duels import ServicePlacementDuels
from application.saisie_duels import Duelliste, ServiceSaisieDuels
from domain.classement import LigneClassement
from domain.erreurs import EffectifTableauInvalide
from domain.participant import Participant
from domain.phase import Phase, PhaseId, StatutPhase, TypePhase
from domain.ports import PhaseRepository
from domain.tableau import Match, PerdantDe, Tableau, VainqueurDe, libelle_tour
from domain.tournoi import TournoiId

# Les phrases que le panneau affiche quand l'information n'existe pas encore. Elles vivent ici (et
# non dans le front) pour la même raison que le `blocage` du feu vert : c'est le serveur qui sait
# **pourquoi** la donnée manque, et les quatre canaux de routage doivent dire la même chose.
CIBLE_A_VENIR = "cible attribuée au lancement du tour"
"""Tour ≥ 2 : la cible **existera**, elle n'est simplement pas encore posée (E05US010)."""

CIBLE_NON_ATTRIBUEE = "cible non attribuée"
"""Tour 1 sans pose : aucun plan matérialisé, ou archer en réserve. Rien ne viendra tant que
l'organisateur n'aura pas placé — d'où le libellé **neutre** du feu vert, et non une promesse."""

PLACEMENT_PERIME = "placement à revoir — adversaire posé sur une autre cible"
"""La pose persistée ne correspond plus au duel d'aujourd'hui (l'appariement s'est recalculé)."""

RANG_A_VENIR = "rang publié en fin de phase"
PHASE_ABSENTE = "phase finale non configurée"
TABLEAU_ABSENT = "tableau non constitué"
HORS_TABLEAU = "non retenu pour le tableau"


class IssueRoutage(str, Enum):
    """Ce que le panneau a à dire d'un archer — les trois seules issues possibles."""

    PROCHAIN_DUEL = "prochain_duel"
    """Il a un duel devant lui (`prochain` renseigné)."""

    TERMINE = "termine"
    """Il n'a plus de duel : éliminé, ou le tableau est allé à son terme pour lui."""

    INDISPONIBLE = "indisponible"
    """On ne sait pas le router (`motif` dit pourquoi)."""


@dataclass(frozen=True)
class ProchainDuel:
    """Le rendez-vous suivant d'un archer : où, quand dans l'arbre, et contre qui.

    `cible` / `position` sont `None` au-delà du tour 1 (le placement intégral est E05US010) ;
    `adversaire` est `None` tant que le duel amont n'est pas tranché, et `sources_en_attente` en
    **nomme** alors le numéro. `manque` résume en clair ce qui reste inconnu (`None` si tout y est).

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


@dataclass(frozen=True)
class RoutageArcher:
    """Ce que le panneau affiche pour **un** archer : son issue et ce qui la détaille."""

    archer_id: int
    nom: str
    prenom: str
    issue: IssueRoutage
    prochain: ProchainDuel | None = None
    rang_final: int | None = None
    tour_sortie: str | None = None
    motif: str | None = None


@dataclass(frozen=True)
class Routage:
    """La réponse du panneau : la phase de tableau visée, et une ligne **par archer demandé**.

    `phase_id` est `None` quand aucune phase d'élimination n'est configurée — l'écran le dit au lieu
    de rendre une liste vide qu'on prendrait pour une panne.
    """

    phase_id: int | None
    archers: tuple[RoutageArcher, ...]


class ServiceRoutage:
    """Cas d'usage du panneau de routage : router des archers vers leur suite (lecture pure)."""

    def __init__(
        self,
        saisie_duels: ServiceSaisieDuels,
        placement_duels: ServicePlacementDuels,
        classement: ServiceClassement,
        phases: PhaseRepository,
    ) -> None:
        self._saisie_duels = saisie_duels
        self._placement_duels = placement_duels
        self._classement = classement
        self._phases = phases

    def routage(
        self,
        tournoi_id: TournoiId,
        archer_ids: tuple[int, ...],
        phase_id: PhaseId | None = None,
    ) -> Routage:
        """Route chaque archer demandé, **dans l'ordre demandé** (l'ordre des positions A→D).

        `phase_id` non fourni ⇒ on vise la **première phase d'élimination directe** du tournoi : la
        tablette de qualification ne connaît que sa cible et son départ, pas l'arbre. Fourni (écran
        de duels), il est utilisé tel quel — ses gardes (`PhaseIntrouvable` / `PhasePasUnTableau`)
        remontent alors du service de saisie, comme partout ailleurs.

        Aucune erreur n'est levée pour un archer : une ligne **indisponible** motivée vaut mieux
        qu'un panneau qui échoue en bloc parce qu'un seul des quatre n'est pas dans le tableau.
        """
        phase = self._phase_de_tableau(tournoi_id, phase_id)
        if phase is None or phase.id is None:
            return self._tous_indisponibles(tournoi_id, None, archer_ids, PHASE_ABSENTE)
        try:
            tableau, lignes = self._saisie_duels.reconstruire(tournoi_id, phase.id)
        except EffectifTableauInvalide:
            # Moins de deux archers en lice : il n'y a pas d'arbre. Comme le feu vert, on rend un
            # panneau **motivé** plutôt qu'une erreur — l'écran est consultable avant la clôture.
            return self._tous_indisponibles(tournoi_id, phase.id, archer_ids, TABLEAU_ABSENT)
        poses = self._poses_par_archer(tournoi_id, phase.id)
        # `podium()` rebalaye tout l'arbre : calculé **une fois** pour la grille entière, pas par
        # archer — la route accepte jusqu'à 64 identifiants.
        rangs = {place.participant: place.rang for place in tableau.podium()}
        return Routage(
            phase_id=phase.id,
            archers=tuple(self._router(a, tableau, lignes, poses, rangs) for a in archer_ids),
        )

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
        return next(iter(en_cours), None) or next(iter(tableaux), None)

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
        noms viennent du classement, lisible **indépendamment** de toute phase de tableau — c'est
        justement ce que les deux branches dégradées n'ont pas.
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
        """`archer_id → (nom, prénom)` depuis le classement (best-effort).

        `{}` si le tournoi a disparu entre-temps : un panneau sans noms reste préférable à un
        panneau qui échoue — on ne troque pas une dégradation contre une panne.
        """
        try:
            classement = self._classement.pour_tournoi(tournoi_id)
        except TournoiIntrouvable:
            return {}
        return {ligne.archer_id: (ligne.nom, ligne.prenom) for ligne in classement.lignes}

    # --- Routage d'un archer -------------------------------------------------------------------

    def _router(
        self,
        archer_id: int,
        tableau: Tableau,
        lignes: dict[int, LigneClassement],
        poses: dict[int, tuple[int, str]],
        rangs: dict[Participant, int],
    ) -> RoutageArcher:
        """L'issue d'un archer : prochain duel, sortie, ou l'aveu qu'on ne sait pas le router.

        La règle tient en une phrase : **son prochain duel est le match non tranché qu'il occupe**.
        Le tableau reconstruit a déjà propagé les vainqueurs et résolu les byes — un exempt du 1er
        tour occupe donc déjà son match du tour 2, et c'est celui-là qu'on trouve. Un participant
        n'occupe au plus qu'un match non tranché à la fois : l'arbre l'interdit.
        """
        moi = Participant.individuel(archer_id)
        identite = self._saisie_duels.duelliste(moi, lignes)
        nom = identite.nom if identite is not None else ""
        prenom = identite.prenom if identite is not None else ""
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
                prochain=self._prochain_duel(prochain, tableau, lignes, poses, moi),
            )
        rang = rangs.get(moi)
        dernier = max(siens, key=lambda m: m.tour)
        return RoutageArcher(
            archer_id=archer_id,
            nom=nom,
            prenom=prenom,
            issue=IssueRoutage.TERMINE,
            rang_final=rang,
            tour_sortie=libelle_tour(dernier.tour, tableau.nb_tours, dernier.place_en_jeu),
            # Le rang d'un battu **avant** le podium (9-16ᵉ d'un tableau de 32…) suppose
            # l'agrégation des rangs de tableau — E06US004, non livrée. On annonce l'attente au
            # lieu d'afficher un rang faux ou un vide.
            motif=RANG_A_VENIR if rang is None else None,
        )

    def _prochain_duel(
        self,
        match: Match,
        tableau: Tableau,
        lignes: dict[int, LigneClassement],
        poses: dict[int, tuple[int, str]],
        moi: Participant,
    ) -> ProchainDuel:
        """Le rendez-vous : sa cible (si elle est **valide**), son libellé de tour, l'adversaire."""
        adversaire_participant = match.bas if match.haut == moi else match.haut
        adversaire = self._saisie_duels.duelliste(adversaire_participant, lignes)
        pose, manque = self._pose_valide(match, moi, adversaire_participant, poses)
        return ProchainDuel(
            numero=match.numero,
            tour=match.tour,
            libelle=libelle_tour(match.tour, tableau.nb_tours, match.place_en_jeu),
            cible=pose[0] if pose is not None else None,
            position=pose[1] if pose is not None else None,
            adversaire=adversaire,
            sources_en_attente=self._sources_en_attente(match),
            manque=manque,
        )

    # DETTE-019 : garde tour-1, jumelle de `ServicePilotageTour._duel_a_venir`.
    @staticmethod
    def _pose_valide(
        match: Match,
        moi: Participant,
        adversaire: Participant | None,
        poses: dict[int, tuple[int, str]],
    ) -> tuple[tuple[int, str] | None, str | None]:
        """La pose à **annoncer**, ou `None` + le motif qui dit pourquoi il n'y en a pas.

        Trois raisons de ne rien annoncer, et elles ne se disent pas de la même façon — c'est tout
        l'objet de cette méthode, qui est la **seule** à décider d'une cible :

        1. **Tour ≥ 2** — le plan ne pose que le 1ᵉʳ tour (ADR-0048 ; l'intégral 1→N est E05US010).
           L'archer garde bien une ligne dans `placement_tableau`, mais c'est **celle de son tour
           1** : elle serait périmée et enverrait un finaliste sur son ancienne butte. La cible
           existera (« attribuée au lancement du tour »). Jumeau de
           `ServicePilotageTour._duel_a_venir`.
        2. **Pose absente au tour 1** — aucun plan matérialisé, pas de gabarit, ou archer en
           réserve. Rien ne viendra tant que l'organisateur n'aura pas placé : libellé **neutre**,
           pas une promesse. *(Le jumeau dit « cible non attribuée » pour la même raison.)*
        3. **Pose incohérente avec le duel du jour** — les deux duellistes d'un match tirent
           forcément sur **la même** cible (E03US009 les veut même côte à côte). Si l'adversaire est
           posé ailleurs, c'est que l'**appariement s'est recalculé** depuis la matérialisation du
           plan : le classement a bougé (une correction de score suffit, E04US013) et l'arbre est
           reconstruit à chaque lecture (ADR-0023) alors que les poses, elles, sont **persistées**.
           Annoncer la pose enverrait deux archers sur deux buttes différentes — l'incident de salle
           que ce panneau existe pour éviter. La garde tour-1 (cas 1) ne couvre **pas** ce cas :
           c'est le même raisonnement décalé d'un cran, de la cible périmée d'un *tour* à celle d'un
           *appariement*. L'écran Plan de duels signale déjà la situation (`duels_separes`) ; ce
           canal-ci est le seul à rendre l'information à l'archer, donc le seul où elle vaut ordre.
        """
        if match.tour != 1:
            return None, CIBLE_A_VENIR
        pose = poses.get(moi.ref_id)
        if pose is None:
            return None, CIBLE_NON_ATTRIBUEE
        pose_adverse = poses.get(adversaire.ref_id) if adversaire is not None else None
        if pose_adverse is None or pose_adverse[0] != pose[0]:
            return None, PLACEMENT_PERIME
        return pose, None

    # --- Lectures best-effort ------------------------------------------------------------------

    # DETTE-019 : jumelle de `ServicePilotageTour._cibles_par_archer`.
    def _poses_par_archer(
        self, tournoi_id: TournoiId, phase_id: PhaseId
    ) -> dict[int, tuple[int, str]]:
        """`archer_id → (cible, position)` depuis le plan de duels **persisté**.

        Jumeau de `ServicePilotageTour._cibles_par_archer` (2ᵉ occurrence), à la **position** près :
        le pilotage compte des cibles, le routage envoie un archer à une place précise sur la butte.
        Même tolérance : sans gabarit appliqué, carte **vide** — d'où « cible attribuée au lancement
        du tour », jamais un échec du panneau.
        """
        try:
            plan = self._placement_duels.plan_de_duels(tournoi_id, phase_id)
        except GabaritDuTournoiAbsent:
            return {}
        return {
            pose.archer_id: (cible.index, pose.position)
            for cible in plan.cibles
            for pose in cible.placements
        }

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
