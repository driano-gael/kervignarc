"""Tests d'intégration des repositories SQL Archer et Score (E00US011, E02US001→E02US003).

Exerce les adapters sur une **vraie base** créée par les migrations (`alembic upgrade head`) :
persistance, relecture, mise à jour (placement, édition), suppression, jointure
score→archer→tournoi, rattachement au club (`archer.club_id`, `par_club`) et inscription complète
(`prenom`, `categorie_id`).
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from domain.archer import Archer
from domain.categorie import Categorie, CategorieId
from domain.club import Club
from domain.score import Score
from domain.tournoi import Tournoi, TournoiId
from infrastructure.db import (
    ArcherRepositorySQL,
    CategorieRepositorySQL,
    ClubRepositorySQL,
    Database,
    ScoreRepositorySQL,
    TournoiRepositorySQL,
)
from infrastructure.erreurs import InfrastructureError

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)


def _migrer(url: str) -> None:
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


def _base(tmp_path: Path) -> Database:
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    return Database(url)


def _tournoi_et_categorie(
    db: Database, nom: str = "Salle 18m", date: datetime.date = _DATE
) -> tuple[TournoiId, CategorieId]:
    """Persiste un tournoi et une catégorie **de ce tournoi** ; renvoie leurs identifiants.

    Depuis E02US002, `archer.categorie_id` est NOT NULL avec une FK : aucun archer ne peut plus
    être persisté sans une catégorie qui existe réellement en base.
    """
    tournoi = TournoiRepositorySQL(db.session_factory).ajouter(Tournoi.creer(nom, date))
    assert tournoi.id is not None
    categorie = CategorieRepositorySQL(db.session_factory).ajouter(
        Categorie.creer(tournoi.id, "Senior 1 H")
    )
    assert categorie.id is not None
    return tournoi.id, categorie.id


def test_archers_et_scores_bout_en_bout(tmp_path: Path) -> None:
    """Persistance/relecture des archers et scores, placement, et agrégation par tournoi."""
    db = _base(tmp_path)
    try:
        tournoi_id, categorie_id = _tournoi_et_categorie(db)
        archers = ArcherRepositorySQL(db.session_factory)
        scores = ScoreRepositorySQL(db.session_factory)

        alice = archers.ajouter(Archer.creer("Martin", "Alice", tournoi_id, categorie_id))
        bob = archers.ajouter(Archer.creer("Durand", "Bob", tournoi_id, categorie_id))
        assert alice.id is not None and bob.id is not None

        # Relecture à l'identique et liste par tournoi.
        assert archers.par_id(alice.id) == alice
        assert {a.id for a in archers.par_tournoi(tournoi_id)} == {alice.id, bob.id}

        # Placement (mise à jour) persisté.
        place = archers.enregistrer(alice.placer(5))
        assert place.cible == 5
        assert archers.par_id(alice.id) == place

        # Scores agrégés par tournoi (jointure archer→tournoi).
        scores.ajouter(Score.creer(alice.id, 10))
        scores.ajouter(Score.creer(alice.id, 9))
        scores.ajouter(Score.creer(bob.id, 8))
        assert sorted(s.points for s in scores.par_tournoi(tournoi_id)) == [8, 9, 10]
    finally:
        db.engine.dispose()


def test_par_id_archer_inexistant_renvoie_none(tmp_path: Path) -> None:
    """`par_id` renvoie None pour un identifiant d'archer absent (pas d'exception)."""
    db = _base(tmp_path)
    try:
        assert ArcherRepositorySQL(db.session_factory).par_id(999) is None
    finally:
        db.engine.dispose()


def test_archer_porte_son_identite_complete_en_base(tmp_path: Path) -> None:
    """`prenom` et `categorie_id` font l'aller-retour agrégat ↔ ORM (migration 0015)."""
    db = _base(tmp_path)
    try:
        tournoi_id, categorie_id = _tournoi_et_categorie(db)
        archers = ArcherRepositorySQL(db.session_factory)

        cree = archers.ajouter(Archer.creer("Lefèvre", "Rémi", tournoi_id, categorie_id))
        assert cree.id is not None
        assert (cree.nom, cree.prenom, cree.categorie_id) == ("Lefèvre", "Rémi", categorie_id)
        assert archers.par_id(cree.id) == cree

        # L'identité survit à une mise à jour portant sur un autre champ (le placement).
        place = archers.enregistrer(cree.placer(3))
        assert (place.prenom, place.categorie_id) == ("Rémi", categorie_id)
        assert archers.par_id(cree.id) == place
    finally:
        db.engine.dispose()


