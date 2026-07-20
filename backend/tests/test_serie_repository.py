"""Tests d'intégration du repository SQL de saisie de qualification (E04US002, tranche PR2a).

Exerce `SerieRepositorySQL` sur une **vraie base** migrée (`alembic upgrade head`) : aller-retour
série + volées enfants (les valeurs reviennent en `ZoneScore`, les marqueurs et le verrou sont
fidèles), lecture `par_archer`, **upsert** par clé métier (ré-enregistrer ne duplique pas), la
**couture d'atomicité** acte↔trace (ADR-0035 : les deux, ou ni l'un ni l'autre sur injection
d'échec), et la **cascade** de suppression `archer` → `serie` → `volee`.

Ces tests sont écrits **après** l'implémentation (règle 9 : repository/câblage, pas d'oracle en
jeu). Une série référence un tournoi et un archer (FK) : chaque contexte les crée d'abord.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from domain.archer import Archer
from domain.blason import ZoneScore
from domain.categorie import Categorie
from domain.entree_audit import ActionAuditee, EntreeAudit
from domain.ports import Horloge
from domain.serie import Serie, Volee
from domain.tournoi import Tournoi
from infrastructure.db import (
    ArcherRepositorySQL,
    AuditRepositorySQL,
    CategorieRepositorySQL,
    Database,
    SerieRepositorySQL,
    TournoiRepositorySQL,
)
from infrastructure.erreurs import InfrastructureError
from infrastructure.horloge import HorlogeSysteme

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)
_QUAND = datetime.datetime(2026, 3, 14, 10, 42, tzinfo=datetime.UTC)
_PLUS_TARD = datetime.datetime(2026, 3, 14, 11, 15, tzinfo=datetime.UTC)


class HorlogeReglable:
    """Horloge de test conforme au port `Horloge` : renvoie un instant **réglable** à la main.

    Sert à observer le `created_at` des volées : on fige l'instant d'une saisie, on l'avance, puis
    on ré-enregistre pour prouver que le « quand » d'une volée déjà saisie **ne bouge pas**.
    """

    def __init__(self, instant: datetime.datetime) -> None:
        self._instant = instant

    def maintenant(self) -> datetime.datetime:
        return self._instant

    def avancer_a(self, instant: datetime.datetime) -> None:
        self._instant = instant


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


def _contexte(tmp_path: Path) -> tuple[Database, int, int]:
    """Migre une base jetable, crée tournoi + catégorie + archer ; renvoie base, tournoi, archer."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    tournoi = TournoiRepositorySQL(db.session_factory).ajouter(Tournoi.creer("Salle 18m", _DATE))
    assert tournoi.id is not None
    categorie = CategorieRepositorySQL(db.session_factory).ajouter(
        Categorie.creer(tournoi.id, "Senior 1 H")
    )
    assert categorie.id is not None
    archer = ArcherRepositorySQL(db.session_factory).ajouter(
        Archer.creer("Martin", "Alice", tournoi.id, categorie.id)
    )
    assert archer.id is not None
    return db, tournoi.id, archer.id


def _serie(tournoi_id: int, archer_id: int, *, validee: str | None = None) -> Serie:
    """Une série à deux volées ; la 2ᵉ est validée si `validee` est fourni (donc verrouillée)."""
    return Serie(
        tournoi_id=tournoi_id,
        archer_id=archer_id,
        volees=(
            Volee(
                numero=1,
                valeurs=(ZoneScore("10"), ZoneScore("9"), ZoneScore("8")),
                saisie_par="DURAND Jean",
            ),
            Volee(
                numero=2,
                valeurs=(ZoneScore("7"), ZoneScore("6"), ZoneScore("M")),
                saisie_par="DURAND Jean",
                validee_par=validee,
            ),
        ),
    )


def _repo(db: Database, horloge: Horloge | None = None) -> SerieRepositorySQL:
    return SerieRepositorySQL(
        db.session_factory,
        AuditRepositorySQL(db.session_factory),
        horloge or HorlogeSysteme(),
    )


