"""Ports du domaine — interfaces implémentées par des adapters d'infrastructure (ADR-0003).

Le domaine définit *ce dont il a besoin* (persister, relire) sans savoir *comment*.
`Protocol` : conformité **structurelle**, sans imposer d'héritage aux adapters — le
domaine reste pur (aucune dépendance vers l'infrastructure).
"""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import Protocol

from domain.archer import Archer, ArcherId
from domain.arret_programme import ArretDeCirconstance, FranchissementArret
from domain.barrage import BarrageDePlaces, BarrageId, TirBarrage
from domain.blason import Blason, BlasonId
from domain.categorie import Categorie, CategorieId
from domain.club import Club, ClubId
from domain.depart import Depart, DepartId
from domain.deroule_etape import EtapeDeroule, EtapeDerouleId
from domain.documents_salle import CartesScoreurs, EtiquettesCibles
from domain.duel import BaremeDuel, Duel
from domain.ecran import PriseDeControle
from domain.entree_audit import EntreeAudit
from domain.feuille_marque import FeuilleDeMarque
from domain.forfait import Forfait
from domain.format_tournoi import FormatTournoi, FormatTournoiId
from domain.gabarit_salle import GabaritSalle, GabaritSalleId
from domain.identite import EmplacementLogo, IdentiteVisuelle, Logo
from domain.inscription import Inscription, InscriptionId
from domain.listes_impression import ListeClubPaiement, ListePlacement
from domain.palmares import Palmares
from domain.phase import Phase, PhaseId, TypePhase
from domain.placement import Affectation
from domain.placement_par_bloc import BlocDeCouloirs
from domain.podium import ReglagePodiums
from domain.poste import Poste, PosteId, TypePoste
from domain.remboursement import Remboursement, RemboursementId
from domain.score import Score
from domain.scoreur import Scoreur, ScoreurId
from domain.serie import Serie
from domain.supervision import ActivitePoste
from domain.tournoi import Tournoi, TournoiId


class TournoiRepository(Protocol):
    """Port de persistance des tournois (adapter fourni par l'infrastructure)."""

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        """Persiste un tournoi et le renvoie avec son identifiant attribué."""
        ...

    def par_id(self, tournoi_id: TournoiId) -> Tournoi | None:
        """Renvoie le tournoi d'identifiant donné, ou `None` s'il n'existe pas."""
        ...

    def lister(self) -> list[Tournoi]:
        """Renvoie tous les tournois (liste éventuellement vide).

        L'ordre n'est **pas** garanti par le port (détail de l'adapter) : un consommateur
        qui a besoin d'un ordre précis doit le trier lui-même.
        """
        ...

    def enregistrer(self, tournoi: Tournoi) -> Tournoi:
        """Met à jour un tournoi déjà persisté (édition, transition de statut) et le renvoie."""
        ...

    def supprimer(self, tournoi_id: TournoiId) -> None:
        """Supprime le tournoi d'identifiant donné (existence garantie par l'appelant)."""
        ...


class ArcherRepository(Protocol):
    """Port de persistance des archers (adapter fourni par l'infrastructure)."""

    def ajouter(self, archer: Archer) -> Archer:
        """Persiste un archer et le renvoie avec son identifiant attribué."""
        ...

    def par_id(self, archer_id: ArcherId) -> Archer | None:
        """Renvoie l'archer d'identifiant donné, ou `None` s'il n'existe pas."""
        ...

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Archer]:
        """Renvoie tous les archers d'un tournoi (liste éventuellement vide)."""
        ...

    def par_club(self, club_id: ClubId) -> list[Archer]:
        """Renvoie les archers rattachés à `club_id`, **tous tournois confondus** (E02US001).

        Sert à refuser la suppression d'un club encore référencé (liste non vide). La portée
        inter-tournois est délibérée : le référentiel des clubs est global, donc un club utilisé
        par un tournoi passé est utilisé tout court.
        """
        ...

    def tous(self) -> list[Archer]:
        """Tous les archers du dépôt, **tous tournois confondus** (recherche transverse E16US010).

        ⚠️ Liste **complète et non filtrée, exprès** : la recherche replie casse et accents
        (`domain.recherche`), ce qu'un `LIKE` SQLite ne sait pas faire — « leveque » n'y trouverait
        jamais « Lévêque ». Le filtrage se fait donc en mémoire, tenable parce que l'appli est
        mono-club et locale (règle 12) ; un référentiel qui grossirait démentirait ce pari —
        `DETTE-092` porte le seuil et le critère de résorption.
        """
        ...

    def enregistrer(self, archer: Archer) -> Archer:
        """Met à jour un archer déjà persisté (placement, édition E02US003) et le renvoie."""
        ...

    def supprimer(self, archer_id: ArcherId) -> None:
        """Supprime l'archer, **ses scores et ses inscriptions** (E02US003, E02US009).

        ⚠️ La purge fait partie du contrat, dans **une seule transaction** : `score.archer_id` et
        `inscription.archer_id` sont des FK **sans `ON DELETE`** (DETTE-001), et deux transactions
        successives laisseraient un archer dépouillé de ses flèches. Existence et confirmation
        (`ArcherEngage`) garanties par l'appelant. Un archer qui **abandonne** ne passe pas par
        ici : c'est un forfait tracé (ADR-0050), qui préserve ses flèches.
        """
        ...

    def fusionner(self, gagnant_id: ArcherId, perdant_id: ArcherId) -> None:
        """Fusionne deux fiches d'un doublon (E02US005) : réassigne inscriptions, scores et séries
        au gagnant, puis **supprime** le perdant — en **une seule transaction** (FK sans
        `ON DELETE`, DETTE-001). Miroir de `supprimer`, qui purge là où celle-ci réattribue.

        L'appelant garantit deux archers distincts du même tournoi dont **pas les deux** n'ont de
        série. ⚠️ Collision `UNIQUE(archer_id, depart_id)` à résoudre dans l'adapter : l'inscription
        doublonnée est supprimée plutôt que réassignée, **paiement reporté** sur celle du gagnant.
        """
        ...


class ClubRepository(Protocol):
    """Port de persistance des clubs (adapter fourni par l'infrastructure).

    Référentiel **global** : un club n'appartient à aucun tournoi (E02US001), d'où l'absence
    de `par_tournoi` — `lister` renvoie tout le référentiel.
    """

    def ajouter(self, club: Club) -> Club:
        """Persiste un club et le renvoie avec son identifiant attribué."""
        ...

    def par_id(self, club_id: ClubId) -> Club | None:
        """Renvoie le club d'identifiant donné, ou `None` s'il n'existe pas."""
        ...

    def par_nom(self, nom: str) -> Club | None:
        """Renvoie le club portant ce nom, ou `None` s'il n'y en a pas.

        **Comparaison au sens de `domain.club.cle_nom`** : espaces de bord, casse et accents
        repliés — « Arc Club Rennes », « arc club rennes » et « Elan » / « Élan » désignent le même
        club. L'adapter n'invente pas sa propre règle : il applique `cle_nom`. Sert à refuser un
        doublon à la création comme au renommage (E02US001).
        """
        ...

    def lister(self) -> list[Club]:
        """Renvoie tout le référentiel des clubs (liste éventuellement vide).

        L'ordre n'est **pas** garanti par le port (détail de l'adapter) : un consommateur qui a
        besoin d'un ordre précis doit le trier lui-même.
        """
        ...

    def enregistrer(self, club: Club) -> Club:
        """Met à jour un club déjà persisté (renommage) et le renvoie."""
        ...

    def supprimer(self, club_id: ClubId) -> None:
        """Supprime le club d'identifiant donné (existence garantie par l'appelant)."""
        ...


