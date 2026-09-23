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
from infrastructure.db.base import Base
from infrastructure.db.models import (
    ArcherORM,
    ArretDeCirconstanceORM,
    BarrageORM,
    BarrageTirORM,
    BlasonORM,
    CategorieORM,
    ClubORM,
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
    ScoreORM,
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

# Les tables **hors** descendance : rien ne les relie au tournoi, elles lui survivent toujours.
# `alembic_version` est de la plomberie de migration ; `club` et `format_tournoi` sont le
# patrimoine du club, réutilisé d'une édition à l'autre (ADR-0060, `domain/club.py`).
_HORS_DESCENDANCE = frozenset({"tournoi", "club", "format_tournoi", "alembic_version"})

# Le rattachement de chaque table au tournoi, pour le comptage. Dérivé à la main **et** confronté à
# `Base.metadata` par `test_aucune_table_neuve_n_echappe_a_l_inventaire` : c'est ce test, et non
# cette table, qui empêche une US d'ajouter une table sans rejoindre la purge.
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
    "archer_id IN (SELECT id FROM archer WHERE tournoi_id = {tid})": (
        "inscription",
        "barrage_tir",
        "score",
    ),
    "serie_id IN (SELECT id FROM serie WHERE tournoi_id = {tid})": ("volee",),
    (
        "phase_id IN (SELECT id FROM phase WHERE depart_id "
        "IN (SELECT id FROM depart WHERE tournoi_id = {tid}))"
    ): (
        "duel",
        "placement_tableau",
        "placement_par_bloc",
        "franchissement_arret",
    ),
}

_TABLES_DE_LA_DESCENDANCE = tuple(
    sorted(table for tables in _RATTACHEMENT.values() for table in tables)
)