def test_enregistrer_puis_par_archer(tmp_path: Path) -> None:
    """Aller-retour fidèle : valeurs en `ZoneScore`, numéros ordonnés, marqueur de saisie gardé."""
    db, tournoi_id, archer_id = _contexte(tmp_path)
    try:
        repo = _repo(db)
        enregistree = repo.enregistrer(_serie(tournoi_id, archer_id))

        assert enregistree.id is not None
        relue = repo.par_archer(tournoi_id, archer_id)
        assert relue == enregistree
        assert relue is not None
        volee_1 = relue.volee(1)
        assert volee_1 is not None
        assert volee_1.valeurs == (ZoneScore("10"), ZoneScore("9"), ZoneScore("8"))
        assert volee_1.saisie_par == "DURAND Jean"
    finally:
        db.engine.dispose()


def test_par_archer_aucune_serie(tmp_path: Path) -> None:
    """Sans série encore saisie, la lecture rend `None` (pas une série vide)."""
    db, tournoi_id, archer_id = _contexte(tmp_path)
    try:
        assert _repo(db).par_archer(tournoi_id, archer_id) is None
    finally:
        db.engine.dispose()


def test_par_tournoi_vide_rend_liste_vide(tmp_path: Path) -> None:
    """Sans aucune série, `par_tournoi` rend une liste vide (support du classement, E06US001)."""
    db, tournoi_id, _ = _contexte(tmp_path)
    try:
        assert _repo(db).par_tournoi(tournoi_id) == []
    finally:
        db.engine.dispose()


def test_par_tournoi_rend_toutes_les_series_volees_ordonnees(tmp_path: Path) -> None:
    """`par_tournoi` rend la série de chaque archer, volées triées par numéro (E06US001).

    Deux archers, une série chacun : on relit l'ensemble d'un bloc (pas archer par archer), chaque
    série portant ses volées dans l'ordre du barème — ce dont le classement a besoin pour le cumul
    et le décompte de 10/9.
    """
    db, tournoi_id, alice_id = _contexte(tmp_path)
    try:
        categorie_id = CategorieRepositorySQL(db.session_factory).par_tournoi(tournoi_id)[0].id
        assert categorie_id is not None
        bob = ArcherRepositorySQL(db.session_factory).ajouter(
            Archer.creer("Durand", "Bob", tournoi_id, categorie_id)
        )
        assert bob.id is not None
        repo = _repo(db)
        repo.enregistrer(_serie(tournoi_id, alice_id, validee="ROUX Sophie"))
        repo.enregistrer(_serie(tournoi_id, bob.id, validee="ROUX Sophie"))

        series = repo.par_tournoi(tournoi_id)
        assert {s.archer_id for s in series} == {alice_id, bob.id}
        for s in series:
            assert [v.numero for v in s.volees] == [1, 2]
            assert s.cumul == 13  # seule la volée 2 (7+6+0) est validée
    finally:
        db.engine.dispose()


def test_verrou_et_cumul_round_trip(tmp_path: Path) -> None:
    """Une volée validée revient **verrouillée** ; le cumul ne compte que les volées validées."""
    db, tournoi_id, archer_id = _contexte(tmp_path)
    try:
        repo = _repo(db)
        repo.enregistrer(_serie(tournoi_id, archer_id, validee="ROUX Sophie"))

        relue = repo.par_archer(tournoi_id, archer_id)
        assert relue is not None
        volee_1, volee_2 = relue.volee(1), relue.volee(2)
        assert volee_1 is not None and volee_2 is not None
        assert not volee_1.verrouillee  # non validée
        assert volee_2.verrouillee and volee_2.validee_par == "ROUX Sophie"
        # Seule la volée 2 est validée : cumul = 7 + 6 + 0 (le manqué vaut 0).
        assert relue.cumul == 13
    finally:
        db.engine.dispose()


