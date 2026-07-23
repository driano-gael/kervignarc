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
from domain.blason import ZoneScore
from domain.categorie import Categorie, CategorieId
from domain.club import Club
from domain.depart import Depart
from domain.inscription import Inscription
from domain.placement import Affectation
from domain.score import Score
from domain.serie import Serie, Volee
from domain.tournoi import Tournoi, TournoiId
from infrastructure.db import (
    ArcherRepositorySQL,
    AuditRepositorySQL,
    CategorieRepositorySQL,
    ClubRepositorySQL,
    Database,
    DepartRepositorySQL,
    InscriptionRepositorySQL,
    PlacementRepositorySQL,
    ScoreRepositorySQL,
    SerieRepositorySQL,
    TournoiRepositorySQL,
)
from infrastructure.erreurs import InfrastructureError
from infrastructure.horloge import HorlogeSysteme

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

    **Ce test ne prouve pas l'atomicité**, que `ports.py` et l'adapter affirment (« une seule
    transaction ; deux transactions laisseraient un archer dépouillé de ses flèches »). Elle tient
    ici **par construction** — un seul `commit` dans un seul `with session` —, mais ce test
    passerait à l'identique avec deux `commit()`. L'exercer demanderait d'injecter une
    `session_factory` qui fasse échouer le second `DELETE` : un harnais dont le coût dépasse le
    risque sur un SQLite mono-writer. Arbitrage assumé, signalé plutôt que tu.
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


def _serie_tiree(tournoi_id: TournoiId, archer_id: int) -> Serie:
    """Une série d'une volée validée (l'archer « a tiré ») — comme `faire_tirer` côté service."""
    volee = Volee(
        numero=1, valeurs=(ZoneScore.NEUF, ZoneScore.NEUF, ZoneScore.NEUF), validee_par="S"
    )
    return Serie(tournoi_id=tournoi_id, archer_id=archer_id, volees=(volee,))


def test_fusionner_reassigne_inscriptions_et_scores_puis_supprime_le_perdant(
    tmp_path: Path,
) -> None:
    """La fusion **réattribue** au gagnant la descendance du perdant, qui disparaît (E02US005).

    Miroir de `supprimer` : là où la suppression purge, la fusion réassigne — dans une transaction.
    Ici, aucune collision : le perdant a une inscription et un score que le gagnant n'a pas.
    """
    db = _base(tmp_path)
    try:
        tournoi_id, categorie_id = _tournoi_et_categorie(db)
        archers = ArcherRepositorySQL(db.session_factory)
        scores = ScoreRepositorySQL(db.session_factory)
        departs = DepartRepositorySQL(db.session_factory)
        inscriptions = InscriptionRepositorySQL(
            db.session_factory, AuditRepositorySQL(db.session_factory)
        )

        gagnant = archers.ajouter(Archer.creer("Dupont", "Jean", tournoi_id, categorie_id))
        perdant = archers.ajouter(Archer.creer("Dupont", "Jean", tournoi_id, categorie_id))
        assert gagnant.id is not None and perdant.id is not None
        depart = departs.ajouter(Depart.creer(tournoi_id, 1, 1500))
        assert depart.id is not None
        inscriptions.ajouter(Inscription.creer(perdant.id, depart.id))
        scores.ajouter(Score.creer(perdant.id, 9))

        archers.fusionner(gagnant.id, perdant.id)

        assert archers.par_id(perdant.id) is None
        assert archers.par_id(gagnant.id) is not None
        assert [i.depart_id for i in inscriptions.par_archer(gagnant.id)] == [depart.id]
        assert inscriptions.par_archer(perdant.id) == []
        assert [s.points for s in scores.par_archer(gagnant.id)] == [9]
    finally:
        db.engine.dispose()