def test_archer_porte_son_club_en_base(tmp_path: Path) -> None:
    """`club_id` fait l'aller-retour agrégat ↔ ORM (migration 0014), placement compris."""
    db = _base(tmp_path)
    try:
        tournoi_id, categorie_id = _tournoi_et_categorie(db)
        club = ClubRepositorySQL(db.session_factory).ajouter(Club.creer("Arc Club Rennes"))
        archers = ArcherRepositorySQL(db.session_factory)

        cree = archers.ajouter(Archer.creer("Robin", "Jean", tournoi_id, categorie_id, club.id))
        assert cree.id is not None
        assert cree.club_id == club.id
        assert archers.par_id(cree.id) == cree

        # Le rattachement survit à une mise à jour portant sur un autre champ.
        place = archers.enregistrer(cree.placer(3))
        assert place.club_id == club.id
        assert archers.par_id(cree.id) == place
    finally:
        db.engine.dispose()


def test_archer_sans_club_est_persistable(tmp_path: Path) -> None:
    """Un archer au club **inconnu** s'inscrit quand même (`club_id` nullable, ADR-0014)."""
    db = _base(tmp_path)
    try:
        tournoi_id, categorie_id = _tournoi_et_categorie(db)
        archers = ArcherRepositorySQL(db.session_factory)

        cree = archers.ajouter(Archer.creer("Robin", "Jean", tournoi_id, categorie_id))
        assert cree.id is not None
        assert cree.club_id is None
        assert archers.par_id(cree.id) == cree
    finally:
        db.engine.dispose()


def test_par_club_renvoie_les_archers_tous_tournois_confondus(tmp_path: Path) -> None:
    """`par_club` ignore les frontières de tournoi : le référentiel des clubs est global."""
    db = _base(tmp_path)
    try:
        premier, categorie_premier = _tournoi_et_categorie(db, "2025", datetime.date(2025, 3, 14))
        second, categorie_second = _tournoi_et_categorie(db, "2026")
        clubs = ClubRepositorySQL(db.session_factory)
        rennes = clubs.ajouter(Club.creer("Arc Club Rennes"))
        fougeres = clubs.ajouter(Club.creer("Élan de Fougères"))
        assert rennes.id is not None and fougeres.id is not None
        archers = ArcherRepositorySQL(db.session_factory)
        archers.ajouter(Archer.creer("Robin", "Jean", premier, categorie_premier, rennes.id))
        archers.ajouter(Archer.creer("Marion", "Lise", second, categorie_second, rennes.id))
        archers.ajouter(Archer.creer("Alix", "Paul", second, categorie_second, fougeres.id))
        archers.ajouter(Archer.creer("Sans club", "Zoé", second, categorie_second))

        assert [a.nom for a in archers.par_club(rennes.id)] == ["Robin", "Marion"]
        assert [a.nom for a in archers.par_club(fougeres.id)] == ["Alix"]
    finally:
        db.engine.dispose()


def test_par_club_sans_archer_renvoie_vide(tmp_path: Path) -> None:
    """Un club que personne ne référence renvoie une liste vide — donc supprimable."""
    db = _base(tmp_path)
    try:
        club = ClubRepositorySQL(db.session_factory).ajouter(Club.creer("Arc Club Rennes"))
        assert club.id is not None
        assert ArcherRepositorySQL(db.session_factory).par_club(club.id) == []
    finally:
        db.engine.dispose()


