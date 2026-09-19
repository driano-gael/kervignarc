"""Tests d'intégration du repository SQL des tournois (E00US009, E01US001, E01US002).

Exerce l'adapter sur une **vraie base** créée par les migrations (`alembic upgrade head`) :
persistance des métadonnées (date, lieu, type) et du statut, relecture, absence (None), listing,
mise à jour (`enregistrer`) et suppression (`supprimer`). Le tarif n'est plus au tournoi (E02US004,
ADR-0017) — voir `test_depart_repository.py`.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from domain.tournoi import StatutTournoi, Tournoi, TypeTournoi
from infrastructure.db import Database, TournoiRepositorySQL
from infrastructure.db.models import (
    ArcherORM,
    ArretDeCirconstanceORM,
    BarrageORM,
    BarrageTirORM,
    BlasonORM,
    CategorieORM,
    DepartORM,
    DerouleEtapeORM,
    DuelORM,
    EntreeAuditORM,
    ForfaitORM,
    FranchissementArretORM,
    GabaritSalleORM,
    IdentiteVisuelleORM,
    InscriptionORM,
    PhaseORM,
    PlacementORM,
    PlacementParBlocORM,
    PlacementTableauORM,
    PosteORM,
    RemboursementORM,
    ScoreurORM,
    SerieORM,
    VoleeORM,
)
from tests.base_migree import preparer_base

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATE = datetime.date(2026, 3, 14)


def _migrer(url: str) -> None:
    preparer_base(url)


def test_ajouter_puis_relire(tmp_path: Path) -> None:
    """`ajouter` attribue un id ; `par_id` relit l'agrégat (métadonnées comprises)."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    try:
        repository = TournoiRepositorySQL(db.session_factory)
        cree = repository.ajouter(
            Tournoi.creer("Salle 18m", _DATE, "Quimper", TypeTournoi.OFFICIEL)
        )
        assert cree.id is not None
        assert cree.date == _DATE
        assert cree.lieu == "Quimper"
        assert cree.type_tournoi is TypeTournoi.OFFICIEL
        assert cree.statut is StatutTournoi.BROUILLON
        assert repository.par_id(cree.id) == cree
    finally:
        db.engine.dispose()


def test_par_id_inexistant_renvoie_none(tmp_path: Path) -> None:
    """`par_id` renvoie None pour un identifiant absent (pas d'exception)."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    try:
        repository = TournoiRepositorySQL(db.session_factory)
        assert repository.par_id(999) is None
    finally:
        db.engine.dispose()


def test_lister_renvoie_du_plus_recent_au_plus_ancien(tmp_path: Path) -> None:
    """`lister` renvoie tous les tournois, le dernier créé en premier."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    try:
        repository = TournoiRepositorySQL(db.session_factory)
        assert repository.lister() == []
        repository.ajouter(Tournoi.creer("Ancien", _DATE))
        repository.ajouter(Tournoi.creer("Récent", _DATE))
        assert [t.nom for t in repository.lister()] == ["Récent", "Ancien"]
    finally:
        db.engine.dispose()


def test_enregistrer_met_a_jour_metadonnees_et_statut(tmp_path: Path) -> None:
    """`enregistrer` persiste l'édition des métadonnées et la transition de statut."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    try:
        repository = TournoiRepositorySQL(db.session_factory)
        cree = repository.ajouter(Tournoi.creer("Ancien", _DATE))
        assert cree.id is not None
        modifie = cree.modifier("Nouveau", _DATE, "Quimper", TypeTournoi.OFFICIEL).demarrer()
        enregistre = repository.enregistrer(modifie)
        assert enregistre.nom == "Nouveau"
        assert enregistre.lieu == "Quimper"
        assert enregistre.type_tournoi is TypeTournoi.OFFICIEL
        assert enregistre.statut is StatutTournoi.EN_COURS
        assert repository.par_id(cree.id) == enregistre
    finally:
        db.engine.dispose()


def test_supprimer_retire_le_tournoi(tmp_path: Path) -> None:
    """`supprimer` retire la ligne ; `par_id` renvoie ensuite None."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    try:
        repository = TournoiRepositorySQL(db.session_factory)
        cree = repository.ajouter(Tournoi.creer("Trophée", _DATE))
        assert cree.id is not None
        repository.supprimer(cree.id)
        assert repository.par_id(cree.id) is None
        assert repository.lister() == []
    finally:
        db.engine.dispose()


# --- Cascade de suppression : toute la descendance, et rien d'autre (E01US026, ADR-0077) ---

_TABLES_DE_LA_DESCENDANCE = (
    "depart",
    "categorie",
    "blason",
    "gabarit_salle",
    "archer",
    "inscription",
    "placement",
    "phase",
    "placement_tableau",
    "placement_par_bloc",
    "duel",
    "serie",
    "volee",
    "forfait",
    "barrage",
    "barrage_tir",
    "remboursement",
    "scoreur",
    "poste",
    "entree_audit",
    "deroule_etape",
    "franchissement_arret",
    "arret_de_circonstance",
    "identite_tournoi",
)

