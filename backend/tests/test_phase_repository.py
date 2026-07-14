"""Tests d'intégration du repository SQL des phases (E01US009 / ADR-0011, E01US015).

Exerce l'adapter sur une **vraie base** créée par les migrations (`alembic upgrade head`) :
persistance du barème (sérialisation JSON `config.scoring`) et du grain de validation
(`config.validation`), relecture par tournoi + type, mise à jour, et enveloppe d'une `config`
illisible. Une phase requiert un tournoi (FK `tournoi_id`).

E01US015 n'ajoute **aucune migration** : la politique s'ajoute dans le JSON existant. Les tests
`…_sans_cle_validation_…` verrouillent la contrepartie de ce choix — une ligne écrite avant
E01US015 doit se relire avec le preset de son type, pas exploser.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from domain.bareme import BaremeQualification
from domain.grain_validation import GrainValidation
from domain.phase import Phase, TypePhase
from domain.tournoi import Tournoi, TournoiId, TypeTournoi
from infrastructure.db import Database, PhaseORM, PhaseRepositorySQL, TournoiRepositorySQL
from infrastructure.erreurs import InfrastructureError

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


def _base(tmp_path: Path) -> Database:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    return Database(url)


def _tournoi(db: Database) -> TournoiId:
    """Persiste un tournoi (FK requise par une phase) et renvoie son identifiant."""
    tournoi = TournoiRepositorySQL(db.session_factory).ajouter(
        Tournoi(
            nom="Kervignarc",
            date=datetime.date(2026, 3, 14),
            lieu=None,
            type_tournoi=TypeTournoi.NON_OFFICIEL,
        )
    )
    assert tournoi.id is not None
    return tournoi.id


def test_ajouter_puis_relire_par_tournoi_et_type(tmp_path: Path) -> None:
    """`ajouter` attribue un id ; `par_tournoi_et_type` relit le barème (config JSON comprise)."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        repository = PhaseRepositorySQL(db.session_factory)
        assert repository.par_tournoi_et_type(tournoi_id, TypePhase.QUALIFICATION) is None

        cree = repository.ajouter(
            Phase.qualification(tournoi_id, BaremeQualification.preset_ffta_18m())
        )
        assert cree.id is not None
        assert cree.bareme.nb_volees == 20
        assert cree.bareme.nb_fleches_par_volee == 3

        relue = repository.par_tournoi_et_type(tournoi_id, TypePhase.QUALIFICATION)
        assert relue == cree
    finally:
        db.engine.dispose()


def test_enregistrer_met_a_jour_le_bareme(tmp_path: Path) -> None:
    """`enregistrer` persiste l'édition du barème et conserve l'identifiant."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        repository = PhaseRepositorySQL(db.session_factory)
        cree = repository.ajouter(Phase.qualification(tournoi_id, BaremeQualification.creer(20, 3)))
        assert cree.id is not None

        enregistre = repository.enregistrer(cree.avec_bareme(BaremeQualification.creer(10, 6)))
        assert enregistre.id == cree.id
        assert enregistre.bareme.nb_volees == 10
        assert enregistre.bareme.nb_fleches_par_volee == 6
        assert repository.par_id(cree.id) == enregistre
    finally:
        db.engine.dispose()


def test_par_tournoi_et_type_isole_les_tournois(tmp_path: Path) -> None:
    """`par_tournoi_et_type` ne renvoie que la phase du tournoi demandé."""
    db = _base(tmp_path)
    try:
        premier = _tournoi(db)
        second = _tournoi(db)
        repository = PhaseRepositorySQL(db.session_factory)
        repository.ajouter(Phase.qualification(premier, BaremeQualification.creer(20, 3)))

        assert repository.par_tournoi_et_type(second, TypePhase.QUALIFICATION) is None
        du_premier = repository.par_tournoi_et_type(premier, TypePhase.QUALIFICATION)
        assert du_premier is not None and du_premier.tournoi_id == premier
    finally:
        db.engine.dispose()


def test_config_corrompue_leve_infrastructure_error(tmp_path: Path) -> None:
    """Une `config` illisible en base est enveloppée en `InfrastructureError` (pas de 500 brut)."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        with db.session_factory() as session:
            session.add(
                PhaseORM(
                    tournoi_id=tournoi_id,
                    ordre=1,
                    type="qualification",
                    config="pas du json",
                    statut="a_venir",
                )
            )
            session.commit()
        with pytest.raises(InfrastructureError):
            PhaseRepositorySQL(db.session_factory).par_tournoi_et_type(
                tournoi_id, TypePhase.QUALIFICATION
            )
    finally:
        db.engine.dispose()


