"""Tests d'intégration du repository SQL des phases (E01US009 / ADR-0011, E01US015, E05US003).

Exerce l'adapter sur une **vraie base** créée par les migrations (`alembic upgrade head`) :
persistance du barème (sérialisation JSON `config.policies.scoring`, forme cible ADR-0046) et du
grain de validation (`config.validation`, hors `policies`), relecture par tournoi + type, mise à
jour, et enveloppe d'une `config` illisible. Une phase requiert un tournoi (FK `depart_id`).

E01US015 n'ajoute **aucune migration** : la politique s'ajoute dans le JSON existant. Les tests
`…_sans_cle_validation_…` verrouillent la contrepartie de ce choix — une ligne écrite avant
E01US015 doit se relire avec le preset de son type, pas exploser.

E05US003/ADR-0046 fait basculer `scoring` de la racine vers `config.policies` (résorbe DETTE-003).
Les lignes brutes en **ancienne forme à plat** (`'{"scoring": {…, "mode": "cumul"}}'`) écrites par
les helpers de test ci-dessous continuent de se relire (repli de `_lire_scoring`) : elles couvrent
donc, en plus de leur intention d'origine, la **compatibilité ascendante**. La bascule d'écriture
et la migration de données (`0028`) ont leurs tests dédiés en fin de fichier.
"""

from __future__ import annotations

import dataclasses
import datetime
import json
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from domain.bareme import BaremeQualification
from domain.depart import Depart, DepartId
from domain.deroule_etape import EtapeDeroule
from domain.format_tournoi import FormatTournoi, ModelePhase
from domain.grain_validation import GrainValidation
from domain.patrimoine import OrigineBrique
from domain.phase import Phase, SourcePhase, StatutPhase, TypePhase
from domain.politiques import ProfondeurClassement
from domain.poule import BaremePoule, ReglageDePoules
from domain.tournoi import Tournoi, TournoiId, TypeTournoi
from infrastructure.db import (
    Database,
    DepartORM,
    DepartRepositorySQL,
    DerouleEtapeORM,
    DerouleEtapeRepositorySQL,
    FormatTournoiRepositorySQL,
    PhaseORM,
    PhaseRepositorySQL,
    TournoiRepositorySQL,
)
from infrastructure.erreurs import InfrastructureError
from tests.base_migree import preparer_base
from tests.conftest import poser_phase_sql

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _migrer(url: str) -> None:
    preparer_base(url)


def _base(tmp_path: Path) -> Database:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    return Database(url)


def _depart(db: Database) -> DepartId:
    """Persiste un tournoi **et son créneau**, et renvoie l'identifiant du créneau.

    Une phase pend au **départ** depuis E01US025 (ADR-0075) : la FK `phase.depart_id` refuse
    désormais un identifiant de tournoi. C'est le seul test du lot où la distinction mord vraiment
    — ailleurs l'identifiant n'est qu'un entier de décor, ici c'est une contrainte SQL.
    """
    tournoi = TournoiRepositorySQL(db.session_factory).ajouter(
        Tournoi(
            nom="Kervignarc",
            date=datetime.date(2026, 3, 14),
            lieu=None,
            type_tournoi=TypeTournoi.NON_OFFICIEL,
        )
    )
    assert tournoi.id is not None
    depart = DepartRepositorySQL(db.session_factory).ajouter(
        Depart.creer(tournoi_id=tournoi.id, numero=1, tarif_centimes=800, horaire="09:00")
    )
    assert depart.id is not None
    return depart.id


def _tournoi_du(db: Database, depart_id: DepartId) -> TournoiId:
    """Le tournoi qui porte ce créneau — donc **le déroulé** de sa phase (ADR-0076).

    Le détour n'est pas de la cérémonie : `par_tournoi` attend un identifiant de **tournoi**, et
    `TournoiId` comme `DepartId` sont des alias de `int`, donc mypy ne dirait rien d'une confusion
    (DETTE-044). Les décors mono-créneau de ce fichier donnaient jusqu'ici le même entier des deux
    côtés — vrai par accident, faux dès le second départ.
    """
    with db.session_factory() as session:
        depart = session.get(DepartORM, depart_id)
        assert depart is not None, "Le décor doit avoir créé le créneau."
        return depart.tournoi_id


def _poser(db: Database, depart_id: DepartId, **reglages: Any) -> Phase:
    """Définit une étape sur le tournoi du créneau, l'y instancie, et rend la phase **assemblée**.

    Deux gestes depuis ADR-0076 : la définition (barème, grain, sources…) va sur `deroule_etape`,
    l'avancement sur `phase`. Les tests de ce fichier éprouvent l'aller-retour de la config — ils
    doivent donc écrire là où elle vit désormais, sinon ils vérifieraient une table vide.
    """
    etape = DerouleEtapeRepositorySQL(db.session_factory).ajouter(
        EtapeDeroule(tournoi_id=_tournoi_du(db, depart_id), **reglages)
    )
    return poser_phase_sql(db.session_factory, etape.instancier(depart_id))