# Rattachement au tournoi de chaque table, pour le comptage du test. Les tables absentes de cette
# carte n'ont pas de chemin direct : on les compte en entier (le test ne pose qu'un tournoi, sauf
# celui du témoin, qui compte ses propres lignes par les tables de 1er rang).
_RATTACHEMENT = {
    "tournoi_id = {tid}": (
        "depart",
        "categorie",
        "blason",
        "gabarit_salle",
        "archer",
        "scoreur",
        "poste",
        "entree_audit",
        "deroule_etape",
        "remboursement",
        "serie",
        "forfait",
        "identite_tournoi",
    ),
    "depart_id IN (SELECT id FROM depart WHERE tournoi_id = {tid})": (
        "phase",
        "barrage",
        "arret_de_circonstance",
        "placement",
    ),
    "archer_id IN (SELECT id FROM archer WHERE tournoi_id = {tid})": ("inscription", "barrage_tir"),
}


def _garnir(session: Session, tournoi_id: int) -> None:
    """Pose **une ligne dans chaque table** de la descendance du tournoi.

    ⚠️ Le point du test est l'**exhaustivité**, pas la vraisemblance des données : une table oubliée
    par la cascade se voit ici et nulle part ailleurs, `PRAGMA foreign_keys=ON` transformant l'oubli
    en `IntegrityError`. Une US qui ajoute une table à la descendance ajoute sa ligne ici.
    """
    instant = datetime.datetime(2026, 3, 14, 9, 0, tzinfo=datetime.UTC)
    blason = BlasonORM(tournoi_id=tournoi_id, nom="40 cm", taille=40.0, capacite=4, zones="[]")
    session.add(blason)
    session.flush()
    categorie = CategorieORM(
        tournoi_id=tournoi_id, libelle="S1H", ages="[]", hauteur_cm=130, blason_id=blason.id
    )
    depart = DepartORM(tournoi_id=tournoi_id, numero=1, horaire="09:00", tarif_centimes=800)
    session.add_all(
        [
            categorie,
            depart,
            GabaritSalleORM(tournoi_id=tournoi_id, nom="Salle", nb_cibles=10, config="{}"),
            ScoreurORM(tournoi_id=tournoi_id, nom="Jean", code=f"SC{tournoi_id}"),
            PosteORM(tournoi_id=tournoi_id, code=f"PO{tournoi_id}"),
            EntreeAuditORM(
                tournoi_id=tournoi_id,
                action="paiement",
                auteur="admin",
                horodatage=instant,
                objet="x",
            ),
            DerouleEtapeORM(tournoi_id=tournoi_id, ordre=1, type="qualification", config="{}"),
            RemboursementORM(
                tournoi_id=tournoi_id,
                archer_prenom="Guillaume",
                archer_nom="Tell",
                creneau="Départ n°1",
                montant_centimes=800,
                motif="depart_supprime",
                statut="a_rembourser",
                cree_le=instant,
            ),
            IdentiteVisuelleORM(tournoi_id=tournoi_id),
        ]
    )
    session.flush()
    archer = ArcherORM(
        tournoi_id=tournoi_id, nom="Tell", prenom="Guillaume", categorie_id=categorie.id
    )
    phase = PhaseORM(depart_id=depart.id, ordre=1, statut="a_venir")
    session.add_all([archer, phase])
    session.flush()
    inscription = InscriptionORM(archer_id=archer.id, depart_id=depart.id)
    serie = SerieORM(tournoi_id=tournoi_id, archer_id=archer.id, phase_id=phase.id)
    barrage = BarrageORM(
        depart_id=depart.id,
        phase_id=phase.id,
        portee="tournoi",
        participants_json=f"[{archer.id}]",
        cree_le=instant,
    )
    session.add_all([inscription, serie, barrage])
    session.flush()
    session.add_all(
        [
            PlacementORM(
                inscription_id=inscription.id, depart_id=depart.id, cible_index=1, position="A"
            ),
            PlacementTableauORM(
                phase_id=phase.id,
                tour=1,
                inscription_id=inscription.id,
                cible_index=1,
                position="A",
            ),
            PlacementParBlocORM(
                phase_id=phase.id, cible_index=1, position="A", groupe_numero=1, rang=1
            ),
            DuelORM(
                phase_id=phase.id,
                match_numero=1,
                haut_genre="inscription",
                haut_ref=inscription.id,
                bas_genre="bye",
                bas_ref=0,
                manches="[]",
            ),
            VoleeORM(serie_id=serie.id, numero=1, valeurs="[10, 9, 8]", validee_par="admin"),
            ForfaitORM(
                tournoi_id=tournoi_id,
                archer_id=archer.id,
                phase_id=phase.id,
                nature="abandon",
                declare_par="admin",
                declare_le=instant,
            ),
            BarrageTirORM(barrage_id=barrage.id, manche=1, archer_id=archer.id),
            FranchissementArretORM(phase_id=phase.id, apres_tour=1, etat="franchi"),
            ArretDeCirconstanceORM(
                depart_id=depart.id, phase_id=phase.id, apres_tour=1, portee="depart"
            ),
        ]
    )
    session.commit()


