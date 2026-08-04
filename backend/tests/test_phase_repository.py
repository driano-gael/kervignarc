"""Tests d'intégration du repository SQL des phases (E01US009 / ADR-0011, E01US015, E05US003).

Exerce l'adapter sur une **vraie base** créée par les migrations (`alembic upgrade head`) :
persistance du barème (sérialisation JSON `config.policies.scoring`, forme cible ADR-0046) et du
grain de validation (`config.validation`, hors `policies`), relecture par tournoi + type, mise à
jour, et enveloppe d'une `config` illisible. Une phase requiert un tournoi (FK `tournoi_id`).

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

import datetime
import json
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from domain.bareme import BaremeQualification
from domain.grain_validation import GrainValidation
from domain.phase import Phase, SourcePhase, StatutPhase, TypePhase
from domain.politiques import ProfondeurClassement
from domain.tournoi import Tournoi, TournoiId, TypeTournoi
from infrastructure.db import Database, PhaseORM, PhaseRepositorySQL, TournoiRepositorySQL
from infrastructure.erreurs import InfrastructureError
from tests.base_migree import preparer_base

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _migrer(url: str) -> None:
    preparer_base(url)


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
        assert cree.bareme is not None and cree.bareme.nb_volees == 20
        assert cree.bareme is not None and cree.bareme.nb_fleches_par_volee == 3

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
        assert enregistre.bareme is not None and enregistre.bareme.nb_volees == 10
        assert enregistre.bareme is not None and enregistre.bareme.nb_fleches_par_volee == 6
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
        assert relue.bareme is not None and relue.bareme.nb_volees == 20
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


# --- E05US001 : phase générique, source/effectif, séquence, suppression ------------------------


def test_une_phase_generique_sans_bareme_fait_l_aller_retour(tmp_path: Path) -> None:
    """Une phase d'élimination directe se persiste **sans** scoring/validation ; source et effectif
    y font l'aller-retour (config JSON à plat, ADR-0045)."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        repository = PhaseRepositorySQL(db.session_factory)
        repository.ajouter(Phase.qualification(tournoi_id, BaremeQualification.creer(20, 3)))

        elim = repository.ajouter(
            Phase.creer(
                tournoi_id,
                ordre=2,
                type=TypePhase.ELIMINATION_DIRECTE,
                sources=(SourcePhase(ordre_source=1, rang_debut=1, rang_fin=16),),
                effectif=16,
            )
        )
        assert elim.id is not None

        relue = repository.par_id(elim.id)
        assert relue == elim
        assert relue is not None
        assert relue.bareme is None
        assert relue.validation is None
        assert relue.sources == (SourcePhase(ordre_source=1, rang_debut=1, rang_fin=16),)
        assert relue.effectif == 16

        # Le JSON ne porte ni scoring ni validation pour une phase non-qualification.
        with db.session_factory() as session:
            ligne = session.get(PhaseORM, elim.id)
            assert ligne is not None
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
        premier = _tournoi(db)
        second = _tournoi(db)
        repository = PhaseRepositorySQL(db.session_factory)
        repository.ajouter(Phase.qualification(premier, BaremeQualification.creer(20, 3)))
        repository.ajouter(Phase.creer(premier, ordre=2, type=TypePhase.ELIMINATION_DIRECTE))
        repository.ajouter(Phase.creer(premier, ordre=3, type=TypePhase.PLACEMENT))
        repository.ajouter(Phase.qualification(second, BaremeQualification.creer(10, 3)))

        phases = repository.par_tournoi(premier)
        assert [p.ordre for p in phases] == [1, 2, 3]
        assert [p.type for p in phases] == [
            TypePhase.QUALIFICATION,
            TypePhase.ELIMINATION_DIRECTE,
            TypePhase.PLACEMENT,
        ]
        assert repository.par_tournoi(second) == [
            repository.par_tournoi_et_type(second, TypePhase.QUALIFICATION)
        ]
    finally:
        db.engine.dispose()


def test_supprimer_retire_la_phase(tmp_path: Path) -> None:
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        repository = PhaseRepositorySQL(db.session_factory)
        phase = repository.ajouter(
            Phase.creer(tournoi_id, ordre=1, type=TypePhase.ELIMINATION_DIRECTE)
        )
        assert phase.id is not None

        repository.supprimer(phase.id)

        assert repository.par_id(phase.id) is None
        assert repository.par_tournoi(tournoi_id) == []
    finally:
        db.engine.dispose()