def test_supprimer_un_club_reference_est_bloque_par_la_fk(tmp_path: Path) -> None:
    """Filet **sous** le service : la FK refuse de laisser une référence pendante.

    Le service refuse déjà en amont (409, `ClubReference`) ; on vérifie ici que la base ne s'en
    remet pas à lui. `PRAGMA foreign_keys=ON` est posé à chaque connexion (`engine.py`), sans quoi
    SQLite ignorerait la contrainte.
    """
    db = _base(tmp_path)
    try:
        tournoi_id, categorie_id = _tournoi_et_categorie(db)
        clubs = ClubRepositorySQL(db.session_factory)
        club = clubs.ajouter(Club.creer("Arc Club Rennes"))
        assert club.id is not None
        ArcherRepositorySQL(db.session_factory).ajouter(
            Archer.creer("Robin", "Jean", tournoi_id, categorie_id, club.id)
        )

        with pytest.raises(InfrastructureError):
            clubs.supprimer(club.id)
    finally:
        db.engine.dispose()


def test_enregistrer_persiste_l_edition_complete(tmp_path: Path) -> None:
    """`enregistrer` recopie **les quatre champs éditables** d'un coup (E02US003).

    Le placement (E00US011) ne faisait bouger que `cible` : une recopie partielle serait passée
    inaperçue jusqu'ici. C'est l'édition qui l'exerce vraiment.
    """
    db = _base(tmp_path)
    try:
        tournoi_id, categorie_id = _tournoi_et_categorie(db)
        autre_categorie = CategorieRepositorySQL(db.session_factory).ajouter(
            Categorie.creer(tournoi_id, "Senior 2 H")
        )
        club = ClubRepositorySQL(db.session_factory).ajouter(Club.creer("Arc Club Rennes"))
        archers = ArcherRepositorySQL(db.session_factory)
        cree = archers.ajouter(Archer.creer("Robain", "Jean", tournoi_id, categorie_id))
        assert cree.id is not None and autre_categorie.id is not None

        edite = archers.enregistrer(cree.modifier("Robin", "Jeanne", autre_categorie.id, club.id))
        assert (edite.nom, edite.prenom) == ("Robin", "Jeanne")
        assert (edite.categorie_id, edite.club_id) == (autre_categorie.id, club.id)
        assert archers.par_id(cree.id) == edite
    finally:
        db.engine.dispose()


def test_enregistrer_detache_le_club_en_base(tmp_path: Path) -> None:
    """Repasser à « club inconnu » écrit bien `NULL` (ADR-0014) — pas un no-op silencieux."""
    db = _base(tmp_path)
    try:
        tournoi_id, categorie_id = _tournoi_et_categorie(db)
        club = ClubRepositorySQL(db.session_factory).ajouter(Club.creer("Arc Club Rennes"))
        archers = ArcherRepositorySQL(db.session_factory)
        cree = archers.ajouter(Archer.creer("Robin", "Jean", tournoi_id, categorie_id, club.id))
        assert cree.id is not None

        archers.enregistrer(cree.modifier("Robin", "Jean", categorie_id, None))
        relu = archers.par_id(cree.id)
        assert relu is not None and relu.club_id is None
    finally:
        db.engine.dispose()


def test_supprimer_archer_retire_la_ligne(tmp_path: Path) -> None:
    """`supprimer` retire l'archer de la base (E02US003)."""
    db = _base(tmp_path)
    try:
        tournoi_id, categorie_id = _tournoi_et_categorie(db)
        archers = ArcherRepositorySQL(db.session_factory)
        cree = archers.ajouter(Archer.creer("Robin", "Jean", tournoi_id, categorie_id))
        assert cree.id is not None

        archers.supprimer(cree.id)
        assert archers.par_id(cree.id) is None
        assert archers.par_tournoi(tournoi_id) == []
    finally:
        db.engine.dispose()


def test_supprimer_un_archer_absent_est_une_incoherence_technique(tmp_path: Path) -> None:
    """L'existence est garantie par le service : une ligne absente n'est pas un 404 métier."""
    db = _base(tmp_path)
    try:
        with pytest.raises(InfrastructureError):
            ArcherRepositorySQL(db.session_factory).supprimer(999)
    finally:
        db.engine.dispose()