def test_ajouter_puis_relire_par_depart_et_type(tmp_path: Path) -> None:
    """`ajouter` attribue un id ; `par_tournoi_et_type` relit le barème (config JSON comprise)."""
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        repository = PhaseRepositorySQL(db.session_factory)
        assert repository.par_depart_et_type(depart_id, TypePhase.QUALIFICATION) is None

        cree = _poser(
            db,
            depart_id,
            ordre=1,
            type=TypePhase.QUALIFICATION,
            bareme=BaremeQualification.preset_ffta_18m(),
            validation=GrainValidation.fin_de_serie(),
        )
        assert cree.id is not None
        assert cree.bareme is not None and cree.bareme.nb_volees == 20
        assert cree.bareme is not None and cree.bareme.nb_fleches_par_volee == 3

        relue = repository.par_depart_et_type(depart_id, TypePhase.QUALIFICATION)
        assert relue == cree
    finally:
        db.engine.dispose()


def test_editer_le_bareme_sur_l_etape_change_toutes_ses_instances(tmp_path: Path) -> None:
    """Le barème s'édite sur l'**étape** — et la phase de chaque créneau le relit (ADR-0076).

    Avant ADR-0076 cette édition passait par `PhaseRepository.enregistrer`, et un tournoi de N
    créneaux portait N copies : éditer l'une laissait les autres en arrière, sans que rien ne le
    signale. Le test le vérifie donc sur **deux** créneaux — une écriture, deux lectures d'accord.
    """
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        tournoi_id = _tournoi_du(db, depart_id)
        second = DepartRepositorySQL(db.session_factory).ajouter(
            Depart.creer(tournoi_id=tournoi_id, numero=2, tarif_centimes=800, horaire="14:00")
        )
        assert second.id is not None
        repository = PhaseRepositorySQL(db.session_factory)
        cree = _poser(
            db,
            depart_id,
            ordre=1,
            type=TypePhase.QUALIFICATION,
            bareme=BaremeQualification.creer(20, 3),
            validation=GrainValidation.fin_de_serie(),
        )
        assert cree.id is not None

        # L'étape est **partagée** : le second créneau l'instancie, il ne la redéfinit pas. C'est
        # le geste de production (`ServicePhases` fait exactement cela pour chaque créneau).
        deroules = DerouleEtapeRepositorySQL(db.session_factory)
        (etape,) = deroules.par_tournoi(tournoi_id)
        repository.ajouter(etape.instancier(second.id))

        deroules.enregistrer(dataclasses.replace(etape, bareme=BaremeQualification.creer(10, 6)))

        for identifiant in (depart_id, second.id):
            (relue,) = repository.par_depart(identifiant)
            assert relue.bareme is not None
            assert (relue.bareme.nb_volees, relue.bareme.nb_fleches_par_volee) == (10, 6)
    finally:
        db.engine.dispose()


def test_enregistrer_une_phase_ne_deplace_pas_sa_definition(tmp_path: Path) -> None:
    """Contrat du port : un barème modifié passé à `PhaseRepository.enregistrer` ne change **rien**.

    C'est le piège que la séparation crée, donc celui qu'il faut fermer par un test : le code
    d'avant ADR-0076 éditait ainsi, et il compile toujours. Sans ce verrou, une régression
    ressemblerait à une écriture réussie — et se lirait comme une donnée perdue.
    """
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        repository = PhaseRepositorySQL(db.session_factory)
        cree = _poser(
            db,
            depart_id,
            ordre=1,
            type=TypePhase.QUALIFICATION,
            bareme=BaremeQualification.creer(20, 3),
            validation=GrainValidation.fin_de_serie(),
        )
        assert cree.id is not None

        enregistre = repository.enregistrer(cree.avec_bareme(BaremeQualification.creer(10, 6)))

        assert enregistre.id == cree.id
        assert enregistre.bareme == BaremeQualification.creer(20, 3), (
            "La définition vient de l'étape : `PhaseRepository.enregistrer` ne déplace que "
            "l'avancement (ADR-0076). L'éditer ici doit être sans effet, pas silencieusement pris."
        )
        assert repository.par_id(cree.id) == enregistre
    finally:
        db.engine.dispose()


def test_par_tournoi_et_type_isole_les_tournois(tmp_path: Path) -> None:
    """`par_tournoi_et_type` ne renvoie que la phase du tournoi demandé."""
    db = _base(tmp_path)
    try:
        premier = _depart(db)
        second = _depart(db)
        repository = PhaseRepositorySQL(db.session_factory)
        _poser(
            db,
            premier,
            ordre=1,
            type=TypePhase.QUALIFICATION,
            bareme=BaremeQualification.creer(20, 3),
            validation=GrainValidation.fin_de_serie(),
        )

        assert repository.par_depart_et_type(second, TypePhase.QUALIFICATION) is None
        du_premier = repository.par_depart_et_type(premier, TypePhase.QUALIFICATION)
        assert du_premier is not None and du_premier.depart_id == premier
    finally:
        db.engine.dispose()


