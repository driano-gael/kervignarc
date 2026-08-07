"""Adapters repository SQLAlchemy — le **patrimoine et la configuration**

Tournoi, archers, clubs, départs, inscriptions, catégories, blasons, gabarits de salle,
remboursements.

Découpé de l'ancien `repositories.py` (3 378 lignes, 21 adapters) par l'action 2 de
[l'audit de maintenabilité](../../../../docs/audit-maintenabilite.md) : le fichier unique
figurait parmi les onze « passages obligés » du dépôt. Le contenu n'a pas bougé d'un
caractère ; seuls les imports inutiles ont été élagués.

Chaque opération ouvre une **session courte** (ADR-0005) et traduit les lignes ORM en agrégats
de domaine. Les pannes SQLAlchemy sont **enveloppées** en `InfrastructureError` — le domaine ne
voit jamais d'exception brute."""

from __future__ import annotations

import datetime
import json
from collections.abc import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy import true as sa_true
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from domain.archer import Archer, ArcherId
from domain.blason import Blason, BlasonId, valider_zones
from domain.categorie import Categorie, CategorieId, SexeCategorie, TrancheAge
from domain.cloisonnement import Cloisonnement
from domain.club import Club, ClubId, cle_nom
from domain.depart import Depart, DepartId
from domain.entree_audit import EntreeAudit
from domain.erreurs import DomainError
from domain.gabarit_salle import GabaritSalle, GabaritSalleId
from domain.inscription import Inscription, InscriptionId
from domain.patrimoine import OrigineBrique
from domain.remboursement import (
    MotifRemboursement,
    Remboursement,
    RemboursementId,
    StatutRemboursement,
)
from domain.tournoi import StatutTournoi, Tournoi, TournoiId, TypeTournoi
from infrastructure.db.models import (
    ArcherORM,
    BarrageORM,
    BarrageTirORM,
    BlasonORM,
    CategorieORM,
    ClubORM,
    DepartORM,
    ForfaitORM,
    GabaritSalleORM,
    InscriptionORM,
    PhaseORM,
    RemboursementORM,
    ScoreORM,
    SerieORM,
    TournoiORM,
)
from infrastructure.db.repositories._mapping import _vers_barrage

# `AuditRepositorySQL` vit dans le thème `exploitation` mais s'annote ici : plusieurs
# adapters **co-écrivent** leur trace d'audit dans la même transaction (ADR-0035). Import
# direct et acyclique — `exploitation` n'importe aucun autre thème.
from infrastructure.db.repositories.exploitation import AuditRepositorySQL
from infrastructure.erreurs import InfrastructureError


def _purger_descendance_du_depart(session: Session, depart_id: DepartId) -> None:
    """Supprime ce qui pend au créneau **avant** lui — cascade applicative maîtrisée (DETTE-001).

    ⚠️ **Élargi par E01US025** (ADR-0075) : le départ est devenu la portée **sportive**, donc
    `phase.depart_id` et `barrage.depart_id` sont des FK **sans `ON DELETE`** qui n'existaient pas
    avant. Sans cette purge, supprimer un créneau d'un tournoi configuré partait en `IntegrityError`
    → 500, à la place des refus typés que le service arbitre (`DepartAvecInscriptions`,
    `DepartEnCoursNonConfirme`, `DernierDepartNonSupprimable`). Défaut relevé en revue.

    L'ordre suit les dépendances : `barrage_tir` → `barrage` → `phase` → `inscription`. Ce qui pend
    à la **phase** (plan de duels, duels, forfaits) porte `ON DELETE CASCADE` et part avec elle ;
    `placement` porte la même cascade depuis le départ. On ne supprime donc à la main que ce que le
    schéma ne sait pas emporter.
    """
    barrages = select(BarrageORM.id).where(BarrageORM.depart_id == depart_id)
    session.execute(delete(BarrageTirORM).where(BarrageTirORM.barrage_id.in_(barrages)))
    session.execute(delete(BarrageORM).where(BarrageORM.depart_id == depart_id))
    session.execute(delete(PhaseORM).where(PhaseORM.depart_id == depart_id))
    session.execute(delete(InscriptionORM).where(InscriptionORM.depart_id == depart_id))


def _vers_tournoi(ligne: TournoiORM) -> Tournoi:
    """Traduit une ligne ORM en agrégat de domaine `Tournoi`.

    Même régime qu'`_vers_format` : le repository est le **seul** rédacteur de ces colonnes et n'y
    écrit que des valeurs valides, donc une ligne que le domaine refuse est une incohérence
    **technique** → `InfrastructureError`, pas une `DomainError` nue qui traverserait l'infra
    (E05US021 ; `Tournoi.__post_init__` peut désormais lever). Sans cette enveloppe, une seule
    ligne éditée à la main rendait `GET /tournois` inutilisable en 500 non typé.
    """
    try:
        return Tournoi(
            nom=ligne.nom,
            date=ligne.date,
            lieu=ligne.lieu,
            type_tournoi=TypeTournoi(ligne.type_tournoi),
            statut=StatutTournoi(ligne.statut),
            effectif_minimum_exige=ligne.effectif_minimum_exige,
            cloisonnement=Cloisonnement(ligne.cloisonnement),
            id=ligne.id,
        )
    except (DomainError, ValueError) as exc:
        raise InfrastructureError(
            f"Tournoi {ligne.id} illisible : une valeur en base viole une règle du domaine."
        ) from exc


def _vers_archer(ligne: ArcherORM) -> Archer:
    """Traduit une ligne ORM en agrégat de domaine `Archer`."""
    return Archer(
        nom=ligne.nom,
        prenom=ligne.prenom,
        tournoi_id=ligne.tournoi_id,
        categorie_id=ligne.categorie_id,
        cible=ligne.cible,
        club_id=ligne.club_id,
        handicap_officiel=ligne.handicap_officiel,
        handicap_surcharge=ligne.handicap_surcharge,
        id=ligne.id,
    )


def _vers_club(ligne: ClubORM) -> Club:
    """Traduit une ligne ORM en agrégat de domaine `Club`."""
    return Club(nom=ligne.nom, id=ligne.id)


def _vers_depart(ligne: DepartORM) -> Depart:
    """Traduit une ligne ORM en agrégat de domaine `Depart` (E02US004)."""
    return Depart(
        tournoi_id=ligne.tournoi_id,
        numero=ligne.numero,
        tarif_centimes=ligne.tarif_centimes,
        horaire=ligne.horaire,
        quota=ligne.quota,
        id=ligne.id,
    )


def _vers_inscription(ligne: InscriptionORM) -> Inscription:
    """Traduit une ligne ORM en agrégat de domaine `Inscription` (E02US009)."""
    return Inscription(
        archer_id=ligne.archer_id,
        depart_id=ligne.depart_id,
        paye=ligne.paye,
        id=ligne.id,
    )