def test_enregistrer_upsert_ne_duplique_pas(tmp_path: Path) -> None:
    """Ré-enregistrer la série d'un archer met à jour la même ligne (clé métier), sans doublon."""
    db, tournoi_id, archer_id = _contexte(tmp_path)
    try:
        repo = _repo(db)
        repo.enregistrer(_serie(tournoi_id, archer_id))
        # Deuxième enregistrement, série reconstruite sans id (comme le ferait le service après
        # relecture-mutation) : c'est la clé (tournoi, archer) qui doit retomber sur la même ligne.
        repo.enregistrer(_serie(tournoi_id, archer_id, validee="ROUX Sophie"))

        with db.session_factory() as session:
            nb_series = session.execute(sa.text("SELECT COUNT(*) FROM serie")).scalar_one()
            nb_volees = session.execute(sa.text("SELECT COUNT(*) FROM volee")).scalar_one()
        assert nb_series == 1  # pas de seconde série
        assert nb_volees == 2  # purge + réinsertion, pas d'accumulation
        relue = repo.par_archer(tournoi_id, archer_id)
        assert relue is not None
        volee_2 = relue.volee(2)
        assert volee_2 is not None and volee_2.validee_par == "ROUX Sophie"
    finally:
        db.engine.dispose()


def test_enregistrer_avec_trace_ecrit_serie_et_audit(tmp_path: Path) -> None:
    """Le chemin tracé persiste la série **et** son entrée d'audit (validation)."""
    db, tournoi_id, archer_id = _contexte(tmp_path)
    try:
        audit = AuditRepositorySQL(db.session_factory)
        repo = SerieRepositorySQL(db.session_factory, audit, HorlogeSysteme())
        entree = EntreeAudit.creer(
            tournoi_id=tournoi_id,
            action=ActionAuditee.VALIDATION,
            auteur="ROUX Sophie",
            horodatage=_QUAND,
            objet=f"série de qualification de l'archer {archer_id}",
        )
        repo.enregistrer_avec_trace(_serie(tournoi_id, archer_id, validee="ROUX Sophie"), entree)

        assert repo.par_archer(tournoi_id, archer_id) is not None
        (trace,) = audit.par_tournoi(tournoi_id)
        assert trace.action is ActionAuditee.VALIDATION
        assert trace.auteur == "ROUX Sophie"
    finally:
        db.engine.dispose()


def test_enregistrer_avec_trace_atomique_tout_ou_rien(tmp_path: Path) -> None:
    """Injection d'échec sur la trace : **ni** la série **ni** l'entrée ne survivent (ADR-0035).

    L'entrée d'audit vise un tournoi **inexistant** : la FK `entree_audit.tournoi_id` (enforced,
    `PRAGMA foreign_keys=ON`) fait échouer le commit **unique** qui scelle série + trace. La série,
    pourtant valide, ne doit pas survivre seule — c'est la fenêtre « validation non tracée » que la
    couture ferme.
    """
    db, tournoi_id, archer_id = _contexte(tmp_path)
    try:
        audit = AuditRepositorySQL(db.session_factory)
        repo = SerieRepositorySQL(db.session_factory, audit, HorlogeSysteme())
        entree_impossible = EntreeAudit.creer(
            tournoi_id=tournoi_id + 999_999,  # aucun tournoi : la FK cassera au commit
            action=ActionAuditee.VALIDATION,
            auteur="ROUX Sophie",
            horodatage=_QUAND,
            objet="série fantôme",
        )

        with pytest.raises(InfrastructureError):
            repo.enregistrer_avec_trace(_serie(tournoi_id, archer_id), entree_impossible)

        assert repo.par_archer(tournoi_id, archer_id) is None  # série non persistée
        assert audit.par_tournoi(tournoi_id) == []  # ni trace
    finally:
        db.engine.dispose()


def test_supprimer_archer_efface_serie_et_volees(tmp_path: Path) -> None:
    """Supprimer un archer efface sa série (cascade applicative) et ses volées (cascade SQLite)."""
    db, tournoi_id, archer_id = _contexte(tmp_path)
    try:
        repo = _repo(db)
        repo.enregistrer(_serie(tournoi_id, archer_id))

        ArcherRepositorySQL(db.session_factory).supprimer(archer_id)

        assert repo.par_archer(tournoi_id, archer_id) is None
        with db.session_factory() as session:
            nb_volees = session.execute(sa.text("SELECT COUNT(*) FROM volee")).scalar_one()
        assert nb_volees == 0  # les volées ont suivi la série (ON DELETE CASCADE)
    finally:
        db.engine.dispose()


