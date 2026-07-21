"""Tests d'intégration du repository SQL des inscriptions (E02US009, ADR-0017).

Exerce l'adapter sur une **vraie base** migrée (`alembic upgrade head`) : persistance d'un lien
archer↔départ (`paye` à False par défaut), relecture, listes par archer et par départ, unicité du
couple `(archer, départ)`, bascule de `paye`, désinscription. Et surtout les **cascades applicatives
maîtrisées** (DETTE-001) : supprimer l'archer **ou** le départ efface ses inscriptions dans la même
transaction. Une inscription référence un archer (donc une catégorie) et un départ : chaque test
monte la chaîne complète.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from domain.archer import Archer
from domain.categorie import Categorie
from domain.depart import Depart
from domain.entree_audit import ActionAuditee, EntreeAudit
from domain.inscription import Inscription
from domain.tournoi import Tournoi
from infrastructure.db import (
    ArcherRepositorySQL,
    AuditRepositorySQL,
    CategorieRepositorySQL,
    Database,
    DepartRepositorySQL,
    InscriptionRepositorySQL,
    TournoiRepositorySQL,
)
from infrastructure.erreurs import InfrastructureError

_QUAND = datetime.datetime(2026, 7, 21, 9, 30, tzinfo=datetime.UTC)


def _trace_paiement(tournoi_id: int) -> EntreeAudit:
    """Construit une entrée d'audit `PAIEMENT` valide (datée) pour les tests de co-écriture."""
    return EntreeAudit.creer(
        tournoi_id=tournoi_id,
        action=ActionAuditee.PAIEMENT,
        auteur="Administrateur",
        horodatage=_QUAND,
        objet="Paiement — Jean Robin, départ n°1",
        avant="non payé",
        apres="payé",
    )


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


def _base_avec_archer_et_depart(tmp_path: Path) -> tuple[Database, int, int]:
    """Monte une base jetable avec tournoi, catégorie, archer et départ ; renvoie leurs ids."""
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
        Archer.creer("Robin", "Jean", tournoi.id, categorie.id)
    )
    depart = DepartRepositorySQL(db.session_factory).ajouter(Depart.creer(tournoi.id, 1, 810))
    assert archer.id is not None and depart.id is not None
    return db, archer.id, depart.id


def test_ajouter_puis_relire(tmp_path: Path) -> None:
    """`ajouter` attribue un id ; `par_id` relit l'agrégat avec `paye` à False."""
    db, archer_id, depart_id = _base_avec_archer_et_depart(tmp_path)
    try:
        repository = InscriptionRepositorySQL(
            db.session_factory, AuditRepositorySQL(db.session_factory)
        )
        cree = repository.ajouter(Inscription.creer(archer_id, depart_id))
        assert cree.id is not None
        assert (cree.archer_id, cree.depart_id) == (archer_id, depart_id)
        assert cree.paye is False
        assert repository.par_id(cree.id) == cree
    finally:
        db.engine.dispose()


def test_enregistrer_bascule_paye(tmp_path: Path) -> None:
    """`enregistrer` persiste la bascule de `paye` ; le couple ne change pas."""
    db, archer_id, depart_id = _base_avec_archer_et_depart(tmp_path)
    try:
        repository = InscriptionRepositorySQL(
            db.session_factory, AuditRepositorySQL(db.session_factory)
        )
        cree = repository.ajouter(Inscription.creer(archer_id, depart_id))
        assert cree.id is not None

        paye = repository.enregistrer(cree.marquer_paye(True))
        assert paye.paye is True
        relu = repository.par_id(cree.id)
        assert relu is not None and relu.paye is True
    finally:
        db.engine.dispose()