def _vers_blason(ligne: BlasonORM) -> Blason:
    """Traduit une ligne ORM en agrégat de domaine `Blason`.

    `zones` est écrit par le repository comme un tableau JSON de valeurs de score (E01US014). Un
    contenu illisible, **ou lisible mais hors règle**, est une **incohérence technique** (le
    repository en est le seul rédacteur, il écrit toujours un jeu valide) → enveloppée en
    `InfrastructureError` (ADR-0007), jamais laissée fuir en agrégat silencieusement invalide.

    On **rejoue `valider_zones`** plutôt que de se contenter d'une coercition `ZoneScore(...)`,
    pour la même raison que `_vers_phase` repasse par `BaremeQualification.creer` : la coercition
    seule ne voit que le vocabulaire, pas la structure. Un `'{"10": 1}'` en base réhydraterait
    `('10',)` — clés d'un objet JSON, vocabulaire valide, mais **sans `M`** — c'est-à-dire un
    blason hors invariant, qui piloterait le pavé d'EPIC-04 sans qu'aucune erreur ne soit levée.
    """
    try:
        zones = valider_zones(json.loads(ligne.zones))
    except (json.JSONDecodeError, TypeError, ValueError, DomainError) as exc:
        raise InfrastructureError("Zones de blason illisibles.") from exc
    return Blason(
        tournoi_id=ligne.tournoi_id,
        origine=OrigineBrique(ligne.origine),
        nom=ligne.nom,
        taille=ligne.taille,
        capacite=ligne.capacite,
        zones=zones,
        id=ligne.id,
    )


