"""Adapters repository SQLAlchemy — le **tir** : scores, séries, duels, forfaits, barrages.

Session courte par opération et pannes SQLAlchemy enveloppées en `InfrastructureError` : ADR-0005.
Le découpage de l'ancien `repositories.py` est l'action 2 de
[l'audit de maintenabilité](../../../../docs/audit-maintenabilite.md).
"""

from __future__ import annotations

import datetime
import json
from collections.abc import Sequence
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql.elements import ColumnElement

from domain.archer import ArcherId
from domain.barrage import (
    BarrageDePlaces,
    BarrageId,
    TirBarrage,
)
from domain.blason import ZoneScore
from domain.depart import DepartId
from domain.duel import BaremeDuel, Barrage, Cote, Duel, MancheDuel
from domain.entree_audit import EntreeAudit
from domain.forfait import Forfait, NatureForfait
from domain.participant import GenreParticipant, Participant
from domain.phase import (
    PhaseId,
)
from domain.ports import Horloge
from domain.score import Score
from domain.serie import Serie, SerieId, Volee
from domain.tournoi import TournoiId
from infrastructure.db.models import (
    ArcherORM,
    BarrageORM,
    BarrageTirORM,
    DepartORM,
    DuelORM,
    ForfaitORM,
    ScoreORM,
    SerieORM,
    VoleeORM,
)
from infrastructure.db.repositories._mapping import _vers_barrage

# `AuditRepositorySQL` vit dans le thème `exploitation` mais s'annote ici : plusieurs
# adapters **co-écrivent** leur trace d'audit dans la même transaction (ADR-0035). Import
# direct et acyclique — `exploitation` n'importe aucun autre thème.
from infrastructure.db.repositories.exploitation import AuditRepositorySQL
from infrastructure.erreurs import InfrastructureError


def _vers_volee(ligne: VoleeORM) -> Volee:
    """Traduit une ligne ORM en value object de domaine `Volee` (E04US002).

    `valeurs` est écrit comme un tableau JSON de codes de zone (même procédé que
    `BlasonORM.zones`). Un contenu illisible **ou** un code hors `ZoneScore` est une **incohérence
    technique** — le repository en est le seul rédacteur — donc enveloppée en `InfrastructureError`
    (ADR-0007), jamais laissée fuir en value object invalide. ⚠️ Le verrou n'est pas une colonne :
    `validee_par` non `NULL` **est** le verrou (`domain.serie.Volee.verrouillee`).
    """
    try:
        valeurs = tuple(ZoneScore(v) for v in json.loads(ligne.valeurs))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise InfrastructureError("Valeurs de volée illisibles.") from exc
    return Volee(
        numero=ligne.numero,
        valeurs=valeurs,
        saisie_par=ligne.saisie_par,
        validee_par=ligne.validee_par,
    )


def _vers_serie(ligne: SerieORM, volees: Sequence[VoleeORM]) -> Serie:
    """Traduit une ligne ORM `serie` et ses volées enfants en agrégat de domaine `Serie`.

    Les `volees` sont supposées **déjà triées par numéro** par l'appelant (le repository les relit
    `ORDER BY numero`) : l'agrégat conserve l'ordre du barème.
    """
    return Serie(
        tournoi_id=ligne.tournoi_id,
        archer_id=ligne.archer_id,
        phase_id=ligne.phase_id,
        volees=tuple(_vers_volee(v) for v in volees),
        id=ligne.id,
    )


def _valeurs_json(volee: Volee) -> str:
    """Sérialise les zones d'une volée en tableau JSON de codes (procédé de `BlasonORM.zones`)."""
    return json.dumps([zone.value for zone in volee.valeurs])


def _manches_json(duel: Duel) -> str:
    """Sérialise les manches d'un duel en JSON (E04US013) : `[{numero, haut:[…], bas:[…]}]`."""
    return json.dumps(
        [
            {
                "numero": manche.numero,
                "haut": [zone.value for zone in manche.volee_haut.valeurs],
                "bas": [zone.value for zone in manche.volee_bas.valeurs],
            }
            for manche in duel.manches
        ]
    )


def _barrage_json(duel: Duel) -> str | None:
    """Sérialise le barrage d'un duel en JSON (`None` si aucun) : `{haut, bas, gagnant}`."""
    if duel.barrage is None:
        return None
    designe = duel.barrage.gagnant_designe
    return json.dumps(
        {
            "haut": duel.barrage.fleche_haut.value,
            "bas": duel.barrage.fleche_bas.value,
            "gagnant": None if designe is None else designe.value,
        }
    )


