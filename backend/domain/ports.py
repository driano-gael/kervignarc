"""Ports du domaine — interfaces implémentées par des adapters d'infrastructure (ADR-0003).

Le domaine définit *ce dont il a besoin* (persister, relire) sans savoir *comment*.
`Protocol` : conformité **structurelle**, sans imposer d'héritage aux adapters — le
domaine reste pur (aucune dépendance vers l'infrastructure).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from domain.archer import Archer, ArcherId
from domain.blason import Blason, BlasonId
from domain.categorie import Categorie, CategorieId
from domain.club import Club, ClubId
from domain.depart import Depart, DepartId
from domain.documents_salle import CartesScoreurs, EtiquettesCibles
from domain.feuille_marque import FeuilleDeMarque
from domain.gabarit_salle import GabaritSalle, GabaritSalleId
from domain.inscription import Inscription, InscriptionId
from domain.phase import Phase, PhaseId, TypePhase
from domain.placement import Affectation
from domain.poste import Poste, PosteId
from domain.score import Score
from domain.scoreur import Scoreur, ScoreurId
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

    def enregistrer(self, archer: Archer) -> Archer:
        """Met à jour un archer déjà persisté (placement, édition E02US003) et le renvoie."""
        ...

    def supprimer(self, archer_id: ArcherId) -> None:
        """Supprime l'archer d'identifiant donné, **ses scores et ses inscriptions** (E02US003,
        E02US009).

        Existence garantie par l'appelant. La purge des scores **et des inscriptions sur départs**
        (E02US009) fait partie du contrat : elle n'est pas un effet de bord, c'est la seule façon de
        tenir la promesse « l'archer disparaît » — `score.archer_id` **et** `inscription.archer_id`
        sont des FK **sans `ON DELETE`** (DETTE-001), donc une suppression qui les laisserait
        derrière elle échouerait en base. Cascade **applicative et maîtrisée**, à faire dans **une
        seule transaction** : deux transactions successives laisseraient, en cas d'échec de la
        seconde, un archer dépouillé de ses flèches.

        L'appelant a **déjà** obtenu la confirmation de l'admin si l'archer était placé ou
        engagé (`ArcherEngage`) : à ce niveau, la décision est prise et les données sont
        perdues volontairement. Un archer qui **abandonne** ne passe pas par ici — c'est un
        forfait tracé (E12US004), qui préserve ses flèches.
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
        """Supprime le départ d'identifiant donné **et ses inscriptions** (E02US009).

        Existence garantie par l'appelant, qui a **déjà** obtenu la confirmation de l'admin si le
        départ portait des inscriptions (`DepartAvecInscriptions`). La purge des inscriptions fait
        partie du contrat, dans **une seule transaction** : `inscription.depart_id` est une FK
        **sans `ON DELETE`** (DETTE-001), donc une suppression qui les laisserait échouerait.
        Même patron que `ArcherRepository.supprimer` avec les scores — cascade **applicative et
        maîtrisée**.
        """
        ...


class InscriptionRepository(Protocol):
    """Port de persistance des inscriptions — liens archer ↔ départ (E02US009, ADR-0017)."""

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
        """Met à jour une inscription déjà persistée (bascule de `paye`) et la renvoie."""
        ...

    def supprimer(self, inscription_id: InscriptionId) -> None:
        """Supprime l'inscription d'identifiant donné (désinscription ; existence garantie)."""
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

    def enregistrer(self, blason: Blason) -> Blason:
        """Met à jour un blason déjà persisté (édition) et le renvoie."""
        ...

    def supprimer(self, blason_id: BlasonId) -> None:
        """Supprime le blason d'identifiant donné (existence garantie par l'appelant)."""
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


class PhaseRepository(Protocol):
    """Port de persistance des phases (adapter fourni par l'infrastructure).

    Introduction minimale (E01US009 / ADR-0011) : n'est exercé que pour la phase de
    `qualification` d'un tournoi, qui porte le barème.
    """

    def ajouter(self, phase: Phase) -> Phase:
        """Persiste une phase et la renvoie avec son identifiant attribué."""
        ...

    def par_id(self, phase_id: PhaseId) -> Phase | None:
        """Renvoie la phase d'identifiant donné, ou `None` si elle n'existe pas."""
        ...

    def par_tournoi_et_type(self, tournoi_id: TournoiId, type_phase: TypePhase) -> Phase | None:
        """Renvoie la phase d'un tournoi pour un type donné, ou `None` s'il n'y en a pas.

        En E01US009, un tournoi porte **au plus une** phase de `qualification`.
        """
        ...

    def enregistrer(self, phase: Phase) -> Phase:
        """Met à jour une phase déjà persistée (édition du barème) et la renvoie."""
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
    """Port de persistance des postes de cible — credential d'une cible (E04US001, ADR-0029).

    Entité **du tournoi** (`par_tournoi` énumère les postes d'un plan), mais le `code` de cible est
    **unique dans toute la base** (`par_code` n'a pas de `tournoi_id`) : le rattachement se fait par
    le seul code (scan/saisie), qui doit désigner une cible sans ambiguïté d'un tournoi à l'autre.
    E04US001 n'expose ni `enregistrer` ni `supprimer` : la régénération d'un code relève d'E09US008.
    """

    def ajouter(self, poste: Poste) -> Poste:
        """Persiste un poste et le renvoie avec son identifiant attribué."""
        ...

    def par_id(self, poste_id: PosteId) -> Poste | None:
        """Renvoie le poste d'identifiant donné, ou `None` s'il n'existe pas."""
        ...

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Poste]:
        """Renvoie tous les postes d'un tournoi (liste éventuellement vide).

        Sert à la **préparation idempotente** des codes (quelles cibles ont déjà un poste). L'ordre
        n'est pas garanti par le port ; le service trie par numéro de cible.
        """
        ...

    def par_code(self, code: str) -> Poste | None:
        """Renvoie le poste portant ce `code` (au sens de `domain.poste.normaliser_code`), ou
        `None` — **tous tournois confondus**.

        Sert à rattacher (par code) et à refuser un code déjà attribué à la génération. Recherche
        **globale** : le code est unique dans toute la base.
        """
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