class DepartRepository(Protocol):
    """Port de persistance des départs — créneaux d'un tournoi (E02US004, ADR-0017)."""

    def ajouter(self, depart: Depart) -> Depart:
        """Persiste un départ et le renvoie avec son identifiant attribué."""
        ...

    def par_id(self, depart_id: DepartId) -> Depart | None:
        """Renvoie le départ d'identifiant donné, ou `None` s'il n'existe pas."""
        ...

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Depart]:
        """Renvoie tous les départs d'un tournoi, **triés par numéro** (liste éventuellement vide).

        L'ordre par numéro est garanti par ce port (au contraire de `lister` des autres
        repositories) : le service s'en sert pour attribuer le prochain numéro (max + 1) et l'écran
        pour afficher les créneaux dans l'ordre.
        """
        ...

    def enregistrer(self, depart: Depart) -> Depart:
        """Met à jour un départ déjà persisté (édition tarif/horaire) et le renvoie."""
        ...

    def supprimer(self, depart_id: DepartId) -> None:
        """Supprime le départ **et ses inscriptions** (E02US009).

        Existence et confirmation (`DepartAvecInscriptions`) garanties par l'appelant. La purge est
        au contrat, en **une seule transaction** : `inscription.depart_id` est une FK **sans
        `ON DELETE`** (DETTE-001). Même patron que `ArcherRepository.supprimer`.
        """
        ...

    def supprimer_avec_remboursements(
        self, depart_id: DepartId, remboursements: Sequence[Remboursement]
    ) -> None:
        """Supprime le départ (et ses inscriptions) **et** ouvre les remboursements en une
        transaction (E08US005, ADR-0057).

        Variante de `supprimer` quand des inscriptions étaient **payées** : les `remboursements`
        construits par le service sont insérés dans la **même session** que les `DELETE`, un unique
        `commit` scellant l'ensemble — jamais de somme encaissée effacée sans contrepartie, jamais
        de remboursement en double. Liste vide tolérée (équivalente à `supprimer`).
        """
        ...


class InscriptionRepository(Protocol):
    """Port de persistance des inscriptions — liens archer ↔ départ (E02US009, ADR-0017).

    `enregistrer` met à jour une inscription **sans trace** (opération générique du port ; depuis
    E08US002 le marquage du paiement ne passe plus par là) ; `definir_paye_avec_trace`
    co-écrit le nouveau statut **et** une entrée d'audit dans **une seule transaction** (atomicité
    acte↔trace, ADR-0035) — c'est la voie du suivi des paiements (E08US002), simple ou groupé.
    L'atomicité est réalisée par l'adapter (session partagée) ; au niveau du port, c'est une seule
    opération « les inscriptions ET leur trace, ou ni l'une ni l'autre »."""

    def ajouter(self, inscription: Inscription) -> Inscription:
        """Persiste une inscription et la renvoie avec son identifiant attribué."""
        ...

    def par_id(self, inscription_id: InscriptionId) -> Inscription | None:
        """Renvoie l'inscription d'identifiant donné, ou `None` si elle n'existe pas."""
        ...

    def par_archer(self, archer_id: ArcherId) -> list[Inscription]:
        """Renvoie les inscriptions d'un archer (liste éventuellement vide).

        Sert à lister ses créneaux **et** à savoir s'il est « engagé » (une inscription suffit,
        E02US009) au moment de le supprimer.
        """
        ...

    def par_depart(self, depart_id: DepartId) -> list[Inscription]:
        """Renvoie les inscriptions portant sur un départ (liste éventuellement vide).

        Sert au garde-fou « supprimer un départ qui porte des inscriptions »
        (`DepartAvecInscriptions`) et au décompte des payées affiché dans son message.
        """
        ...

    def par_archer_et_depart(self, archer_id: ArcherId, depart_id: DepartId) -> Inscription | None:
        """Renvoie l'inscription du couple `(archer, départ)`, ou `None`.

        Sert à refuser une **seconde** inscription sur le même créneau (`DejaInscrit`) — le pendant
        applicatif de la contrainte `UNIQUE(archer_id, depart_id)`.
        """
        ...

    def enregistrer(self, inscription: Inscription) -> Inscription:
        """Met à jour une inscription déjà persistée (bascule de `paye`, sans trace) et la
        renvoie."""
        ...

    def definir_paye_avec_trace(
        self, inscription_ids: Sequence[InscriptionId], paye: bool, entree: EntreeAudit
    ) -> list[Inscription]:
        """Bascule `paye` sur plusieurs inscriptions **et** co-écrit une entrée d'audit (E08US002).

        Une seule transaction (ADR-0035, comme `SerieRepository.enregistrer_avec_trace`) : le
        marquage — simple (une inscription) ou groupé (plusieurs) — et sa trace `PAIEMENT` tiennent
        dans un « tout ou rien ». Jamais un paiement basculé sans trace, jamais de trace fantôme.
        L'entrée arrive **déjà construite et datée** par le service (port `Horloge`). Renvoie les
        inscriptions mises à jour. L'existence des inscriptions est garantie par l'appelant.
        """
        ...

    def supprimer(self, inscription_id: InscriptionId) -> None:
        """Supprime l'inscription d'identifiant donné (désinscription ; existence garantie)."""
        ...

    def supprimer_avec_remboursement(
        self, inscription_id: InscriptionId, remboursement: Remboursement
    ) -> None:
        """Supprime l'inscription **et** ouvre son remboursement en une transaction (E08US005).

        Variante de `supprimer` pour une désinscription dont l'inscription **était payée** (créneau
        tarifé) : le `remboursement` (construit par le service) est **inséré dans la même session**
        que le `DELETE`, puis un **unique** `commit` scelle l'ensemble (ADR-0057, même couture que
        `DepartRepository.supprimer_avec_remboursements`). Jamais de somme encaissée effacée sans
        contrepartie ; jamais de remboursement en double. Existence garantie par l'appelant.
        """
        ...


class PlacementRepository(Protocol):
    """Port de persistance du plan de cibles **matérialisé** (E03US004, ADR-0024).

    Le plan cesse d'être recalculé à la demande : il est stocké comme un ensemble d'`Affectation`
    (une par inscription posée). Un inscrit **sans** affectation est en réserve — l'absence de ligne
    *est* l'information, il n'y a rien à persister pour la réserve.
    """

    def par_depart(self, depart_id: DepartId) -> list[Affectation]:
        """Renvoie les affectations d'un départ (liste éventuellement vide = tout en réserve)."""
        ...

    def definir_plan(self, depart_id: DepartId, affectations: Sequence[Affectation]) -> None:
        """Remplace **intégralement** le plan d'un départ : purge les affectations puis insère.

        Sert à **régénérer / annuler** (ADR-0024) : le placement auto réécrit tout le plan en une
        transaction. Ce qui n'est pas dans `affectations` retombe en réserve.
        """
        ...

    def definir_plan_avec_trace(
        self, depart_id: DepartId, affectations: Sequence[Affectation], entree: EntreeAudit
    ) -> None:
        """Remplace le plan **et** co-écrit son entrée d'audit en une transaction (E12US007).

        Face « trace atomique » de `definir_plan` (ADR-0035, comme `SerieRepository`) : la
        régénération **massive** du plan (des scores existent déjà) et sa trace `REPLACEMENT`
        tiennent dans un seul « tout ou rien » — jamais de replacement massif non tracé, jamais de
        trace fantôme. L'entrée arrive **déjà construite et datée** par le service (port `Horloge`).
        """
        ...

    def poser_plusieurs(self, depart_id: DepartId, affectations: Sequence[Affectation]) -> None:
        """Insère/met à jour plusieurs affectations d'un départ en **une** transaction (upsert).

        Atomicité voulue par l'**échange** (deux poses indissociables) et par le déplacement
        (une pose) : le service valide avant, la file sérialise, la transaction unique garantit le
        tout-ou-rien.
        """
        ...

    def retirer(self, inscription_id: InscriptionId) -> None:
        """Retire l'affectation d'un inscrit — mise en réserve (sans effet s'il n'en avait pas)."""
        ...