def test_fusionner_collision_inscription_garde_une_ligne_et_reporte_le_paiement(
    tmp_path: Path,
) -> None:
    """Sur un départ où **les deux** sont inscrits (UNIQUE(archer, départ)), une seule ligne reste.

    Le paiement est **reporté** : si l'une des deux inscriptions était payée, celle qui reste l'est
    (OU logique). On ne crée pas de doublon d'inscription (violerait l'unicité) et on ne perd pas
    « a payé ».
    """
    db = _base(tmp_path)
    try:
        tournoi_id, categorie_id = _tournoi_et_categorie(db)
        archers = ArcherRepositorySQL(db.session_factory)
        departs = DepartRepositorySQL(db.session_factory)
        inscriptions = InscriptionRepositorySQL(
            db.session_factory, AuditRepositorySQL(db.session_factory)
        )

        gagnant = archers.ajouter(Archer.creer("Dupont", "Jean", tournoi_id, categorie_id))
        perdant = archers.ajouter(Archer.creer("Dupont", "Jean", tournoi_id, categorie_id))
        assert gagnant.id is not None and perdant.id is not None
        depart = departs.ajouter(Depart.creer(tournoi_id, 1, 1500))
        assert depart.id is not None
        # Le gagnant est inscrit **non payé** ; le perdant **payé** sur le même créneau.
        inscriptions.ajouter(Inscription.creer(gagnant.id, depart.id))
        inscrit_perdant = inscriptions.ajouter(Inscription.creer(perdant.id, depart.id))
        inscriptions.enregistrer(inscrit_perdant.marquer_paye(True))

        archers.fusionner(gagnant.id, perdant.id)

        restantes = inscriptions.par_archer(gagnant.id)
        assert [(i.depart_id, i.paye) for i in restantes] == [(depart.id, True)]
        assert inscriptions.par_archer(perdant.id) == []
    finally:
        db.engine.dispose()


def test_fusionner_collision_ne_deprecie_pas_un_paiement_du_gagnant(tmp_path: Path) -> None:
    """Le report de paiement est un **OU** : un gagnant déjà payé le reste (perdant non payé).

    Sans ce test, un report qui recopierait bêtement le `paye` du perdant (au lieu d'un OU)
    dépaierait le gagnant — une régression silencieuse sur l'argent.
    """
    db = _base(tmp_path)
    try:
        tournoi_id, categorie_id = _tournoi_et_categorie(db)
        archers = ArcherRepositorySQL(db.session_factory)
        departs = DepartRepositorySQL(db.session_factory)
        inscriptions = InscriptionRepositorySQL(
            db.session_factory, AuditRepositorySQL(db.session_factory)
        )

        gagnant = archers.ajouter(Archer.creer("Dupont", "Jean", tournoi_id, categorie_id))
        perdant = archers.ajouter(Archer.creer("Dupont", "Jean", tournoi_id, categorie_id))
        assert gagnant.id is not None and perdant.id is not None
        depart = departs.ajouter(Depart.creer(tournoi_id, 1, 1500))
        assert depart.id is not None
        inscrit_gagnant = inscriptions.ajouter(Inscription.creer(gagnant.id, depart.id))
        inscriptions.enregistrer(inscrit_gagnant.marquer_paye(True))
        inscriptions.ajouter(Inscription.creer(perdant.id, depart.id))

        archers.fusionner(gagnant.id, perdant.id)

        assert [(i.depart_id, i.paye) for i in inscriptions.par_archer(gagnant.id)] == [
            (depart.id, True)
        ]
    finally:
        db.engine.dispose()


def test_fusionner_collision_les_deux_non_payes_reste_non_paye(tmp_path: Path) -> None:
    """Collision où **aucune** des deux inscriptions n'est payée : la ligne gardée reste non payée.

    Complète la table de vérité du report (OU) : perdant-payé et gagnant-payé sont couverts
    ailleurs ; ici les deux `False` → résultat `False` (le OU ne fabrique pas un paiement).
    """
    db = _base(tmp_path)
    try:
        tournoi_id, categorie_id = _tournoi_et_categorie(db)
        archers = ArcherRepositorySQL(db.session_factory)
        departs = DepartRepositorySQL(db.session_factory)
        inscriptions = InscriptionRepositorySQL(
            db.session_factory, AuditRepositorySQL(db.session_factory)
        )

        gagnant = archers.ajouter(Archer.creer("Dupont", "Jean", tournoi_id, categorie_id))
        perdant = archers.ajouter(Archer.creer("Dupont", "Jean", tournoi_id, categorie_id))
        assert gagnant.id is not None and perdant.id is not None
        depart = departs.ajouter(Depart.creer(tournoi_id, 1, 1500))
        assert depart.id is not None
        inscriptions.ajouter(Inscription.creer(gagnant.id, depart.id))
        inscriptions.ajouter(Inscription.creer(perdant.id, depart.id))

        archers.fusionner(gagnant.id, perdant.id)

        assert [(i.depart_id, i.paye) for i in inscriptions.par_archer(gagnant.id)] == [
            (depart.id, False)
        ]
    finally:
        db.engine.dispose()


