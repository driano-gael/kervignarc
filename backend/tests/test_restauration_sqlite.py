"""Tests de l'adapter `MagasinSauvegardesSQLite` (E11US006) — infra, écrits après l'adapter.

Ce qui se vérifie ici ne se voit pas avec une doublure : corruption réelle d'un fichier, ouverture
d'une sauvegarde en WAL, et surtout restauration **sous une connexion déjà ouverte** du pool.
"""

from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path

from sqlalchemy import text

from application.sauvegardes import NatureSauvegarde
from infrastructure.backup.restauration import MagasinSauvegardesSQLite
from infrastructure.backup.sauvegarde import SauvegardeSQLite
from infrastructure.db.engine import Database

_REVISION = "0058_tete"


class _HorlogeFigee:
    def maintenant(self) -> datetime.datetime:
        return datetime.datetime(2026, 10, 3, 12, 0, 0, tzinfo=datetime.UTC)


def _base(chemin: Path, valeur: str, *, revision: str | None = _REVISION, lignes: int = 1) -> None:
    connexion = sqlite3.connect(str(chemin))
    try:
        connexion.execute("PRAGMA journal_mode=WAL")
        connexion.execute("CREATE TABLE t (x TEXT)")
        connexion.executemany("INSERT INTO t (x) VALUES (?)", [(valeur,)] * lignes)
        if revision is not None:
            connexion.execute("CREATE TABLE alembic_version (version_num TEXT NOT NULL)")
            connexion.execute("INSERT INTO alembic_version VALUES (?)", (revision,))
        connexion.commit()
    finally:
        connexion.close()


def _valeur(chemin: Path) -> str:
    connexion = sqlite3.connect(str(chemin))
    try:
        return str(connexion.execute("SELECT x FROM t").fetchone()[0])
    finally:
        connexion.close()


def _magasin(tmp_path: Path) -> tuple[MagasinSauvegardesSQLite, Path, Path]:
    base = tmp_path / "kervignarc.db"
    dossier = tmp_path / "backups"
    dossier.mkdir()
    return MagasinSauvegardesSQLite(base, dossier, _HorlogeFigee()), base, dossier


def test_lister_reconnait_les_deux_natures_et_ignore_le_reste(tmp_path: Path) -> None:
    magasin, _, dossier = _magasin(tmp_path)
    for nom in [
        "kervignarc-20261003-090000.db",
        "avant-restauration-20261003-100000.db",
        "avant-restauration-20261003-100000-1.db",
        "kervignarc.db",
        "notes.txt",
        "kervignarc-20261003-090000.db-wal",
    ]:
        (dossier / nom).write_bytes(b"x")

    trouvees = {s.nom: s for s in magasin.lister()}

    assert set(trouvees) == {
        "kervignarc-20261003-090000.db",
        "avant-restauration-20261003-100000.db",
        "avant-restauration-20261003-100000-1.db",
    }
    periodique = trouvees["kervignarc-20261003-090000.db"]
    assert periodique.nature is NatureSauvegarde.PERIODIQUE
    assert periodique.prise_le == datetime.datetime(2026, 10, 3, 9, 0, tzinfo=datetime.UTC)
    assert periodique.taille_octets == 1
    nature = trouvees["avant-restauration-20261003-100000.db"].nature
    assert nature is NatureSauvegarde.AVANT_RESTAURATION


def test_lister_un_dossier_absent_rend_une_liste_vide(tmp_path: Path) -> None:
    magasin = MagasinSauvegardesSQLite(tmp_path / "k.db", tmp_path / "absent", _HorlogeFigee())

    assert magasin.lister() == []


def test_examiner_une_sauvegarde_saine_produite_par_la_sauvegarde_periodique(
    tmp_path: Path,
) -> None:
    # Bout en bout avec E11US003 : la copie hérite du mode WAL de la base, et s'ouvre quand même.
    magasin, base, dossier = _magasin(tmp_path)
    _base(base, "vive")
    nom = SauvegardeSQLite(base, dossier, 5, _HorlogeFigee()).sauvegarder().name

    examen = magasin.examiner(nom)

    assert examen.integre
    assert examen.revision == _REVISION