def test_par_archer_et_par_depart(tmp_path: Path) -> None:
    """`par_archer` et `par_depart` renvoient les inscriptions de leur côté du lien."""
    db, archer_id, depart_id = _base_avec_archer_et_depart(tmp_path)
    try:
        repository = InscriptionRepositorySQL(
            db.session_factory, AuditRepositorySQL(db.session_factory)
        )
        cree = repository.ajouter(Inscription.creer(archer_id, depart_id))
        assert [i.id for i in repository.par_archer(archer_id)] == [cree.id]
        assert [i.id for i in repository.par_depart(depart_id)] == [cree.id]
    finally:
        db.engine.dispose()


def test_par_archer_et_depart_trouve_ou_none(tmp_path: Path) -> None:
    """`par_archer_et_depart` trouve le couple existant, renvoie None sinon (contrôle d'unicité)."""
    db, archer_id, depart_id = _base_avec_archer_et_depart(tmp_path)
    try:
        repository = InscriptionRepositorySQL(
            db.session_factory, AuditRepositorySQL(db.session_factory)
        )
        assert repository.par_archer_et_depart(archer_id, depart_id) is None
        cree = repository.ajouter(Inscription.creer(archer_id, depart_id))
        trouve = repository.par_archer_et_depart(archer_id, depart_id)
        assert trouve is not None and trouve.id == cree.id
    finally:
        db.engine.dispose()


def test_unicite_du_couple_archer_depart(tmp_path: Path) -> None:
    """La contrainte `UNIQUE(archer_id, depart_id)` refuse un doublon (filet ultime, `DejaInscrit`).

    Le service refuse en amont (`DejaInscrit`, 409) ; cette contrainte est le garde-fou de dernier
    ressort, et une violation remonte enveloppée en `InfrastructureError` (jamais brute).
    """
    db, archer_id, depart_id = _base_avec_archer_et_depart(tmp_path)
    try:
        repository = InscriptionRepositorySQL(
            db.session_factory, AuditRepositorySQL(db.session_factory)
        )
        repository.ajouter(Inscription.creer(archer_id, depart_id))
        with pytest.raises(InfrastructureError):
            repository.ajouter(Inscription.creer(archer_id, depart_id))
    finally:
        db.engine.dispose()


def test_supprimer_retire_l_inscription(tmp_path: Path) -> None:
    """`supprimer` retire la ligne ; `par_id` renvoie ensuite None."""
    db, archer_id, depart_id = _base_avec_archer_et_depart(tmp_path)
    try:
        repository = InscriptionRepositorySQL(
            db.session_factory, AuditRepositorySQL(db.session_factory)
        )
        cree = repository.ajouter(Inscription.creer(archer_id, depart_id))
        assert cree.id is not None
        repository.supprimer(cree.id)
        assert repository.par_id(cree.id) is None
    finally:
        db.engine.dispose()


def test_supprimer_l_archer_purge_ses_inscriptions(tmp_path: Path) -> None:
    """Supprimer l'archer efface ses inscriptions **dans la même transaction** (DETTE-001).

    C'est la cascade applicative maîtrisée : `inscription.archer_id` est une FK sans `ON DELETE`,
    donc `ArcherRepositorySQL.supprimer` doit les purger avant de retirer l'archer.
    """
    db, archer_id, depart_id = _base_avec_archer_et_depart(tmp_path)
    try:
        inscriptions = InscriptionRepositorySQL(
            db.session_factory, AuditRepositorySQL(db.session_factory)
        )
        inscriptions.ajouter(Inscription.creer(archer_id, depart_id))

        ArcherRepositorySQL(db.session_factory).supprimer(archer_id)
        assert inscriptions.par_depart(depart_id) == []
    finally:
        db.engine.dispose()