def test_reenregistrer_reecrit_les_valeurs_d_une_volee(tmp_path: Path) -> None:
    """Ré-enregistrer avec des valeurs de volée différentes : la relecture reflète les nouvelles.

    Prouve que le purge + réinsertion réécrit fidèlement une volée corrigée (et fait disparaître
    une volée absente de la nouvelle série), au-delà du seul cas `validee_par` de l'upsert simple.
    """
    db, tournoi_id, archer_id = _contexte(tmp_path)
    try:
        repo = _repo(db)
        repo.enregistrer(_serie(tournoi_id, archer_id))  # volée 1 = 10/9/8, volée 2 présente
        modifiee = Serie(
            tournoi_id=tournoi_id,
            archer_id=archer_id,
            volees=(
                Volee(
                    numero=1,
                    valeurs=(ZoneScore("7"), ZoneScore("7"), ZoneScore("7")),
                    saisie_par="DURAND Jean",
                ),
            ),
        )
        repo.enregistrer(modifiee)

        relue = repo.par_archer(tournoi_id, archer_id)
        assert relue is not None
        volee_1 = relue.volee(1)
        assert volee_1 is not None
        assert volee_1.valeurs == (ZoneScore("7"), ZoneScore("7"), ZoneScore("7"))
        assert relue.volee(2) is None  # la volée 2 de la 1ʳᵉ série a été purgée
    finally:
        db.engine.dispose()


def test_valeurs_illisibles_levent_infrastructure_error(tmp_path: Path) -> None:
    """Une ligne `volee.valeurs` corrompue en base ne fuit pas : `InfrastructureError` (non-fuite).

    Le repository est normalement le **seul rédacteur** de `valeurs` et n'écrit que des zones
    valides ; une valeur hors `ZoneScore` relue est une incohérence technique enveloppée (ADR-0007),
    jamais laissée fuir en value object silencieusement invalide. On corrompt directement la base
    (`["99"]` : JSON lisible, mais `99` n'est pas une zone) pour exercer cette garde.
    """
    db, tournoi_id, archer_id = _contexte(tmp_path)
    try:
        repo = _repo(db)
        repo.enregistrer(_serie(tournoi_id, archer_id))
        with db.session_factory() as session:
            session.execute(
                sa.text("UPDATE volee SET valeurs = :v WHERE numero = 1"), {"v": '["99"]'}
            )
            session.commit()

        with pytest.raises(InfrastructureError):
            repo.par_archer(tournoi_id, archer_id)
    finally:
        db.engine.dispose()


def test_enregistrer_ignore_un_id_incoherent(tmp_path: Path) -> None:
    """Un `id` de série incohérent avec la clé métier est **ignoré** : `(tournoi, archer)` gagne.

    Garde-fou anti-régression de `_ligne_serie` : ré-introduire un lookup par `serie.id` rouvrirait
    la surface de corruption (réécrire les volées sur la **mauvaise** série). On fabrique une série
    portant la clé métier de l'archer B **mais** l'`id` de la série de l'archer A ; l'écriture doit
    atterrir sur la série de B et laisser celle de A **intacte**.
    """
    db, tournoi_id, archer_id = _contexte(tmp_path)
    try:
        repo = _repo(db)
        categorie_b = CategorieRepositorySQL(db.session_factory).ajouter(
            Categorie.creer(tournoi_id, "Senior 2 H")
        )
        assert categorie_b.id is not None
        archer_b = ArcherRepositorySQL(db.session_factory).ajouter(
            Archer.creer("Durand", "Bob", tournoi_id, categorie_b.id)
        )
        assert archer_b.id is not None

        serie_a = repo.enregistrer(_serie(tournoi_id, archer_id))  # volée 1 = 10/9/8
        repo.enregistrer(_serie(tournoi_id, archer_b.id))
        piege = Serie(
            tournoi_id=tournoi_id,
            archer_id=archer_b.id,
            id=serie_a.id,  # id de la série de A, clé métier de B → incohérent
            volees=(
                Volee(
                    numero=1,
                    valeurs=(ZoneScore("5"), ZoneScore("5"), ZoneScore("5")),
                    saisie_par="DURAND Bob",
                ),
            ),
        )
        repo.enregistrer(piege)

        relue_a = repo.par_archer(tournoi_id, archer_id)
        assert relue_a is not None
        volee_a = relue_a.volee(1)
        assert volee_a is not None
        # La série de A n'a PAS été réécrite par les volées du piège :
        assert volee_a.valeurs == (ZoneScore("10"), ZoneScore("9"), ZoneScore("8"))
        relue_b = repo.par_archer(tournoi_id, archer_b.id)
        assert relue_b is not None
        volee_b = relue_b.volee(1)
        assert volee_b is not None
        assert volee_b.valeurs == (ZoneScore("5"), ZoneScore("5"), ZoneScore("5"))
    finally:
        db.engine.dispose()