class PlacementParBlocRepository(Protocol):
    """Port de persistance du **plan de blocs** matérialisé d'une phase (E05US023, ADR-0083 §3).

    ⚠️ Seul port de placement dont l'unité posée n'est **pas** un archer : on persiste « groupe →
    plage de couloirs contigus ». Le membre au repos change à chaque tour
    (`poule.couloirs_occupes`), donc écrire « archer → couloir » écrirait une information fausse.
    D'où deux gestes seulement, contre quatre pour `PlacementTableauRepository` — l'organisateur
    déplace un **groupe** ; en offrir plus inviterait à casser la contiguïté du bloc.
    """

    def par_phase(self, phase_id: PhaseId) -> list[BlocDeCouloirs]:
        """Renvoie les blocs posés d'une phase, groupe par groupe (liste vide = plan non posé).

        Les couloirs de chaque bloc sortent **dans l'ordre de remplissage** — c'est ce que
        `BlocDeCouloirs.places` promet, et ce dont dépend la dérivation des couloirs de rencontre.
        """
        ...

    def definir_plan(self, phase_id: PhaseId, blocs: Sequence[BlocDeCouloirs]) -> None:
        """Remplace **intégralement** le plan de blocs d'une phase, en une transaction.

        Purge puis insère. Le remplacement en bloc n'est pas une commodité : un plan partiellement
        réécrit pourrait laisser deux poules sur le même couloir le temps d'une lecture, et la
        contrainte d'unicité de la table refuserait alors l'insertion à mi-chemin.
        """
        ...


class PlacementTableauRepository(Protocol):
    """Port de persistance du **plan de duels** matérialisé d'une phase (E03US009, ADR-0048).

    Jumeau de `PlacementRepository` mais scoppé par **phase** (et non par départ) : le placement des
    duellistes d'une phase de tableau, ajustable au glisser-déposer. Une `Affectation` par
    inscription posée ; un inscrit **sans** affectation est en réserve (l'absence *est*
    l'information, ADR-0024). L'appariement n'est pas persisté (recalculé du classement, ADR-0023) —
    seule la pose l'est.
    """

    def par_phase(self, phase_id: PhaseId) -> list[Affectation]:
        """Renvoie les affectations d'une phase (liste éventuellement vide = tout en réserve)."""
        ...

    def definir_plan(self, phase_id: PhaseId, affectations: Sequence[Affectation]) -> None:
        """Remplace **intégralement** le plan de duels d'une phase — régénérer / annuler (ADR-0048).

        Purge les affectations de la phase puis insère, en une transaction. Ce qui n'est pas dans
        `affectations` retombe en réserve.
        """
        ...

    def poser_plusieurs(self, phase_id: PhaseId, affectations: Sequence[Affectation]) -> None:
        """Insère/met à jour plusieurs affectations d'une phase en **une** transaction (upsert).

        Atomicité voulue par l'**échange** (deux poses indissociables) et le déplacement (une
        pose) : le service valide avant, la file sérialise, la transaction unique garantit le
        tout-ou-rien.
        """
        ...

    def retirer(self, phase_id: PhaseId, inscription_id: InscriptionId) -> None:
        """Retire l'affectation d'un inscrit **dans cette phase** (réserve) ; sans effet sinon.

        La clé est **composite** `(phase_id, inscription_id)` : retirer un duelliste ne touche pas
        sa pose de qualification (autre table), d'où le `phase_id` requis ici.
        """
        ...


class DuelRepository(Protocol):
    """Port de persistance du **tir** d'un match du tableau (saisie en duels, E04US013, ADR-0049).

    On persiste le tir (manches, barrage, validateur) **et l'identité des duellistes**, keyés
    `(phase_id, match_numero)`. Cette identité n'est pas l'appariement *plan*, recalculé du
    classement (ADR-0048) : c'est le fait « qui a tiré », qui **ancre** le résultat pour que
    l'appelant détecte une divergence (ADR-0049 §4). Seul le barème est réinjecté à la lecture.
    """

    def numeros_enregistres(self, phase_id: PhaseId) -> frozenset[int]:
        """Les `match_numero` d'une phase qui portent un tir enregistré (`frozenset` vide sinon).

        Sert la **reconstruction** de l'arbre (rejouer les duels validés) sans une requête par
        match : on repère d'abord les matchs porteurs d'un tir, puis on `charger` ceux-là.
        """
        ...

    def charger(self, phase_id: PhaseId, match_numero: int, *, bareme: BaremeDuel) -> Duel | None:
        """Réhydrate le `Duel` d'un match (duellistes **stockés** + `bareme` fourni), ou `None`.

        Les duellistes viennent de la base — l'appelant compare l'identité réhydratée aux occupants
        recalculés pour détecter une divergence. Le `bareme` est re-résolu de l'arme (ADR-0049).
        """
        ...

    def enregistrer(self, phase_id: PhaseId, match_numero: int, duel: Duel) -> Duel:
        """Persiste le **tir et l'identité des duellistes** du match, et renvoie le duel.

        Écriture idempotente par `(phase_id, match_numero)`. Le barème n'est pas stocké (re-résolu
        l'arme à la lecture) ; les duellistes le sont (ancrage anti-ré-attribution, ADR-0049 §4).
        """
        ...


class CategorieRepository(Protocol):
    """Port de persistance des catégories (adapter fourni par l'infrastructure)."""

    def ajouter(self, categorie: Categorie) -> Categorie:
        """Persiste une catégorie et la renvoie avec son identifiant attribué."""
        ...

    def par_id(self, categorie_id: CategorieId) -> Categorie | None:
        """Renvoie la catégorie d'identifiant donné, ou `None` si elle n'existe pas."""
        ...

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Categorie]:
        """Renvoie toutes les catégories d'un tournoi (liste éventuellement vide)."""
        ...

    def par_bibliotheque(self) -> list[Categorie]:
        """Renvoie les **modèles de bibliothèque** — patrimoine du club, sans tournoi (E01US023).

        Distincte de `par_tournoi` et non un cas particulier avec `tournoi_id=None` : la
        bibliothèque et la copie d'un tournoi sont deux lectures **de nature différente**, et les
        confondre reviendrait à laisser un appelant demander « les catégories du tournoi `None` ».
        """
        ...

    def par_blason(self, blason_id: BlasonId) -> list[Categorie]:
        """Renvoie les catégories dont le blason par défaut est `blason_id` (E01US006).

        Sert à refuser la suppression d'un blason encore référencé (liste non vide).
        """
        ...

    def enregistrer(self, categorie: Categorie) -> Categorie:
        """Met à jour une catégorie déjà persistée (édition) et la renvoie."""
        ...

    def supprimer(self, categorie_id: CategorieId) -> None:
        """Supprime la catégorie d'identifiant donné (existence garantie par l'appelant)."""
        ...


class BlasonRepository(Protocol):
    """Port de persistance des blasons (adapter fourni par l'infrastructure)."""

    def ajouter(self, blason: Blason) -> Blason:
        """Persiste un blason et le renvoie avec son identifiant attribué."""
        ...

    def par_id(self, blason_id: BlasonId) -> Blason | None:
        """Renvoie le blason d'identifiant donné, ou `None` s'il n'existe pas."""
        ...

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Blason]:
        """Renvoie tous les blasons d'un tournoi (liste éventuellement vide)."""
        ...

    def par_bibliotheque(self) -> list[Blason]:
        """Renvoie les **modèles de bibliothèque** — patrimoine du club, sans tournoi (E01US023).

        Distincte de `par_tournoi` et non un cas particulier avec `tournoi_id=None` : la
        bibliothèque et la copie d'un tournoi sont deux lectures **de nature différente**, et les
        confondre reviendrait à laisser un appelant demander « les blasons du tournoi `None` ».
        """
        ...

    def enregistrer(self, blason: Blason) -> Blason:
        """Met à jour un blason déjà persisté (édition) et le renvoie."""
        ...

    def supprimer(self, blason_id: BlasonId) -> None:
        """Supprime le blason d'identifiant donné (existence garantie par l'appelant)."""
        ...