def _garnir(session: Session, tournoi_id: int) -> None:
    """Pose des lignes dans **chaque** table de la descendance du tournoi.

    ⚠️ **Les cardinalités sont volontairement toutes différentes** (2 archers, 3 inscriptions,
    4 duels, 5 actes d'audit…) : avec une ligne partout, sept compteurs de `DescendanceTournoi`
    valaient `1`, et intervertir deux critères du décompte laissait le test vert (relevé en revue,
    axe C1). Une US qui ajoute une table à la descendance ajoute sa ligne ici — et si elle l'oublie,
    `test_aucune_table_neuve_n_echappe_a_l_inventaire` le dit.
    """
    instant = datetime.datetime(2026, 3, 14, 9, 0, tzinfo=datetime.UTC)
    marque = f"t{tournoi_id}"
    blason = BlasonORM(tournoi_id=tournoi_id, nom="40 cm", taille=40.0, capacite=4, zones="[]")
    session.add(blason)
    session.flush()
    categorie = CategorieORM(
        tournoi_id=tournoi_id, libelle="S1H", ages="[]", hauteur_cm=130, blason_id=blason.id
    )
    session.add(categorie)
    session.add(GabaritSalleORM(tournoi_id=tournoi_id, nom="Salle", nb_cibles=10, config="{}"))
    session.add(DerouleEtapeORM(tournoi_id=tournoi_id, ordre=1, type="qualification", config="{}"))
    session.add(IdentiteVisuelleORM(tournoi_id=tournoi_id))
    # 2 créneaux : sans eux, « 3 inscriptions » serait impossible (UNIQUE(archer_id, depart_id)).
    departs = [
        DepartORM(tournoi_id=tournoi_id, numero=n, horaire=f"0{8 + n}:00", tarif_centimes=800)
        for n in (1, 2)
    ]
    session.add_all(departs)
    # Cardinalités distinctes, une par nature comptée.
    session.add_all(
        ScoreurORM(tournoi_id=tournoi_id, nom=f"Jean {n}", code=f"SC{marque}{n}") for n in range(2)
    )
    session.add_all(
        PosteORM(tournoi_id=tournoi_id, code=f"PO{marque}{n}", cible_index=n) for n in range(3)
    )
    session.add_all(
        EntreeAuditORM(
            tournoi_id=tournoi_id, action="paiement", auteur="admin", horodatage=instant, objet="x"
        )
        for _ in range(5)
    )
    session.add(
        RemboursementORM(
            tournoi_id=tournoi_id,
            archer_prenom="Guillaume",
            archer_nom="Tell",
            creneau="Départ n°1 — 09:00",
            montant_centimes=800,
            motif="depart_supprime",
            statut="a_rembourser",
            cree_le=instant,
        )
    )
    session.flush()
    archers = [
        ArcherORM(tournoi_id=tournoi_id, nom="Tell", prenom=p, categorie_id=categorie.id)
        for p in ("Guillaume", "Walter")
    ]
    etape = DerouleEtapeORM(tournoi_id=tournoi_id, ordre=1, type="qualification", config="{}")
    session.add(etape)
    session.flush()  # l'avancement désigne son étape par identité (ADR-0078)
    phase = PhaseORM(depart_id=departs[0].id, etape_id=etape.id, statut="a_venir")
    session.add_all([*archers, phase])
    session.flush()
    # 3 inscriptions : les deux archers sur le 1er créneau, le premier aussi sur le second.
    inscriptions = [
        InscriptionORM(archer_id=archers[0].id, depart_id=departs[0].id, paye=True),
        InscriptionORM(archer_id=archers[1].id, depart_id=departs[0].id),
        InscriptionORM(archer_id=archers[0].id, depart_id=departs[1].id),
    ]
    series = [SerieORM(tournoi_id=tournoi_id, archer_id=a.id, phase_id=phase.id) for a in archers]
    barrage = BarrageORM(
        depart_id=departs[0].id,
        phase_id=phase.id,
        portee="tournoi",
        participants_json=f"[{archers[0].id}]",
        cree_le=instant,
    )
    session.add_all([*inscriptions, *series, barrage])
    session.flush()
    session.add_all(
        [
            PlacementORM(
                inscription_id=inscriptions[0].id,
                depart_id=departs[0].id,
                cible_index=1,
                position="A",
            ),
            PlacementTableauORM(
                phase_id=phase.id,
                tour=1,
                inscription_id=inscriptions[0].id,
                cible_index=1,
                position="A",
            ),
            PlacementParBlocORM(
                phase_id=phase.id, cible_index=1, position="A", groupe_numero=1, rang=1
            ),
            BarrageTirORM(barrage_id=barrage.id, manche=1, archer_id=archers[0].id),
            FranchissementArretORM(phase_id=phase.id, apres_tour=1, etat="franchi"),
            ArretDeCirconstanceORM(
                depart_id=departs[0].id, phase_id=phase.id, apres_tour=1, portee="depart"
            ),
            # `score` est l'agrégat du walking skeleton : plus aucun flux ne l'alimente (DETTE-011),
            # mais sa FK vers `archer` est *enforced* — il doit donc rester dans la purge, et une
            # ligne ici est la seule chose qui le prouve.
            ScoreORM(archer_id=archers[0].id, points=280),
            ForfaitORM(
                tournoi_id=tournoi_id,
                archer_id=archers[0].id,
                phase_id=phase.id,
                nature="abandon",
                declare_par="admin",
                declare_le=instant,
            ),
        ]
    )
    # 4 duels, 3 flèches par volée, 2 volées sur la 1ʳᵉ série et 1 sur la seconde → 9 flèches.
    session.add_all(
        DuelORM(
            phase_id=phase.id,
            match_numero=n,
            haut_genre="inscription",
            haut_ref=inscriptions[0].id,
            bas_genre="bye",
            bas_ref=0,
            manches="[]",
        )
        for n in range(1, 5)
    )
    session.add_all(
        [
            VoleeORM(serie_id=series[0].id, numero=1, valeurs="[10, 9, 8]", validee_par="admin"),
            # ⚠️ Volée **non validée** : elle doit compter malgré tout — le message annonçait « 0
            # flèche » en fin de journée, avant la validation du scoreur (revue, axe D).
            VoleeORM(serie_id=series[0].id, numero=2, valeurs="[7, 6, 5]"),
            VoleeORM(serie_id=series[1].id, numero=1, valeurs="[9, 9, 9]", validee_par="admin"),
        ]
    )
    session.commit()


def _lignes(session: Session, table: str, tournoi_id: int) -> int:
    """Compte les lignes de `table` rattachées à ce tournoi, par le chemin de FK qui le relie."""
    for gabarit, tables in _RATTACHEMENT.items():
        if table in tables:
            critere = gabarit.format(tid=tournoi_id)
            break
    else:  # pragma: no cover - une table hors inventaire est déjà un échec de l'autre test
        raise AssertionError(f"{table} n'est dans aucun chemin de rattachement.")
    return session.scalar(text(f"SELECT COUNT(*) FROM {table} WHERE {critere}")) or 0


