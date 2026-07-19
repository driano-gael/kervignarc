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

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)
_QUAND = datetime.datetime(2026, 3, 14, 10, 42, tzinfo=datetime.UTC)


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


def _repo(db: Database) -> SerieRepositorySQL:
    return SerieRepositorySQL(db.session_factory, AuditRepositorySQL(db.session_factory))


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
        repo = SerieRepositorySQL(db.session_factory, audit)
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
        repo = SerieRepositorySQL(db.session_factory, audit)
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