class FormatTournoiRepository(Protocol):
    """Port de persistance des formats de tournoi (E01US023, ADR-0060 §5).

    **Pas de `par_tournoi` ni de `par_bibliotheque`** — et c'est le fait notable de ce port : un
    format n'existe qu'en bibliothèque. Sa « copie » dans un tournoi n'est pas un format rattaché,
    ce sont les **phases** du tournoi, persistées par `PhaseRepository`. `lister` renvoie donc
    toute la bibliothèque, sans filtre à écrire.
    """

    def ajouter(self, format_tournoi: FormatTournoi) -> FormatTournoi:
        """Persiste un format et le renvoie avec son identifiant attribué."""
        ...

    def par_id(self, format_id: FormatTournoiId) -> FormatTournoi | None:
        """Renvoie le format d'identifiant donné, ou `None` s'il n'existe pas."""
        ...

    def lister(self) -> list[FormatTournoi]:
        """Renvoie tous les formats de la bibliothèque (liste éventuellement vide).

        L'ordre n'est **pas** garanti par le port (détail de l'adapter) : un consommateur qui a
        besoin d'un ordre précis le trie lui-même.
        """
        ...

    def par_nom(self, nom: str) -> FormatTournoi | None:
        """Renvoie le format dont le nom correspond, ou `None` — comparaison **exacte**.

        Sert à la **promotion** (E01US023) : promouvoir un déroulé sous un nom déjà pris met à jour
        le format existant au lieu d'en créer un homonyme. La comparaison est exacte, comme
        l'unicité en base ; le repli de casse et d'accents de `domain.club.cle_nom` ne s'applique
        pas ici (un format se choisit dans une liste courte, pas au clavier sous pression).
        """
        ...

    def enregistrer(self, format_tournoi: FormatTournoi) -> FormatTournoi:
        """Met à jour un format déjà persisté (édition, promotion) et le renvoie."""
        ...

    def supprimer(self, format_id: FormatTournoiId) -> None:
        """Supprime le format d'identifiant donné (existence garantie par l'appelant).

        Les tournois qui l'avaient appliqué gardent leurs **phases** intactes : elles ne le
        référencent pas (ADR-0060 §2, copie plutôt que référence).
        """
        ...


class GabaritSalleRepository(Protocol):
    """Port de persistance des gabarits de salle (adapter fourni par l'infrastructure).

    Deux natures cohabitent : les **modèles** de bibliothèque (`tournoi_id is None`),
    réutilisables (E01US007), et les **instances** appliquées à un tournoi (E01US008), copies
    ajustables. `lister` ne renvoie que les modèles ; `par_tournoi` récupère l'instance d'un
    tournoi.
    """

    def ajouter(self, gabarit: GabaritSalle) -> GabaritSalle:
        """Persiste un gabarit (modèle ou instance) et le renvoie avec son identifiant attribué."""
        ...

    def par_id(self, gabarit_id: GabaritSalleId) -> GabaritSalle | None:
        """Renvoie le gabarit d'identifiant donné, ou `None` s'il n'existe pas."""
        ...

    def lister(self) -> list[GabaritSalle]:
        """Renvoie les gabarits **modèles** (bibliothèque, `tournoi_id is None`)."""
        ...

    def par_tournoi(self, tournoi_id: TournoiId) -> GabaritSalle | None:
        """Renvoie l'instance de gabarit appliquée à un tournoi, ou `None` s'il n'y en a pas.

        Un tournoi porte **au plus une** instance (son plan de salle courant).
        """
        ...

    def enregistrer(self, gabarit: GabaritSalle) -> GabaritSalle:
        """Met à jour un gabarit déjà persisté (édition, ajustement) et le renvoie."""
        ...

    def supprimer(self, gabarit_id: GabaritSalleId) -> None:
        """Supprime le gabarit d'identifiant donné (existence garantie par l'appelant)."""
        ...


class ScoreRepository(Protocol):
    """Port de persistance des scores (adapter fourni par l'infrastructure)."""

    def ajouter(self, score: Score) -> Score:
        """Persiste un score et le renvoie avec son identifiant attribué."""
        ...

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Score]:
        """Renvoie tous les scores des archers d'un tournoi (liste éventuellement vide)."""
        ...

    def par_archer(self, archer_id: ArcherId) -> list[Score]:
        """Renvoie les scores d'un archer (liste éventuellement vide).

        Sert à savoir si un archer est **engagé** — a-t-il déjà tiré ? (E02US003 : refus de
        suppression, signalement d'un changement de catégorie). Un port dédié plutôt qu'un filtre
        sur `par_tournoi` : la question porte sur un archer, et la balayer depuis le tournoi
        chargerait toutes les flèches de la compétition pour répondre « oui » à la première.
        """
        ...


class DerouleRepository(Protocol):
    """Port de persistance du **déroulé** d'un tournoi — la définition, une seule fois (ADR-0076).

    Distinct de `PhaseRepository`, qui porte l'**avancement** de chaque créneau. La séparation est
    le propos : tant que la définition était recopiée par départ, elle pouvait diverger en silence.

    L'ordre 1..N est la clé de lecture **et** la clé de jointure vers les phases : une phase joue
    l'étape de même rang, dans le tournoi de son créneau.
    """

    def ajouter(self, etape: EtapeDeroule) -> EtapeDeroule:
        """Persiste une étape et la renvoie avec son identifiant attribué."""
        ...

    def par_tournoi(self, tournoi_id: TournoiId) -> list[EtapeDeroule]:
        """Le déroulé du tournoi, **ordonné par `ordre`** (liste éventuellement vide).

        Le tri est garanti par le port : la séquence se compose et se valide dans son ordre, et un
        appelant qui devrait trier lui-même finirait par oublier de le faire.
        """
        ...

    def enregistrer(self, etape: EtapeDeroule) -> EtapeDeroule:
        """Met à jour une étape déjà persistée (barème, grain, type, sources, rang…)."""
        ...

    def reordonner(self, etapes: list[EtapeDeroule]) -> list[EtapeDeroule]:
        """Réécrit **en un bloc** les rangs (et définitions remappées) de tout un déroulé.

        ⚠️ **Pas une boucle sur `enregistrer`** : un déroulé est une suite 1..N sans doublon, et
        l'échange de deux rangs voisins passe par un état que l'unicité SQL refuse. Sortir du piège
        est une affaire de **persistance**, pas de métier (ADR-0003). L'écriture est **atomique** —
        à moitié appliquée, elle laisserait une séquence que le domaine rejette. Renvoie les étapes
        relues dans l'ordre demandé. `# DETTE-026` : 3ᵉ écrivain, le rang porte l'identité.
        """
        ...

    def supprimer(self, etape_id: EtapeDerouleId) -> None:
        """Supprime une étape du déroulé (existence garantie par l'appelant)."""
        ...


class PhaseRepository(Protocol):
    """Port de persistance des phases — l'**avancement** d'une étape dans un créneau (ADR-0076).

    ⚠️ **Une phase ne persiste plus sa définition** : seuls `depart_id`, `ordre` et `statut` sont
    écrits, le reste venant de l'`EtapeDeroule` de même rang, que le repository **assemble**.
    Corollaire : passer une `Phase` au barème modifié ne change rien — la définition s'édite sur
    l'étape. ⚠️ Lectures `par_depart` et non `par_tournoi` depuis E01US025 (ADR-0075) ; le
    renommage est **cassant à dessein**, les deux identifiants étant des alias d'`int` (DETTE-044).
    """

    def ajouter(self, phase: Phase) -> Phase:
        """Persiste une phase et la renvoie avec son identifiant attribué."""
        ...

    def par_id(self, phase_id: PhaseId) -> Phase | None:
        """Renvoie la phase d'identifiant donné, ou `None` si elle n'existe pas."""
        ...

    def par_depart_et_type(self, depart_id: DepartId, type_phase: TypePhase) -> Phase | None:
        """Renvoie **la dernière** phase d'un départ pour ce type, ou `None`.

        ⚠️ **Plus aucun appelant de production** (E05US025) : ne survit que dans des décors de
        tests. Un départ ne porte **plus** au plus une qualification (ADR-0082) ; en cas de
        multiplicité, les deux adapters rendent l'`ordre` le plus élevé — un choix arbitraire, pas
        une résolution. Qui doit désigner « la » qualification passe par
        `application/portee.py:qualification_courante`, jamais par ici.
        """
        ...

    def par_depart(self, depart_id: DepartId) -> list[Phase]:
        """Renvoie **toutes** les phases d'un **départ**, **ordonnées par `ordre`** (E05US001).

        La séquence de phases (`ServicePhases`) se compose et se valide sur cette liste ; l'ordre
        y est significatif (1..N sans trou **dans le départ**), d'où le tri à la source.
        """
        ...

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Phase]:
        """Renvoie les phases de **tous les départs** d'un tournoi, triées (départ, ordre).

        ⚠️ **Ce n'est pas une séquence** : la liste renvoyée contient N suites 1..M concaténées, une
        par départ. La passer à `SequencePhases` lèverait `SequenceOrdreInvalide` — et c'est voulu.
        Elle sert aux vues **transverses** (supervision, complétude, suppression en cascade d'un
        tournoi), jamais au moteur, qui raisonne toujours dans un départ.
        """
        ...

    def enregistrer(self, phase: Phase) -> Phase:
        """Met à jour l'**avancement** d'une phase déjà persistée — son `statut`, et son rang.

        ⚠️ La définition portée par l'objet reçu est **ignorée** (voir l'avertissement du port) :
        elle s'édite sur l'étape, par `DerouleRepository`.
        """
        ...

    def reordonner(self, phases: list[Phase]) -> None:
        """Réécrit **en un bloc** le rang des phases d'un créneau (réalignement sur les étapes).

        Pendant de `DerouleRepository.reordonner`, même raison : l'unicité du rang par créneau
        refuse un décalage un à un. ⚠️ Le rang **est** la clé de jointure vers la définition
        (ADR-0076) — une phase laissée sur son ancien rang pointerait l'étape voisine, soit un
        changement de barème silencieux. D'où l'atomicité. `# DETTE-026`, 4ᵉ écrivain.
        """
        ...

    def supprimer(self, phase_id: PhaseId) -> None:
        """Supprime une phase persistée (retrait d'une phase de la séquence, E05US001)."""
        ...


