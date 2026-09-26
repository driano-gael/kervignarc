"""Adapters SQL du référentiel — session **courte** par opération, pannes SQLAlchemy **enveloppées**
en `InfrastructureError` : le domaine ne voit jamais d'exception brute.
"""

from __future__ import annotations

import datetime
import json
from collections.abc import Sequence
from typing import assert_never

from sqlalchemy import ColumnElement, Select, delete, func, select, update
from sqlalchemy import true as sa_true
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.attributes import InstrumentedAttribute

from domain.archer import Archer, ArcherId
from domain.blason import Blason, BlasonId, valider_zones
from domain.categorie import Categorie, CategorieId, SexeCategorie, TrancheAge
from domain.cloisonnement import Cloisonnement
from domain.club import Club, ClubId, cle_nom
from domain.depart import Depart, DepartId
from domain.entree_audit import EntreeAudit
from domain.erreurs import DomainError
from domain.gabarit_salle import GabaritSalle, GabaritSalleId
from domain.identite import Couleur, EmplacementLogo, IdentiteVisuelle, Logo, TypeLogo
from domain.inscription import Inscription, InscriptionId, date_fusionnee
from domain.patrimoine import OrigineBrique
from domain.podium import PorteePodium, ReglagePodiums
from domain.remboursement import (
    MotifRemboursement,
    Remboursement,
    RemboursementId,
    StatutRemboursement,
)
from domain.tournoi import (
    DescendanceTournoi,
    StatutTournoi,
    Tournoi,
    TournoiId,
    TypeTournoi,
)
from infrastructure.db.models import (
    ArcherORM,
    ArretDeCirconstanceORM,
    BarrageORM,
    BarrageTirORM,
    BlasonORM,
    CategorieORM,
    ClubORM,
    DepartORM,
    DerouleEtapeORM,
    DuelORM,
    EntreeAuditORM,
    ForfaitORM,
    FranchissementArretORM,
    GabaritSalleORM,
    IdentiteVisuelleORM,
    InscriptionORM,
    PhaseORM,
    PosteORM,
    RemboursementORM,
    ScoreORM,
    ScoreurORM,
    SerieORM,
    TournoiORM,
    VoleeORM,
)
from infrastructure.db.repositories._mapping import _vers_barrage

# `AuditRepositorySQL` vit dans le thème `exploitation` mais s'annote ici : plusieurs
# adapters **co-écrivent** leur trace d'audit dans la même transaction (ADR-0035). Import
# direct et acyclique — `exploitation` n'importe aucun autre thème.
from infrastructure.db.repositories.exploitation import AuditRepositorySQL
from infrastructure.erreurs import InfrastructureError


def _purger_descendance_des_departs(session: Session, depart_ids: Sequence[DepartId]) -> None:
    """Supprime ce qui pend aux créneaux **avant** eux — cascade applicative maîtrisée (ADR-0077).

    ⚠️ **L'ordre n'est pas commutatif** et s'y tromper redonne l'`IntegrityError` qu'on corrige :
    `barrage_tir` → `barrage` → arrêts → `phase` → `inscription`. Ce qui pend à la phase porte
    `ON DELETE CASCADE` — on ne supprime à la main que ce que le schéma n'emporte pas. Les deux
    tables d'arrêts ont rejoint la liste en E01US026 : FK *enforced*, un créneau portant un arrêt
    partait en 500.
    """
    phases = select(PhaseORM.id).where(PhaseORM.depart_id.in_(depart_ids))
    barrages = select(BarrageORM.id).where(BarrageORM.depart_id.in_(depart_ids))
    session.execute(delete(BarrageTirORM).where(BarrageTirORM.barrage_id.in_(barrages)))
    session.execute(delete(BarrageORM).where(BarrageORM.depart_id.in_(depart_ids)))
    session.execute(
        delete(ArretDeCirconstanceORM).where(ArretDeCirconstanceORM.depart_id.in_(depart_ids))
    )
    session.execute(
        delete(FranchissementArretORM).where(FranchissementArretORM.phase_id.in_(phases))
    )
    session.execute(delete(PhaseORM).where(PhaseORM.depart_id.in_(depart_ids)))
    session.execute(delete(InscriptionORM).where(InscriptionORM.depart_id.in_(depart_ids)))


def _purger_enfants_directs_du_tournoi(session: Session, tournoi_id: TournoiId) -> None:
    """Purge les tables qui pendent **au tournoi lui-même**, une fois archers et départs vidés.

    `identite_visuelle` porte `ON DELETE CASCADE` et partirait seule ; elle est listée quand même —
    cette liste est ce qu'on relit pour savoir si une table neuve a été oubliée, et une table
    absente s'y lirait comme « rien à faire » plutôt que comme « la base s'en charge ».
    """
    session.execute(delete(DerouleEtapeORM).where(DerouleEtapeORM.tournoi_id == tournoi_id))
    session.execute(delete(ScoreurORM).where(ScoreurORM.tournoi_id == tournoi_id))
    session.execute(delete(PosteORM).where(PosteORM.tournoi_id == tournoi_id))
    session.execute(delete(EntreeAuditORM).where(EntreeAuditORM.tournoi_id == tournoi_id))
    session.execute(delete(RemboursementORM).where(RemboursementORM.tournoi_id == tournoi_id))
    session.execute(delete(SerieORM).where(SerieORM.tournoi_id == tournoi_id))
    session.execute(delete(ForfaitORM).where(ForfaitORM.tournoi_id == tournoi_id))
    session.execute(delete(IdentiteVisuelleORM).where(IdentiteVisuelleORM.tournoi_id == tournoi_id))