def test_supprimer_un_archer_emporte_ses_scores(tmp_path: Path) -> None:
    """La purge est **dans la transaction** de l'adapter (E02US003), pas laissée à la FK.

    `score.archer_id` n'a pas d'`ON DELETE` (DETTE-001) : sans le `DELETE` explicite des scores,
    ce `supprimer` échouerait en `InfrastructureError` → 500. C'est la cascade **applicative
    maîtrisée** qui manque au reste de la descendance de `tournoi`.
    """
    db = _base(tmp_path)
    try:
        tournoi_id, categorie_id = _tournoi_et_categorie(db)
        archers = ArcherRepositorySQL(db.session_factory)
        scores = ScoreRepositorySQL(db.session_factory)
        cree = archers.ajouter(Archer.creer("Robin", "Jean", tournoi_id, categorie_id))
        assert cree.id is not None
        scores.ajouter(Score.creer(cree.id, 9))
        scores.ajouter(Score.creer(cree.id, 10))

        archers.supprimer(cree.id)
        assert archers.par_id(cree.id) is None
        assert scores.par_archer(cree.id) == []
        assert scores.par_tournoi(tournoi_id) == []
    finally:
        db.engine.dispose()


def test_supprimer_un_archer_ne_touche_pas_aux_scores_des_autres(tmp_path: Path) -> None:
    """La purge est cloisonnée par `archer_id` — un `DELETE` trop large viderait le tournoi."""
    db = _base(tmp_path)
    try:
        tournoi_id, categorie_id = _tournoi_et_categorie(db)
        archers = ArcherRepositorySQL(db.session_factory)
        scores = ScoreRepositorySQL(db.session_factory)
        partant = archers.ajouter(Archer.creer("Durand", "Bob", tournoi_id, categorie_id))
        reste = archers.ajouter(Archer.creer("Martin", "Alice", tournoi_id, categorie_id))
        assert partant.id is not None and reste.id is not None
        scores.ajouter(Score.creer(partant.id, 9))
        scores.ajouter(Score.creer(reste.id, 8))

        archers.supprimer(partant.id)
        assert [s.points for s in scores.par_archer(reste.id)] == [8]
        assert archers.par_id(reste.id) is not None
    finally:
        db.engine.dispose()


def test_par_archer_ne_renvoie_que_les_scores_de_cet_archer(tmp_path: Path) -> None:
    """`par_archer` cloisonne par archer (E02US003) — base du « a-t-il déjà tiré ? »."""
    db = _base(tmp_path)
    try:
        tournoi_id, categorie_id = _tournoi_et_categorie(db)
        archers = ArcherRepositorySQL(db.session_factory)
        scores = ScoreRepositorySQL(db.session_factory)
        alice = archers.ajouter(Archer.creer("Martin", "Alice", tournoi_id, categorie_id))
        bob = archers.ajouter(Archer.creer("Durand", "Bob", tournoi_id, categorie_id))
        assert alice.id is not None and bob.id is not None
        scores.ajouter(Score.creer(alice.id, 10))
        scores.ajouter(Score.creer(alice.id, 9))
        scores.ajouter(Score.creer(bob.id, 8))

        assert sorted(s.points for s in scores.par_archer(alice.id)) == [9, 10]
        assert [s.points for s in scores.par_archer(bob.id)] == [8]
    finally:
        db.engine.dispose()


def test_par_archer_sans_score_renvoie_vide(tmp_path: Path) -> None:
    """Un archer qui n'a pas tiré renvoie une liste vide — donc supprimable."""
    db = _base(tmp_path)
    try:
        tournoi_id, categorie_id = _tournoi_et_categorie(db)
        cree = ArcherRepositorySQL(db.session_factory).ajouter(
            Archer.creer("Robin", "Jean", tournoi_id, categorie_id)
        )
        assert cree.id is not None
        assert ScoreRepositorySQL(db.session_factory).par_archer(cree.id) == []
    finally:
        db.engine.dispose()


def test_une_categorie_inexistante_est_bloquee_par_la_fk(tmp_path: Path) -> None:
    """Filet **sous** le service pour `categorie_id` (migration 0015), pendant du test ci-dessus.

    Le service refuse déjà en amont (409, `CategorieHorsTournoi`) ; la base ne s'en remet pas à lui.
    """
    db = _base(tmp_path)
    try:
        tournoi_id, _ = _tournoi_et_categorie(db)
        archers = ArcherRepositorySQL(db.session_factory)

        with pytest.raises(InfrastructureError):
            archers.ajouter(Archer.creer("Robin", "Jean", tournoi_id, 404))
    finally:
        db.engine.dispose()