def _vers_duel(ligne: DuelORM, *, bareme: BaremeDuel) -> Duel:
    """Réhydrate un `Duel` d'une ligne ORM, complété du seul **barème** (ADR-0049).

    Le tir (manches, barrage, validateur) **et l'identité des duellistes** viennent de la base ; le
    **barème** (dérivé de l'arme, re-résolu à la lecture) est **fourni** par l'appelant. Les
    duellistes stockés **ancrent** le tir : l'appelant compare l'identité réhydratée aux occupants
    recalculés pour détecter une divergence (ADR-0049 §4). Un contenu JSON illisible est une
    incohérence technique (`InfrastructureError`), le repository en étant le seul rédacteur.
    """
    participant_haut = Participant(genre=GenreParticipant(ligne.haut_genre), ref_id=ligne.haut_ref)
    participant_bas = Participant(genre=GenreParticipant(ligne.bas_genre), ref_id=ligne.bas_ref)
    try:
        manches = tuple(
            MancheDuel(
                numero=int(brute["numero"]),
                volee_haut=Volee(
                    numero=int(brute["numero"]),
                    valeurs=tuple(ZoneScore(v) for v in brute["haut"]),
                ),
                volee_bas=Volee(
                    numero=int(brute["numero"]),
                    valeurs=tuple(ZoneScore(v) for v in brute["bas"]),
                ),
            )
            for brute in json.loads(ligne.manches)
        )
        barrage = None
        if ligne.barrage is not None:
            brut = json.loads(ligne.barrage)
            gagnant = brut["gagnant"]
            barrage = Barrage(
                fleche_haut=ZoneScore(brut["haut"]),
                fleche_bas=ZoneScore(brut["bas"]),
                gagnant_designe=None if gagnant is None else Cote(gagnant),
            )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise InfrastructureError("Tir de duel illisible.") from exc
    return Duel(
        bareme=bareme,
        participant_haut=participant_haut,
        participant_bas=participant_bas,
        manches=manches,
        barrage=barrage,
        validee_par=ligne.validee_par,
    )