def test_examiner_une_base_sans_alembic_version(tmp_path: Path) -> None:
    magasin, _, dossier = _magasin(tmp_path)
    _base(dossier / "kervignarc-20261003-090000.db", "x", revision=None)

    examen = magasin.examiner("kervignarc-20261003-090000.db")

    assert examen.integre
    assert examen.revision is None


def test_examiner_un_fichier_qui_n_est_pas_une_base(tmp_path: Path) -> None:
    magasin, _, dossier = _magasin(tmp_path)
    (dossier / "kervignarc-20261003-090000.db").write_bytes(b"pas une base SQLite" * 200)

    assert not magasin.examiner("kervignarc-20261003-090000.db").integre


def test_examiner_une_base_aux_pages_abimees(tmp_path: Path) -> None:
    magasin, _, dossier = _magasin(tmp_path)
    chemin = dossier / "kervignarc-20261003-090000.db"
    _base(chemin, "y" * 200, lignes=500)
    contenu = bytearray(chemin.read_bytes())
    taille_page = int.from_bytes(contenu[16:18], "big")
    # Une page de données du milieu, écrasée : l'en-tête reste lisible, l'arbre ne l'est plus.
    debut = taille_page * 3
    contenu[debut : debut + taille_page] = b"\xff" * taille_page
    chemin.write_bytes(bytes(contenu))

    assert not magasin.examiner(chemin.name).integre


def test_examiner_une_base_que_integrity_check_signale_sans_lever(tmp_path: Path) -> None:
    # Le cas précédent lève à la lecture ; celui-ci se lit sans erreur, seul le PRAGMA le voit :
    # un index retiré du schéma laisse ses pages orphelines (« Page N is never used »).
    magasin, _, dossier = _magasin(tmp_path)
    chemin = dossier / "kervignarc-20261003-090000.db"
    _base(chemin, "z" * 200, lignes=200)
    connexion = sqlite3.connect(str(chemin))
    try:
        connexion.execute("CREATE INDEX i ON t (x)")
        connexion.execute("PRAGMA writable_schema = ON")
        connexion.execute("DELETE FROM sqlite_master WHERE name = 'i'")
        connexion.commit()
    finally:
        connexion.close()

    examen = magasin.examiner(chemin.name)

    assert not examen.integre
    assert examen.revision == _REVISION  # la base se lit : c'est bien le PRAGMA qui a parlé


def test_revision_en_service(tmp_path: Path) -> None:
    magasin, base, _ = _magasin(tmp_path)
    _base(base, "vive")

    assert magasin.revision_en_service() == _REVISION


def test_copie_avant_restauration_hors_retention_et_sans_ecrasement(tmp_path: Path) -> None:
    magasin, base, dossier = _magasin(tmp_path)
    _base(base, "original")

    premiere = magasin.copier_avant_restauration()
    seconde = magasin.copier_avant_restauration()  # même seconde (horloge figée)
    SauvegardeSQLite(base, dossier, 1, _HorlogeFigee()).sauvegarder()

    assert premiere == "avant-restauration-20261003-120000.db"
    assert seconde == "avant-restauration-20261003-120000-1.db"
    # La rétention à 1 des périodiques n'a touché aucune des deux copies de sécurité.
    assert (dossier / premiere).exists()
    assert (dossier / seconde).exists()
    assert _valeur(dossier / premiere) == "original"


def test_restaurer_sous_une_connexion_du_pool_deja_ouverte(tmp_path: Path) -> None:
    magasin, base, dossier = _magasin(tmp_path)
    _base(dossier / "kervignarc-20261003-090000.db", "avant")
    _base(base, "apres")
    database = Database(f"sqlite:///{base}")
    try:
        with database.engine.connect() as connexion:
            assert connexion.execute(text("SELECT x FROM t")).scalar_one() == "apres"
            connexion.commit()

            magasin.restaurer("kervignarc-20261003-090000.db")

            # Même connexion, transaction suivante : elle lit le contenu restauré.
            assert connexion.execute(text("SELECT x FROM t")).scalar_one() == "avant"
    finally:
        database.engine.dispose()