def _compte(session: Session, *criteres: ColumnElement[bool]) -> int:
    """Combien de lignes satisfont ces critères — `count(*)`, jamais un `len()` de lignes lues."""
    return session.scalar(select(func.count()).where(*criteres)) or 0


def _encaisse(session: Session, departs_payes: Select[tuple[int]]) -> int:
    """La somme **réellement reçue** : une inscription payée vaut le tarif de son créneau.

    ⚠️ **Ce n'est pas la somme du registre de remboursements** — les confondre faisait annoncer
    zéro euro à un tournoi de 400 payants sans remboursement. Le tarif lu est le **courant**, pas
    celui encaissé (DETTE-016) : le modèle ne stocke qu'un booléen `paye`.
    """
    tarifs: dict[int, int] = {}
    for depart_id, tarif in session.execute(
        select(DepartORM.id, DepartORM.tarif_centimes)
    ).tuples():
        tarifs[depart_id] = tarif
    return sum(tarifs.get(depart_id, 0) for depart_id in session.scalars(departs_payes))


def _reste_a_rendre(session: Session, tournoi_id: TournoiId) -> int:
    """Les remboursements **encore dus**, à l'exclusion de ceux déjà traités (E01US026).

    ⚠️ Sommer tous les statuts gonflait l'alerte : un poste `remboursé` est de l'argent **déjà
    rendu**, l'annoncer comme perdu use la garde qu'ADR-0077 veut préserver.
    """
    somme = session.scalar(
        select(func.coalesce(func.sum(RemboursementORM.montant_centimes), 0)).where(
            RemboursementORM.tournoi_id == tournoi_id,
            RemboursementORM.statut == StatutRemboursement.A_REMBOURSER.value,
        )
    )
    return somme or 0


def _compter_fleches(session: Session, series: Select[tuple[int]]) -> int:
    """Les flèches de ces séries, volée par volée — **validées ou non** (E01US026).

    ⚠️ Ne filtrer que les validées sous-comptait : en fin de journée, avant validation, le message
    annonçait « 0 flèche » alors que 7 200 partaient. Compté en Python car `valeurs` est un
    document JSON et `json_array_length` est une extension qu'on ne peut supposer compilée
    (règle 12) ; un document corrompu est **ignoré** — SQLite est à typage dynamique, même parti
    que `_vers_reglage_podiums`.
    """
    fleches = 0
    for document in session.scalars(select(VoleeORM.valeurs).where(VoleeORM.serie_id.in_(series))):
        try:
            valeurs = json.loads(document)
        except ValueError:
            continue
        if isinstance(valeurs, list):
            fleches += len(valeurs)
    return fleches


def _purger_descendance_des_archers(session: Session, archer_ids: Sequence[ArcherId]) -> None:
    """Supprime ce qui pend aux archers **avant** eux — même cascade pour un archer ou pour tous.

    ⚠️ **Une seule liste de tables pour les deux appelants** (suppression d'archer E02US003 et
    suppression de tournoi E01US026) : en tenir deux ferait oublier dans l'une la table qu'une US
    ajoute à l'autre — c'est l'avertissement d'ADR-0077 sur le « quatrième adapter ».
    Les **volées** suivent leur série par `ON DELETE CASCADE`, d'où le `DELETE` SQL sur `serie`
    (un `session.delete` ORM ne déclencherait pas la cascade de la base).
    """
    session.execute(delete(ScoreORM).where(ScoreORM.archer_id.in_(archer_ids)))
    session.execute(delete(InscriptionORM).where(InscriptionORM.archer_id.in_(archer_ids)))
    session.execute(delete(SerieORM).where(SerieORM.archer_id.in_(archer_ids)))
    # `forfait` (E04US015) et `barrage_tir` (E06US003) : FK *enforced*, une ligne orpheline rend
    # l'archer indéracinable (500) — le piège relevé en revue adversariale d'E04US015.
    session.execute(delete(ForfaitORM).where(ForfaitORM.archer_id.in_(archer_ids)))
    _supprimer_barrages_des_archers(session, archer_ids)