class ScoreRepositorySQL:
    """Adapter SQLite du port `ScoreRepository` (E00US011, E02US003)."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def ajouter(self, score: Score) -> Score:
        """Persiste le score et le renvoie avec son identifiant attribué."""
        try:
            with self._session_factory() as session:
                ligne = ScoreORM(archer_id=score.archer_id, points=score.points)
                session.add(ligne)
                session.commit()
                return Score(archer_id=ligne.archer_id, points=ligne.points, id=ligne.id)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du score.") from exc

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Score]:
        """Renvoie tous les scores des archers d'un tournoi (jointure archer→tournoi)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(ScoreORM)
                    .join(ArcherORM, ScoreORM.archer_id == ArcherORM.id)
                    .where(ArcherORM.tournoi_id == tournoi_id)
                ).scalars()
                return [
                    Score(archer_id=ligne.archer_id, points=ligne.points, id=ligne.id)
                    for ligne in lignes
                ]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des scores du tournoi.") from exc

    def par_archer(self, archer_id: ArcherId) -> list[Score]:
        """Renvoie les scores d'un archer (liste éventuellement vide) — E02US003."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(ScoreORM).where(ScoreORM.archer_id == archer_id)
                ).scalars()
                return [
                    Score(archer_id=ligne.archer_id, points=ligne.points, id=ligne.id)
                    for ligne in lignes
                ]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des scores de l'archer.") from exc


class SerieRepositorySQL:
    """Adapter SQLite du port `SerieRepository` (E04US002) — série + volées enfants.

    La saisie réécrit **toute** la série à chaque opération : l'écriture est un **purge +
    réinsertion** des volées, la série étant la source de vérité. `enregistrer_avec_trace` réalise
    la **couture de session partagée** (ADR-0035) : série et entrée d'audit dans **un seul
    `commit`**, d'où l'`AuditRepositorySQL` injecté — collaboration infra → infra que le port du
    domaine ignore. ⚠️ Le `created_at` d'une volée est **préservé par numéro** (ex-017).
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        audit_repository: AuditRepositorySQL,
        horloge: Horloge,
    ) -> None:
        self._session_factory = session_factory
        self._audit = audit_repository
        self._horloge = horloge

    def par_archer(self, phase_id: PhaseId, archer_id: ArcherId) -> Serie | None:
        """Relit la feuille de l'archer **dans cette phase** (volées triées par numéro), ou `None`.

        La clé est `(phase_id, archer_id)` depuis E05US025 : un archer peut tenir plusieurs feuilles
        dans un même tournoi, une par qualification tirée (ADR-0082).
        """
        try:
            with self._session_factory() as session:
                ligne = session.execute(
                    select(SerieORM).where(
                        SerieORM.phase_id == phase_id,
                        SerieORM.archer_id == archer_id,
                    )
                ).scalar_one_or_none()
                if ligne is None:
                    return None
                return _vers_serie(ligne, self._volees(session, ligne.id))
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture de la série.") from exc

    def par_phase(self, phase_id: PhaseId) -> list[Serie]:
        """Relit les feuilles d'une **phase** (volées triées par numéro), pour son classement.

        C'est la lecture dont le classement a besoin depuis E05US025 : le cumul et le départage
        d'une qualification ne regardent que les flèches tirées **dans celle-ci**. `par_tournoi`
        mélangerait les deux tours de l'exemple d'ADR-0082.
        """
        return self._series_de(SerieORM.phase_id == phase_id, "de la phase")

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Serie]:
        """Relit toutes les séries d'un tournoi, **toutes phases confondues**.

        ⚠️ Vue d'ensemble : un archer y figure une fois **par phase tirée**. Indexer le résultat par
        `archer_id` n'en garderait qu'une, au hasard de l'ordre — c'est `par_phase` qu'il faut.
        """
        return self._series_de(SerieORM.tournoi_id == tournoi_id, "du tournoi")

    def _series_de(self, critere: ColumnElement[bool], quoi: str) -> list[Serie]:
        """Les séries répondant au critère, avec leurs volées — **deux requêtes**, pas de N+1.

        Les séries d'abord, puis **toutes** leurs volées d'un bloc regroupées par série. L'ordre des
        séries n'est pas garanti (le classement trie) ; les volées de chacune le sont, par numéro
        (même contrat que `par_archer`). `quoi` ne sert qu'au message d'erreur.
        """
        try:
            with self._session_factory() as session:
                series = session.execute(select(SerieORM).where(critere)).scalars().all()
                if not series:
                    return []
                volees_par_serie: dict[SerieId, list[VoleeORM]] = {}
                lignes_volees = (
                    session.execute(
                        select(VoleeORM)
                        .where(VoleeORM.serie_id.in_([s.id for s in series]))
                        .order_by(VoleeORM.serie_id, VoleeORM.numero)
                    )
                    .scalars()
                    .all()
                )
                for volee in lignes_volees:
                    volees_par_serie.setdefault(volee.serie_id, []).append(volee)
                return [_vers_serie(s, volees_par_serie.get(s.id, [])) for s in series]
        except SQLAlchemyError as exc:
            raise InfrastructureError(f"Échec de lecture des séries {quoi}.") from exc

    def horodatages(self, phase_id: PhaseId, archer_id: ArcherId) -> dict[int, datetime.datetime]:
        """Le « quand » (`created_at`, UTC-aware) de chaque volée de l'archer, par **numéro** — `{}`
        s'il n'a pas de série.

        Chemin de lecture/consultation du « quand » (ex-017), tenu **à l'écart du domaine** `Volee`
        (métadonnée de persistance, arbitrage de revue) : l'API le joint à la série par numéro pour
        afficher « volée N saisie par … à HH:MM ». UTC réattaché comme l'`horodatage` d'audit
        (SQLite stocke sans fuseau, l'application n'écrit que de l'UTC).
        """
        try:
            with self._session_factory() as session:
                ligne = session.execute(
                    select(SerieORM).where(
                        SerieORM.phase_id == phase_id,
                        SerieORM.archer_id == archer_id,
                    )
                ).scalar_one_or_none()
                if ligne is None:
                    return {}
                return {
                    volee.numero: (
                        volee.created_at
                        if volee.created_at.tzinfo is not None
                        else volee.created_at.replace(tzinfo=datetime.UTC)
                    )
                    for volee in self._volees(session, ligne.id)
                }
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des horodatages de volées.") from exc

    def enregistrer(self, serie: Serie) -> Serie:
        """Persiste une série (saisie sans trace) — **une** transaction (parent + volées)."""
        try:
            with self._session_factory() as session:
                ligne = self._poser_serie(session, serie)
                session.commit()
                return _vers_serie(ligne, self._volees(session, ligne.id))
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance de la série.") from exc

    def enregistrer_avec_trace(self, serie: Serie, entree: EntreeAudit) -> Serie:
        """Persiste la série **et** son entrée d'audit dans **une seule transaction** (ADR-0035).

        Tout ou rien : la série est réécrite, la trace est ajoutée dans **la même** session (via
        `AuditRepositorySQL.consigner_dans`, qui ne commit pas), puis un **unique** `commit` scelle
        les deux. Un échec avant le commit ne laisse ni validation/correction non tracée, ni trace
        fantôme (testé sur injection d'échec).
        """
        try:
            with self._session_factory() as session:
                ligne = self._poser_serie(session, serie)
                self._audit.consigner_dans(session, entree)
                session.commit()
                return _vers_serie(ligne, self._volees(session, ligne.id))
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance de la série et de sa trace.") from exc

    def _poser_serie(self, session: Session, serie: Serie) -> SerieORM:
        """Upsert le parent `serie` (clé métier `phase_id, archer_id`) et réécrit ses volées.

        Ne commit pas — l'appelant tient la transaction. Les volées sont **purgées puis
        réinsérées** ; `flush` attribue l'id d'une série nouvelle avant de rattacher ses volées. ⚠️
        Le `created_at` de chaque volée est **préservé par numéro** : on relit les horodatages
        avant la purge et on les réapplique, sans quoi le « quand » serait réinitialisé à chaque
        sauvegarde (ex-017). Une volée nouvelle est datée de l'instant courant (`Horloge`).
        """
        ligne = self._ligne_serie(session, serie)
        horodatages = {v.numero: v.created_at for v in self._volees(session, ligne.id)}
        maintenant = self._horloge.maintenant()
        session.execute(delete(VoleeORM).where(VoleeORM.serie_id == ligne.id))
        session.add_all(
            VoleeORM(
                serie_id=ligne.id,
                numero=volee.numero,
                valeurs=_valeurs_json(volee),
                saisie_par=volee.saisie_par,
                validee_par=volee.validee_par,
                created_at=horodatages.get(volee.numero, maintenant),
            )
            for volee in serie.volees
        )
        return ligne

    def _ligne_serie(self, session: Session, serie: Serie) -> SerieORM:
        """Retrouve la ligne parente **par sa clé métier** `(phase_id, archer_id)`, ou la crée.

        L'identité d'une feuille **est** son couple `(phase, archer)` (`uq_serie_phase_archer`). On
        ne cherche **pas** par `serie.id` : cette micro-optimisation ouvrait une corruption
        silencieuse — un `id` incohérent avec la clé métier aurait fait réécrire les volées sur la
        **mauvaise** série. ⚠️ **La clé est descendue du tournoi à la phase** (E05US025, ADR-0082)
        : sous l'ancienne, une seconde qualification réécrivait les volées de la première.
        """
        ligne = session.execute(
            select(SerieORM).where(
                SerieORM.phase_id == serie.phase_id,
                SerieORM.archer_id == serie.archer_id,
            )
        ).scalar_one_or_none()
        if ligne is None:
            ligne = SerieORM(
                tournoi_id=serie.tournoi_id,
                archer_id=serie.archer_id,
                phase_id=serie.phase_id,
            )
            session.add(ligne)
            session.flush()
        return ligne

    def _volees(self, session: Session, serie_id: SerieId) -> Sequence[VoleeORM]:
        """Les volées d'une série, triées par numéro (ordre du barème)."""
        return (
            session.execute(
                select(VoleeORM).where(VoleeORM.serie_id == serie_id).order_by(VoleeORM.numero)
            )
            .scalars()
            .all()
        )