def test_aucune_table_neuve_n_echappe_a_l_inventaire() -> None:
    """Toute table rattachée au tournoi doit figurer à l'inventaire de la descendance.

    ⚠️ **C'est ce test qui remplace la ligne `DETTE-001` du registre.** Pendant treize mois, ce qui
    a fait tenir l'inventaire, c'est qu'une revue relisait cette ligne à chaque table ajoutée — et
    elle l'a manquée deux fois. Sans ce test, une table neuve ne fait rougir personne et rouvre le
    500 que l'US vient de fermer (relevé en revue, axes C2 et D).
    """
    attendues = set(Base.metadata.tables) - _HORS_DESCENDANCE
    assert attendues == set(_TABLES_DE_LA_DESCENDANCE), (
        "Une table a rejoint (ou quitté) la descendance du tournoi sans rejoindre l'inventaire. "
        "Elle doit être ajoutée à `_RATTACHEMENT`, à `_garnir`, à la purge "
        "(`TournoiRepositorySQL.supprimer`) et, si sa perte est irrécupérable, au décompte "
        "(`compter_descendance` + `DescendanceTournoi`)."
    )


def test_aucune_fk_de_la_descendance_ne_cascade_en_base() -> None:
    """CA E01US026 : **aucun `ON DELETE CASCADE`** en base — la confirmation vit dans le service.

    ⚠️ Une cascade SQL ne contournerait pas la confirmation *sur le chemin de l'admin*, mais elle
    armerait une purge **silencieuse** sur tout autre chemin — import, script, futur endpoint
    (ADR-0077 §5). Les exceptions ci-dessous sont des **données dérivées ou des composants stricts**
    d'un agrégat, chacune motivée à sa colonne dans `models.py`. Allonger cette liste est une
    décision qui se voit en revue ; aujourd'hui, rien d'autre ne la rendait visible.
    """
    cascades = {
        f"{table.name}.{colonne.name}"
        for table in Base.metadata.tables.values()
        for colonne in table.columns
        for cle in colonne.foreign_keys
        if cle.ondelete is not None
    }
    assert cascades == {
        "placement.inscription_id",
        "placement.depart_id",
        "placement_tableau.phase_id",
        "placement_tableau.inscription_id",
        "placement_par_bloc.phase_id",
        "serie.phase_id",
        "volee.serie_id",
        "duel.phase_id",
        "forfait.phase_id",
        "identite_tournoi.tournoi_id",
    }


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
    """Le tournoi **voisin** garde toute sa descendance, et le patrimoine du club aussi.

    Le risque est asymétrique — une table oubliée fait un 500 qu'on voit tout de suite, un `WHERE`
    trop large efface en silence un tournoi que personne ne regardait. D'où le contrôle des **24**
    tables du témoin, et non d'un échantillon (relevé en revue, axe C1).
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
            # Le patrimoine du club : un club, et des **modèles de bibliothèque** (`tournoi_id`
            # NULL, E01US023). Un `WHERE tournoi_id IS NULL OR …` les effacerait en silence.
            session.add(ClubORM(nom="Arc Club de Kervignarc"))
            session.add(BlasonORM(nom="Modèle 60", taille=60.0, capacite=1, zones="[]"))
            session.add(CategorieORM(libelle="Modèle S1H", ages="[]", hauteur_cm=130))
            session.commit()
        repository.supprimer(cible.id)
        with db.session_factory() as session:
            for table in _TABLES_DE_LA_DESCENDANCE:
                assert _lignes(session, table, temoin.id) > 0, f"{table} : le témoin a été amputé"
            assert session.scalar(text("SELECT COUNT(*) FROM club")) == 1
            assert session.scalar(text("SELECT COUNT(*) FROM blason WHERE tournoi_id IS NULL")) == 1
            bibliotheque = text("SELECT COUNT(*) FROM categorie WHERE tournoi_id IS NULL")
            assert session.scalar(bibliotheque) == 1
    finally:
        db.engine.dispose()


def test_compter_descendance_chiffre_ce_qui_partira(tmp_path: Path) -> None:
    """Le décompte annoncé à l'admin est **celui de la base**, pas une estimation.

    Chaque nature a une cardinalité distincte dans `_garnir` : intervertir deux critères du
    décompte ferait échouer ce test, ce qui n'était pas le cas quand tout valait `1`.
    """
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
        assert descendance.archers == 2
        assert descendance.inscriptions == 3
        assert descendance.fleches == 9
        assert descendance.series == 2
        assert descendance.duels == 4
        assert descendance.forfaits == 1
        assert descendance.barrages == 1
        assert descendance.postes == 3
        assert descendance.scoreurs == 2
        assert descendance.entrees_audit == 5
        assert descendance.inscriptions_payees == 1
        assert descendance.encaisse_centimes == 800
        assert descendance.remboursements == 1
        assert descendance.remboursements_centimes == 800
    finally:
        db.engine.dispose()


def test_le_decompte_ignore_les_remboursements_deja_traites(tmp_path: Path) -> None:
    """Un poste **remboursé** est de l'argent déjà rendu : l'annoncer comme perdu use la garde.

    Le décompte des lignes reste global (elles partent toutes), seule la **somme** se restreint à ce
    qui reste dû (relevé en revue, axes A, C2 et D).
    """
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    try:
        repository = TournoiRepositorySQL(db.session_factory)
        cible = repository.ajouter(Tournoi.creer("Trophée", _DATE))
        assert cible.id is not None
        with db.session_factory() as session:
            _garnir(session, cible.id)
            session.execute(
                text("UPDATE remboursement SET statut = 'rembourse' WHERE tournoi_id = :tid"),
                {"tid": cible.id},
            )
            session.commit()
        descendance = repository.compter_descendance(cible.id)
        assert descendance.remboursements == 1
        assert descendance.remboursements_centimes == 0
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
            session.add(
                DerouleEtapeORM(tournoi_id=cible.id, ordre=1, type="qualification", config="{}")
            )
            session.commit()
        assert repository.compter_descendance(cible.id).est_vide()
    finally:
        db.engine.dispose()


def test_un_tournoi_prepare_mais_sans_archer_n_est_pas_vide(tmp_path: Path) -> None:
    """⚠️ Le symétrique du test précédent, et c'est lui qui porte le vrai risque.

    Un tournoi entièrement préparé la veille — postes enrôlés, QR imprimés et collés sur les buttes,
    scoreurs codés — n'a pas encore un seul archer. Les codes étant tirés au hasard (`secrets`), ils
    ne se ressaisissent pas : sans ce contrôle, tout cela partait sur **un seul clic** (revue
    adversariale d'E01US026).
    """
    url = f"sqlite:///{(tmp_path / 'kervignarc.db').as_posix()}"
    _migrer(url)
    db = Database(url)
    try:
        repository = TournoiRepositorySQL(db.session_factory)
        cible = repository.ajouter(Tournoi.creer("Trophée", _DATE))
        assert cible.id is not None
        with db.session_factory() as session:
            session.add(PosteORM(tournoi_id=cible.id, code="PO-1", cible_index=1))
            session.add(ScoreurORM(tournoi_id=cible.id, nom="Jean", code="SC-1"))
            session.commit()
        descendance = repository.compter_descendance(cible.id)
        assert not descendance.est_vide()
        assert (descendance.postes, descendance.scoreurs) == (1, 1)
    finally:
        db.engine.dispose()


def test_le_journal_d_audit_seul_suffit_a_demander_confirmation(tmp_path: Path) -> None:
    """Le journal d'audit est une **trace**, pas de la configuration : rien ne le reconstitue.

    Un tournoi vidé de ses archers un à un gardait ses actes tracés et partait sans un mot —
    E16US016 venait pourtant de lui donner son écran (relevé en revue, axes A, C1, C2).
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
                EntreeAuditORM(
                    tournoi_id=cible.id,
                    action="paiement",
                    auteur="admin",
                    horodatage=datetime.datetime(2026, 3, 14, 9, 0, tzinfo=datetime.UTC),
                    objet="inscription 1",
                )
            )
            session.commit()
        descendance = repository.compter_descendance(cible.id)
        assert not descendance.est_vide()
        assert descendance.entrees_audit == 1
    finally:
        db.engine.dispose()