def test_supprimer_le_depart_purge_ses_inscriptions(tmp_path: Path) -> None:
    """Supprimer le départ efface ses inscriptions **dans la même transaction** (DETTE-001).

    Pendant du test ci-dessus, côté départ : `inscription.depart_id` est aussi une FK sans
    `ON DELETE`, donc `DepartRepositorySQL.supprimer` purge les inscriptions liées d'abord.
    """
    db, archer_id, depart_id = _base_avec_archer_et_depart(tmp_path)
    try:
        inscriptions = InscriptionRepositorySQL(
            db.session_factory, AuditRepositorySQL(db.session_factory)
        )
        inscriptions.ajouter(Inscription.creer(archer_id, depart_id))

        DepartRepositorySQL(db.session_factory).supprimer(depart_id)
        assert inscriptions.par_archer(archer_id) == []
    finally:
        db.engine.dispose()


def test_par_id_inexistant_renvoie_none(tmp_path: Path) -> None:
    """`par_id` renvoie None pour un identifiant absent (pas d'exception)."""
    db, _, _ = _base_avec_archer_et_depart(tmp_path)
    try:
        repository = InscriptionRepositorySQL(
            db.session_factory, AuditRepositorySQL(db.session_factory)
        )
        assert repository.par_id(999) is None
    finally:
        db.engine.dispose()


def test_definir_paye_avec_trace_bascule_et_consigne(tmp_path: Path) -> None:
    """`definir_paye_avec_trace` bascule `paye` **et** persiste la trace, en une transaction.

    Face « atomique » d'`enregistrer` : le marquage et son entrée d'audit `PAIEMENT` sont scellés
    par un unique commit (ADR-0035). On vérifie les deux effets présents après l'appel.
    """
    db, archer_id, depart_id = _base_avec_archer_et_depart(tmp_path)
    try:
        audit = AuditRepositorySQL(db.session_factory)
        repository = InscriptionRepositorySQL(db.session_factory, audit)
        cree = repository.ajouter(Inscription.creer(archer_id, depart_id))
        assert cree.id is not None
        tournoi_id = TournoiRepositorySQL(db.session_factory).lister()[0].id
        assert tournoi_id is not None

        (maj,) = repository.definir_paye_avec_trace([cree.id], True, _trace_paiement(tournoi_id))

        assert maj.paye is True
        relu = repository.par_id(cree.id)
        assert relu is not None and relu.paye is True
        traces = audit.par_tournoi(tournoi_id)
        assert len(traces) == 1 and traces[0].action is ActionAuditee.PAIEMENT
    finally:
        db.engine.dispose()


def test_definir_paye_avec_trace_est_atomique_si_la_trace_echoue(tmp_path: Path) -> None:
    """Si la co-écriture de la trace échoue, **rien** n'est persisté (ni marquage, ni trace).

    On injecte un audit dont `consigner_dans` lève : le service ne doit laisser ni paiement basculé
    sans trace, ni trace fantôme. L'échec remonte enveloppé en `InfrastructureError` (ADR-0007), et
    `paye` reste à sa valeur d'avant — preuve que le commit unique a bien tout annulé.
    """

    class _AuditQuiEchoue(AuditRepositorySQL):
        def consigner_dans(self, session: Session, entree: EntreeAudit) -> None:
            raise SQLAlchemyError("échec simulé de la trace")

    db, archer_id, depart_id = _base_avec_archer_et_depart(tmp_path)
    try:
        repository = InscriptionRepositorySQL(
            db.session_factory, _AuditQuiEchoue(db.session_factory)
        )
        cree = repository.ajouter(Inscription.creer(archer_id, depart_id))
        assert cree.id is not None
        tournoi_id = TournoiRepositorySQL(db.session_factory).lister()[0].id
        assert tournoi_id is not None

        with pytest.raises(InfrastructureError):
            repository.definir_paye_avec_trace([cree.id], True, _trace_paiement(tournoi_id))

        relu = repository.par_id(cree.id)
        assert relu is not None and relu.paye is False  # rollback : rien n'a été marqué
        # ...et aucune trace fantôme : le rollback a aussi annulé la moindre écriture d'audit.
        assert AuditRepositorySQL(db.session_factory).par_tournoi(tournoi_id) == []
    finally:
        db.engine.dispose()