def _vers_gabarit(ligne: GabaritSalleORM) -> GabaritSalle:
    """Traduit une ligne ORM en agrégat de domaine `GabaritSalle` (config JSON → tuple).

    Une `config` illisible ou d'un format inattendu est une **incohérence technique** (le
    repository est le seul rédacteur et écrit toujours un JSON valide) : elle est enveloppée en
    `InfrastructureError` — jamais laissée fuir en traceback brut à la frontière (ADR-0007).
    """
    try:
        capacites = tuple(int(c) for c in json.loads(ligne.config)["capacites"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise InfrastructureError("Configuration de gabarit de salle illisible.") from exc
    return GabaritSalle(
        nom=ligne.nom, capacites=capacites, id=ligne.id, tournoi_id=ligne.tournoi_id
    )


def _config_gabarit(gabarit: GabaritSalle) -> str:
    """Sérialise le plafond par cible d'un gabarit en JSON (`{"capacites": [...]}`)."""
    return json.dumps({"capacites": list(gabarit.capacites)})


def _vers_categorie(ligne: CategorieORM) -> Categorie:
    """Traduit une ligne ORM en agrégat de domaine `Categorie` (ages JSON → tuple de `TrancheAge`).

    `ages` est écrit par le repository comme un tableau JSON de codes de tranche (E01US013). Un
    contenu illisible ou une valeur hors des huit tranches FFTA est une **incohérence technique**
    (le repository en est le seul rédacteur, il écrit toujours des codes valides) → enveloppée en
    `InfrastructureError` (ADR-0007), jamais laissée fuir en value object silencieusement invalide.
    """
    try:
        ages = tuple(TrancheAge(code) for code in json.loads(ligne.ages))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise InfrastructureError("Tranches d'âge de catégorie illisibles.") from exc
    return Categorie(
        tournoi_id=ligne.tournoi_id,
        origine=OrigineBrique(ligne.origine),
        libelle=ligne.libelle,
        arme=ligne.arme,
        ages=ages,
        sexe=None if ligne.sexe is None else SexeCategorie(ligne.sexe),
        blason_id=ligne.blason_id,
        hauteur_cm=ligne.hauteur_cm,
        id=ligne.id,
    )


def _ages_categorie(categorie: Categorie) -> str:
    """Sérialise les tranches d'âge en tableau JSON de codes (ex. `["U15","U18"]`)."""
    return json.dumps([tranche.value for tranche in categorie.ages])


class TournoiRepositorySQL:
    """Adapter SQLite du port `TournoiRepository`."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, tournoi: Tournoi) -> Tournoi:
        """Persiste le tournoi et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = TournoiORM(
                    nom=tournoi.nom,
                    date=tournoi.date,
                    lieu=tournoi.lieu,
                    type_tournoi=tournoi.type_tournoi.value,
                    statut=tournoi.statut.value,
                    effectif_minimum_exige=tournoi.effectif_minimum_exige,
                    cloisonnement=tournoi.cloisonnement.value,
                )
                session.add(ligne)
                session.commit()
                return _vers_tournoi(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du tournoi.") from exc

    def par_id(self, tournoi_id: TournoiId) -> Tournoi | None:
        """Relit le tournoi d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(TournoiORM, tournoi_id)
                return None if ligne is None else _vers_tournoi(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du tournoi.") from exc

    def lister(self) -> list[Tournoi]:
        """Renvoie tous les tournois, du plus récent au plus ancien (par identifiant)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(TournoiORM).order_by(TournoiORM.id.desc())
                ).scalars()
                return [_vers_tournoi(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des tournois.") from exc

    def enregistrer(self, tournoi: Tournoi) -> Tournoi:
        """Met à jour un tournoi déjà persisté (édition, transition de statut) et le renvoie.

        **Contrat** : l'appelant (le service) garantit l'existence du tournoi (vérifiée en
        amont). La ligne absente est donc une **incohérence technique**, non un cas métier
        — d'où `InfrastructureError` (et non une erreur applicative « 404 »).
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(TournoiORM, tournoi.id)
                if ligne is None:
                    raise InfrastructureError("Tournoi à mettre à jour introuvable en base.")
                ligne.nom = tournoi.nom
                ligne.date = tournoi.date
                ligne.lieu = tournoi.lieu
                ligne.type_tournoi = tournoi.type_tournoi.value
                ligne.statut = tournoi.statut.value
                ligne.effectif_minimum_exige = tournoi.effectif_minimum_exige
                ligne.cloisonnement = tournoi.cloisonnement.value
                session.commit()
                return _vers_tournoi(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour du tournoi.") from exc

    def supprimer(self, tournoi_id: TournoiId) -> None:
        """Supprime le tournoi d'identifiant donné (existence garantie par l'appelant)."""
        try:
            with self._session_factory() as session:
                ligne = session.get(TournoiORM, tournoi_id)
                if ligne is None:
                    raise InfrastructureError("Tournoi à supprimer introuvable en base.")
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression du tournoi.") from exc


class ArcherRepositorySQL:
    """Adapter SQLite du port `ArcherRepository` (E00US011, E02US003)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, archer: Archer) -> Archer:
        """Persiste l'archer et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = ArcherORM(
                    tournoi_id=archer.tournoi_id,
                    nom=archer.nom,
                    prenom=archer.prenom,
                    categorie_id=archer.categorie_id,
                    cible=archer.cible,
                    club_id=archer.club_id,
                    handicap_officiel=archer.handicap_officiel,
                    handicap_surcharge=archer.handicap_surcharge,
                )
                session.add(ligne)
                session.commit()
                return _vers_archer(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance de l'archer.") from exc

    def par_id(self, archer_id: ArcherId) -> Archer | None:
        """Relit l'archer d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(ArcherORM, archer_id)
                return None if ligne is None else _vers_archer(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de l'archer.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Archer]:
        """Renvoie tous les archers d'un tournoi (liste éventuellement vide)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(ArcherORM).where(ArcherORM.tournoi_id == tournoi_id)
                ).scalars()
                return [_vers_archer(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des archers du tournoi.") from exc

    def par_club(self, club_id: ClubId) -> list[Archer]:
        """Renvoie les archers rattachés à un club, **tous tournois confondus** (E02US001)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(ArcherORM).where(ArcherORM.club_id == club_id).order_by(ArcherORM.id)
                ).scalars()
                return [_vers_archer(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des archers du club.") from exc

    def enregistrer(self, archer: Archer) -> Archer:
        """Met à jour un archer déjà persisté (placement E00US011, édition E02US003).

        **Contrat** : l'appelant (le service applicatif) garantit l'existence de l'archer
        (vérifiée en amont). La ligne absente est donc une **incohérence technique**, non
        un cas métier — d'où `InfrastructureError` (et non une erreur applicative « 404 »).
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(ArcherORM, archer.id)
                if ligne is None:
                    raise InfrastructureError("Archer à mettre à jour introuvable en base.")
                # Tous les champs mutables sont recopiés, et ils ont désormais **deux** appelants
                # aux besoins disjoints : `nom`/`prenom`/`categorie_id`/`club_id` sont ceux de
                # l'édition (E02US003), `cible` celui du placement (E00US011). Un `enregistrer`
                # partiel perdrait donc l'un ou l'autre en silence — le genre d'oubli qui ne se
                # voit qu'en base, longtemps après.
                ligne.nom = archer.nom
                ligne.prenom = archer.prenom
                ligne.categorie_id = archer.categorie_id
                ligne.cible = archer.cible
                ligne.club_id = archer.club_id
                # E05US015 : les deux handicaps rejoignent la liste, pour la raison exacte que le
                # commentaire ci-dessus annonce — un `enregistrer` partiel les perdrait dès qu'un
                # appelant enregistre pour une autre raison (un placement effacerait le handicap).
                ligne.handicap_officiel = archer.handicap_officiel
                ligne.handicap_surcharge = archer.handicap_surcharge
                session.commit()
                return _vers_archer(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour de l'archer.") from exc

    def supprimer(self, archer_id: ArcherId) -> None:
        """Supprime l'archer, **ses scores, ses inscriptions, sa série de saisie et ses forfaits**
        (E02US003, E02US009, E04US002, E04US015).

        **Contrat** (même que `enregistrer`) : l'existence est garantie par le service ; une ligne
        absente est une incohérence technique, pas un 404. Le service a par ailleurs déjà obtenu
        la confirmation de l'admin si l'archer était placé, engagé ou inscrit (`ArcherEngage`) :
        ici, la destruction est voulue.

        **Une seule transaction** pour tous les `DELETE`, dans cet ordre : `score.archer_id`,
        `inscription.archer_id`, `serie.archer_id` **et** `forfait.archer_id` sont des FK **sans
        `ON DELETE`** (DETTE-001), donc supprimer l'archer d'abord échouerait. `serie` (E04US002) et
        `forfait` (E04US015) sont des enfants de plus : les retirer ici étend la **cascade
        applicative maîtrisée** (qui manque au reste de la descendance de `tournoi` — DETTE-001). Le
        `forfait` **doit** être purgé ici, pas seulement « assumé en dette » : sa FK est *enforced*
        (`PRAGMA foreign_keys=ON`), une ligne orpheline ferait échouer la suppression (500, archer
        indéracinable — trouvé en revue adversariale). Les **volées** de la série suivent
        automatiquement (`volee.serie_id` est `ON DELETE CASCADE` — composant strict de l'agrégat) :
        le `DELETE` de la série déclenche la cascade SQLite. Deux transactions successives
        laisseraient, si la seconde échouait, un archer à demi dépouillé — un état que personne n'a
        demandé.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(ArcherORM, archer_id)
                if ligne is None:
                    raise InfrastructureError("Archer à supprimer introuvable en base.")
                session.execute(delete(ScoreORM).where(ScoreORM.archer_id == archer_id))
                session.execute(delete(InscriptionORM).where(InscriptionORM.archer_id == archer_id))
                # `serie` (E04US002) : `DELETE` SQL, donc la cascade `volee` (ON DELETE CASCADE)
                # s'applique au niveau base — contrairement à un `session.delete` ORM.
                session.execute(delete(SerieORM).where(SerieORM.archer_id == archer_id))
                # `forfait` (E04US015) : même cascade applicative que `serie` — FK enforced, sinon
                # une ligne orpheline bloque la suppression (revue adversariale E04US015).
                session.execute(delete(ForfaitORM).where(ForfaitORM.archer_id == archer_id))
                # `barrage_tir` (E06US003) : **exactement le même piège que `forfait`**, rejoué sur
                # une table neuve — FK enforced, archer indéracinable sans ce nettoyage. On supprime
                # le **barrage entier**, pas seulement les tirs : un barrage amputé d'un de ses
                # tireurs annoncés n'a plus de sens et serait refusé à la relecture (la manche 1
                # doit couvrir tous les participants). D'où la lecture de `participants_json` — un
                # archer peut être *annoncé* sans avoir encore tiré, donc sans ligne de tir.
                _supprimer_barrages_de_l_archer(session, archer_id)
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression de l'archer.") from exc

    def fusionner(self, gagnant_id: ArcherId, perdant_id: ArcherId) -> None:
        """Réassigne la descendance du perdant au gagnant, puis supprime le perdant (E02US005).

        **Miroir de `supprimer`** : mêmes FK sans `ON DELETE` (DETTE-001), même transaction unique,
        mais on **réattribue** au lieu de purger. Tout en instructions **Core** (`update`/`delete`),
        comme `supprimer` : une collision d'inscription est effacée par un `DELETE` SQL, qui
        déclenche la cascade base `placement.inscription_id` (`ON DELETE CASCADE`) — un
        `session.delete` ORM
        laisserait SQLAlchemy deviner la descendance (cf. `supprimer`, la série et ses volées).

        Contrat (garanti par le service) : deux archers distincts, même tournoi, **pas tous les
        deux** une série (sinon `UNIQUE(tournoi_id, archer_id)` sauterait). Les collisions d'unicité
        d'**inscription** (par départ) **et de forfait** (par phase, E04US015) sont résolues **ici**
        (le service ne les voit pas) : voir `ArcherRepository.fusionner`.
        """
        try:
            with self._session_factory() as session:
                if session.get(ArcherORM, gagnant_id) is None or (
                    session.get(ArcherORM, perdant_id) is None
                ):
                    raise InfrastructureError("Archer(s) à fusionner introuvable(s) en base.")
                # Inscriptions : réassigner celles du perdant, sauf collision sur un départ où le
                # gagnant est déjà inscrit (UNIQUE(archer_id, depart_id)) — on garde alors celle du
                # gagnant, en y **reportant le paiement** (paye vrai si l'une des deux l'était),
                # et on supprime celle du perdant (son placement éventuel cascade).
                gagnant_par_depart = {
                    depart_id: (inscription_id, paye)
                    for inscription_id, depart_id, paye in session.execute(
                        select(
                            InscriptionORM.id, InscriptionORM.depart_id, InscriptionORM.paye
                        ).where(InscriptionORM.archer_id == gagnant_id)
                    ).all()
                }
                for inscription_id, depart_id, paye in session.execute(
                    select(InscriptionORM.id, InscriptionORM.depart_id, InscriptionORM.paye).where(
                        InscriptionORM.archer_id == perdant_id
                    )
                ).all():
                    collision = gagnant_par_depart.get(depart_id)
                    if collision is None:
                        session.execute(
                            update(InscriptionORM)
                            .where(InscriptionORM.id == inscription_id)
                            .values(archer_id=gagnant_id)
                        )
                        continue
                    gagnant_inscription_id, gagnant_paye = collision
                    if paye and not gagnant_paye:
                        session.execute(
                            update(InscriptionORM)
                            .where(InscriptionORM.id == gagnant_inscription_id)
                            .values(paye=True)
                        )
                    session.execute(
                        delete(InscriptionORM).where(InscriptionORM.id == inscription_id)
                    )
                # Scores (agrégat legacy, DETTE-011) : aucune unicité, réassignation nue.
                session.execute(
                    update(ScoreORM)
                    .where(ScoreORM.archer_id == perdant_id)
                    .values(archer_id=gagnant_id)
                )
                # Série : au plus une côté perdant (contrat « pas les deux »), donc pas de collision
                # sur UNIQUE(tournoi_id, archer_id) — ses volées la suivent (via serie_id).
                session.execute(
                    update(SerieORM)
                    .where(SerieORM.archer_id == perdant_id)
                    .values(archer_id=gagnant_id)
                )
                # Forfaits (E04US015) : réassigner ceux du perdant, sauf collision sur une phase où
                # le gagnant est déjà forfait (UNIQUE(tournoi_id, archer_id, phase_id)) — on garde
                # alors celui du gagnant et on supprime celui du perdant. Sans ce nettoyage, la FK
                # `forfait.archer_id` (enforced) ferait échouer le `DELETE` du perdant (revue
                # adversariale E04US015). Même tournoi (contrat), la clé de collision est la phase.
                gagnant_phases = {
                    phase_id
                    for (phase_id,) in session.execute(
                        select(ForfaitORM.phase_id).where(ForfaitORM.archer_id == gagnant_id)
                    ).all()
                }
                for forfait_id, phase_id in session.execute(
                    select(ForfaitORM.id, ForfaitORM.phase_id).where(
                        ForfaitORM.archer_id == perdant_id
                    )
                ).all():
                    if phase_id in gagnant_phases:
                        session.execute(delete(ForfaitORM).where(ForfaitORM.id == forfait_id))
                    else:
                        session.execute(
                            update(ForfaitORM)
                            .where(ForfaitORM.id == forfait_id)
                            .values(archer_id=gagnant_id)
                        )
                # Barrages (E06US003) : même famille que le forfait — FK `barrage_tir.archer_id`
                # enforced, donc sans ce report le `DELETE` du perdant échoue et la fusion d'un
                # doublon devient impossible dès qu'un des deux a barré.
                _fusionner_barrages(session, gagnant_id, perdant_id)
                session.execute(delete(ArcherORM).where(ArcherORM.id == perdant_id))
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de la fusion des archers.") from exc


class ClubRepositorySQL:
    """Adapter SQLite du port `ClubRepository` (E02US001)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, club: Club) -> Club:
        """Persiste le club et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = ClubORM(nom=club.nom)
                session.add(ligne)
                session.commit()
                return _vers_club(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du club.") from exc

    def par_id(self, club_id: ClubId) -> Club | None:
        """Relit le club d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(ClubORM, club_id)
                return None if ligne is None else _vers_club(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du club.") from exc

    def par_nom(self, nom: str) -> Club | None:
        """Relit le club de même nom au sens de `domain.club.cle_nom`, ou `None` s'il n'y en a pas.

        La comparaison est faite **côté Python**, via la clé du domaine, plutôt qu'en SQL : le
        `COLLATE NOCASE` de SQLite ne replie que la casse **ASCII** — il laisserait passer « Élan »
        / « élan » comme « Élan » / « Elan », alors que les noms de clubs sont accentués. L'adapter
        n'invente donc aucune règle de comparaison : il applique celle du domaine.

        Le référentiel compte quelques dizaines de lignes et cette lecture n'a lieu qu'à la
        création/au renommage (donc dans la file d'écriture, jamais sur un chemin chaud) : les
        parcourir est sans conséquence, et l'unique lecture reste courte.
        """
        try:
            with self._session_factory() as session:
                recherche = cle_nom(nom)
                lignes = session.execute(select(ClubORM)).scalars()
                for ligne in lignes:
                    if cle_nom(ligne.nom) == recherche:
                        return _vers_club(ligne)
                return None
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du club par nom.") from exc

    def lister(self) -> list[Club]:
        """Renvoie tout le référentiel des clubs (liste éventuellement vide)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(select(ClubORM).order_by(ClubORM.id)).scalars()
                return [_vers_club(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du référentiel des clubs.") from exc

    def enregistrer(self, club: Club) -> Club:
        """Met à jour un club déjà persisté (renommage) et le renvoie.

        **Contrat** : l'appelant (le service) garantit l'existence (vérifiée en amont). La ligne
        absente est une **incohérence technique** (non un cas métier) → `InfrastructureError`.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(ClubORM, club.id)
                if ligne is None:
                    raise InfrastructureError("Club à mettre à jour introuvable en base.")
                ligne.nom = club.nom
                session.commit()
                return _vers_club(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour du club.") from exc

    def supprimer(self, club_id: ClubId) -> None:
        """Supprime le club d'identifiant donné (existence garantie par l'appelant)."""
        try:
            with self._session_factory() as session:
                ligne = session.get(ClubORM, club_id)
                if ligne is None:
                    raise InfrastructureError("Club à supprimer introuvable en base.")
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression du club.") from exc


class DepartRepositorySQL:
    """Adapter SQLite du port `DepartRepository` (E02US004)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, depart: Depart) -> Depart:
        """Persiste le départ et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = DepartORM(
                    tournoi_id=depart.tournoi_id,
                    numero=depart.numero,
                    horaire=depart.horaire,
                    tarif_centimes=depart.tarif_centimes,
                    quota=depart.quota,
                )
                session.add(ligne)
                session.commit()
                return _vers_depart(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du départ.") from exc

    def par_id(self, depart_id: DepartId) -> Depart | None:
        """Relit le départ d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(DepartORM, depart_id)
                return None if ligne is None else _vers_depart(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du départ.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Depart]:
        """Renvoie tous les départs d'un tournoi, **triés par numéro** (liste éventuellement vide).

        Le tri par numéro rend l'ordre d'affichage stable et sert au service à calculer le prochain
        numéro (le plus grand + 1).
        """
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(DepartORM)
                    .where(DepartORM.tournoi_id == tournoi_id)
                    .order_by(DepartORM.numero)
                ).scalars()
                return [_vers_depart(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des départs du tournoi.") from exc

    def enregistrer(self, depart: Depart) -> Depart:
        """Met à jour un départ déjà persisté (édition tarif/horaire) et le renvoie.

        **Contrat** : l'appelant (le service) garantit l'existence (vérifiée en amont). La ligne
        absente est une **incohérence technique** (non un cas métier) → `InfrastructureError`. Le
        `numero` et le `tournoi_id` d'un départ persisté ne changent pas (édition sur place).
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(DepartORM, depart.id)
                if ligne is None:
                    raise InfrastructureError("Départ à mettre à jour introuvable en base.")
                ligne.horaire = depart.horaire
                ligne.tarif_centimes = depart.tarif_centimes
                ligne.quota = depart.quota
                session.commit()
                return _vers_depart(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour du départ.") from exc

    def supprimer(self, depart_id: DepartId) -> None:
        """Supprime le départ d'identifiant donné **et ses inscriptions** (E02US004, E02US009).

        **Contrat** : existence garantie par l'appelant, qui a déjà obtenu la confirmation de
        l'admin si le départ portait des inscriptions (`DepartAvecInscriptions`). **Une seule
        transaction** pour les deux `DELETE`, dans cet ordre : `inscription.depart_id` est une FK
        **sans `ON DELETE`** (DETTE-001), donc supprimer le départ d'abord échouerait. Même patron
        que `ArcherRepositorySQL.supprimer` avec les scores — cascade applicative maîtrisée.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(DepartORM, depart_id)
                if ligne is None:
                    raise InfrastructureError("Départ à supprimer introuvable en base.")
                _purger_descendance_du_depart(session, depart_id)
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression du départ.") from exc

    def supprimer_avec_remboursements(
        self, depart_id: DepartId, remboursements: Sequence[Remboursement]
    ) -> None:
        """Supprime le départ (et ses inscriptions) **et** ouvre les remboursements — une
        transaction.

        Variante de `supprimer` (E08US005, ADR-0057) : les `remboursements` (un par inscription
        payée
        d'un créneau tarifé) sont **insérés** dans la **même** session que les deux `DELETE`,
        scellés
        par un **unique** `commit`. Ordre des `DELETE` inchangé (`inscription` avant `depart` — FK
        sans `ON DELETE`, DETTE-001). Atomicité « on n'efface une inscription payée que si son
        remboursement est ouvert » — jamais de somme encaissée effacée sans contrepartie, jamais de
        remboursement en double (un échec avant le `commit` annule **tout**). Une liste vide est
        tolérée (équivalente à `supprimer`) — mais le service appelle `supprimer` dans ce cas.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(DepartORM, depart_id)
                if ligne is None:
                    raise InfrastructureError("Départ à supprimer introuvable en base.")
                for remboursement in remboursements:
                    session.add(_remboursement_orm(remboursement))
                _purger_descendance_du_depart(session, depart_id)
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError(
                "Échec de suppression du départ avec remboursements."
            ) from exc


class InscriptionRepositorySQL:
    """Adapter SQLite du port `InscriptionRepository` — liens archer↔départ (E02US009, E08US002).

    `definir_paye_avec_trace` réalise la **couture de session partagée** (ADR-0035), comme
    `SerieRepositorySQL.enregistrer_avec_trace` : le nouveau statut de paiement **et** son entrée
    d'audit s'écrivent dans **une seule session, un seul `commit`**. D'où l'`AuditRepositorySQL`
    injecté — couplage **infra → infra** (le port `InscriptionRepository` ignore cette couture ; sa
    signature ne cite aucune session).
    """

    def __init__(
        self, session_factory: sessionmaker[Session], audit_repository: AuditRepositorySQL
    ) -> None:
        self._session_factory = session_factory
        self._audit = audit_repository

    def ajouter(self, inscription: Inscription) -> Inscription:
        """Persiste l'inscription et la renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = InscriptionORM(
                    archer_id=inscription.archer_id,
                    depart_id=inscription.depart_id,
                    paye=inscription.paye,
                )
                session.add(ligne)
                session.commit()
                return _vers_inscription(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance de l'inscription.") from exc

    def par_id(self, inscription_id: InscriptionId) -> Inscription | None:
        """Relit l'inscription d'identifiant donné, ou `None` si elle n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(InscriptionORM, inscription_id)
                return None if ligne is None else _vers_inscription(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de l'inscription.") from exc

    def par_archer(self, archer_id: ArcherId) -> list[Inscription]:
        """Renvoie les inscriptions d'un archer, triées par départ (liste éventuellement vide)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(InscriptionORM)
                    .where(InscriptionORM.archer_id == archer_id)
                    .order_by(InscriptionORM.depart_id)
                ).scalars()
                return [_vers_inscription(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des inscriptions de l'archer.") from exc

    def par_depart(self, depart_id: DepartId) -> list[Inscription]:
        """Renvoie les inscriptions portant sur un départ (liste éventuellement vide)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(InscriptionORM)
                    .where(InscriptionORM.depart_id == depart_id)
                    .order_by(InscriptionORM.id)
                ).scalars()
                return [_vers_inscription(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des inscriptions du départ.") from exc

    def par_archer_et_depart(self, archer_id: ArcherId, depart_id: DepartId) -> Inscription | None:
        """Renvoie l'inscription du couple `(archer, départ)`, ou `None` (contrôle d'unicité)."""
        try:
            with self._session_factory() as session:
                ligne = session.execute(
                    select(InscriptionORM).where(
                        InscriptionORM.archer_id == archer_id,
                        InscriptionORM.depart_id == depart_id,
                    )
                ).scalar_one_or_none()
                return None if ligne is None else _vers_inscription(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de l'inscription du couple.") from exc

    def enregistrer(self, inscription: Inscription) -> Inscription:
        """Met à jour une inscription déjà persistée (bascule de `paye`) et la renvoie.

        **Contrat** : l'appelant (le service) garantit l'existence. Le couple `(archer, départ)`
        d'une inscription persistée ne change pas — seule `paye` évolue.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(InscriptionORM, inscription.id)
                if ligne is None:
                    raise InfrastructureError("Inscription à mettre à jour introuvable en base.")
                ligne.paye = inscription.paye
                session.commit()
                return _vers_inscription(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour de l'inscription.") from exc

    def definir_paye_avec_trace(
        self, inscription_ids: Sequence[InscriptionId], paye: bool, entree: EntreeAudit
    ) -> list[Inscription]:
        """Bascule `paye` sur plusieurs inscriptions **et** co-écrit sa trace — une transaction.

        Tout ou rien (ADR-0035) : les inscriptions visées passent à `paye`, la trace est ajoutée
        dans **la même** session (via `AuditRepositorySQL.consigner_dans`, qui ne commit pas), puis
        un **unique** `commit` scelle l'ensemble. Un échec avant le commit ne laisse ni marquage non
        tracé, ni trace fantôme. Une ligne absente est une **incohérence technique** (l'appelant
        garantit l'existence) → `InfrastructureError`. Les inscriptions mises à jour sont renvoyées
        dans l'ordre des identifiants fournis.
        """
        try:
            with self._session_factory() as session:
                maj: list[InscriptionORM] = []
                for inscription_id in inscription_ids:
                    ligne = session.get(InscriptionORM, inscription_id)
                    if ligne is None:
                        raise InfrastructureError("Inscription à marquer introuvable en base.")
                    ligne.paye = paye
                    maj.append(ligne)
                self._audit.consigner_dans(session, entree)
                session.commit()
                return [_vers_inscription(ligne) for ligne in maj]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de marquage du paiement et de sa trace.") from exc

    def supprimer(self, inscription_id: InscriptionId) -> None:
        """Supprime l'inscription d'identifiant donné (désinscription ; existence garantie)."""
        try:
            with self._session_factory() as session:
                ligne = session.get(InscriptionORM, inscription_id)
                if ligne is None:
                    raise InfrastructureError("Inscription à supprimer introuvable en base.")
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression de l'inscription.") from exc

    def supprimer_avec_remboursement(
        self, inscription_id: InscriptionId, remboursement: Remboursement
    ) -> None:
        """Supprime l'inscription **et** ouvre son remboursement — une transaction (E08US005).

        Tout ou rien (ADR-0057, couture de session partagée comme `definir_paye_avec_trace`) : le
        remboursement est **inséré** puis l'inscription **supprimée** dans la **même** session, un
        **unique** `commit` scelle l'ensemble. Ordre insertion-avant-suppression sans importance
        (un seul commit), mais l'atomicité garantit qu'on n'efface **jamais** une inscription payée
        sans ouvrir sa contrepartie, ni l'inverse. Ligne absente = incohérence technique (l'appelant
        garantit l'existence) → `InfrastructureError`.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(InscriptionORM, inscription_id)
                if ligne is None:
                    raise InfrastructureError("Inscription à supprimer introuvable en base.")
                session.add(_remboursement_orm(remboursement))
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de désinscription avec remboursement.") from exc


class CategorieRepositorySQL:
    """Adapter SQLite du port `CategorieRepository` (E01US003)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, categorie: Categorie) -> Categorie:
        """Persiste la catégorie et la renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = CategorieORM(
                    tournoi_id=categorie.tournoi_id,
                    origine=categorie.origine.value,
                    libelle=categorie.libelle,
                    arme=categorie.arme,
                    ages=_ages_categorie(categorie),
                    sexe=None if categorie.sexe is None else categorie.sexe.value,
                    blason_id=categorie.blason_id,
                    hauteur_cm=categorie.hauteur_cm,
                )
                session.add(ligne)
                session.commit()
                return _vers_categorie(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance de la catégorie.") from exc

    def par_id(self, categorie_id: CategorieId) -> Categorie | None:
        """Relit la catégorie d'identifiant donné, ou `None` si elle n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(CategorieORM, categorie_id)
                return None if ligne is None else _vers_categorie(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de la catégorie.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Categorie]:
        """Renvoie toutes les catégories d'un tournoi (liste éventuellement vide)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(CategorieORM)
                    .where(CategorieORM.tournoi_id == tournoi_id)
                    .order_by(CategorieORM.id)
                ).scalars()
                return [_vers_categorie(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des catégories du tournoi.") from exc

    def par_bibliotheque(self) -> list[Categorie]:
        """Renvoie les modèles de bibliothèque — patrimoine du club, sans tournoi (E01US023)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(CategorieORM)
                    .where(CategorieORM.tournoi_id.is_(None))
                    .order_by(CategorieORM.id)
                ).scalars()
                return [_vers_categorie(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de la bibliothèque de catégories.") from exc

    def par_blason(self, blason_id: BlasonId) -> list[Categorie]:
        """Renvoie les catégories dont le blason par défaut est `blason_id` (E01US006)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(CategorieORM)
                    .where(CategorieORM.blason_id == blason_id)
                    .order_by(CategorieORM.id)
                ).scalars()
                return [_vers_categorie(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des catégories par blason.") from exc

    def enregistrer(self, categorie: Categorie) -> Categorie:
        """Met à jour une catégorie déjà persistée (édition) et la renvoie.

        **Contrat** : l'appelant (le service) garantit l'existence (vérifiée en amont). La ligne
        absente est une **incohérence technique** (non un cas métier) → `InfrastructureError`.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(CategorieORM, categorie.id)
                if ligne is None:
                    raise InfrastructureError("Catégorie à mettre à jour introuvable en base.")
                ligne.libelle = categorie.libelle
                ligne.arme = categorie.arme
                ligne.ages = _ages_categorie(categorie)
                ligne.sexe = None if categorie.sexe is None else categorie.sexe.value
                ligne.blason_id = categorie.blason_id
                ligne.hauteur_cm = categorie.hauteur_cm
                session.commit()
                return _vers_categorie(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour de la catégorie.") from exc

    def supprimer(self, categorie_id: CategorieId) -> None:
        """Supprime la catégorie d'identifiant donné (existence garantie par l'appelant)."""
        try:
            with self._session_factory() as session:
                ligne = session.get(CategorieORM, categorie_id)
                if ligne is None:
                    raise InfrastructureError("Catégorie à supprimer introuvable en base.")
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression de la catégorie.") from exc


class BlasonRepositorySQL:
    """Adapter SQLite du port `BlasonRepository` (E01US005)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, blason: Blason) -> Blason:
        """Persiste le blason et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = BlasonORM(
                    tournoi_id=blason.tournoi_id,
                    origine=blason.origine.value,
                    nom=blason.nom,
                    taille=blason.taille,
                    capacite=blason.capacite,
                    zones=json.dumps([zone.value for zone in blason.zones]),
                )
                session.add(ligne)
                session.commit()
                return _vers_blason(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du blason.") from exc

    def par_id(self, blason_id: BlasonId) -> Blason | None:
        """Relit le blason d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(BlasonORM, blason_id)
                return None if ligne is None else _vers_blason(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du blason.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Blason]:
        """Renvoie tous les blasons d'un tournoi (liste éventuellement vide)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(BlasonORM)
                    .where(BlasonORM.tournoi_id == tournoi_id)
                    .order_by(BlasonORM.id)
                ).scalars()
                return [_vers_blason(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des blasons du tournoi.") from exc

    def par_bibliotheque(self) -> list[Blason]:
        """Renvoie les modèles de bibliothèque — patrimoine du club, sans tournoi (E01US023)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(BlasonORM).where(BlasonORM.tournoi_id.is_(None)).order_by(BlasonORM.id)
                ).scalars()
                return [_vers_blason(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de la bibliothèque de blasons.") from exc

    def enregistrer(self, blason: Blason) -> Blason:
        """Met à jour un blason déjà persisté (édition) et le renvoie.

        **Contrat** : l'appelant (le service) garantit l'existence (vérifiée en amont). La ligne
        absente est une **incohérence technique** (non un cas métier) → `InfrastructureError`.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(BlasonORM, blason.id)
                if ligne is None:
                    raise InfrastructureError("Blason à mettre à jour introuvable en base.")
                ligne.nom = blason.nom
                ligne.taille = blason.taille
                ligne.capacite = blason.capacite
                ligne.zones = json.dumps([zone.value for zone in blason.zones])
                session.commit()
                return _vers_blason(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour du blason.") from exc

    def supprimer(self, blason_id: BlasonId) -> None:
        """Supprime le blason d'identifiant donné (existence garantie par l'appelant)."""
        try:
            with self._session_factory() as session:
                ligne = session.get(BlasonORM, blason_id)
                if ligne is None:
                    raise InfrastructureError("Blason à supprimer introuvable en base.")
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression du blason.") from exc


class GabaritSalleRepositorySQL:
    """Adapter SQLite du port `GabaritSalleRepository` (E01US007, E01US008)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, gabarit: GabaritSalle) -> GabaritSalle:
        """Persiste le gabarit (modèle ou instance) et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = GabaritSalleORM(
                    nom=gabarit.nom,
                    nb_cibles=gabarit.nb_cibles,
                    config=_config_gabarit(gabarit),
                    tournoi_id=gabarit.tournoi_id,
                )
                session.add(ligne)
                session.commit()
                return _vers_gabarit(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du gabarit de salle.") from exc

    def par_id(self, gabarit_id: GabaritSalleId) -> GabaritSalle | None:
        """Relit le gabarit d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(GabaritSalleORM, gabarit_id)
                return None if ligne is None else _vers_gabarit(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du gabarit de salle.") from exc

    def lister(self) -> list[GabaritSalle]:
        """Renvoie les gabarits **modèles** (bibliothèque, `tournoi_id IS NULL`), par identifiant.

        Les instances appliquées à un tournoi (E01US008) sont **exclues** : elles se lisent via
        `par_tournoi`.
        """
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(GabaritSalleORM)
                    .where(GabaritSalleORM.tournoi_id.is_(None))
                    .order_by(GabaritSalleORM.id)
                ).scalars()
                return [_vers_gabarit(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des gabarits de salle.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> GabaritSalle | None:
        """Renvoie l'instance de gabarit appliquée à un tournoi, ou `None` s'il n'y en a pas.

        Un tournoi porte au plus une instance ; en cas de multiplicité (ne devrait pas survenir),
        la plus récente (`id` le plus élevé) l'emporte.
        """
        try:
            with self._session_factory() as session:
                ligne = (
                    session.execute(
                        select(GabaritSalleORM)
                        .where(GabaritSalleORM.tournoi_id == tournoi_id)
                        .order_by(GabaritSalleORM.id.desc())
                    )
                    .scalars()
                    .first()
                )
                return None if ligne is None else _vers_gabarit(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du gabarit du tournoi.") from exc

    def enregistrer(self, gabarit: GabaritSalle) -> GabaritSalle:
        """Met à jour un gabarit déjà persisté (édition, ajustement) et le renvoie.

        **Contrat** : l'appelant (le service) garantit l'existence (vérifiée en amont). La ligne
        absente est une **incohérence technique** (non un cas métier) → `InfrastructureError`.
        Le rattachement `tournoi_id` d'un gabarit persisté ne change pas (édition sur place).
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(GabaritSalleORM, gabarit.id)
                if ligne is None:
                    raise InfrastructureError("Gabarit à mettre à jour introuvable en base.")
                ligne.nom = gabarit.nom
                ligne.nb_cibles = gabarit.nb_cibles
                ligne.config = _config_gabarit(gabarit)
                session.commit()
                return _vers_gabarit(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour du gabarit de salle.") from exc

    def supprimer(self, gabarit_id: GabaritSalleId) -> None:
        """Supprime le gabarit d'identifiant donné (existence garantie par l'appelant)."""
        try:
            with self._session_factory() as session:
                ligne = session.get(GabaritSalleORM, gabarit_id)
                if ligne is None:
                    raise InfrastructureError("Gabarit à supprimer introuvable en base.")
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression du gabarit de salle.") from exc


class RemboursementRepositorySQL:
    """Adapter SQLite du port `RemboursementRepository` (E08US005, ADR-0057).

    Registre des sommes encaissées à rendre. Les **créations** ne passent pas par cet adapter : une
    ligne naît **atomiquement** avec la suppression de l'inscription payée qui la provoque
    (`InscriptionRepositorySQL.supprimer_avec_remboursement`,
    `DepartRepositorySQL.supprimer_avec_remboursements`, via `_remboursement_orm`). Cet adapter sert
    la **lecture** (`par_tournoi`, `par_id`) et le **traitement** (`enregistrer_avec_trace`).

    `enregistrer_avec_trace` réalise la **couture de session partagée** (ADR-0035, comme
    `InscriptionRepositorySQL.definir_paye_avec_trace`) : le nouveau statut du remboursement **et**
    son entrée d'audit `REMBOURSEMENT` s'écrivent dans **une seule session, un seul `commit`**. D'où
    l'`AuditRepositorySQL` injecté — collaboration **infra → infra** (le port du domaine ignore la
    couture). L'entrée arrive **déjà construite et datée** par le service (via `Horloge`).
    """

    def __init__(
        self, session_factory: sessionmaker[Session], audit_repository: AuditRepositorySQL
    ) -> None:
        self._session_factory = session_factory
        self._audit = audit_repository

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Remboursement]:
        """Renvoie les remboursements d'un tournoi (ordre non garanti — le service trie)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(RemboursementORM).where(RemboursementORM.tournoi_id == tournoi_id)
                ).scalars()
                return [_vers_remboursement(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des remboursements.") from exc

    def par_id(self, remboursement_id: RemboursementId) -> Remboursement | None:
        """Renvoie le remboursement d'identifiant donné, ou `None` s'il n'existe pas."""
        try:
            with self._session_factory() as session:
                ligne = session.get(RemboursementORM, remboursement_id)
                return None if ligne is None else _vers_remboursement(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du remboursement.") from exc

    def enregistrer_avec_trace(
        self, remboursement: Remboursement, entree: EntreeAudit
    ) -> Remboursement:
        """Met à jour le remboursement traité **et** co-écrit sa trace `REMBOURSEMENT` — une
        transaction.

        Tout ou rien (ADR-0035) : le nouveau `statut`/`traite_le` et l'entrée d'audit (via
        `AuditRepositorySQL.consigner_dans`, qui ne commit pas) tiennent dans un **unique**
        `commit`.
        Ligne absente = incohérence technique (l'appelant garantit l'existence) →
        `InfrastructureError`.
        """
        assert remboursement.id is not None, "Un remboursement à traiter est persisté."
        try:
            with self._session_factory() as session:
                ligne = session.get(RemboursementORM, remboursement.id)
                if ligne is None:
                    raise InfrastructureError("Remboursement à traiter introuvable en base.")
                ligne.statut = remboursement.statut.value
                ligne.traite_le = remboursement.traite_le
                self._audit.consigner_dans(session, entree)
                session.commit()
                return _vers_remboursement(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError(
                "Échec de traitement du remboursement et de sa trace."
            ) from exc


def _remboursement_orm(remboursement: Remboursement) -> RemboursementORM:
    """Construit une ligne ORM `remboursement` depuis l'agrégat (statut/motif → valeur d'énum).

    Partagé par les trois sites d'écriture — la co-écriture à la désinscription
    (`InscriptionRepositorySQL`), à la suppression d'un départ (`DepartRepositorySQL`) — d'où une
    fonction libre plutôt qu'une méthode. `id` reste `None` (auto-attribué par SQLite à
    l'insertion).
    """
    return RemboursementORM(
        tournoi_id=remboursement.tournoi_id,
        archer_prenom=remboursement.archer_prenom,
        archer_nom=remboursement.archer_nom,
        creneau=remboursement.creneau,
        montant_centimes=remboursement.montant_centimes,
        motif=remboursement.motif.value,
        statut=remboursement.statut.value,
        cree_le=remboursement.cree_le,
        traite_le=remboursement.traite_le,
    )


def _vers_remboursement(ligne: RemboursementORM) -> Remboursement:
    """Traduit une ligne ORM `remboursement` en agrégat de domaine (E08US005, ADR-0057).

    `motif`/`statut` : la valeur relue redevient l'énumération. `cree_le`/`traite_le` : SQLite
    stocke
    un `DateTime` **sans fuseau** ; on **réattache UTC** (le service n'écrit que de l'UTC via
    `Horloge`), round-trip fidèle comme l'horodatage d'audit. `traite_le` reste `None` tant que le
    poste est à traiter.
    """
    cree_le = ligne.cree_le
    if cree_le.tzinfo is None:
        cree_le = cree_le.replace(tzinfo=datetime.UTC)
    traite_le = ligne.traite_le
    if traite_le is not None and traite_le.tzinfo is None:
        traite_le = traite_le.replace(tzinfo=datetime.UTC)
    return Remboursement(
        tournoi_id=ligne.tournoi_id,
        archer_prenom=ligne.archer_prenom,
        archer_nom=ligne.archer_nom,
        creneau=ligne.creneau,
        montant_centimes=ligne.montant_centimes,
        motif=MotifRemboursement(ligne.motif),
        cree_le=cree_le,
        statut=StatutRemboursement(ligne.statut),
        traite_le=traite_le,
        id=ligne.id,
    )


def _barrages_contenant(session: Session, archer_id: int) -> list[BarrageORM]:
    """Les barrages dont `archer_id` est un **participant annoncé** (tir saisi ou non).

    On lit `participants_json` plutôt que la table des tirs : un archer peut être annoncé sans
    avoir encore tiré, et c'est précisément ce cas qui laisserait un identifiant fantôme derrière
    lui. La table est petite (quelques lignes par tournoi) — un filtre Python est ici plus sûr
    qu'une recherche dans du JSON en SQL.
    """
    return [
        ligne
        for ligne in session.execute(select(BarrageORM)).scalars()
        if archer_id in json.loads(ligne.participants_json)
    ]


def _supprimer_barrages_de_l_archer(session: Session, archer_id: int) -> None:
    """Supprime les barrages où figure cet archer, tirs compris (suppression d'archer, E06US003)."""
    for ligne in _barrages_contenant(session, archer_id):
        session.execute(delete(BarrageTirORM).where(BarrageTirORM.barrage_id == ligne.id))
        session.execute(delete(BarrageORM).where(BarrageORM.id == ligne.id))
    # Ceinture : un tir dont l'archer ne figure (plus) dans `participants_json` échapperait à la
    # boucle et rebloquerait la suppression en 500. Inatteignable par le service aujourd'hui — une
    # ligne pour que ça le reste.
    session.execute(delete(BarrageTirORM).where(BarrageTirORM.archer_id == archer_id))


def _fusionner_barrages(session: Session, gagnant_id: int, perdant_id: int) -> None:
    """Reporte sur le gagnant les barrages du perdant (fusion de doublons, E02US005 et E06US003).

    Deux collisions à traiter, et elles ne sont pas symétriques :

    - **un tir** — `uq_barrage_tir(barrage_id, manche, archer_id)` : si les deux fiches ont tiré la
      même manche du même barrage (le cas d'un doublon réellement dédoublé sur le pas de tir), on
      **garde celui du gagnant** et on supprime celui du perdant, comme pour l'inscription ;
    - **la liste des participants** : le perdant y est remplacé par le gagnant, **dédoublonné**.
      Sans cela le barrage compterait deux fois la même personne, ce que l'agrégat refuse.

    Un barrage qui se retrouverait à **moins de deux** participants après fusion n'oppose plus
    personne : il est supprimé plutôt que laissé dans un état que l'agrégat rejetterait.
    """
    # Ceinture symétrique de `_supprimer_barrages_de_l_archer` : un tir du perdant orphelin de
    # `participants_json` échapperait à la boucle et ferait échouer le `DELETE` de l'archer (500).
    orphelins = [ligne.id for ligne in _barrages_contenant(session, perdant_id)]
    session.execute(
        delete(BarrageTirORM).where(
            BarrageTirORM.archer_id == perdant_id,
            BarrageTirORM.barrage_id.notin_(orphelins) if orphelins else sa_true(),
        )
    )
    for ligne in _barrages_contenant(session, perdant_id):
        deja = {
            manche
            for (manche,) in session.execute(
                select(BarrageTirORM.manche).where(
                    BarrageTirORM.barrage_id == ligne.id,
                    BarrageTirORM.archer_id == gagnant_id,
                )
            ).all()
        }
        session.execute(
            delete(BarrageTirORM).where(
                BarrageTirORM.barrage_id == ligne.id,
                BarrageTirORM.archer_id == perdant_id,
                BarrageTirORM.manche.in_(deja),
            )
        )
        session.execute(
            update(BarrageTirORM)
            .where(
                BarrageTirORM.barrage_id == ligne.id,
                BarrageTirORM.archer_id == perdant_id,
            )
            .values(archer_id=gagnant_id)
        )
        participants: list[int] = []
        for reference in json.loads(ligne.participants_json):
            remplace = gagnant_id if reference == perdant_id else reference
            if remplace not in participants:
                participants.append(remplace)
        if len(participants) < 2:
            session.execute(delete(BarrageTirORM).where(BarrageTirORM.barrage_id == ligne.id))
            session.execute(delete(BarrageORM).where(BarrageORM.id == ligne.id))
            continue
        session.execute(
            update(BarrageORM)
            .where(BarrageORM.id == ligne.id)
            .values(participants_json=json.dumps(participants))
        )
        _supprimer_si_illisible(session, ligne.id)


def _supprimer_si_illisible(session: Session, barrage_id: int) -> None:
    """Supprime le barrage **seulement s'il ne se relit plus** après fusion.

    ⚠️ **On vérifie au lieu de présumer, et c'est un correctif de revue.** Une première version
    supprimait le barrage dès que la fusion touchait deux de ses participants — ce qui détruisait
    aussi des barrages parfaitement sains : à une seule manche, le report des tirs produit un
    agrégat relisible. L'organisateur nettoyait un doublon d'inscription, geste de routine, et un
    barrage tiré et acté sur la dernière place qualificative disparaissait sans trace, le classement
    revenant silencieusement au rang partagé.

    Le vrai critère n'est pas « deux fiches concernées » mais « l'agrégat tient-il encore » : une
    manche ≥ 2 peut se retrouver avec un tireur que la manche 1 vient de départager. On rejoue donc
    le moteur, et on ne supprime que s'il refuse.
    """
    ligne = session.get(BarrageORM, barrage_id)
    if ligne is None:  # pragma: no cover — on vient de l'écrire
        return
    tirs = list(
        session.execute(
            select(BarrageTirORM)
            .where(BarrageTirORM.barrage_id == barrage_id)
            .order_by(BarrageTirORM.id)
        ).scalars()
    )
    try:
        _vers_barrage(ligne, tirs).resultat()
    except DomainError:
        session.execute(delete(BarrageTirORM).where(BarrageTirORM.barrage_id == barrage_id))
        session.execute(delete(BarrageORM).where(BarrageORM.id == barrage_id))