class ScoreurRepository(Protocol):
    """Port de persistance des scoreurs — personnes habilitées à valider (E10US003).

    Entité **du tournoi** (comme `Depart`), d'où `par_tournoi`. Mais le `code` individuel est
    **unique dans toute la base** (`par_code` n'a pas de `tournoi_id`) : un scoreur ouvre sa session
    en tapant son seul code, sans désigner de tournoi — le code doit donc résoudre un scoreur sans
    ambiguïté d'un tournoi à l'autre.
    """

    def ajouter(self, scoreur: Scoreur) -> Scoreur:
        """Persiste un scoreur et le renvoie avec son identifiant attribué."""
        ...

    def par_id(self, scoreur_id: ScoreurId) -> Scoreur | None:
        """Renvoie le scoreur d'identifiant donné, ou `None` s'il n'existe pas."""
        ...

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Scoreur]:
        """Renvoie tous les scoreurs d'un tournoi (liste éventuellement vide).

        L'ordre n'est **pas** garanti par le port (détail de l'adapter) : un consommateur qui a
        besoin d'un ordre précis le trie lui-même (`ServiceScoreurs.lister` classe par nom).
        """
        ...

    def par_code(self, code: str) -> Scoreur | None:
        """Renvoie le scoreur portant ce `code` (au sens de `domain.scoreur.normaliser_code`), ou
        `None` — **tous tournois confondus**.

        Sert à ouvrir une session (connexion par code) et à refuser un code déjà attribué à la
        génération. La recherche est **globale** : le code est unique dans toute la base.
        """
        ...

    def enregistrer(self, scoreur: Scoreur) -> Scoreur:
        """Met à jour un scoreur déjà persisté (renommage ; le code est fixe) et le renvoie."""
        ...

    def supprimer(self, scoreur_id: ScoreurId) -> None:
        """Supprime le scoreur d'identifiant donné (existence garantie par l'appelant).

        **Feuille** : un scoreur n'a pas d'enfant en base (les validations tracées d'E10US005
        porteront son **nom**, pas une FK — la trace survit à sa suppression). Aucune cascade.
        """
        ...


class PosteRepository(Protocol):
    """Port de persistance des postes — credential d'un lieu (E04US001, ADR-0029 ; élargi E07US004).

    Entité **du tournoi**, mais le `code` est **unique dans toute la base** (`par_code` n'a pas de
    `tournoi_id`) : le rattachement se fait par le seul code, qui doit désigner un lieu sans
    ambiguïté d'un tournoi à l'autre. ⚠️ Un poste est de type **cible** ou **écran** (E07US004),
    d'où `par_tournoi_et_type` ; `supprimer` n'existe que pour les écrans, une cible existant tant
    que le plan de salle la porte.
    """

    def ajouter(self, poste: Poste) -> Poste:
        """Persiste un poste et le renvoie avec son identifiant attribué."""
        ...

    def par_id(self, poste_id: PosteId) -> Poste | None:
        """Renvoie le poste d'identifiant donné, ou `None` s'il n'existe pas."""
        ...

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Poste]:
        """Renvoie **tous** les postes d'un tournoi, cibles **et** écrans (liste éventuellement
        vide).

        ⚠️ Depuis E07US004, « tous » inclut les écrans : un appelant qui ne traite que des cibles
        passe par `par_tournoi_et_type`, sous peine de trier des écrans par numéro de cible
        inexistant. Le seul appelant légitime est la console de supervision.
        """
        ...

    def par_tournoi_et_type(self, tournoi_id: TournoiId, type_poste: TypePoste) -> list[Poste]:
        """Renvoie les postes d'un tournoi d'un **type** donné (liste éventuellement vide).

        Sert à la **préparation idempotente** des codes de cible (quelles cibles ont déjà un poste)
        et à l'énumération des écrans de salle. L'ordre n'est pas garanti par le port ; le service
        trie.
        """
        ...

    def enregistrer(self, poste: Poste) -> Poste:
        """Réécrit un poste existant (renommage ou déroulé d'un écran, E07US004).

        Ne touche ni au `code` ni au `type` : le code est imprimé sous un QR — le réécrire
        invaliderait une affiche déjà posée — et la nature d'un poste ne change pas, une cible ne
        devient pas un écran.
        """
        ...

    def supprimer(self, poste_id: PosteId) -> None:
        """Supprime un poste ; sans effet s'il n'existe pas.

        Réservé aux **écrans** (un écran se débranche et se retire), la garde étant portée par le
        service : une cible, elle, existe aussi longtemps que le plan de salle la porte, et son code
        est imprimé — le supprimer invaliderait un QR distribué.
        """
        ...

    def par_code(self, code: str) -> Poste | None:
        """Renvoie le poste portant ce `code` (au sens de `domain.poste.normaliser_code`), ou
        `None` — **tous tournois confondus**.

        Sert à rattacher (par code) et à refuser un code déjà attribué à la génération. Recherche
        **globale** : le code est unique dans toute la base.
        """
        ...


class RegistreConsignes(Protocol):
    """Port : **prises de contrôle** des écrans de salle (E07US004, ADR-0064) — volatil en mémoire.

    La consigne est **posée ici**, pas poussée à l'écran : le hub temps réel est mono-canal, et la
    **fin** d'une prise de contrôle naît du temps qui passe, qu'aucun événement serveur ne peut
    pousser (même raisonnement qu'ADR-0038 §4) — l'écran lit sa consigne et décompte lui-même.
    ⚠️ **En mémoire, comme les sessions de poste** : un redémarrage **libère** les écrans au lieu
    de les figer, ce qui est « jamais un état forcé qu'on oublie » appliqué à la panne.
    """

    def poser(self, poste_id: PosteId, prise: PriseDeControle) -> None:
        """Pose (ou remplace) la prise de contrôle d'un écran."""
        ...

    def prise_de(self, poste_id: PosteId) -> PriseDeControle | None:
        """Prise de contrôle en vigueur pour cet écran, ou `None`.

        **Ne juge pas l'expiration** : le registre ne lit pas l'heure, il stocke. C'est le service
        qui compare via `Horloge` et retire les prises échues.
        """
        ...

    def retirer(self, poste_id: PosteId) -> None:
        """Rend la main sur un écran ; sans effet s'il n'était pas sous consigne.

        Geste **volontaire** de l'admin : il efface ce qui est en place, quel qu'il soit.
        """
        ...

    def retirer_si(self, poste_id: PosteId, prise: PriseDeControle) -> None:
        """Retire la prise **seulement si c'est toujours celle-ci** ; sans effet sinon.

        Sert au nettoyage d'une prise **échue**, qui est un effet de bord de la lecture — donc non
        volontaire, donc obligé d'être prudent. Sans cette condition, la séquence « je lis une prise
        expirée, l'admin en repose une neuve, je retire » effacerait **la neuve** : une fenêtre
        étroite, mais qui s'ouvre précisément au moment où l'organisateur reprend la main sur un
        podium qui vient d'expirer, et la console poll en continu (correctif de revue E07US004).
        """
        ...

    def toutes(self) -> dict[PosteId, PriseDeControle]:
        """Toutes les prises en vigueur, par écran — la console en a besoin d'un coup."""
        ...