def _lignes(session: Session, table: str, tournoi_id: int) -> int:
    """Compte les lignes de `table` rattachées à ce tournoi, par le chemin de FK qui le relie."""
    for gabarit, tables in _RATTACHEMENT.items():
        if table in tables:
            critere = gabarit.format(tid=tournoi_id)
            break
    else:
        critere = "1 = 1"
    return session.scalar(text(f"SELECT COUNT(*) FROM {table} WHERE {critere}")) or 0


def test_supprimer_emporte_toute_la_descendance(tmp_path: Path) -> None:
    """Chaque table de la descendance est vidée — et l'`IntegrityError` d'avant ne revient pas."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    try:
        repository = TournoiRepositorySQL(db.session_factory)
        cible = repository.ajouter(Tournoi.creer("À supprimer", _DATE))
        assert cible.id is not None
        with db.session_factory() as session:
            _garnir(session, cible.id)
        with db.session_factory() as session:
            for table in _TABLES_DE_LA_DESCENDANCE:
                assert _lignes(session, table, cible.id) > 0, f"{table} : le test ne garnit rien"
        repository.supprimer(cible.id)
        assert repository.par_id(cible.id) is None
        with db.session_factory() as session:
            for table in _TABLES_DE_LA_DESCENDANCE:
                assert _lignes(session, table, cible.id) == 0, f"{table} : lignes orphelines"
    finally:
        db.engine.dispose()


def test_supprimer_un_tournoi_epargne_les_autres(tmp_path: Path) -> None:
    """Le tournoi **voisin** garde toute sa descendance : un `WHERE` oublié se verrait ici.

    Le risque est asymétrique — une table oubliée fait un 500 qu'on voit tout de suite, un `WHERE`
    trop large efface en silence un tournoi que personne ne regardait.
    """
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    try:
        repository = TournoiRepositorySQL(db.session_factory)
        cible = repository.ajouter(Tournoi.creer("À supprimer", _DATE))
        temoin = repository.ajouter(Tournoi.creer("À garder", _DATE))
        assert cible.id is not None and temoin.id is not None
        with db.session_factory() as session:
            _garnir(session, cible.id)
            _garnir(session, temoin.id)
        repository.supprimer(cible.id)
        with db.session_factory() as session:
            for table in ("depart", "archer", "categorie", "blason", "scoreur", "poste", "serie"):
                assert _lignes(session, table, temoin.id) > 0, f"{table} : le témoin a été amputé"
            assert _lignes(session, "phase", temoin.id) > 0
            assert _lignes(session, "inscription", temoin.id) > 0
    finally:
        db.engine.dispose()


def test_compter_descendance_chiffre_ce_qui_partira(tmp_path: Path) -> None:
    """Le décompte annoncé à l'admin est **celui de la base**, pas une estimation."""
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    try:
        repository = TournoiRepositorySQL(db.session_factory)
        cible = repository.ajouter(Tournoi.creer("Trophée", _DATE))
        assert cible.id is not None
        assert repository.compter_descendance(cible.id).est_vide()
        with db.session_factory() as session:
            _garnir(session, cible.id)
        descendance = repository.compter_descendance(cible.id)
        assert not descendance.est_vide()
        assert descendance.archers == 1
        assert descendance.inscriptions == 1
        assert descendance.fleches == 3
        assert descendance.series == 1
        assert descendance.duels == 1
        assert descendance.forfaits == 1
        assert descendance.barrages == 1
        assert descendance.remboursements == 1
        assert descendance.montant_encaisse_centimes == 800
    finally:
        db.engine.dispose()


def test_un_tournoi_sans_archers_est_vide_meme_avec_des_creneaux(tmp_path: Path) -> None:
    """CA (arbitrage 19/09/2026) : créneaux et référentiel sont de la **configuration**.

    Un tournoi qu'on vient de monter part sans confirmation — sinon le dialogue surgit sur un
    tournoi d'essai où il n'y a rien à perdre, et c'est ainsi qu'on apprend à cliquer sans lire.
    """
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    try:
        repository = TournoiRepositorySQL(db.session_factory)
        cible = repository.ajouter(Tournoi.creer("Trophée", _DATE))
        assert cible.id is not None
        with db.session_factory() as session:
            session.add(
                DepartORM(tournoi_id=cible.id, numero=1, horaire="09:00", tarif_centimes=800)
            )
            session.add(
                BlasonORM(tournoi_id=cible.id, nom="40 cm", taille=40.0, capacite=4, zones="[]")
            )
            session.commit()
        assert repository.compter_descendance(cible.id).est_vide()
    finally:
        db.engine.dispose()