class DuelRepositorySQL:
    """Adapter SQLite du port `DuelRepository` — le tir d'un match du tableau (E04US013, ADR-0049).

    On ne persiste que le **tir** (manches, barrage, validateur), keyé `(phase_id, match_numero)` :
    ni barème ni participants (l'appariement, recalculé du classement — ADR-0048). `charger`
    réhydrate donc un `Duel` en **recevant** ce contexte du service. Écriture idempotente par upsert
    sur la clé composite (patron `PlacementTableauRepositorySQL`).
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def numeros_enregistres(self, phase_id: PhaseId) -> frozenset[int]:
        """Les `match_numero` de la phase porteurs d'un tir (pour ne charger que ceux-là)."""
        try:
            with self._session_factory() as session:
                numeros = session.execute(
                    select(DuelORM.match_numero).where(DuelORM.phase_id == phase_id)
                ).scalars()
                return frozenset(numeros)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des duels d'une phase.") from exc

    def charger(self, phase_id: PhaseId, match_numero: int, *, bareme: BaremeDuel) -> Duel | None:
        """Réhydrate le duel d'un match (duellistes stockés + barème), ou `None` si absent."""
        try:
            with self._session_factory() as session:
                ligne = session.get(DuelORM, (phase_id, match_numero))
                if ligne is None:
                    return None
                return _vers_duel(ligne, bareme=bareme)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture d'un duel.") from exc

    def enregistrer(self, phase_id: PhaseId, match_numero: int, duel: Duel) -> Duel:
        """Persiste le tir **et l'identité des duellistes** (upsert sur `(phase, match)`)."""
        try:
            with self._session_factory() as session:
                ligne = session.get(DuelORM, (phase_id, match_numero))
                if ligne is None:
                    session.add(
                        DuelORM(
                            phase_id=phase_id,
                            match_numero=match_numero,
                            haut_genre=duel.participant_haut.genre.value,
                            haut_ref=duel.participant_haut.ref_id,
                            bas_genre=duel.participant_bas.genre.value,
                            bas_ref=duel.participant_bas.ref_id,
                            manches=_manches_json(duel),
                            barrage=_barrage_json(duel),
                            validee_par=duel.validee_par,
                        )
                    )
                else:
                    ligne.haut_genre = duel.participant_haut.genre.value
                    ligne.haut_ref = duel.participant_haut.ref_id
                    ligne.bas_genre = duel.participant_bas.genre.value
                    ligne.bas_ref = duel.participant_bas.ref_id
                    ligne.manches = _manches_json(duel)
                    ligne.barrage = _barrage_json(duel)
                    ligne.validee_par = duel.validee_par
                session.commit()
                return duel
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance d'un duel.") from exc