def test_fusionner_collision_cascade_le_placement_de_l_inscription_supprimee(
    tmp_path: Path,
) -> None:
    """Sur collision, l'inscription du perdant supprimée, son **placement cascade** (E02US005).

    La suppression Core de l'inscription en collision déclenche la cascade base
    `placement.inscription_id` (`ON DELETE CASCADE`). Ce test **verrouille** ce comportement contre
    une régression (ex. passage à un `session.delete` ORM) : sans lui, seul le schéma le garantit,
    pas la transaction de fusion. Le placement de l'inscription **gardée** (le gagnant) demeure.
    """
    db = _base(tmp_path)
    try:
        tournoi_id, categorie_id = _tournoi_et_categorie(db)
        archers = ArcherRepositorySQL(db.session_factory)
        departs = DepartRepositorySQL(db.session_factory)
        inscriptions = InscriptionRepositorySQL(
            db.session_factory, AuditRepositorySQL(db.session_factory)
        )
        placements = PlacementRepositorySQL(
            db.session_factory, AuditRepositorySQL(db.session_factory)
        )

        gagnant = archers.ajouter(Archer.creer("Dupont", "Jean", tournoi_id, categorie_id))
        perdant = archers.ajouter(Archer.creer("Dupont", "Jean", tournoi_id, categorie_id))
        assert gagnant.id is not None and perdant.id is not None
        depart = departs.ajouter(Depart.creer(tournoi_id, 1, 1500))
        assert depart.id is not None
        insc_gagnant = inscriptions.ajouter(Inscription.creer(gagnant.id, depart.id))
        insc_perdant = inscriptions.ajouter(Inscription.creer(perdant.id, depart.id))
        assert insc_gagnant.id is not None and insc_perdant.id is not None
        placements.poser_plusieurs(
            depart.id,
            [
                Affectation(inscription_id=insc_gagnant.id, cible_index=1, position="A"),
                Affectation(inscription_id=insc_perdant.id, cible_index=1, position="B"),
            ],
        )

        archers.fusionner(gagnant.id, perdant.id)

        # Le placement du perdant (via l'inscription supprimée) a cascadé ; celui du gagnant reste.
        assert [a.inscription_id for a in placements.par_depart(depart.id)] == [insc_gagnant.id]
    finally:
        db.engine.dispose()


def test_fusionner_reassigne_la_serie_du_perdant(tmp_path: Path) -> None:
    """La série de saisie du perdant (une seule des deux a tiré) passe au gagnant (E02US005).

    Le service refuse la fusion si les **deux** ont une série ; ici seul le perdant en a une, donc
    pas de collision sur `UNIQUE(tournoi_id, archer_id)` : la série est réassignée, ses volées avec.
    """
    db = _base(tmp_path)
    try:
        tournoi_id, categorie_id = _tournoi_et_categorie(db)
        archers = ArcherRepositorySQL(db.session_factory)
        series = SerieRepositorySQL(
            db.session_factory, AuditRepositorySQL(db.session_factory), HorlogeSysteme()
        )

        gagnant = archers.ajouter(Archer.creer("Dupont", "Jean", tournoi_id, categorie_id))
        perdant = archers.ajouter(Archer.creer("Dupont", "Jean", tournoi_id, categorie_id))
        assert gagnant.id is not None and perdant.id is not None
        series.enregistrer(_serie_tiree(tournoi_id, perdant.id))

        archers.fusionner(gagnant.id, perdant.id)

        assert series.par_archer(tournoi_id, perdant.id) is None
        serie_gagnant = series.par_archer(tournoi_id, gagnant.id)
        assert serie_gagnant is not None and serie_gagnant.nb_fleches_validees == 3
    finally:
        db.engine.dispose()


def test_fusionner_un_archer_absent_est_une_incoherence_technique(tmp_path: Path) -> None:
    """L'existence est garantie par le service : une fiche absente est un `InfrastructureError`."""
    db = _base(tmp_path)
    try:
        tournoi_id, categorie_id = _tournoi_et_categorie(db)
        archers = ArcherRepositorySQL(db.session_factory)
        gagnant = archers.ajouter(Archer.creer("Dupont", "Jean", tournoi_id, categorie_id))
        assert gagnant.id is not None
        with pytest.raises(InfrastructureError):
            archers.fusionner(gagnant.id, 999)
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