class RegistrePresence(Protocol):
    """Port : **présence des postes** par heartbeat (E12US001, ADR-0038) — état volatil en mémoire.

    Mémorise, par poste, **quand** il a été vu et **depuis quelle IP** ; le service en dérive
    *en ligne / hors ligne* en comparant au port `Horloge`. Effacé au redémarrage, comme le jeton
    de poste (ADR-0029). ⚠️ **Ce n'est pas** l'activité de saisie : « depuis combien de temps ça
    n'a pas *tiré* » se lit sur les séries (ADR-0038 §2).
    """

    def enregistrer(self, poste_id: PosteId, instant: datetime.datetime, ip: str | None) -> None:
        """Mémorise le heartbeat d'un poste (dernière vue + IP), en écrasant le précédent."""
        ...

    def derniere_activite(self, poste_id: PosteId) -> ActivitePoste | None:
        """Dernière présence signalée par ce poste, ou `None` s'il n'a jamais pingé."""
        ...

    def oublier(self, poste_id: PosteId) -> None:
        """Oublie la présence d'un poste (à sa révocation) ; sans effet s'il est absent."""
        ...


class GenerateurFeuilleDeMarque(Protocol):
    """Port de génération du **PDF de feuille de marque** (adapter fourni par l'infrastructure).

    Le domaine décrit le **contenu** (`FeuilleDeMarque`) ; l'adapter (ReportLab, ADR-0031) le rend
    en octets PDF. Le retour est un simple `bytes` : le domaine ne connaît ni ReportLab ni HTTP
    (règle 1). Un échec de rendu remonte en `InfrastructureError`, traduit en 500 à la frontière.
    """

    def generer(self, feuille: FeuilleDeMarque) -> bytes:
        """Rend la feuille de marque d'un départ en un document PDF (une page par archer placé)."""
        ...


class GenerateurDocumentsSalle(Protocol):
    """Port de génération des **PDF de préparation de salle** (E09US008 ; adapter d'infrastructure).

    Le domaine décrit le **contenu** (`EtiquettesCibles`, `CartesScoreurs`) ; l'adapter (ReportLab,
    ADR-0031) le rend en octets PDF, QR compris. Deux documents, deux méthodes : les étiquettes de
    cible (un QR par cible) et les cartes de scoreur (un papier par code). Le retour est un simple
    `bytes` : le domaine ne connaît ni ReportLab ni HTTP (règle 1). Un échec de rendu remonte en
    `InfrastructureError`, traduit en 500 à la frontière.
    """

    def etiquettes_cibles(self, document: EtiquettesCibles) -> bytes:
        """Rend les étiquettes de cible en un PDF (une page par cible : QR + code en clair)."""
        ...

    def cartes_scoreurs(self, document: CartesScoreurs) -> bytes:
        """Rend les cartes de scoreur en un PDF (un papier par scoreur : nom + code personnel)."""
        ...

    def qr_rattachement(self, url: str) -> bytes:
        """Rend un seul QR en **image SVG** (octets UTF-8) — cible ou scoreur. ⚠️ Le nom ment
        depuis E16US015 : un scoreur ouvre une **session** (DETTE-098).

        Ce QR s'affiche **à l'écran**, il n'est pas imprimé — d'où le **SVG**, net une fois agrandi
        et sans dépendance ajoutée (règle 11). `url` est **déjà composée** : le domaine ne sait pas
        la bâtir (règle 1), ce qui permet de réutiliser ce port sans en ajouter un second.
        """
        ...


class GenerateurListesImpression(Protocol):
    """Port de génération des **listes imprimables** d'organisation (E09US003 ; adapter infra).

    Le domaine décrit le **contenu** (`ListePlacement`, `ListeClubPaiement`) ; l'adapter (ReportLab,
    ADR-0031) le rend en octets PDF. Deux documents, deux méthodes : la liste de placement (accueil
    des archers) et la liste club & paiement (administratif). Le retour est un simple `bytes` : le
    domaine ne connaît ni ReportLab ni HTTP (règle 1). Un échec de rendu remonte en
    `InfrastructureError`, traduit en 500 à la frontière.
    """

    def placement(self, liste: ListePlacement) -> bytes:
        """Rend la liste de placement en un PDF (une ligne par archer placé)."""
        ...

    def club_paiement(self, liste: ListeClubPaiement) -> bytes:
        """Rend la liste club & paiement en un PDF (un bloc par club, avec totaux)."""
        ...


class GenerateurPalmares(Protocol):
    """Port de génération du **palmarès imprimable** (E06US004 ; adapter d'infrastructure).

    Le domaine décrit le contenu (`Palmares`), l'adapter (ReportLab, ADR-0031) le rend en octets.
    Une seule méthode : le palmarès **est** le document. `tournoi` est passé à part plutôt
    qu'enveloppé dans un objet « document » — le palmarès porte déjà tout son contenu ; les listes
    d'impression en ont un parce qu'elles portent, elles, des paramètres de composition.
    """

    def palmares(
        self,
        tournoi: str,
        *,
        complet: Palmares,
        affiche: Palmares,
        reglage: ReglagePodiums,
    ) -> bytes:
        """Rend le palmarès en un PDF (les podiums réglés + le classement).

        ⚠️ **Deux palmarès, et ce n'est pas une redondance** : les podiums se composent sur
        `complet`, le classement se tire d'`affiche` (restreint quand une catégorie est filtrée).
        Les confondre imprimait au mur un podium amputé (E16US014, bloquant de revue). ⚠️ **Passés
        par mot-clé** : deux `Palmares` positionnels s'inversent sans que mypy le voie.
        """
        ...


class Horloge(Protocol):
    """Port : la **source de temps** de l'application (règle 2 — un effet de bord derrière un port).

    Lire l'heure est un effet de bord : appeler `datetime.now()` directement dans un service le
    rendrait **non déterministe** en test (règle 9 : « pas d'horloge non maîtrisée »). Le journal
    d'audit horodate chaque entrée (« quand », E10US005) — première brique du projet à avoir besoin
    de l'heure —, d'où ce port, injecté dans `ServiceAudit`. L'adapter `HorlogeSysteme` lit
    l'horloge système ; un test injecte une horloge **figée**, et l'horodatage devient reproduit.
    """

    def maintenant(self) -> datetime.datetime:
        """Renvoie l'instant courant, en **UTC** (datetime *aware*)."""
        ...


class AuditRepository(Protocol):
    """Port de persistance du **journal d'audit métier** (E10US005).

    Journal **en ajout seul** : une trace ne se modifie ni ne se supprime — c'est l'équivalent
    numérique d'une signature de feuille de marque (FFTA B.6.1.1), la retoucher la viderait de sa
    valeur de preuve. D'où deux seules opérations : `consigner` (ajouter) et `par_tournoi`
    (consulter). Aucune FK d'auteur : l'entrée fige le **nom** de qui a agi (cf. `EntreeAudit`), la
    trace survit donc à la suppression du scoreur (E10US003).
    """

    def consigner(self, entree: EntreeAudit) -> EntreeAudit:
        """Persiste une entrée d'audit et la renvoie avec son identifiant attribué."""
        ...

    def par_tournoi(self, tournoi_id: TournoiId) -> list[EntreeAudit]:
        """Renvoie les entrées d'audit d'un tournoi, en **ordre chronologique** (id croissant).

        Liste éventuellement vide. L'ordre chronologique est **garanti par le port** (à rebours des
        autres `par_tournoi`, qui laissent le tri au service) : un journal se lit dans le sens du
        temps, c'est une propriété de l'audit, pas une préférence d'affichage.
        """
        ...