def test_horodatages_vide_sans_serie(tmp_path: Path) -> None:
    """Sans série saisie, aucun « quand » à consulter : `horodatages` rend un dictionnaire vide."""
    db, tournoi_id, archer_id = _contexte(tmp_path)
    try:
        assert _repo(db).horodatages(tournoi_id, archer_id) == {}
    finally:
        db.engine.dispose()


def test_created_at_pose_a_la_saisie_et_relu_aware(tmp_path: Path) -> None:
    """Chaque volée est datée de l'instant de saisie (`Horloge`), relu en UTC *aware* (ex-017)."""
    db, tournoi_id, archer_id = _contexte(tmp_path)
    try:
        repo = _repo(db, HorlogeReglable(_QUAND))
        repo.enregistrer(_serie(tournoi_id, archer_id))

        horodatages = repo.horodatages(tournoi_id, archer_id)
        assert horodatages == {1: _QUAND, 2: _QUAND}
        assert horodatages[1].tzinfo is not None  # relu *aware*, comme l'horodatage d'audit
    finally:
        db.engine.dispose()


def test_created_at_preserve_au_reenregistrement(tmp_path: Path) -> None:
    """Le « quand » d'une volée déjà saisie **ne bouge pas** quand on ré-enregistre la série.

    C'est l'invariant d'identité que le CA a renvoyé à cette tranche : le purge + réinsertion ne
    doit pas réinitialiser `created_at`. On valide la série plus tard (horloge avancée) : les deux
    volées gardent leur horodatage initial.
    """
    db, tournoi_id, archer_id = _contexte(tmp_path)
    try:
        horloge = HorlogeReglable(_QUAND)
        repo = _repo(db, horloge)
        repo.enregistrer(_serie(tournoi_id, archer_id))

        horloge.avancer_a(_PLUS_TARD)
        repo.enregistrer(_serie(tournoi_id, archer_id, validee="ROUX Sophie"))

        # Malgré la réécriture (purge + réinsertion) à un instant postérieur, le « quand » tient.
        assert repo.horodatages(tournoi_id, archer_id) == {1: _QUAND, 2: _QUAND}
    finally:
        db.engine.dispose()


def test_created_at_d_une_volee_nouvelle_recoit_l_instant_courant(tmp_path: Path) -> None:
    """Une volée **ajoutée** à une série existante est datée de l'instant courant, pas de l'ancien.

    Le contrepoint de la préservation : seules les volées de numéro **déjà présent** conservent leur
    horodatage ; une volée neuve reçoit l'instant de sa saisie.
    """
    db, tournoi_id, archer_id = _contexte(tmp_path)
    try:
        horloge = HorlogeReglable(_QUAND)
        repo = _repo(db, horloge)
        # 1re saisie : la seule volée 1, à T1.
        premiere = Serie(
            tournoi_id=tournoi_id,
            archer_id=archer_id,
            volees=(Volee(numero=1, valeurs=(ZoneScore("10"), ZoneScore("9"), ZoneScore("8"))),),
        )
        repo.enregistrer(premiere)

        horloge.avancer_a(_PLUS_TARD)
        # 2e saisie : volées 1 ET 2, à T2 → la 1 conserve T1, la 2 (neuve) prend T2.
        repo.enregistrer(_serie(tournoi_id, archer_id))

        assert repo.horodatages(tournoi_id, archer_id) == {1: _QUAND, 2: _PLUS_TARD}
    finally:
        db.engine.dispose()
