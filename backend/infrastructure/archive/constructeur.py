"""Constructeur du paquet d'archive ZIP (E11US003, CA « export/archive fin de tournoi »).

Assemble en mémoire un `.zip` (module `zipfile` de la **stdlib** — aucune dépendance ajoutée,
règle 11) réunissant, au choix de l'appelant :

- `kervignarc.db` : un **instantané cohérent** de toute la base (API `sqlite3.backup`, cf.
  `infrastructure/db/snapshot.py`) — le filet anti-plantage, fidèle et rejouable ;
- `donnees/<table>.csv` : un **dump lisible** de chaque table de la base, colonnes en en-tête. Les
  tables sont lues depuis `sqlite_master` (fidèle au schéma réel, sans coupler ce module aux
  modèles ORM) ; c'est la couche « ouvrable dans un tableur » de l'archive ;
- les **documents PDF** fournis par l'appelant (feuilles de marque, listes) sous `documents/` ;
- `manifeste.json` : les métadonnées métier fournies par l'appelant, **complétées** ici des faits
  tirés de la base (version du schéma Alembic, tables et nombre de lignes).

**Cohérence interne.** Un **unique instantané** de la base vive est pris au début, et **toutes** les
parties tirées de la base (fichier `.db`, CSV, comptes et version du manifeste) sont lues depuis
**cet** instantané figé — jamais de la base vive à des instants différents. Ainsi le `.db`, les CSV
et le manifeste décrivent le **même** état, même si des saisies ont lieu pendant la composition.
Seuls les PDF, régénérés en amont par le service, reflètent leur propre instant de lecture.

Ce module est purement mécanique : il ne connaît ni tournoi ni règle métier (règle 12 — l'infra
d'export reste simple). L'orchestration (quel tournoi, quels PDF) est dans `ServiceArchive`.
"""

from __future__ import annotations

import csv
import io
import json
import sqlite3
import tempfile
import zipfile
from collections.abc import Mapping
from pathlib import Path

from infrastructure.db.snapshot import copier_base_coherente


class ConstructeurArchiveZip:
    """Compose un paquet ZIP d'archive à partir d'une base SQLite et de documents fournis."""

    def __init__(self, chemin_base: Path) -> None:
        self._chemin_base = chemin_base

    def construire(
        self,
        *,
        inclure_base: bool,
        inclure_csv: bool,
        documents: Mapping[str, bytes],
        metadonnees: Mapping[str, object],
    ) -> bytes:
        """Renvoie les octets du ZIP (snapshot + CSV + PDF + manifeste), selon les inclusions."""
        with tempfile.TemporaryDirectory() as dossier_tmp:
            # Instantané cohérent unique : source de toutes les parties tirées de la base.
            snapshot = Path(dossier_tmp) / "snapshot.db"
            copier_base_coherente(self._chemin_base, snapshot)
            tables = self._tables_et_comptes(snapshot)

            tampon = io.BytesIO()
            with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as paquet:
                if inclure_base:
                    paquet.writestr("kervignarc.db", snapshot.read_bytes())
                if inclure_csv:
                    for table in tables:
                        paquet.writestr(f"donnees/{table}.csv", self._table_en_csv(snapshot, table))
                for nom, octets in documents.items():
                    paquet.writestr(f"documents/{nom}", octets)
                manifeste = {
                    **metadonnees,
                    "version_schema": self._version_schema(snapshot),
                    "tables": tables,
                }
                paquet.writestr(
                    "manifeste.json",
                    json.dumps(manifeste, ensure_ascii=False, indent=2, sort_keys=True),
                )
            return tampon.getvalue()

    @staticmethod
    def _tables_et_comptes(chemin: Path) -> dict[str, int]:
        """Nom → nombre de lignes de chaque table de la base (ordre alphabétique stable)."""
        connexion = sqlite3.connect(str(chemin))
        try:
            noms = [
                str(ligne[0])
                for ligne in connexion.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' "
                    "AND name NOT LIKE 'sqlite_%' ORDER BY name"
                )
            ]
            comptes: dict[str, int] = {}
            for nom in noms:
                # `nom` provient de `sqlite_master` (notre propre schéma) ; on le double-quote
                # tout de même par principe. Pas de paramètre lié possible sur un nom de table.
                (compte,) = connexion.execute(f'SELECT COUNT(*) FROM "{nom}"').fetchone()
                comptes[nom] = int(compte)
            return comptes
        finally:
            connexion.close()

    @staticmethod
    def _table_en_csv(chemin: Path, table: str) -> str:
        """Dump CSV d'une table : ligne d'en-tête = colonnes, puis toutes les lignes."""
        connexion = sqlite3.connect(str(chemin))
        try:
            curseur = connexion.execute(f'SELECT * FROM "{table}"')
            colonnes = [description[0] for description in curseur.description]
            tampon = io.StringIO()
            ecrivain = csv.writer(tampon)
            ecrivain.writerow(colonnes)
            ecrivain.writerows(curseur.fetchall())
            return tampon.getvalue()
        finally:
            connexion.close()

    @staticmethod
    def _version_schema(chemin: Path) -> str | None:
        """Révision Alembic courante (`alembic_version`), ou `None` si absente."""
        connexion = sqlite3.connect(str(chemin))
        try:
            ligne = connexion.execute("SELECT version_num FROM alembic_version").fetchone()
            return str(ligne[0]) if ligne is not None else None
        except sqlite3.OperationalError:
            return None
        finally:
            connexion.close()