def _vers_forfait(ligne: ForfaitORM) -> Forfait:
    """Traduit une ligne ORM en agrégat de domaine `Forfait` (E04US015, ADR-0050).

    `nature` : la valeur relue redevient l'énumération `NatureForfait`. `declare_le` : SQLite stocke
    un `DateTime` **sans fuseau** ; on lui **réattache UTC** (le service n'écrit que de l'UTC via
    `Horloge`), round-trip fidèle comme l'horodatage d'audit.
    """
    declare_le = ligne.declare_le
    if declare_le.tzinfo is None:
        declare_le = declare_le.replace(tzinfo=datetime.UTC)
    return Forfait(
        tournoi_id=ligne.tournoi_id,
        archer_id=ligne.archer_id,
        phase_id=ligne.phase_id,
        nature=NatureForfait(ligne.nature),
        declare_par=ligne.declare_par,
        declare_le=declare_le,
        motif=ligne.motif,
        id=ligne.id,
    )


class ForfaitRepositorySQL:
    """Adapter SQLite du port `ForfaitRepository` (E04US015, ADR-0050) — forfait + trace atomiques.

    `declarer_avec_trace` / `annuler_avec_trace` co-écrivent le forfait (ajout / suppression) **et**
    son entrée d'audit dans **une seule session, un seul `commit`** (ADR-0035, comme
    `SerieRepositorySQL`) — d'où l'`AuditRepositorySQL` injecté (collaboration infra → infra ; le
    port du domaine ignore la couture de session). L'entrée arrive **déjà construite et datée** par
    le service (via `Horloge`) ; le forfait porte lui aussi sa propre date de déclaration.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        audit_repository: AuditRepositorySQL,
    ) -> None:
        self._session_factory = session_factory
        self._audit = audit_repository

    def par_tournoi(self, tournoi_id: TournoiId) -> list[Forfait]:
        """Tous les forfaits d'un tournoi (ordre non garanti)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(ForfaitORM).where(ForfaitORM.tournoi_id == tournoi_id)
                ).scalars()
                return [_vers_forfait(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des forfaits du tournoi.") from exc

    def par_phase(self, phase_id: PhaseId) -> list[Forfait]:
        """Les forfaits déclarés dans une phase (qualif → classement ; tableau → walkover duels)."""
        try:
            with self._session_factory() as session:
                lignes = session.execute(
                    select(ForfaitORM).where(ForfaitORM.phase_id == phase_id)
                ).scalars()
                return [_vers_forfait(ligne) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des forfaits de la phase.") from exc

    def par_archer_et_phase(
        self, tournoi_id: TournoiId, archer_id: ArcherId, phase_id: PhaseId
    ) -> Forfait | None:
        """Le forfait de cet archer dans cette phase, ou `None` (garde de doublon / annulation)."""
        try:
            with self._session_factory() as session:
                ligne = session.execute(
                    select(ForfaitORM).where(
                        ForfaitORM.tournoi_id == tournoi_id,
                        ForfaitORM.archer_id == archer_id,
                        ForfaitORM.phase_id == phase_id,
                    )
                ).scalar_one_or_none()
                return None if ligne is None else _vers_forfait(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du forfait.") from exc

    def declarer_avec_trace(self, forfait: Forfait, entree: EntreeAudit) -> Forfait:
        """Insère le forfait **et** sa trace dans **une seule transaction** (tout ou rien)."""
        try:
            with self._session_factory() as session:
                ligne = ForfaitORM(
                    tournoi_id=forfait.tournoi_id,
                    archer_id=forfait.archer_id,
                    phase_id=forfait.phase_id,
                    nature=forfait.nature.value,
                    declare_par=forfait.declare_par,
                    declare_le=forfait.declare_le,
                    motif=forfait.motif,
                )
                session.add(ligne)
                self._audit.consigner_dans(session, entree)
                session.commit()
                return _vers_forfait(ligne)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du forfait et de sa trace.") from exc

    def annuler_avec_trace(self, forfait: Forfait, entree: EntreeAudit) -> None:
        """Supprime le forfait (`forfait.id`) et consigne sa trace d'annulation, atomiquement."""
        try:
            with self._session_factory() as session:
                session.execute(delete(ForfaitORM).where(ForfaitORM.id == forfait.id))
                self._audit.consigner_dans(session, entree)
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de l'annulation du forfait et de sa trace.") from exc


class BarrageRepositorySQL:
    """Adapter SQLite du port `BarrageRepository` (E06US003, ADR-0066).

    Le grain d'écriture est la **manche** : `enregistrer_manche` remplace en bloc les tirs d'un
    numéro, ce qui fait de la ressaisie le mode de **correction**. Suppression puis insertion dans
    **une seule transaction** — un remplacement à moitié appliqué donnerait un verdict faux et
    plausible. ⚠️ **Le verdict n'est jamais persisté** : il se recalcule depuis les tirs.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def par_depart(self, depart_id: DepartId) -> list[BarrageDePlaces]:
        """Tous les barrages **d'un départ**, **clos compris** — ce sont eux qui portent les
        verdicts déjà acquis, et les filtrer ferait retomber les rangs tranchés en ex æquo."""
        return self._lire(BarrageORM.depart_id == depart_id)

    def par_tournoi(self, tournoi_id: TournoiId) -> list[BarrageDePlaces]:
        """Les barrages de **tous les départs** d'un tournoi (vue transverse, jointure).

        Le lien au tournoi n'est plus direct depuis ADR-0075 : il passe par le départ.
        """
        return self._lire(
            BarrageORM.depart_id.in_(select(DepartORM.id).where(DepartORM.tournoi_id == tournoi_id))
        )

    def _lire(self, critere: Any) -> list[BarrageDePlaces]:
        """Relit les barrages satisfaisant `critere`, avec leurs manches (source unique)."""
        try:
            with self._session_factory() as session:
                lignes = list(
                    session.execute(
                        select(BarrageORM).where(critere).order_by(BarrageORM.id)
                    ).scalars()
                )
                if not lignes:
                    return []
                tirs = list(
                    session.execute(
                        select(BarrageTirORM)
                        .where(BarrageTirORM.barrage_id.in_([ligne.id for ligne in lignes]))
                        .order_by(BarrageTirORM.id)
                    ).scalars()
                )
                par_barrage: dict[int, list[BarrageTirORM]] = {}
                for tir in tirs:
                    par_barrage.setdefault(tir.barrage_id, []).append(tir)
                return [_vers_barrage(ligne, par_barrage.get(ligne.id, [])) for ligne in lignes]
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture des barrages du tournoi.") from exc

    def par_id(self, barrage_id: BarrageId) -> BarrageDePlaces | None:
        """Le barrage d'identifiant donné avec toutes ses manches, ou `None`."""
        try:
            with self._session_factory() as session:
                ligne = session.get(BarrageORM, barrage_id)
                if ligne is None:
                    return None
                tirs = list(
                    session.execute(
                        select(BarrageTirORM)
                        .where(BarrageTirORM.barrage_id == barrage_id)
                        .order_by(BarrageTirORM.id)
                    ).scalars()
                )
                return _vers_barrage(ligne, tirs)
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de lecture du barrage.") from exc

    def ouvrir(self, barrage: BarrageDePlaces) -> BarrageDePlaces:
        """Persiste un barrage annoncé (sans tir) et le renvoie avec son identifiant."""
        try:
            with self._session_factory() as session:
                ligne = BarrageORM(
                    depart_id=barrage.depart_id,
                    phase_id=barrage.phase_id,
                    portee=barrage.portee.value,
                    reference=barrage.reference,
                    rang_dispute=barrage.rang_dispute,
                    participants_json=json.dumps(
                        [participant.ref_id for participant in barrage.participants]
                    ),
                    clos=barrage.clos,
                    cree_le=barrage.cree_le,
                )
                session.add(ligne)
                session.commit()
                return _vers_barrage(ligne, [])
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de persistance du barrage.") from exc

    def enregistrer_manche(
        self, barrage_id: BarrageId, manche: int, tirs: Sequence[TirBarrage]
    ) -> BarrageDePlaces:
        """Remplace **en bloc** les tirs de cette manche, puis renvoie le barrage rechargé."""
        try:
            with self._session_factory() as session:
                # `>=` et non `==` : réécrire une manche **tronque les suivantes**. Corriger la
                # manche 1 change la partition, donc les retirs qui en découlaient n'ont plus
                # d'objet — les garder produirait un agrégat que le moteur refuse à la relecture,
                # c'est-à-dire un classement en 422 permanent.
                session.execute(
                    delete(BarrageTirORM).where(
                        BarrageTirORM.barrage_id == barrage_id,
                        BarrageTirORM.manche >= manche,
                    )
                )
                for tir in tirs:
                    session.add(
                        BarrageTirORM(
                            barrage_id=barrage_id,
                            manche=manche,
                            archer_id=tir.participant.ref_id,
                            score=tir.score,
                            distance_au_centre=tir.distance_au_centre,
                        )
                    )
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec d'enregistrement de la manche de barrage.") from exc
        recharge = self.par_id(barrage_id)
        if recharge is None:  # pragma: no cover — l'appelant a vérifié l'existence
            raise InfrastructureError("Le barrage a disparu pendant l'enregistrement de sa manche.")
        return recharge

    def supprimer(self, barrage_id: BarrageId) -> None:
        """Supprime un barrage **et ses tirs** — les tirs d'abord, ils le référencent."""
        try:
            with self._session_factory() as session:
                session.execute(delete(BarrageTirORM).where(BarrageTirORM.barrage_id == barrage_id))
                session.execute(delete(BarrageORM).where(BarrageORM.id == barrage_id))
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de suppression du barrage.") from exc

    def rouvrir(self, barrage_id: BarrageId) -> BarrageDePlaces:
        """Lève la clôture (une manche a été saisie après coup)."""
        return self._basculer_cloture(barrage_id, clos=False)

    def clore(self, barrage_id: BarrageId) -> BarrageDePlaces:
        """Marque le barrage comme clos — le juge a acté le verdict, plus de retir attendu."""
        return self._basculer_cloture(barrage_id, clos=True)

    def _basculer_cloture(self, barrage_id: BarrageId, *, clos: bool) -> BarrageDePlaces:
        """Pose ou lève le drapeau de clôture, puis recharge l'agrégat."""
        try:
            with self._session_factory() as session:
                session.execute(
                    update(BarrageORM).where(BarrageORM.id == barrage_id).values(clos=clos)
                )
                session.commit()
        except SQLAlchemyError as exc:
            raise InfrastructureError("Échec de mise à jour de la clôture du barrage.") from exc
        recharge = self.par_id(barrage_id)
        if recharge is None:  # pragma: no cover — l'appelant a vérifié l'existence
            raise InfrastructureError("Le barrage a disparu pendant sa clôture.")
        return recharge