def test_le_statut_en_pause_fait_l_aller_retour(tmp_path: Path) -> None:
    """`en_pause` (E05US001) se persiste et se relit comme les autres statuts."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        repository = PhaseRepositorySQL(db.session_factory)
        phase = repository.ajouter(
            Phase.creer(tournoi_id, ordre=1, type=TypePhase.ELIMINATION_DIRECTE)
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
        tournoi_id = _tournoi(db)
        with db.session_factory() as session:
            session.add(
                PhaseORM(
                    tournoi_id=tournoi_id,
                    ordre=1,
                    type="elimination_directe",
                    config="{}",
                    statut="en_vacances",
                )
            )
            session.commit()
        with pytest.raises(InfrastructureError):
            PhaseRepositorySQL(db.session_factory).par_tournoi(tournoi_id)
    finally:
        db.engine.dispose()


def test_une_source_illisible_leve_infrastructure_error(tmp_path: Path) -> None:
    """Une `config.source` bien formée mais hors règle (plage vide) est une base altérée : le
    repository relit via `SourcePhase`, donc jamais un value object silencieusement invalide."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        with db.session_factory() as session:
            session.add(
                PhaseORM(
                    tournoi_id=tournoi_id,
                    ordre=2,
                    type="elimination_directe",
                    config='{"source": {"ordre_source": 1, "rang_debut": 8, "rang_fin": 4}}',
                    statut="a_venir",
                )
            )
            session.commit()
        with pytest.raises(InfrastructureError):
            PhaseRepositorySQL(db.session_factory).par_tournoi(tournoi_id)
    finally:
        db.engine.dispose()


# --- E05US003 / ADR-0046 : bascule config.policies + compatibilité ascendante ------------------


def test_le_scoring_est_persiste_sous_policies(tmp_path: Path) -> None:
    """Forme cible (ADR-0046) : le barème s'écrit sous `config.policies.scoring`, nommé « cumul »
    et paramétré (volées x flèches), **pas** à la racine. C'est la résorption de DETTE-003."""
    db = _base(tmp_path)
    try:
        tournoi_id = _tournoi(db)
        repository = PhaseRepositorySQL(db.session_factory)
        cree = repository.ajouter(Phase.qualification(tournoi_id, BaremeQualification.creer(20, 3)))
        assert cree.id is not None

        with db.session_factory() as session:
            ligne = session.get(PhaseORM, cree.id)
            assert ligne is not None
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
        tournoi_id = _tournoi(db)
        _phase_brute(db, tournoi_id, '{"scoring": {"volees": 15, "fleches": 6, "mode": "cumul"}}')

        relue = PhaseRepositorySQL(db.session_factory).par_tournoi_et_type(
            tournoi_id, TypePhase.QUALIFICATION
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
        tournoi_id = _tournoi_au_schema_historique(db)
        _phase_brute(
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
            ligne = session.query(PhaseORM).one()
            config = json.loads(ligne.config)
        assert "scoring" not in config  # déplacé
        assert config["policies"]["scoring"] == {"nom": "cumul", "volees": 20, "fleches": 3}
        assert config["validation"] == {"grain": "fin_de_serie"}  # resté à la racine
    finally:
        db.engine.dispose()


# --- Profondeur de classement (E06US006, ADR-0070) ----------------------------------------------


def _tableau_brut(db: Database, tournoi_id: TournoiId, config: str) -> None:
    """Écrit une ligne `phase` **de tableau** directement, config imposée.

    Jumeau de `_phase_brute`, qui force `type="qualification"` : une profondeur ne se règle que sur
    un tableau, et la relire sur une qualification échouerait pour une **autre** raison (barème
    manquant), donc sans rien prouver de ce qu'on veut vérifier.
    """
    with db.session_factory() as session:
        session.add(
            PhaseORM(
                tournoi_id=tournoi_id,
                ordre=1,
                type="elimination_directe",
                config=config,
                statut="a_venir",
            )
        )
        session.commit()


def test_la_profondeur_fait_l_aller_retour(tmp_path: Path) -> None:
    """`config.policies.depth` s'écrit et se relit à l'identique, sans migration."""
    db = _base(tmp_path)
    tournoi_id = _tournoi(db)
    repo = PhaseRepositorySQL(db.session_factory)

    integrale = repo.ajouter(
        Phase.creer(
            tournoi_id,
            ordre=1,
            type=TypePhase.ELIMINATION_DIRECTE,
            profondeur=ProfondeurClassement.integrale(),
        )
    )
    top = repo.ajouter(
        Phase.creer(
            tournoi_id,
            ordre=2,
            type=TypePhase.ELIMINATION_DIRECTE,
            profondeur=ProfondeurClassement.top(8),
        )
    )

    relues = {p.ordre: p.profondeur for p in repo.par_tournoi(tournoi_id)}
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
    tournoi_id = _tournoi(db)
    _tableau_brut(db, tournoi_id, json.dumps({"validation": {"grain": "fin_de_duel"}}))

    phase = PhaseRepositorySQL(db.session_factory).par_tournoi(tournoi_id)[0]

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
    tournoi_id = _tournoi(db)
    _tableau_brut(db, tournoi_id, json.dumps({"policies": {"depth": depth}}))

    with pytest.raises(InfrastructureError):
        PhaseRepositorySQL(db.session_factory).par_tournoi(tournoi_id)
