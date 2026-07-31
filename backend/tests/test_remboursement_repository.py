"""Tests d'intégration des adapters SQL du registre de remboursements (E08US005, ADR-0057).

Exerce sur une **vraie base** migrée (`alembic upgrade head`) : (1) l'ouverture **atomique** d'un
remboursement à la disparition d'une inscription payée — `InscriptionRepositorySQL.
supprimer_avec_remboursement` (désinscription) et
`DepartRepositorySQL.supprimer_avec_remboursements`
(suppression de départ, avec cascade des inscriptions) ; (2) la lecture et le **traitement** —
`RemboursementRepositorySQL.par_tournoi`/`par_id`/`enregistrer_avec_trace` (co-écriture acte↔trace).
Les tests **après** implémentation (adapter/câblage, pas d'oracle métier).
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from domain.archer import Archer
from domain.categorie import Categorie
from domain.depart import Depart
from domain.entree_audit import ActionAuditee, EntreeAudit
from domain.inscription import Inscription
from domain.remboursement import MotifRemboursement, Remboursement, StatutRemboursement
from domain.tournoi import Tournoi
from infrastructure.db import (
    ArcherRepositorySQL,
    AuditRepositorySQL,
    CategorieRepositorySQL,
    Database,
    DepartRepositorySQL,
    InscriptionRepositorySQL,
    RemboursementRepositorySQL,
    TournoiRepositorySQL,
)
from infrastructure.erreurs import InfrastructureError
from tests.base_migree import preparer_base

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)
_CREE = datetime.datetime(2026, 7, 29, 9, 0, tzinfo=datetime.UTC)
_TRAITE = datetime.datetime(2026, 7, 29, 11, 30, tzinfo=datetime.UTC)


def _migrer(url: str) -> None:
    preparer_base(url)


def _base(tmp_path: Path) -> tuple[Database, int, int, int]:
    """Base jetable avec tournoi, archer et départ ; renvoie (db, tournoi_id, archer_id,
    depart_id)."""
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
    depart = DepartRepositorySQL(db.session_factory).ajouter(
        Depart.creer(tournoi.id, 1, 810, "09:00")
    )
    assert archer.id is not None and depart.id is not None
    return db, tournoi.id, archer.id, depart.id


def _remboursement(tournoi_id: int, motif: MotifRemboursement) -> Remboursement:
    return Remboursement.creer(
        tournoi_id,
        archer_prenom="Jean",
        archer_nom="Robin",
        creneau="Départ n°1 — 09:00",
        montant_centimes=810,
        motif=motif,
        cree_le=_CREE,
    )


def _trace(tournoi_id: int) -> EntreeAudit:
    return EntreeAudit.creer(
        tournoi_id=tournoi_id,
        action=ActionAuditee.REMBOURSEMENT,
        auteur="Administrateur",
        horodatage=_TRAITE,
        objet="Remboursement — Jean Robin, Départ n°1 — 09:00 (8,10 €)",
        avant="à rembourser",
        apres="remboursé",
    )


def test_desinscrire_avec_remboursement_supprime_et_ouvre_le_poste(tmp_path: Path) -> None:
    """`supprimer_avec_remboursement` retire l'inscription **et** insère le poste (une
    transaction)."""
    db, tournoi_id, archer_id, depart_id = _base(tmp_path)
    try:
        audit = AuditRepositorySQL(db.session_factory)
        inscriptions = InscriptionRepositorySQL(db.session_factory, audit)
        remboursements = RemboursementRepositorySQL(db.session_factory, audit)
        cree = inscriptions.ajouter(Inscription.creer(archer_id, depart_id).marquer_paye(True))
        assert cree.id is not None

        inscriptions.supprimer_avec_remboursement(
            cree.id, _remboursement(tournoi_id, MotifRemboursement.DESINSCRIPTION)
        )

        assert inscriptions.par_id(cree.id) is None  # inscription partie
        postes = remboursements.par_tournoi(tournoi_id)
        assert len(postes) == 1
        assert postes[0].montant_centimes == 810
        assert postes[0].motif is MotifRemboursement.DESINSCRIPTION
        assert postes[0].statut is StatutRemboursement.A_REMBOURSER
    finally:
        db.engine.dispose()


def test_supprimer_depart_avec_remboursements_purge_et_ouvre_les_postes(tmp_path: Path) -> None:
    """`supprimer_avec_remboursements` efface départ + inscriptions **et** ouvre les postes."""
    db, tournoi_id, archer_id, depart_id = _base(tmp_path)
    try:
        audit = AuditRepositorySQL(db.session_factory)
        inscriptions = InscriptionRepositorySQL(db.session_factory, audit)
        departs = DepartRepositorySQL(db.session_factory)
        remboursements = RemboursementRepositorySQL(db.session_factory, audit)
        inscriptions.ajouter(Inscription.creer(archer_id, depart_id).marquer_paye(True))

        departs.supprimer_avec_remboursements(
            depart_id, [_remboursement(tournoi_id, MotifRemboursement.DEPART_SUPPRIME)]
        )

        assert departs.par_id(depart_id) is None  # départ parti
        assert inscriptions.par_depart(depart_id) == []  # cascade des inscriptions
        postes = remboursements.par_tournoi(tournoi_id)
        assert len(postes) == 1 and postes[0].motif is MotifRemboursement.DEPART_SUPPRIME
    finally:
        db.engine.dispose()


def test_par_id_relit_l_instant_utc(tmp_path: Path) -> None:
    """`par_id` relit un poste avec ses dates **UTC aware** (round-trip fidèle, comme l'audit)."""
    db, tournoi_id, archer_id, depart_id = _base(tmp_path)
    try:
        audit = AuditRepositorySQL(db.session_factory)
        inscriptions = InscriptionRepositorySQL(db.session_factory, audit)
        remboursements = RemboursementRepositorySQL(db.session_factory, audit)
        cree = inscriptions.ajouter(Inscription.creer(archer_id, depart_id).marquer_paye(True))
        assert cree.id is not None
        inscriptions.supprimer_avec_remboursement(
            cree.id, _remboursement(tournoi_id, MotifRemboursement.DESINSCRIPTION)
        )
        poste = remboursements.par_tournoi(tournoi_id)[0]
        assert poste.id is not None

        relu = remboursements.par_id(poste.id)
        assert relu is not None
        assert relu.cree_le == _CREE  # aware, égal à l'instant écrit
        assert relu.traite_le is None
        assert remboursements.par_id(999) is None
    finally:
        db.engine.dispose()


def test_enregistrer_avec_trace_traite_et_consigne(tmp_path: Path) -> None:
    """`enregistrer_avec_trace` met à jour le statut **et** consigne la trace `REMBOURSEMENT`."""
    db, tournoi_id, archer_id, depart_id = _base(tmp_path)
    try:
        audit = AuditRepositorySQL(db.session_factory)
        inscriptions = InscriptionRepositorySQL(db.session_factory, audit)
        remboursements = RemboursementRepositorySQL(db.session_factory, audit)
        cree = inscriptions.ajouter(Inscription.creer(archer_id, depart_id).marquer_paye(True))
        assert cree.id is not None
        inscriptions.supprimer_avec_remboursement(
            cree.id, _remboursement(tournoi_id, MotifRemboursement.DESINSCRIPTION)
        )
        poste = remboursements.par_tournoi(tournoi_id)[0]

        maj = remboursements.enregistrer_avec_trace(
            poste.marquer_rembourse(_TRAITE), _trace(tournoi_id)
        )

        assert maj.statut is StatutRemboursement.REMBOURSE
        assert maj.traite_le == _TRAITE
        traces = audit.par_tournoi(tournoi_id)
        assert len(traces) == 1 and traces[0].action is ActionAuditee.REMBOURSEMENT
    finally:
        db.engine.dispose()


def test_enregistrer_avec_trace_est_atomique_si_la_trace_echoue(tmp_path: Path) -> None:
    """Si la co-écriture de la trace échoue, **rien** n'est persisté (ni statut, ni trace).

    Le statut reste `à_rembourser` et aucune trace n'apparaît — preuve que le commit unique a tout
    annulé (ADR-0035). L'échec remonte enveloppé en `InfrastructureError`.
    """

    class _AuditQuiEchoue(AuditRepositorySQL):
        def consigner_dans(self, session: Session, entree: EntreeAudit) -> None:
            raise SQLAlchemyError("échec simulé de la trace")

    db, tournoi_id, archer_id, depart_id = _base(tmp_path)
    try:
        audit = AuditRepositorySQL(db.session_factory)
        inscriptions = InscriptionRepositorySQL(db.session_factory, audit)
        cree = inscriptions.ajouter(Inscription.creer(archer_id, depart_id).marquer_paye(True))
        assert cree.id is not None
        inscriptions.supprimer_avec_remboursement(
            cree.id, _remboursement(tournoi_id, MotifRemboursement.DESINSCRIPTION)
        )
        remboursements_ok = RemboursementRepositorySQL(db.session_factory, audit)
        poste = remboursements_ok.par_tournoi(tournoi_id)[0]
        assert poste.id is not None

        remboursements_ko = RemboursementRepositorySQL(
            db.session_factory, _AuditQuiEchoue(db.session_factory)
        )
        with pytest.raises(InfrastructureError):
            remboursements_ko.enregistrer_avec_trace(
                poste.marquer_rembourse(_TRAITE), _trace(tournoi_id)
            )

        relu = remboursements_ok.par_id(poste.id)
        assert relu is not None and relu.statut is StatutRemboursement.A_REMBOURSER  # rollback
        assert audit.par_tournoi(tournoi_id) == []  # aucune trace fantôme
    finally:
        db.engine.dispose()