def test_config_lisible_mais_hors_regle_leve_infrastructure_error(tmp_path: Path) -> None:
    """Une `config` bien formée mais hors règle (volées 0) remonte aussi en `InfrastructureError`.

    Le repository relit via `BaremeQualification.creer`, si bien qu'une incohérence en base ne
    produit jamais un value object silencieusement invalide.
    """
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        with db.session_factory() as session:
            session.add(
                PhaseORM(
                    tournoi_id=tournoi_id,
                    ordre=1,
                    type="qualification",
                    config='{"scoring": {"volees": 0, "fleches": 3, "mode": "cumul"}}',
                    statut="a_venir",
                )
            )
            session.commit()
        with pytest.raises(InfrastructureError):
            PhaseRepositorySQL(db.session_factory).par_tournoi_et_type(
                tournoi_id, TypePhase.QUALIFICATION
            )
    finally:
        db.engine.dispose()


def _phase_brute(db: Database, tournoi_id: TournoiId, config: str) -> None:
    """Écrit une ligne `phase` directement, pour simuler une `config` que le repository n'écrit
    pas (ligne antérieure à E01US015, ou base altérée)."""
    with db.session_factory() as session:
        session.add(
            PhaseORM(
                tournoi_id=tournoi_id,
                ordre=1,
                type="qualification",
                config=config,
                statut="a_venir",
            )
        )
        session.commit()


def test_le_grain_est_persiste_et_relu(tmp_path: Path) -> None:
    """Le grain fait l'aller-retour en base, cadence comprise (`config.validation`)."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        repository = PhaseRepositorySQL(db.session_factory)
        cree = repository.ajouter(
            Phase.qualification(
                tournoi_id,
                BaremeQualification.creer(20, 3),
                GrainValidation.toutes_les_n_volees(2),
            )
        )
        assert cree.id is not None

        relue = repository.par_id(cree.id)
        assert relue is not None
        assert relue.validation == GrainValidation.toutes_les_n_volees(2)
    finally:
        db.engine.dispose()


def test_enregistrer_met_a_jour_le_grain(tmp_path: Path) -> None:
    """`enregistrer` persiste l'édition du grain et conserve le barème."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        repository = PhaseRepositorySQL(db.session_factory)
        cree = repository.ajouter(Phase.qualification(tournoi_id, BaremeQualification.creer(20, 3)))
        assert cree.validation == GrainValidation.fin_de_serie()

        enregistre = repository.enregistrer(
            cree.avec_validation(GrainValidation.toutes_les_n_volees(4))
        )
        assert enregistre.validation == GrainValidation.toutes_les_n_volees(4)
        assert enregistre.bareme == cree.bareme
    finally:
        db.engine.dispose()


def test_un_grain_de_fin_nest_pas_serialise_avec_une_cadence(tmp_path: Path) -> None:
    """`fin de série` n'a pas de cadence : `n_volees` est absent du JSON, pas mis à `null`."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        repository = PhaseRepositorySQL(db.session_factory)
        cree = repository.ajouter(Phase.qualification(tournoi_id, BaremeQualification.creer(20, 3)))
        assert cree.id is not None

        with db.session_factory() as session:
            ligne = session.get(PhaseORM, cree.id)
            assert ligne is not None
            validation = json.loads(ligne.config)["validation"]
        assert validation == {"grain": "fin_de_serie"}
    finally:
        db.engine.dispose()


def test_une_phase_sans_cle_validation_se_relit_avec_le_preset_du_type(tmp_path: Path) -> None:
    """**Le cœur du « zéro migration »** : une phase écrite avant E01US015 n'a pas de clé
    `validation` ; elle se relit avec le preset de son type (`fin de série`), sans erreur."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        _phase_brute(db, tournoi_id, '{"scoring": {"volees": 20, "fleches": 3, "mode": "cumul"}}')

        relue = PhaseRepositorySQL(db.session_factory).par_tournoi_et_type(
            tournoi_id, TypePhase.QUALIFICATION
        )
        assert relue is not None
        assert relue.validation == GrainValidation.fin_de_serie()
        assert relue.bareme.nb_volees == 20
    finally:
        db.engine.dispose()