def test_config_corrompue_leve_infrastructure_error(tmp_path: Path) -> None:
    """Une `config` illisible en base est enveloppée en `InfrastructureError` (pas de 500 brut)."""
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        _phase_brute(db, depart_id, "pas du json")
        with pytest.raises(InfrastructureError):
            PhaseRepositorySQL(db.session_factory).par_depart_et_type(
                depart_id, TypePhase.QUALIFICATION
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
        depart_id = _depart(db)
        _phase_brute(db, depart_id, '{"scoring": {"volees": 0, "fleches": 3, "mode": "cumul"}}')
        with pytest.raises(InfrastructureError):
            PhaseRepositorySQL(db.session_factory).par_depart_et_type(
                depart_id, TypePhase.QUALIFICATION
            )
    finally:
        db.engine.dispose()


def _tournoi_au_schema_historique(db: Database) -> TournoiId:
    """Insère un tournoi en **SQL explicite**, pour une base arrêtée à une révision ancienne.

    `_tournoi` passe par `TournoiRepositorySQL`, donc par le mapping ORM **courant** : dès qu'une
    migration ajoute une colonne à `tournoi` (E05US021 et sa `effectif_minimum_exige`, 0040),
    l'`INSERT` généré nomme une colonne que le schéma historique n'a pas, et le test de migration
    échoue pour une raison qui n'a rien à voir avec ce qu'il vérifie.

    On nomme donc **explicitement** les seules colonnes qui existaient déjà. Le test devient
    insensible aux colonnes futures, ce qu'un test de migration doit être par nature : il décrit un
    passé, que le présent n'a pas à réécrire.
    """
    with db.session_factory() as session:
        session.execute(
            text(
                "INSERT INTO tournoi (nom, date, lieu, type_tournoi, statut) "
                "VALUES (:nom, :date, NULL, :type_tournoi, :statut)"
            ),
            {
                "nom": "Kervignarc",
                "date": "2026-03-14",
                "type_tournoi": TypeTournoi.NON_OFFICIEL.value,
                "statut": "brouillon",
            },
        )
        session.commit()
        identifiant = session.execute(text("SELECT id FROM tournoi")).scalar_one()
    assert isinstance(identifiant, int)
    return identifiant


def _phase_brute_au_schema_0027(db: Database, tournoi_id: TournoiId, config: str) -> None:
    """Écrit une ligne `phase` **au schéma d'avant la 0042** (colonne `tournoi_id`).

    Réservée au test de la migration `0028`, qui monte une base à la 0027 : à cette date la portée
    sportive était encore le tournoi. Utiliser le helper courant y écrirait une colonne qui n'existe
    pas encore.
    """
    with db.session_factory() as session:
        session.execute(
            text(
                "INSERT INTO phase (tournoi_id, ordre, type, config, statut) "
                "VALUES (:tournoi_id, 1, 'qualification', :config, 'a_venir')"
            ),
            {"tournoi_id": tournoi_id, "config": config},
        )
        session.commit()


def _phase_brute(db: Database, depart_id: DepartId, config: str) -> None:
    """Écrit **l'étape et son avancement** directement, pour simuler une `config` que le repository
    n'écrit pas (ligne antérieure à E01US015, ou base altérée).

    Deux lignes depuis ADR-0076 : la `config` vit sur l'étape du **tournoi**, l'avancement sur la
    phase du **créneau**. Le test qui s'en sert éprouve la relecture d'une config douteuse — donc
    c'est bien l'étape qu'il faut salir, la phase n'en portant plus.
    """
    with db.session_factory() as session:
        depart = session.get(DepartORM, depart_id)
        assert depart is not None, "Le décor doit avoir créé le créneau."
        session.add(
            DerouleEtapeORM(
                tournoi_id=depart.tournoi_id, ordre=1, type="qualification", config=config
            )
        )
        session.add(PhaseORM(depart_id=depart_id, ordre=1, statut="a_venir"))
        session.commit()


def test_le_grain_est_persiste_et_relu(tmp_path: Path) -> None:
    """Le grain fait l'aller-retour en base, cadence comprise (`config.validation`)."""
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        repository = PhaseRepositorySQL(db.session_factory)
        cree = poser_phase_sql(
            db.session_factory,
            Phase.qualification(
                depart_id,
                BaremeQualification.creer(20, 3),
                GrainValidation.toutes_les_n_volees(2),
            ),
        )
        assert cree.id is not None

        relue = repository.par_id(cree.id)
        assert relue is not None
        assert relue.validation == GrainValidation.toutes_les_n_volees(2)
    finally:
        db.engine.dispose()


def test_editer_le_grain_sur_l_etape_conserve_le_bareme(tmp_path: Path) -> None:
    """Éditer le grain sur l'étape le persiste et **laisse le barème intact** (ADR-0076).

    Les deux réglages vivent dans la même `config` JSON : une écriture partielle qui écraserait
    l'autre serait une perte silencieuse, du même genre que celle qu'ADR-0076 vient de fermer.
    """
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        repository = PhaseRepositorySQL(db.session_factory)
        cree = _poser(
            db,
            depart_id,
            ordre=1,
            type=TypePhase.QUALIFICATION,
            bareme=BaremeQualification.creer(20, 3),
            validation=GrainValidation.fin_de_serie(),
        )
        assert cree.id is not None and cree.validation == GrainValidation.fin_de_serie()

        deroules = DerouleEtapeRepositorySQL(db.session_factory)
        (etape,) = deroules.par_tournoi(_tournoi_du(db, depart_id))
        deroules.enregistrer(
            dataclasses.replace(etape, validation=GrainValidation.toutes_les_n_volees(4))
        )

        relue = repository.par_id(cree.id)
        assert relue is not None
        assert relue.validation == GrainValidation.toutes_les_n_volees(4)
        assert relue.bareme == cree.bareme
    finally:
        db.engine.dispose()


def test_un_grain_de_fin_nest_pas_serialise_avec_une_cadence(tmp_path: Path) -> None:
    """`fin de série` n'a pas de cadence : `n_volees` est absent du JSON, pas mis à `null`."""
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        cree = _poser(
            db,
            depart_id,
            ordre=1,
            type=TypePhase.QUALIFICATION,
            bareme=BaremeQualification.creer(20, 3),
            validation=GrainValidation.fin_de_serie(),
        )
        assert cree.id is not None

        with db.session_factory() as session:
            ligne = session.query(DerouleEtapeORM).one()
            validation = json.loads(ligne.config)["validation"]
        assert validation == {"grain": "fin_de_serie"}
    finally:
        db.engine.dispose()


def test_une_phase_sans_cle_validation_se_relit_avec_le_preset_du_type(tmp_path: Path) -> None:
    """**Le cœur du « zéro migration »** : une phase écrite avant E01US015 n'a pas de clé
    `validation` ; elle se relit avec le preset de son type (`fin de série`), sans erreur."""
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        _phase_brute(db, depart_id, '{"scoring": {"volees": 20, "fleches": 3, "mode": "cumul"}}')

        relue = PhaseRepositorySQL(db.session_factory).par_depart_et_type(
            depart_id, TypePhase.QUALIFICATION
        )
        assert relue is not None
        assert relue.validation == GrainValidation.fin_de_serie()
        assert relue.bareme is not None and relue.bareme.nb_volees == 20
    finally:
        db.engine.dispose()


def test_une_phase_sans_cle_validation_reecrit_le_grain_a_lenregistrement(tmp_path: Path) -> None:
    """La ligne héritée se complète d'elle-même dès la première écriture : pas de rattrapage."""
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        _phase_brute(db, depart_id, '{"scoring": {"volees": 20, "fleches": 3, "mode": "cumul"}}')
        repository = PhaseRepositorySQL(db.session_factory)
        relue = repository.par_depart_et_type(depart_id, TypePhase.QUALIFICATION)
        assert relue is not None and relue.id is not None

        # ⚠️ **La définition s'édite sur l'étape, pas sur la phase** (ADR-0076) : le port le dit
        # explicitement, et passer par `PhaseRepositorySQL.enregistrer` ne changerait *rien* — c'est
        # précisément le piège que ce contrat existe pour fermer.
        deroules = DerouleEtapeRepositorySQL(db.session_factory)
        with db.session_factory() as session:
            depart = session.get(DepartORM, depart_id)
            assert depart is not None
            tournoi_id = depart.tournoi_id
        (etape,) = deroules.par_tournoi(tournoi_id)
        deroules.enregistrer(
            dataclasses.replace(etape, validation=GrainValidation.toutes_les_n_volees(2))
        )

        with db.session_factory() as session:
            ligne = session.query(DerouleEtapeORM).one()
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
        depart_id = _depart(db)
        _phase_brute(
            db,
            depart_id,
            '{"scoring": {"volees": 20, "fleches": 3, "mode": "cumul"},'
            ' "validation": {"grain": "toutes_les_n_volees", "n_volees": 0}}',
        )
        with pytest.raises(InfrastructureError):
            PhaseRepositorySQL(db.session_factory).par_depart_et_type(
                depart_id, TypePhase.QUALIFICATION
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
        depart_id = _depart(db)
        _phase_brute(
            db,
            depart_id,
            '{"scoring": {"volees": 20, "fleches": 3, "mode": "cumul"},'
            f' "validation": {validation}}}',
        )
        with pytest.raises(InfrastructureError):
            PhaseRepositorySQL(db.session_factory).par_depart_et_type(
                depart_id, TypePhase.QUALIFICATION
            )
    finally:
        db.engine.dispose()


def test_un_grain_inconnu_leve_infrastructure_error(tmp_path: Path) -> None:
    """Un grain hors énumération (base altérée) ne produit pas de value object bancal."""
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        _phase_brute(
            db,
            depart_id,
            '{"scoring": {"volees": 20, "fleches": 3, "mode": "cumul"},'
            ' "validation": {"grain": "quand_ca_arrange"}}',
        )
        with pytest.raises(InfrastructureError):
            PhaseRepositorySQL(db.session_factory).par_depart_et_type(
                depart_id, TypePhase.QUALIFICATION
            )
    finally:
        db.engine.dispose()


def test_un_grain_incoherent_avec_le_bareme_leve_infrastructure_error(tmp_path: Path) -> None:
    """Barème et grain valides séparément mais incohérents entre eux : le repository n'écrit
    jamais ça (l'agrégat le refuse) — donc la base a été altérée → `InfrastructureError`."""
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        _phase_brute(
            db,
            depart_id,
            '{"scoring": {"volees": 5, "fleches": 3, "mode": "cumul"},'
            ' "validation": {"grain": "toutes_les_n_volees", "n_volees": 30}}',
        )
        with pytest.raises(InfrastructureError):
            PhaseRepositorySQL(db.session_factory).par_depart_et_type(
                depart_id, TypePhase.QUALIFICATION
            )
    finally:
        db.engine.dispose()


# --- E05US001 : phase générique, source/effectif, séquence, suppression ------------------------


def test_une_phase_generique_sans_bareme_fait_l_aller_retour(tmp_path: Path) -> None:
    """Une phase d'élimination directe se persiste **sans** scoring/validation ; source et effectif
    y font l'aller-retour (config JSON à plat, ADR-0045)."""
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        repository = PhaseRepositorySQL(db.session_factory)
        _poser(
            db,
            depart_id,
            ordre=1,
            type=TypePhase.QUALIFICATION,
            bareme=BaremeQualification.creer(20, 3),
            validation=GrainValidation.fin_de_serie(),
        )

        elim = poser_phase_sql(
            db.session_factory,
            Phase.creer(
                depart_id,
                ordre=2,
                type=TypePhase.ELIMINATION_DIRECTE,
                sources=(SourcePhase(ordre_source=1, rang_debut=1, rang_fin=16),),
                effectif=16,
            ),
        )
        assert elim.id is not None

        relue = repository.par_id(elim.id)
        assert relue == elim
        assert relue is not None
        assert relue.bareme is None
        assert relue.validation is None
        assert relue.sources == (SourcePhase(ordre_source=1, rang_debut=1, rang_fin=16),)
        assert relue.effectif == 16

        # Le JSON ne porte ni scoring ni validation pour une phase non-qualification. On vise
        # l'étape **de rang 2** : le décor en a posé deux, la qualification occupant le rang 1.
        with db.session_factory() as session:
            ligne = session.query(DerouleEtapeORM).filter_by(ordre=2).one()
            config = json.loads(ligne.config)
        assert "scoring" not in config and "validation" not in config
        assert config["sources"] == [
            {"nature": "rangs", "ordre_source": 1, "rang_debut": 1, "rang_fin": 16}
        ]
    finally:
        db.engine.dispose()


def test_par_tournoi_renvoie_les_phases_ordonnees(tmp_path: Path) -> None:
    """`par_tournoi` trie par `ordre` et isole le tournoi demandé."""
    db = _base(tmp_path)
    try:
        premier = _depart(db)
        second = _depart(db)
        repository = PhaseRepositorySQL(db.session_factory)
        _poser(
            db,
            premier,
            ordre=1,
            type=TypePhase.QUALIFICATION,
            bareme=BaremeQualification.creer(20, 3),
            validation=GrainValidation.fin_de_serie(),
        )
        poser_phase_sql(
            db.session_factory, Phase.creer(premier, ordre=2, type=TypePhase.ELIMINATION_DIRECTE)
        )
        poser_phase_sql(db.session_factory, Phase.creer(premier, ordre=3, type=TypePhase.PLACEMENT))
        _poser(
            db,
            second,
            ordre=1,
            type=TypePhase.QUALIFICATION,
            bareme=BaremeQualification.creer(10, 3),
            validation=GrainValidation.fin_de_serie(),
        )

        phases = repository.par_depart(premier)
        assert [p.ordre for p in phases] == [1, 2, 3]
        assert [p.type for p in phases] == [
            TypePhase.QUALIFICATION,
            TypePhase.ELIMINATION_DIRECTE,
            TypePhase.PLACEMENT,
        ]
        assert repository.par_depart(second) == [
            repository.par_depart_et_type(second, TypePhase.QUALIFICATION)
        ]
    finally:
        db.engine.dispose()


def test_supprimer_retire_la_phase(tmp_path: Path) -> None:
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        repository = PhaseRepositorySQL(db.session_factory)
        phase = poser_phase_sql(
            db.session_factory, Phase.creer(depart_id, ordre=1, type=TypePhase.ELIMINATION_DIRECTE)
        )
        assert phase.id is not None

        repository.supprimer(phase.id)

        assert repository.par_id(phase.id) is None
        assert repository.par_depart(depart_id) == []
    finally:
        db.engine.dispose()


def test_le_statut_en_pause_fait_l_aller_retour(tmp_path: Path) -> None:
    """`en_pause` (E05US001) se persiste et se relit comme les autres statuts."""
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        repository = PhaseRepositorySQL(db.session_factory)
        phase = poser_phase_sql(
            db.session_factory, Phase.creer(depart_id, ordre=1, type=TypePhase.ELIMINATION_DIRECTE)
        )
        assert phase.id is not None

        repository.enregistrer(phase.demarrer().mettre_en_pause())

        relue = repository.par_id(phase.id)
        assert relue is not None
        assert relue.statut is StatutPhase.EN_PAUSE
    finally:
        db.engine.dispose()


def test_un_statut_illisible_leve_infrastructure_error(tmp_path: Path) -> None:
    """Un `statut` hors énumération (base altérée) remonte en `InfrastructureError`, pas en 500 :
    le cast est dans le bloc qui enveloppe (revue axe C1)."""
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        _tableau_brut(db, depart_id, "{}", statut="en_vacances")
        with pytest.raises(InfrastructureError):
            PhaseRepositorySQL(db.session_factory).par_tournoi(_tournoi_du(db, depart_id))
    finally:
        db.engine.dispose()


def test_une_source_illisible_leve_infrastructure_error(tmp_path: Path) -> None:
    """Une `config.source` bien formée mais hors règle (plage vide) est une base altérée : le
    repository relit via `SourcePhase`, donc jamais un value object silencieusement invalide."""
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        _tableau_brut(
            db, depart_id, '{"source": {"ordre_source": 1, "rang_debut": 8, "rang_fin": 4}}'
        )
        with pytest.raises(InfrastructureError):
            PhaseRepositorySQL(db.session_factory).par_tournoi(_tournoi_du(db, depart_id))
    finally:
        db.engine.dispose()


# --- E05US003 / ADR-0046 : bascule config.policies + compatibilité ascendante ------------------


def test_le_scoring_est_persiste_sous_policies(tmp_path: Path) -> None:
    """Forme cible (ADR-0046) : le barème s'écrit sous `config.policies.scoring`, nommé « cumul »
    et paramétré (volées x flèches), **pas** à la racine. C'est la résorption de DETTE-003."""
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        cree = _poser(
            db,
            depart_id,
            ordre=1,
            type=TypePhase.QUALIFICATION,
            bareme=BaremeQualification.creer(20, 3),
            validation=GrainValidation.fin_de_serie(),
        )
        assert cree.id is not None

        with db.session_factory() as session:
            ligne = session.query(DerouleEtapeORM).one()
            config = json.loads(ligne.config)
        assert "scoring" not in config  # plus à la racine
        assert config["policies"]["scoring"] == {"nom": "cumul", "volees": 20, "fleches": 3}
    finally:
        db.engine.dispose()


def test_ancienne_forme_a_plat_du_scoring_se_relit(tmp_path: Path) -> None:
    """Compatibilité ascendante (DETTE-003 c) : une ligne écrite avant E05US003 (scoring à la
    racine, clé `mode`) se relit sans erreur — filet pour une base restaurée d'une sauvegarde
    antérieure à la migration `0028`. Le barème est intact ; `mode`/`nom` n'entre pas en jeu."""
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        _phase_brute(db, depart_id, '{"scoring": {"volees": 15, "fleches": 6, "mode": "cumul"}}')

        relue = PhaseRepositorySQL(db.session_factory).par_depart_et_type(
            depart_id, TypePhase.QUALIFICATION
        )
        assert relue is not None
        assert relue.bareme is not None
        assert relue.bareme.nb_volees == 15
        assert relue.bareme.nb_fleches_par_volee == 6
    finally:
        db.engine.dispose()


def test_migration_0028_deplace_le_scoring_sous_policies(tmp_path: Path) -> None:
    """La migration de données `0028` réécrit une `config` héritée (scoring à la racine) en forme
    `policies`. On monte jusqu'à `0027`, insère une ligne à plat, puis on migre jusqu'au head."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "0027_volee_created_at")

    db = Database(url)
    try:
        # ⚠️ **À la révision 0027, `phase` pend encore au tournoi** : la bascule vers `depart_id`
        # est la 0042. Un test de migration doit parler le schéma **de sa révision**, sinon il
        # vérifie un passé qui n'a jamais existé. D'où l'écriture SQL brute ci-dessous, sur
        # `tournoi_id`, et non le helper `_phase_brute` qui suit le schéma d'aujourd'hui.
        tournoi_id = _tournoi_au_schema_historique(db)
        _phase_brute_au_schema_0027(
            db,
            tournoi_id,
            '{"scoring": {"volees": 20, "fleches": 3, "mode": "cumul"},'
            ' "validation": {"grain": "fin_de_serie"}}',
        )
    finally:
        db.engine.dispose()

    command.upgrade(cfg, "head")

    db = Database(url)
    try:
        with db.session_factory() as session:
            ligne = session.query(DerouleEtapeORM).one()
            config = json.loads(ligne.config)
        assert "scoring" not in config  # déplacé
        assert config["policies"]["scoring"] == {"nom": "cumul", "volees": 20, "fleches": 3}
        assert config["validation"] == {"grain": "fin_de_serie"}  # resté à la racine
    finally:
        db.engine.dispose()


# --- Profondeur de classement (E06US006, ADR-0070) ----------------------------------------------


def _tableau_brut(db: Database, depart_id: DepartId, config: str, statut: str = "a_venir") -> None:
    """Écrit une **étape de tableau et son avancement** directement, config et statut imposés.

    Jumeau de `_phase_brute`, qui force `type="qualification"` : une profondeur ne se règle que sur
    un tableau, et la relire sur une qualification échouerait pour une **autre** raison (barème
    manquant), donc sans rien prouver de ce qu'on veut vérifier.

    `statut` est paramétrable parce que c'est le **seul** champ de la phase qu'une base altérée peut
    encore corrompre depuis ADR-0076 — tout le reste a migré sur l'étape.
    """
    with db.session_factory() as session:
        depart = session.get(DepartORM, depart_id)
        assert depart is not None, "Le décor doit avoir créé le créneau."
        session.add(
            DerouleEtapeORM(
                tournoi_id=depart.tournoi_id,
                ordre=1,
                type="elimination_directe",
                config=config,
            )
        )
        session.add(
            PhaseORM(
                depart_id=depart_id,
                ordre=1,
                statut=statut,
            )
        )
        session.commit()


def test_la_profondeur_fait_l_aller_retour(tmp_path: Path) -> None:
    """`config.policies.depth` s'écrit et se relit à l'identique, sans migration."""
    db = _base(tmp_path)
    depart_id = _depart(db)
    repo = PhaseRepositorySQL(db.session_factory)

    integrale = poser_phase_sql(
        db.session_factory,
        Phase.creer(
            depart_id,
            ordre=1,
            type=TypePhase.ELIMINATION_DIRECTE,
            profondeur=ProfondeurClassement.integrale(),
        ),
    )
    top = poser_phase_sql(
        db.session_factory,
        Phase.creer(
            depart_id,
            ordre=2,
            type=TypePhase.ELIMINATION_DIRECTE,
            profondeur=ProfondeurClassement.top(8),
        ),
    )

    relues = {p.ordre: p.profondeur for p in repo.par_tournoi(_tournoi_du(db, depart_id))}
    assert relues[1] == ProfondeurClassement.integrale()
    assert relues[2] == ProfondeurClassement.top(8)
    assert integrale.profondeur == relues[1] and top.profondeur == relues[2]


def test_une_phase_sans_cle_depth_se_relit_non_reglee(tmp_path: Path) -> None:
    """Contrepartie du choix « aucune migration » : une ligne écrite **avant** E06US006 se relit
    `profondeur=None`, donc au preset de son type — elle ne doit ni exploser, ni changer de régime.

    C'est l'affirmation centrale d'ADR-0070 §3 (« rien de déjà joué ne bouge ») ; rien ne la
    vérifiait avant cette correction de revue.
    """
    db = _base(tmp_path)
    depart_id = _depart(db)
    _tableau_brut(db, depart_id, json.dumps({"validation": {"grain": "fin_de_duel"}}))

    phase = PhaseRepositorySQL(db.session_factory).par_tournoi(_tournoi_du(db, depart_id))[0]

    assert phase.profondeur is None


@pytest.mark.parametrize(
    "depth",
    [
        {"nom": "aucun"},  # existe au catalogue, jamais offert en façade → base altérée
        {"nom": "top_n"},  # top N sans rang d'arrêt
        {"nom": "un_vers_n", "jusqu_au": 4},  # deux profondeurs contradictoires
        {"jusqu_au": 4},  # pas de nom : on ne devine pas l'implémentation
        {"nom": "inconnue"},
    ],
)
def test_une_profondeur_alteree_remonte_en_erreur_typee(
    tmp_path: Path, depth: dict[str, object]
) -> None:
    """Une `config` altérée hors API doit rendre « configuration illisible », **jamais** un 500 nu.

    Le repository attrape `KeyError` / `ValueError` / `DomainError` et les enveloppe. Le jour où
    quelqu'un resserre ce tuple d'exceptions, une seule ligne corrompue mettrait toute la lecture
    en 500 — la panne déjà documentée sur `_vers_modele_phase`, sans route pour s'en sortir.
    """
    db = _base(tmp_path)
    depart_id = _depart(db)
    _tableau_brut(db, depart_id, json.dumps({"policies": {"depth": depth}}))

    with pytest.raises(InfrastructureError):
        PhaseRepositorySQL(db.session_factory).par_tournoi(_tournoi_du(db, depart_id))


# --- E05US023 / ADR-0083 : le réglage de poules à la racine du `config` -------------------------


def _poules_brutes(db: Database, depart_id: DepartId, config: str) -> None:
    """Jumeau de `_tableau_brut` pour une étape de **type poules**, config imposée.

    Un réglage de poules relu sur une élimination directe échouerait pour une **autre** raison
    (`ReglageDePoulesInvalide` : le type n'en porte pas), donc sans rien prouver de la relecture
    elle-même. Il faut le bon type pour que le test parle du bon sujet.
    """
    with db.session_factory() as session:
        depart = session.get(DepartORM, depart_id)
        assert depart is not None, "Le décor doit avoir créé le créneau."
        session.add(
            DerouleEtapeORM(tournoi_id=depart.tournoi_id, ordre=1, type="poules", config=config)
        )
        session.add(PhaseORM(depart_id=depart_id, ordre=1, statut="a_venir"))
        session.commit()


def test_le_reglage_de_poules_fait_l_aller_retour(tmp_path: Path) -> None:
    """`config.poules` s'écrit et se relit à l'identique — **sans migration**.

    C'est le CA « le réglage vit dans le `config`, sans migration » : il tient dans le JSON
    existant. **À la racine**, comme `validation`/`sources`/`effectif`, et non sous `policies` —
    ce dernier est un catalogue **fermé** de familles injectables (`FamillePolitique`), et une
    taille de poule n'est pas une stratégie (arbitrage de revue, reversé au CA). Aucune colonne
    neuve, alors que
    le *placement* des poules, lui, en demandera une (ADR-0083 §3) — la différence tient à ce que
    le réglage est **de la configuration** et le plan **de la donnée d'exploitation**.
    """
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        reglage = ReglageDePoules(
            taille_visee=4,
            bareme=BaremePoule(victoire=2, nul=1, defaite=0),
            nb_qualifies=2,
            rencontres_par_archer=3,
        )

        _poser(db, depart_id, ordre=1, type=TypePhase.POULES, poules=reglage)
        relue = PhaseRepositorySQL(db.session_factory).par_tournoi(_tournoi_du(db, depart_id))[0]

        assert relue.poules == reglage
    finally:
        db.engine.dispose()


def test_un_bareme_non_defaut_ne_se_relit_pas_du_defaut_de_code(tmp_path: Path) -> None:
    """Le barème est **écrit même quand il vaut le défaut**, et relu de ce qui est écrit.

    Le piège serait de n'écrire que ce qui diffère de 3/1/0 pour alléger le document : le jour où
    ce défaut changerait, tous les tournois déjà réglés changeraient de points de match **sans que
    personne ne touche à leur réglage**. Un classement de poule resterait parfaitement cohérent, et
    faux — c'est le mode de défaillance que `BaremePoule` documente déjà pour l'invariant
    victoire ≥ nul ≥ défaite.
    """
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        _poser(
            db,
            depart_id,
            ordre=1,
            type=TypePhase.POULES,
            poules=ReglageDePoules(taille_visee=4, bareme=BaremePoule()),
        )

        with db.session_factory() as session:
            ligne = session.execute(text("SELECT config FROM deroule_etape")).scalar_one()

        assert json.loads(ligne)["poules"]["bareme"] == [3, 1, 0]
    finally:
        db.engine.dispose()


def test_une_phase_de_poules_non_reglee_se_relit_sans_reglage(tmp_path: Path) -> None:
    """Le type se choisit **avant** ses paramètres : le déroulé s'enregistre en cours de route.

    C'est le brouillon d'ADR-0063 appliqué aux poules — l'absence de clé n'est pas une incohérence,
    et la relecture ne doit surtout pas inventer une taille. C'est la **composition du jour J** qui
    exigera le réglage, pas la relecture.
    """
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        _poules_brutes(db, depart_id, "{}")

        relue = PhaseRepositorySQL(db.session_factory).par_tournoi(_tournoi_du(db, depart_id))[0]

        assert relue.poules is None
    finally:
        db.engine.dispose()


@pytest.mark.parametrize(
    "poules",
    [
        {"taille": 1},  # une poule apparie au moins deux archers
        {"taille": 4, "bareme": [0, 1, 3]},  # perdre ferait monter
        {"taille": 4, "qualifies": 5},  # plus de qualifiés que de membres
        {},  # pas de taille : on ne devine pas la répartition
    ],
)
def test_un_reglage_de_poules_altere_remonte_en_erreur_typee(
    tmp_path: Path, poules: dict[str, object]
) -> None:
    """Une `config` altérée hors API rend « configuration illisible », **jamais** un value object.

    Le repository n'écrit jamais ces valeurs — l'agrégat les refuse en amont —, donc les trouver en
    base signifie que quelqu'un a édité le fichier. Les relire par la fabrique du domaine plutôt
    que de construire à la main est ce qui transforme « poules absurdes le jour J » en refus net à
    la lecture (ADR-0007).
    """
    db = _base(tmp_path)
    try:
        depart_id = _depart(db)
        _poules_brutes(db, depart_id, json.dumps({"poules": poules}))

        with pytest.raises(InfrastructureError):
            PhaseRepositorySQL(db.session_factory).par_tournoi(_tournoi_du(db, depart_id))
    finally:
        db.engine.dispose()


# --- E05US023 : la **seconde** table — le format de bibliothèque ------------------------------


def test_un_format_conserve_le_reglage_de_poules_et_le_seuil_de_barrage(tmp_path: Path) -> None:
    """L'aller-retour du **format**, seconde représentation de la même définition (ADR-0060 §5).

    Deux champs y sont vérifiés ensemble, et le second est un correctif :

    - `poules` : sans lui, promouvoir un tournoi dont une phase est réglée en poules de 4 rendrait
      un format qui ne l'est plus. C'est l'écueil que la migration 0036 nommait — « un format resté
      en forme ancienne produirait, à l'application, exactement le défaut qu'on vient de corriger ».
    - `barrage_jusqu_au` : **il était perdu**. `ModelePhase` le porte depuis le 07/08/2026, avec une
      docstring affirmant que le défaut est clos — mais `_config_format` ne le passait pas à
      `_politiques_json`, si bien que le champ existait dans l'agrégat et disparaissait à
      l'écriture. Le défaut avait seulement changé d'étage, de l'agrégat vers sa sérialisation, et
      rien ne le testait. Trouvé en câblant `poules` par le même chemin.

    C'est la raison pour laquelle ce test vérifie une **égalité d'étapes**, pas deux champs isolés :
    un aller-retour se garde en entier, sinon le prochain champ ajouté se perdra de la même façon.
    """
    db = _base(tmp_path)
    try:
        modele = ModelePhase(
            ordre=1,
            type=TypePhase.POULES,
            poules=ReglageDePoules(taille_visee=4, nb_qualifies=2),
            barrage_jusqu_au=8,
        )
        repository = FormatTournoiRepositorySQL(db.session_factory)

        cree = repository.ajouter(
            FormatTournoi.creer("Poules de 4", [modele], OrigineBrique.UTILISATEUR)
        )
        assert cree.id is not None
        relu = repository.par_id(cree.id)

        assert relu is not None
        assert relu.etapes == (modele,)
    finally:
        db.engine.dispose()