def _vers_reglage_podiums(ligne: TournoiORM) -> ReglagePodiums:
    """Traduit les deux colonnes de podium en value object (E16US014).

    ⚠️ Une portée **inconnue** est refusée, elle n'est pas ignorée : un code que cette version ne
    sait pas lire vient d'une base plus récente (ou éditée à la main), et l'ignorer rendrait
    silencieusement un palmarès amputé d'un podium que l'organisateur croit réglé.
    """
    codes = json.loads(ligne.podium_portees)
    # ⚠️ `4` ou `{"a": 1}` sont du JSON **valide** : sans ce contrôle, l'itération levait un
    # `TypeError` que l'enveloppe de `_vers_tournoi` (`DomainError`, `ValueError`) ne rattrapait
    # pas, et toute lecture de tournoi tombait en 500 non typé au lieu de l'`InfrastructureError`
    # que la migration promet.
    if not isinstance(codes, list):
        raise ValueError(f"`podium_portees` n'est pas une liste JSON : {ligne.podium_portees!r}")
    # Même modèle de menace sur la colonne d'à côté : SQLite est à typage **dynamique**, une
    # affinité `INTEGER` ne rejette pas `'abc'`. Sans ce contrôle, `1 <= 'abc'` lève un `TypeError`
    # que l'enveloppe de `_vers_tournoi` ne rattrape pas — 500 non typé sur une route publique.
    if not isinstance(ligne.podium_profondeur, int):
        raise ValueError(f"`podium_profondeur` n'est pas un entier : {ligne.podium_profondeur!r}")
    return ReglagePodiums(
        portees=frozenset(PorteePodium(code) for code in codes),
        profondeur=ligne.podium_profondeur,
    )


def _portees_en_json(reglage: ReglagePodiums) -> str:
    """Sérialise les portées dans l'ordre d'affichage — un ensemble n'en a pas, une colonne si.

    Sans tri, deux réglages identiques s'écriraient différemment d'une écriture à l'autre : la ligne
    changerait sans que rien n'ait changé, et tout diff de base deviendrait illisible.
    """
    return json.dumps([portee.value for portee in reglage.portees_actives()])


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
            reglage_podiums=_vers_reglage_podiums(ligne),
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
    """Traduit une ligne ORM en agrégat de domaine `Inscription` (E02US009).

    `cree_le` : SQLite relit un `datetime` **naïf** — on lui rend son fuseau UTC, comme les
    remboursements. `NULL` reste `None` (inscription antérieure à E17US012).
    """
    cree_le = ligne.cree_le
    if cree_le is not None and cree_le.tzinfo is None:
        cree_le = cree_le.replace(tzinfo=datetime.UTC)
    return Inscription(
        archer_id=ligne.archer_id,
        depart_id=ligne.depart_id,
        paye=ligne.paye,
        id=ligne.id,
        cree_le=cree_le,
    )