def test_une_phase_sans_cle_validation_reecrit_le_grain_a_lenregistrement(tmp_path: Path) -> None:
    """La ligne héritée se complète d'elle-même dès la première écriture : pas de rattrapage."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        _phase_brute(db, tournoi_id, '{"scoring": {"volees": 20, "fleches": 3, "mode": "cumul"}}')
        repository = PhaseRepositorySQL(db.session_factory)
        relue = repository.par_tournoi_et_type(tournoi_id, TypePhase.QUALIFICATION)
        assert relue is not None and relue.id is not None

        repository.enregistrer(relue.avec_validation(GrainValidation.toutes_les_n_volees(2)))

        with db.session_factory() as session:
            ligne = session.get(PhaseORM, relue.id)
            assert ligne is not None
            assert json.loads(ligne.config)["validation"] == {
                "grain": "toutes_les_n_volees",
                "n_volees": 2,
            }
    finally:
        db.engine.dispose()


def test_un_grain_present_mais_illisible_leve_infrastructure_error(tmp_path: Path) -> None:
    """Une clé `validation` **présente** et hors règle est une incohérence, pas un héritage."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        _phase_brute(
            db,
            tournoi_id,
            '{"scoring": {"volees": 20, "fleches": 3, "mode": "cumul"},'
            ' "validation": {"grain": "toutes_les_n_volees", "n_volees": 0}}',
        )
        with pytest.raises(InfrastructureError):
            PhaseRepositorySQL(db.session_factory).par_tournoi_et_type(
                tournoi_id, TypePhase.QUALIFICATION
            )
    finally:
        db.engine.dispose()


@pytest.mark.parametrize(
    "validation",
    ['"fin_de_serie"', "[]", "42", "null"],
    ids=["scalaire_texte", "tableau", "scalaire_nombre", "null"],
)
def test_une_cle_validation_qui_nest_pas_un_objet_leve_infrastructure_error(
    tmp_path: Path, validation: str
) -> None:
    """La clé `validation` **présente** doit être un objet : toute autre forme est une base
    altérée, pas une phase héritée (dont la clé serait *absente*) → `InfrastructureError`."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        _phase_brute(
            db,
            tournoi_id,
            '{"scoring": {"volees": 20, "fleches": 3, "mode": "cumul"},'
            f' "validation": {validation}}}',
        )
        with pytest.raises(InfrastructureError):
            PhaseRepositorySQL(db.session_factory).par_tournoi_et_type(
                tournoi_id, TypePhase.QUALIFICATION
            )
    finally:
        db.engine.dispose()


def test_un_grain_inconnu_leve_infrastructure_error(tmp_path: Path) -> None:
    """Un grain hors énumération (base altérée) ne produit pas de value object bancal."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        _phase_brute(
            db,
            tournoi_id,
            '{"scoring": {"volees": 20, "fleches": 3, "mode": "cumul"},'
            ' "validation": {"grain": "quand_ca_arrange"}}',
        )
        with pytest.raises(InfrastructureError):
            PhaseRepositorySQL(db.session_factory).par_tournoi_et_type(
                tournoi_id, TypePhase.QUALIFICATION
            )
    finally:
        db.engine.dispose()


def test_un_grain_incoherent_avec_le_bareme_leve_infrastructure_error(tmp_path: Path) -> None:
    """Barème et grain valides séparément mais incohérents entre eux : le repository n'écrit
    jamais ça (l'agrégat le refuse) — donc la base a été altérée → `InfrastructureError`."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        _phase_brute(
            db,
            tournoi_id,
            '{"scoring": {"volees": 5, "fleches": 3, "mode": "cumul"},'
            ' "validation": {"grain": "toutes_les_n_volees", "n_volees": 30}}',
        )
        with pytest.raises(InfrastructureError):
            PhaseRepositorySQL(db.session_factory).par_tournoi_et_type(
                tournoi_id, TypePhase.QUALIFICATION
            )
    finally:
        db.engine.dispose()