class RemboursementRepository(Protocol):
    """Port de persistance du **registre de remboursements** (E08US005, ADR-0057).

    ⚠️ Le registre n'est **pas** alimenté par ce port : ses lignes naissent **atomiquement** avec la
    suppression de l'inscription payée (`…supprimer_avec_remboursement(s)`). Ce port sert le
    **traitement** — lire, marquer « remboursé » ou « reporté » — et rien d'autre.
    `enregistrer_avec_trace` co-écrit statut **et** entrée d'audit en une transaction (ADR-0035) :
    un mouvement d'argent ne bascule jamais sans trace.
    """

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Remboursement]:
        """Renvoie les remboursements d'un tournoi (liste éventuellement vide).

        L'ordre n'est **pas** garanti par le port (le service trie pour l'affichage : les
        `à_rembourser` d'abord, puis par date).
        """
        ...

    def par_id(self, remboursement_id: RemboursementId) -> Remboursement | None:
        """Renvoie le remboursement d'identifiant donné, ou `None` s'il n'existe pas."""
        ...

    def enregistrer_avec_trace(
        self, remboursement: Remboursement, entree: EntreeAudit
    ) -> Remboursement:
        """Met à jour un remboursement traité **et** co-écrit sa trace `REMBOURSEMENT` (E08US005).

        Une seule transaction (ADR-0035) : le nouveau statut (`remboursé`/`reporté`, daté) et son
        entrée d'audit tiennent dans un « tout ou rien ». L'entrée arrive **déjà construite et
        datée** par le service (port `Horloge`). Existence garantie par l'appelant. Renvoie le
        remboursement mis à jour.
        """
        ...


class SerieRepository(Protocol):
    """Port de persistance des séries de saisie de qualification (E04US002).

    ⚠️ **Une série par `(phase, archer)`** depuis E05US025 (ADR-0082), et non plus par
    `(tournoi, archer)` : un déroulé peut enchaîner plusieurs qualifications, et les deux feuilles
    coexistent. Résorbe `DETTE-046`. `enregistrer` sert la saisie ordinaire ;
    `enregistrer_avec_trace` co-écrit la série **et** son audit en une seule transaction
    (ADR-0035) — la validation et la correction, elles, laissent une trace.
    """

    def par_archer(self, phase_id: PhaseId, archer_id: ArcherId) -> Serie | None:
        """La feuille de cet archer **dans cette phase**, ou `None` si elle n'existe pas encore.

        ⚠️ **Le 1ᵉʳ paramètre était `tournoi_id` jusqu'à E05US025, et rien ne le vérifie.** Le
        remplacer devait faire cesser de compiler les appelants restés à la maille tournoi ; le pari
        a échoué — `TournoiId` et `PhaseId` sont deux alias d'`int` (`DETTE-044`), et neuf sites ont
        été manqués en silence. La liste a été relevée à la main. **Ne pas se fier au compilateur
        ici** tant que `NewType("PhaseId", int)` n'existe pas : vérifier l'appelant.
        """
        ...

    def par_phase(self, phase_id: PhaseId) -> list[Serie]:
        """Toutes les feuilles d'une phase (liste éventuellement vide).

        Sert au **classement** (E06US001), qui se calcule phase par phase : les lire au tournoi
        mélangerait les deux tours de l'exemple d'ADR-0082 et rendrait un classement faux.

        L'ordre n'est pas garanti (le classement trie lui-même) ; les volées, si (`par_archer`).
        """
        ...

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Serie]:
        """Toutes les séries d'un tournoi, **toutes phases confondues** (éventuellement vide).

        ⚠️ **Vue d'ensemble, jamais base de calcul d'un classement.** Depuis E05US025 un archer peut
        y figurer plusieurs fois — une ligne par phase tirée. Un consommateur qui indexerait le
        résultat par `archer_id` (`{s.archer_id: s for s in …}`) n'en garderait qu'une **au hasard
        de l'ordre** : c'est `par_phase` qu'il lui faut.
        """
        ...

    def horodatages(self, phase_id: PhaseId, archer_id: ArcherId) -> dict[int, datetime.datetime]:
        """Le « quand » de chaque volée de l'archer, par **numéro** (`{}` s'il n'a pas de série).

        Le `created_at` d'une volée est une **métadonnée de persistance**, hors de l'agrégat `Volee`
        (arbitrage de revue E04US002) : ce port l'expose donc **à part** de `par_archer`, pour le
        chemin de lecture/consultation (« volée N saisie par … à HH:MM », ex-017). Instants **UTC**.
        """
        ...

    def enregistrer(self, serie: Serie) -> Serie:
        """Persiste une série (saisie sans trace) et la renvoie avec son identifiant attribué."""
        ...

    def enregistrer_avec_trace(self, serie: Serie, entree: EntreeAudit) -> Serie:
        """Persiste une série **et** son entrée d'audit dans **une seule transaction** (ADR-0035).

        Tout ou rien : jamais de validation/correction non tracée, jamais de trace fantôme. La
        série est renvoyée avec son identifiant attribué.
        """
        ...


class ForfaitRepository(Protocol):
    """Port de persistance des **forfaits** — abandon / disqualification (E04US015, ADR-0050).

    Un forfait par `(tournoi, archer, phase)`. Comme la série, les écritures co-écrivent une trace
    d'audit en **une seule transaction** (ADR-0035) : `declarer_avec_trace` et `annuler_avec_trace`
    (réversibilité, `D-15`). Les lectures servent le **classement** et le **rejeu des duels**.
    """

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Forfait]:
        """Renvoie tous les forfaits d'un tournoi (liste éventuellement vide, ordre non garanti)."""
        ...

    def par_phase(self, phase_id: PhaseId) -> list[Forfait]:
        """Renvoie les forfaits déclarés **dans une phase** (qualif ou tableau) — vide si aucun.

        Chemin de lecture des deux effets : le classement lit les forfaits de la **qualification**
        (relégation/exclusion), le rejeu des duels ceux de la **phase de tableau** (walkover).
        """
        ...

    def par_archer_et_phase(
        self, tournoi_id: TournoiId, archer_id: ArcherId, phase_id: PhaseId
    ) -> Forfait | None:
        """Le forfait de cet archer dans cette phase, ou `None` — pour la garde de doublon et
        l'annulation (retrouver la déclaration à supprimer)."""
        ...

    def declarer_avec_trace(self, forfait: Forfait, entree: EntreeAudit) -> Forfait:
        """Persiste un forfait **et** sa trace d'audit dans **une seule transaction** (ADR-0035).

        Tout ou rien : jamais de forfait non tracé, jamais de trace fantôme. Renvoie le forfait avec
        son identifiant attribué.
        """
        ...

    def annuler_avec_trace(self, forfait: Forfait, entree: EntreeAudit) -> None:
        """Supprime un forfait **et** consigne sa trace d'annulation dans **une seule transaction**.

        La réversibilité est une **suppression** de la déclaration (les flèches n'ont jamais été
        touchées), pas un drapeau. `forfait` porte l'`id` à supprimer (résolu par
        `par_archer_et_phase`). Tout ou rien : jamais d'annulation non tracée.
        """
        ...