def _vers_blason(ligne: BlasonORM) -> Blason:
    """Traduit une ligne ORM en agrégat de domaine `Blason`.

    Un `zones` illisible **ou lisible mais hors règle** est une **incohérence technique** (ce
    repository en est le seul rédacteur) → `InfrastructureError` (ADR-0007). ⚠️ On **rejoue
    `valider_zones`** plutôt qu'une simple coercition `ZoneScore(...)` : celle-ci ne voit que le
    vocabulaire, pas la structure — un `'{"10": 1}'` réhydraterait `('10',)`, valide au vocabulaire
    et **sans `M`**, c'est-à-dire un blason hors invariant qui piloterait le pavé d'EPIC-04.
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
                    podium_portees=_portees_en_json(tournoi.reglage_podiums),
                    podium_profondeur=tournoi.reglage_podiums.profondeur,
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
                ligne.podium_portees = _portees_en_json(tournoi.reglage_podiums)
                ligne.podium_profondeur = tournoi.reglage_podiums.profondeur
                session.commit()
                return _vers_tournoi(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour du tournoi.") from exc

    def compter_descendance(self, tournoi_id: TournoiId) -> DescendanceTournoi:
        """Compte ce que la suppression emporterait **et ne se ressaisirait pas** (ADR-0077).

        ⚠️ **Plus étroit que la purge, volontairement** : `depart`, `categorie`, `blason`,
        `gabarit_salle`, `deroule_etape` et `identite_tournoi` partent aussi mais se refont — les
        compter ferait surgir la confirmation sur un tournoi d'essai (arbitrage du 19/09/2026).
        Le critère exact et la liste des exclus vivent sur `DescendanceTournoi`.
        """
        try:
            with self._session_factory() as session:
                departs = select(DepartORM.id).where(DepartORM.tournoi_id == tournoi_id)
                phases = select(PhaseORM.id).where(PhaseORM.depart_id.in_(departs))
                series = select(SerieORM.id).where(SerieORM.tournoi_id == tournoi_id)
                payees = select(InscriptionORM.depart_id).where(
                    InscriptionORM.depart_id.in_(departs), InscriptionORM.paye
                )
                return DescendanceTournoi(
                    archers=_compte(session, ArcherORM.tournoi_id == tournoi_id),
                    inscriptions=_compte(session, InscriptionORM.depart_id.in_(departs)),
                    fleches=_compter_fleches(session, series),
                    series=_compte(session, SerieORM.tournoi_id == tournoi_id),
                    duels=_compte(session, DuelORM.phase_id.in_(phases)),
                    forfaits=_compte(session, ForfaitORM.tournoi_id == tournoi_id),
                    barrages=_compte(session, BarrageORM.depart_id.in_(departs)),
                    postes=_compte(session, PosteORM.tournoi_id == tournoi_id),
                    scoreurs=_compte(session, ScoreurORM.tournoi_id == tournoi_id),
                    entrees_audit=_compte(session, EntreeAuditORM.tournoi_id == tournoi_id),
                    inscriptions_payees=_compte(
                        session,
                        InscriptionORM.depart_id.in_(departs),
                        InscriptionORM.paye.is_(sa_true()),
                    ),
                    encaisse_centimes=_encaisse(session, payees),
                    remboursements=_compte(session, RemboursementORM.tournoi_id == tournoi_id),
                    remboursements_centimes=_reste_a_rendre(session, tournoi_id),
                )
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec du décompte de la descendance du tournoi.") from exc

    def supprimer(self, tournoi_id: TournoiId) -> None:
        """Supprime le tournoi **et toute sa descendance** en une transaction (ADR-0077).

        ⚠️ **L'ordre n'est pas commutatif** : `inscription` avant archers *et* départs (deux FK),
        `phase` avant les départs (ADR-0075), `categorie` avant son `blason`, `archer` avant sa
        `categorie`. S'y tromper redonne l'`IntegrityError` qu'on corrige. `club` et
        `format_tournoi`, référentiels **globaux**, ne partent pas. Confirmation garantie par
        l'appelant.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(TournoiORM, tournoi_id)
                if ligne is None:
                    raise InfrastructureError("Tournoi à supprimer introuvable en base.")
                depart_ids = list(
                    session.scalars(select(DepartORM.id).where(DepartORM.tournoi_id == tournoi_id))
                )
                archer_ids = list(
                    session.scalars(select(ArcherORM.id).where(ArcherORM.tournoi_id == tournoi_id))
                )
                _purger_descendance_des_archers(session, archer_ids)
                _purger_descendance_des_departs(session, depart_ids)
                _purger_enfants_directs_du_tournoi(session, tournoi_id)
                session.execute(delete(DepartORM).where(DepartORM.tournoi_id == tournoi_id))
                session.execute(delete(ArcherORM).where(ArcherORM.tournoi_id == tournoi_id))
                session.execute(delete(CategorieORM).where(CategorieORM.tournoi_id == tournoi_id))
                session.execute(delete(BlasonORM).where(BlasonORM.tournoi_id == tournoi_id))
                session.execute(
                    delete(GabaritSalleORM).where(GabaritSalleORM.tournoi_id == tournoi_id)
                )
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

    def compter_par_tournoi(self) -> dict[TournoiId, int]:
        """Nombre d'archers de chaque tournoi, en **une** requête — la liste A04 est pollée."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(ArcherORM.tournoi_id, func.count()).group_by(ArcherORM.tournoi_id)
                ).all()
                return {int(tournoi_id): int(nombre) for tournoi_id, nombre in lignes}
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec du comptage des archers par tournoi.") from exc

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

    def tous(self) -> list[Archer]:
        """Tous les archers, tous tournois confondus (recherche transverse E16US010)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(select(ArcherORM).order_by(ArcherORM.id)).scalars()
                return [_vers_archer(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des archers.") from exc

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
        """Supprime l'archer, **ses scores, inscriptions, série de saisie et forfaits**.

        Existence garantie par le service, qui a déjà obtenu la confirmation de l'admin. **Une
        seule transaction** pour tous les `DELETE`, dans cet ordre : ces FK sont **sans `ON
        DELETE`** (ADR-0077), donc supprimer l'archer d'abord échouerait. Le `forfait` **doit**
        être purgé ici — sa FK est *enforced*, et une ligne orpheline rendait l'archer
        indéracinable (500). Les **volées** suivent leur série par cascade SQLite.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(ArcherORM, archer_id)
                if ligne is None:
                    raise InfrastructureError("Archer à supprimer introuvable en base.")
                _purger_descendance_des_archers(session, [archer_id])
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression de l'archer.") from exc

    def supprimer_avec_remboursements(
        self, archer_id: ArcherId, remboursements: Sequence[Remboursement]
    ) -> None:
        """Supprime l'archer (descendance comprise) **et** ouvre les remboursements — une
        transaction.

        Variante de `supprimer` (E01US026, résorbe DETTE-018) : les `remboursements` sont insérés
        dans la **même** session que les `DELETE`, scellés par un **unique** `commit` — même couture
        que `DepartRepositorySQL.supprimer_avec_remboursements` (ADR-0057). Jamais une inscription
        payée effacée sans sa contrepartie au registre.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(ArcherORM, archer_id)
                if ligne is None:
                    raise InfrastructureError("Archer à supprimer introuvable en base.")
                for remboursement in remboursements:
                    session.add(_remboursement_orm(remboursement))
                _purger_descendance_des_archers(session, [archer_id])
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError(
                "Échec de suppression de l'archer avec remboursements."
            ) from exc

    def fusionner(self, gagnant_id: ArcherId, perdant_id: ArcherId) -> None:
        """Réassigne la descendance du perdant au gagnant, puis supprime le perdant (E02US005).

        **Miroir de `supprimer`** : mêmes FK sans `ON DELETE`, même transaction unique, mais on
        **réattribue** au lieu de purger. Tout en instructions **Core** — un `session.delete` ORM
        laisserait SQLAlchemy deviner la descendance. Contrat garanti par le service : deux archers
        distincts, même tournoi, **pas tous les deux** une série. Les collisions d'unicité
        d'inscription et de forfait sont résolues **ici**, le service ne les voyant pas.
        """
        try:
            with self._session_factory() as session:
                if session.get(ArcherORM, gagnant_id) is None or (
                    session.get(ArcherORM, perdant_id) is None
                ):
                    raise InfrastructureError("Archer(s) à fusionner introuvable(s) en base.")
                # Inscriptions : réassigner celles du perdant, sauf collision sur un départ où le
                # gagnant est déjà inscrit (UNIQUE(archer_id, depart_id)) — on garde alors celle du
                # gagnant, en y **reportant le paiement** (paye vrai si l'une des deux l'était) et
                # la **plus ancienne date** (`date_fusionnee`), et on supprime celle du perdant (son
                # placement éventuel cascade).
                colonnes = (
                    InscriptionORM.id,
                    InscriptionORM.depart_id,
                    InscriptionORM.paye,
                    InscriptionORM.cree_le,
                )
                gagnant_par_depart = {
                    depart_id: (inscription_id, paye, cree_le)
                    for inscription_id, depart_id, paye, cree_le in session.execute(
                        select(*colonnes).where(InscriptionORM.archer_id == gagnant_id)
                    ).all()
                }
                for inscription_id, depart_id, paye, cree_le in session.execute(
                    select(*colonnes).where(InscriptionORM.archer_id == perdant_id)
                ).all():
                    collision = gagnant_par_depart.get(depart_id)
                    if collision is None:
                        session.execute(
                            update(InscriptionORM)
                            .where(InscriptionORM.id == inscription_id)
                            .values(archer_id=gagnant_id)
                        )
                        continue
                    gagnant_inscription_id, gagnant_paye, gagnant_cree_le = collision
                    session.execute(
                        update(InscriptionORM)
                        .where(InscriptionORM.id == gagnant_inscription_id)
                        .values(
                            paye=paye or gagnant_paye,
                            cree_le=date_fusionnee(cree_le, gagnant_cree_le),
                        )
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
        """Relit le club de même nom au sens de `domain.club.cle_nom`, ou `None`.

        La comparaison est faite **côté Python**, via la clé du domaine, plutôt qu'en SQL : le
        `COLLATE NOCASE` de SQLite ne replie que la casse **ASCII**, or les noms de clubs sont
        accentués. Le référentiel compte quelques dizaines de lignes et cette lecture n'a lieu qu'à
        la création ou au renommage, donc dans la file d'écriture — jamais sur un chemin chaud.
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
        **sans `ON DELETE`** (ADR-0077), donc supprimer le départ d'abord échouerait. Même patron
        que `ArcherRepositorySQL.supprimer` avec les scores — cascade applicative maîtrisée.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(DepartORM, depart_id)
                if ligne is None:
                    raise InfrastructureError("Départ à supprimer introuvable en base.")
                _purger_descendance_des_departs(session, [depart_id])
                session.delete(ligne)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression du départ.") from exc

    def supprimer_avec_remboursements(
        self, depart_id: DepartId, remboursements: Sequence[Remboursement]
    ) -> None:
        """Supprime le départ (et ses inscriptions) **et** ouvre les remboursements — une
        transaction.

        Variante de `supprimer` (E08US005, ADR-0057) : les `remboursements` sont insérés dans la
        **même** session que les deux `DELETE`, scellés par un **unique** `commit`. Ordre inchangé
        (`inscription` avant `depart`). Atomicité « on n'efface une inscription payée que si son
        remboursement est ouvert ». Liste vide tolérée, mais le service appelle `supprimer`.
        """
        try:
            with self._session_factory() as session:
                ligne = session.get(DepartORM, depart_id)
                if ligne is None:
                    raise InfrastructureError("Départ à supprimer introuvable en base.")
                for remboursement in remboursements:
                    session.add(_remboursement_orm(remboursement))
                _purger_descendance_des_departs(session, [depart_id])
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
                    cree_le=inscription.cree_le,
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

        Tout ou rien (ADR-0035) : la trace est ajoutée dans **la même** session (via
        `consigner_dans`, qui ne commit pas), puis un **unique** `commit` scelle l'ensemble — ni
        marquage non tracé, ni trace fantôme. Une ligne absente est une incohérence technique →
        `InfrastructureError`. Retour dans l'ordre des identifiants fournis.
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

        Tout ou rien (ADR-0057, couture de session partagée comme `definir_paye_avec_trace`) : un
        **unique** `commit` scelle l'ensemble, si bien qu'on n'efface **jamais** une inscription
        payée sans ouvrir sa contrepartie, ni l'inverse. Ligne absente = incohérence technique.
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

    ⚠️ Les **créations** ne passent pas par cet adapter : une ligne naît **atomiquement** avec la
    suppression de l'inscription payée qui la provoque. Il sert la lecture et le traitement.
    `enregistrer_avec_trace` réalise la **couture de session partagée** (ADR-0035) — statut et
    audit dans une seule session, un seul `commit` —, d'où l'`AuditRepositorySQL` injecté :
    collaboration **infra → infra**, le port du domaine ignorant la couture.
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
        """Met à jour le remboursement traité **et** co-écrit sa trace — une transaction.

        Tout ou rien (ADR-0035) : le nouveau `statut`/`traite_le` et l'entrée d'audit tiennent dans
        un **unique** `commit`. Ligne absente = incohérence technique → `InfrastructureError`.
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


def _supprimer_barrages_des_archers(session: Session, archer_ids: Sequence[ArcherId]) -> None:
    """Supprime les barrages où figure **l'un** de ces archers, tirs compris (E06US003).

    ⚠️ **Un seul parcours, quel que soit le nombre d'archers** : rejouer le scan en boucle pour les
    400 d'un tournoi tenait 400 parcours **dans la transaction du writer unique**, donc autant
    d'attente pour les tablettes en salle (règle 7). On supprime le **barrage entier** et pas les
    seuls tirs : amputé d'un tireur annoncé, il serait refusé à la relecture.
    """
    vises = set(archer_ids)
    cibles = [
        ligne.id
        for ligne in session.execute(select(BarrageORM)).scalars()
        if vises & set(json.loads(ligne.participants_json))
    ]
    if cibles:
        session.execute(delete(BarrageTirORM).where(BarrageTirORM.barrage_id.in_(cibles)))
        session.execute(delete(BarrageORM).where(BarrageORM.id.in_(cibles)))
    # Ceinture : un tir dont l'archer ne figure (plus) dans `participants_json` échapperait au
    # filtre et rebloquerait la suppression en 500. Inatteignable par le service aujourd'hui.
    session.execute(delete(BarrageTirORM).where(BarrageTirORM.archer_id.in_(archer_ids)))


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
    """Reporte sur le gagnant les barrages du perdant (fusion de doublons, E02US005, E06US003).

    Deux collisions, non symétriques : **un tir** (`uq_barrage_tir`) — on garde celui du gagnant et
    supprime celui du perdant, comme pour l'inscription ; **la liste des participants** — le
    perdant y est remplacé par le gagnant, **dédoublonné**, sinon le barrage compterait deux fois
    la même personne. Un barrage tombé sous **deux** participants n'oppose plus personne : il est
    supprimé plutôt que laissé dans un état que l'agrégat rejetterait.
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

    ⚠️ **On vérifie au lieu de présumer.** Supprimer dès que la fusion touche deux participants
    détruisait aussi des barrages sains : à une seule manche, le report des tirs produit un agrégat
    relisible. Un doublon d'inscription nettoyé faisait alors disparaître sans trace un barrage
    tiré sur la dernière place qualificative. Le critère est « l'agrégat tient-il encore » — on
    rejoue le moteur, et on ne supprime que s'il refuse.
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


class IdentiteVisuelleRepositorySQL:
    """Adapter SQLite du port `IdentiteVisuelleRepository` (E16US006, ADR-0097).

    ⚠️ **Les colonnes de blob ne sont jamais chargées par `reglages`.** La projection y est écrite
    colonne par colonne plutôt que sur l'entité : `session.get(IdentiteVisuelleORM, …)` aurait
    ramené jusqu'à un mégaoctet d'octets pour répondre « quelle est la couleur d'accent ? », à
    chaque affichage public. C'est la raison d'être de la table séparée ; la perdre ici l'annulerait
    silencieusement, sans qu'aucun test fonctionnel ne bouge.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def reglages(self, tournoi_id: TournoiId) -> IdentiteVisuelle:
        """Relit accents et présence des logos, sans charger un seul octet de fichier."""
        try:
            with self._session_factory() as session:
                return _lire_reglages_identite(session, tournoi_id)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de l'identité visuelle.") from exc

    def logo(self, tournoi_id: TournoiId, emplacement: EmplacementLogo) -> Logo | None:
        """Relit les octets d'**un** logo (l'autre emplacement n'est pas chargé)."""
        colonne_octets, colonne_type = _colonnes_du_logo(emplacement)
        try:
            with self._session_factory() as session:
                ligne = session.execute(
                    select(colonne_octets, colonne_type).where(
                        IdentiteVisuelleORM.tournoi_id == tournoi_id
                    )
                ).one_or_none()
                if ligne is None:
                    return None
                octets, type_mime = ligne
                if octets is None or type_mime is None:
                    return None
                # `TypeLogo(...)` lève une `ValueError` — pas une `SQLAlchemyError` — si la colonne
                # porte un type inconnu : elle traverserait l'adapter et sortirait en 500 non typé.
                # Le partage du fichier (cf. `_vers_tournoi`) veut qu'une ligne que le domaine
                # refuse soit une incohérence **technique**.
                try:
                    format_du_logo = TypeLogo(type_mime)
                except ValueError as exc:
                    raise InfrastructureError("Type de logo illisible en base.") from exc
                # Reconstruction **directe**, sans repasser par `Logo.deposer` : les octets ont déjà
                # été validés au dépôt, et les revalider ici transformerait une base écrite sous une
                # version antérieure des règles en erreur 500 à la lecture. Le domaine valide ce qui
                # **entre**, l'adapter relit ce qui est **déjà entré** — même partage que partout
                # ailleurs dans ce fichier.
                return Logo(contenu=octets, type_logo=format_du_logo)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du logo.") from exc

    def empreinte_du_logo(self, tournoi_id: TournoiId, emplacement: EmplacementLogo) -> str | None:
        """Relit la seule empreinte — **aucun octet ne remonte** (cf. port)."""
        colonne = _colonne_d_empreinte(emplacement)
        try:
            with self._session_factory() as session:
                ligne = session.execute(
                    select(colonne).where(IdentiteVisuelleORM.tournoi_id == tournoi_id)
                ).one_or_none()
                return None if ligne is None else ligne[0]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de l'empreinte du logo.") from exc

    def enregistrer_accents(
        self, tournoi_id: TournoiId, identite: IdentiteVisuelle
    ) -> IdentiteVisuelle:
        """Écrit les deux accents ; crée la ligne au besoin, **sans toucher aux logos**.

        ⚠️ Écrit `accent_primaire` / `accent_secondaire` — les accents **choisis** — et non
        `identite.accents`, qui est la propriété *effective* : celle-ci retombe sur les couleurs du
        club quand rien n'a été choisi, si bien qu'`enregistrer_accents(id, IdentiteVisuelle())`
        aurait persisté le rouge du club et fait basculer `reglee` à `true` sans qu'on ait rien
        réglé.
        """
        try:
            with self._session_factory() as session:
                ligne = _ligne_identite_ou_creation(session, tournoi_id)
                ligne.accent_primaire = _hex_ou_rien(identite.accent_primaire)
                ligne.accent_secondaire = _hex_ou_rien(identite.accent_secondaire)
                session.commit()
                return _lire_reglages_identite(session, tournoi_id)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec d'enregistrement des accents.") from exc

    def enregistrer_logo(
        self, tournoi_id: TournoiId, emplacement: EmplacementLogo, logo: Logo | None
    ) -> IdentiteVisuelle:
        """Remplace ou efface **un** emplacement ; l'autre et les accents ne bougent pas.

        Les trois colonnes du triplet sont écrites **ensemble** — octets, type MIME et empreinte —
        dans les deux sens. C'est ici, et uniquement ici, que tient l'invariant « les trois `NULL`,
        ou aucune » que le schéma ne pose pas.
        """
        try:
            with self._session_factory() as session:
                ligne = _ligne_identite_ou_creation(session, tournoi_id)
                _ecrire_le_logo(ligne, emplacement, logo)
                session.commit()
                return _lire_reglages_identite(session, tournoi_id)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec d'enregistrement du logo.") from exc


def _ligne_identite_ou_creation(session: Session, tournoi_id: TournoiId) -> IdentiteVisuelleORM:
    """Renvoie la ligne d'identité du tournoi, en la créant **sans accents** si besoin.

    La création à la volée permet de déposer un logo **sans avoir réglé de couleur** : les deux
    gestes sont indépendants à l'écran, ils doivent l'être en base. Et la ligne naît avec ses
    accents à `NULL`, jamais avec ceux du club — y semer un défaut ferait qu'un tournoi dont on a
    seulement déposé le logo se présenterait comme « réglé ». C'est exactement le défaut qu'un test
    d'API a relevé sur la première rédaction.
    """
    ligne = session.get(IdentiteVisuelleORM, tournoi_id)
    if ligne is None:
        ligne = IdentiteVisuelleORM(tournoi_id=tournoi_id)
        session.add(ligne)
    return ligne


def _lire_reglages_identite(session: Session, tournoi_id: TournoiId) -> IdentiteVisuelle:
    """Projection **sans blob** : les accents éventuels, et la seule *présence* de chaque logo.

    On projette les **empreintes** — de courtes chaînes — plus un `IS NOT NULL` évalué par SQLite :
    aucun octet ne remonte jusqu'à Python, là où un `len(...) > 0` côté Python les aurait tous
    chargés pour n'en garder qu'un booléen. Aucune ligne rend l'identité **vide**, pas `None` : un
    tournoi a toujours une identité, simplement entièrement héritée (défaut porté par l'agrégat).
    """
    ligne = session.execute(
        select(
            IdentiteVisuelleORM.accent_primaire,
            IdentiteVisuelleORM.accent_secondaire,
            IdentiteVisuelleORM.logo_evenement_empreinte,
            IdentiteVisuelleORM.logo_club_empreinte,
            # Toujours **sans** blob : `is_not(None)` s'évalue dans SQLite, les octets ne remontent
            # pas. Sert uniquement à confronter les deux lectures de « y a-t-il un logo ? ».
            IdentiteVisuelleORM.logo_evenement.is_not(None),
            IdentiteVisuelleORM.logo_club.is_not(None),
        ).where(IdentiteVisuelleORM.tournoi_id == tournoi_id)
    ).one_or_none()
    if ligne is None:
        return IdentiteVisuelle()
    primaire, secondaire, empreinte_evenement, empreinte_club, a_evenement, a_club = ligne
    # ⚠️ Deux lectures pour un même fait, depuis que l'empreinte existe : cette projection déduit la
    # présence de l'empreinte, la route des octets la déduit du blob. Une ligne où elles divergent
    # ferait dire « aucun logo » à `/identite` pendant que `/identite/logos/{…}` en sert un — sur la
    # seule paire de routes que l'écran de salle appelle ensemble. SQLite ne sait pas exprimer
    # l'invariant (pas de `CHECK` posé) ; on le vérifie donc ici, au seul endroit qui voit les deux.
    for empreinte, present in ((empreinte_evenement, a_evenement), (empreinte_club, a_club)):
        if (empreinte is None) != (not present):
            raise InfrastructureError("Identité visuelle incohérente en base.")
    # `Couleur.depuis_hex` lève une `DomainError` : sur une valeur écrite hors du chemin normal
    # (édition manuelle, restauration partielle), elle traverserait l'infra et sortirait en **422**
    # sur une lecture **publique** — en recopiant au passage la valeur de base dans le message
    # rendu au client. C'est une incohérence technique, donc un 500 typé : même partage que
    # `_vers_tournoi` en tête de ce module, qui documente déjà ce piège pour `GET /tournois`.
    try:
        accent_primaire = None if primaire is None else Couleur.depuis_hex(primaire)
        accent_secondaire = None if secondaire is None else Couleur.depuis_hex(secondaire)
    except DomainError as exc:
        raise InfrastructureError("Identité visuelle illisible en base.") from exc
    return IdentiteVisuelle(
        accent_primaire=accent_primaire,
        accent_secondaire=accent_secondaire,
        empreintes={
            emplacement: empreinte
            for emplacement, empreinte in (
                (EmplacementLogo.EVENEMENT, empreinte_evenement),
                (EmplacementLogo.CLUB, empreinte_club),
            )
            if empreinte is not None
        },
    )


def _hex_ou_rien(couleur: Couleur | None) -> str | None:
    """Forme persistée d'un accent **choisi** : sa notation `#rrggbb`, ou `NULL` s'il n'y en a pas.

    Une fonction plutôt qu'un ternaire écrit deux fois, pour que « absent en base = rien de choisi »
    n'ait qu'une seule écriture.
    """
    return None if couleur is None else couleur.hex


def _ecrire_le_logo(
    ligne: IdentiteVisuelleORM, emplacement: EmplacementLogo, logo: Logo | None
) -> None:
    """Écrit le triplet (octets, type MIME, empreinte) : les trois ensemble, ou trois `NULL`.

    ⚠️ Nommément, et non par `setattr(ligne, colonne.key, …)`. La clé y était une `str` : ni le nom
    de la colonne ni le type de la valeur n'étaient vérifiés, si bien que l'invariant le plus
    fragile du schéma — « les deux `NULL`, ou aucune », que SQLite ne sait pas exprimer — était
    précisément le seul endroit du module hors de portée de `mypy --strict` (relevé en revue).
    L'appariement reste écrit d'un seul endroit, ce qui était l'argument de la version d'origine.
    """
    octets = None if logo is None else logo.contenu
    type_mime = None if logo is None else logo.type_logo.value
    empreinte = None if logo is None else logo.empreinte
    if emplacement is EmplacementLogo.EVENEMENT:
        ligne.logo_evenement = octets
        ligne.logo_evenement_type = type_mime
        ligne.logo_evenement_empreinte = empreinte
    elif emplacement is EmplacementLogo.CLUB:
        ligne.logo_club = octets
        ligne.logo_club_type = type_mime
        ligne.logo_club_empreinte = empreinte
    else:  # pragma: no cover — `assert_never` fait de l'oubli une erreur de typage
        assert_never(emplacement)


def _colonne_d_empreinte(emplacement: EmplacementLogo) -> InstrumentedAttribute[str | None]:
    """La colonne d'empreinte d'un emplacement — pour la lire **seule**, sans son blob."""
    if emplacement is EmplacementLogo.EVENEMENT:
        return IdentiteVisuelleORM.logo_evenement_empreinte
    if emplacement is EmplacementLogo.CLUB:
        return IdentiteVisuelleORM.logo_club_empreinte
    assert_never(emplacement)


def _colonnes_du_logo(
    emplacement: EmplacementLogo,
) -> tuple[InstrumentedAttribute[bytes | None], InstrumentedAttribute[str | None]]:
    """Le couple (octets, type MIME) de l'emplacement, **pour la lecture** (`select`).

    L'écriture passe par `_ecrire_le_logo`, qui nomme les colonnes : ici, ce sont les attributs
    eux-mêmes qu'il faut, pour construire une projection sans charger les octets.
    """
    if emplacement is EmplacementLogo.EVENEMENT:
        return IdentiteVisuelleORM.logo_evenement, IdentiteVisuelleORM.logo_evenement_type
    if emplacement is EmplacementLogo.CLUB:
        return IdentiteVisuelleORM.logo_club, IdentiteVisuelleORM.logo_club_type
    # `assert_never` comme sur le chemin d'écriture : un `return` de repli lisait silencieusement
    # les colonnes du club pour un troisième emplacement, alors que mypy voyait l'oubli à
    # l'écriture.
    assert_never(emplacement)