class BarrageRepository(Protocol):
    """Port de persistance des **barrages de places** (E06US003, ADR-0066).

    Le grain d'écriture est la **manche**, pas la flèche : un barrage se tire en une fois, et
    enregistrer flèche par flèche exposerait une manche incomplète — donc un verdict provisoire.
    ⚠️ **Aucune méthode ne rend le verdict** : il se recalcule depuis les tirs
    (`BarrageDePlaces.resultat`). C'est ce qui rend une flèche mal saisie corrigeable ; l'exposer
    inviterait à le mémoriser, donc à créer une seconde vérité périmée dès le premier correctif.
    """

    def par_depart(self, depart_id: DepartId) -> list[BarrageDePlaces]:
        """Tous les barrages **d'un départ**, clos compris (liste éventuellement vide).

        Les **clos** sont rendus : ce sont eux qui portent les verdicts déjà appliqués au
        classement, et les filtrer ferait retomber les rangs tranchés en ex æquo.

        ⚠️ D'un **départ** depuis E01US025 (ADR-0075). Renommé comme `PhaseRepository.par_depart` :
        les deux identifiants étant des alias d'`int`, garder le nom laissait l'appelant faux.
        """
        ...

    def par_tournoi(self, tournoi_id: TournoiId) -> list[BarrageDePlaces]:
        """Les barrages de **tous les départs** d'un tournoi (vue transverse, jointure).

        Comme `PhaseRepository.par_tournoi` : réservée aux lectures d'ensemble, jamais au moteur,
        qui raisonne toujours dans un départ.
        """
        ...

    def par_id(self, barrage_id: BarrageId) -> BarrageDePlaces | None:
        """Le barrage d'identifiant donné, avec toutes ses manches, ou `None`."""
        ...

    def ouvrir(self, barrage: BarrageDePlaces) -> BarrageDePlaces:
        """Persiste un barrage **annoncé** (sans tir) et renvoie l'agrégat avec son identifiant."""
        ...

    def enregistrer_manche(
        self, barrage_id: BarrageId, manche: int, tirs: Sequence[TirBarrage]
    ) -> BarrageDePlaces:
        """Écrit les tirs d'une manche, en **remplaçant** ceux déjà saisis pour ce numéro.

        Le remplacement est le mode de **correction** : ressaisir la manche 2 corrige une flèche mal
        notée, et le verdict s'en déduit à nouveau. Renvoie le barrage rechargé.
        """
        ...

    def supprimer(self, barrage_id: BarrageId) -> None:
        """Supprime un barrage **et ses tirs** (annonce erronée — E06US003).

        Porte de sortie indispensable : `clore` exige un barrage **résolu**, donc un barrage qu'on
        ne veut pas faire tirer ne pourrait jamais quitter l'écran, et son rang bloquerait toute
        nouvelle annonce.
        """
        ...

    def clore(self, barrage_id: BarrageId) -> BarrageDePlaces:
        """Marque le barrage comme clos — le juge a acté le verdict, plus de retir attendu."""
        ...

    def rouvrir(self, barrage_id: BarrageId) -> BarrageDePlaces:
        """Lève la clôture — une manche vient d'être saisie, le verdict acté n'est plus le bon."""
        ...


class FranchissementArretRepository(Protocol):
    """Port de persistance des **franchissements d'arrêt** — ce qu'un arrêt a coupé (E05US033).

    ⚠️ **Ce port ne persiste pas les arrêts eux-mêmes** (ADR-0091) : leur *définition* vit sur
    l'`EtapeDeroule` du tournoi, servie par `DerouleRepository`. Ce port-ci ne porte que
    l'**avancement** — cet arrêt-là a-t-il coupé dans ce créneau, et l'admin l'a-t-il relevé. C'est
    le seul état **persisté** du mécanisme (ADR-0090 §5) : la condition étant monotone, un
    déclencheur sans mémoire remettrait la phase en pause à chaque reprise.
    """

    def par_depart(self, depart_id: DepartId) -> list[FranchissementArret]:
        """Tous les franchissements du créneau, quel qu'en soit l'état (liste possiblement vide)."""
        ...

    def par_id(self, franchissement_id: int) -> FranchissementArret | None:
        """Le franchissement d'identifiant donné, ou `None` s'il n'existe pas."""
        ...

    def ajouter(self, franchissement: FranchissementArret) -> FranchissementArret:
        """Persiste un franchissement et le renvoie avec son identifiant attribué."""
        ...

    def enregistrer(self, franchissement: FranchissementArret) -> FranchissementArret:
        """Réécrit un franchissement existant (existence garantie par l'appelant)."""
        ...


class ArretDeCirconstanceRepository(Protocol):
    """Port de persistance des **arrêts posés le jour J**, propres à un créneau (E05US034).

    ⚠️ Troisième port du mécanisme (ADR-0092) : `DerouleRepository` sert les arrêts **programmés
    à l'atelier** (portés par le tournoi, rejoués par tous ses créneaux) et **celui-ci** ceux
    **décidés dans la journée** (portés par le départ, rejoués par personne) — les confondre ferait
    rejouer l'après-midi une pause du matin. Pas de `retirer` : l'arrêt tombe, l'organisateur
    relance. `# DETTE-075` — aucune route ne rend les arrêts **posés**.
    """

    def par_depart(self, depart_id: DepartId) -> list[ArretDeCirconstance]:
        """Les arrêts de circonstance de **ce créneau seul** (liste possiblement vide).

        Le filtrage par créneau est la propriété que ce port existe pour tenir : un adapter qui
        rendrait tout le tournoi rendrait le concept indistinguable d'un arrêt programmé.
        """
        ...

    def ajouter(self, arret: ArretDeCirconstance) -> ArretDeCirconstance:
        """Persiste un arrêt de circonstance et le renvoie avec son identifiant attribué.

        ⚠️ **Lève `ArretProgrammeInvalide` (domaine) si un arrêt occupe déjà ce tour** — c'est au
        contrat. L'unicité `(depart_id, phase_id, apres_tour)` est tenue par le **schéma** parce que
        la pose est concurrente : le service refuse le doublon qu'il *voit*, la contrainte ferme la
        **course**. Le refus est **métier** dans les deux cas (`doublon_d_arret`, 422), jamais un
        500. ⚠️ Une doublure de test doit honorer ce `raise` : la course n'a pas d'autre oracle.
        """
        ...


class IdentiteVisuelleRepository(Protocol):
    """Port de persistance de l'identité visuelle d'un tournoi (E16US006, adapter en infra).

    ⚠️ **Trois méthodes de lecture et non une, à dessein** : les réglages pèsent quelques octets et
    sont lus à chaque affichage public, les octets d'un logo jusqu'à 512 Ko et seulement par la
    balise `<img>` — tout rendre d'un bloc ferait traîner les blobs au chemin chaud.
    **L'absence de réglage est un état normal** : `reglages` rend des accents à `None`, et c'est
    l'agrégat qui sait que cela veut dire « celle du club ». L'adapter ne fabrique aucun défaut.
    """

    def reglages(self, tournoi_id: TournoiId) -> IdentiteVisuelle:
        """Renvoie les accents et la présence des logos ; l'identité **vide** si rien n'existe.

        **Ne lit pas les octets des logos** — seulement s'ils existent. Ne rend jamais `None` : un
        tournoi a toujours une identité, éventuellement entièrement héritée.
        """
        ...

    def logo(self, tournoi_id: TournoiId, emplacement: EmplacementLogo) -> Logo | None:
        """Renvoie les octets et le format d'un logo, ou `None` si cet emplacement est vide."""
        ...

    def empreinte_du_logo(self, tournoi_id: TournoiId, emplacement: EmplacementLogo) -> str | None:
        """Renvoie la seule **empreinte** d'un logo, ou `None` si l'emplacement est vide.

        ⚠️ **Une quatrième méthode, et pour une raison précise** : la route qui sert les octets
        répond `304` la plupart du temps (`no-cache` impose une revalidation, que l'écran de salle
        et trente tablettes déclenchent en boucle). Sans cette lecture il fallait charger les
        512 Ko pour calculer l'`ETag`, annulant la projection sans blob sur la route la plus
        chaude. C'est aussi la seule source de version : `ETag` et `?v=` sortent d'ici.
        """
        ...

    def enregistrer_accents(
        self, tournoi_id: TournoiId, identite: IdentiteVisuelle
    ) -> IdentiteVisuelle:
        """Écrit les deux accents, en créant la ligne d'identité si elle n'existe pas.

        **Ne touche à aucun logo** : régler une couleur ne doit pas effacer un fichier déposé.
        Renvoie l'identité relue, présence des logos comprise.
        """
        ...

    def enregistrer_logo(
        self, tournoi_id: TournoiId, emplacement: EmplacementLogo, logo: Logo | None
    ) -> IdentiteVisuelle:
        """Remplace (ou efface, si `logo is None`) un emplacement, en créant la ligne au besoin.

        **Ne touche ni aux accents ni à l'autre emplacement** : le CA d'E16US006 dit « un champ *de
        plus* », donc déposer le logo du club ne remplace pas celui de l'événement. Renvoie
        l'identité relue.
        """
        ...
