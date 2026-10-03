"""Adapter du port `StoreSauvegardes` : le dossier des sauvegardes et la base en service.

⚠️ **`restaurer` est une ÉCRITURE dans la base vive** : elle n'est sûre que soumise à la file
d'écriture (ADR-0119). `examiner` et `revision_en_service` sont des lectures hors file (ADR-0044).
"""

from __future__ import annotations

import datetime
import re
import sqlite3
from pathlib import Path

from application.sauvegardes import ExamenSauvegarde, NatureSauvegarde, SauvegardeDisponible
from domain.ports import Horloge
from infrastructure.db.snapshot import copier_base_atomique
from infrastructure.erreurs import RestaurationImpossible

# Le préfixe périodique dérive de `SauvegardeSQLite` ; celui de la copie de sécurité doit rester
# hors de son motif `kervignarc-*.db`, sans quoi la rétention la purgerait (CA 4).
_PREFIXES = {
    "kervignarc": NatureSauvegarde.PERIODIQUE,
    "avant-restauration": NatureSauvegarde.AVANT_RESTAURATION,
}
_NOM = re.compile(r"^(kervignarc|avant-restauration)-(\d{8}-\d{6})(?:-(\d+))?\.db$")
_FORMAT = "%Y%m%d-%H%M%S"


def _ouvrir_en_lecture(chemin: Path) -> sqlite3.Connection:
    # `immutable=1` : aucun verrou ni fichier `-shm` — une sauvegarde n'est écrite par personne.
    return sqlite3.connect(f"{chemin.resolve().as_uri()}?mode=ro&immutable=1", uri=True)


def _revision(connexion: sqlite3.Connection) -> str | None:
    try:
        ligne = connexion.execute("SELECT version_num FROM alembic_version").fetchone()
    except sqlite3.DatabaseError:
        return None
    return None if ligne is None else str(ligne[0])


class StoreSauvegardesSQLite:
    def __init__(self, base: Path, dossier: Path, horloge: Horloge) -> None:
        self._base = base
        self._dossier = dossier
        self._horloge = horloge

    def lister(self) -> list[SauvegardeDisponible]:
        if not self._dossier.is_dir():
            return []
        disponibles = []
        for chemin in self._dossier.iterdir():
            correspondance = _NOM.match(chemin.name)
            if correspondance is None or not chemin.is_file():
                continue
            prefixe, horodatage, _ = correspondance.groups()
            prise_le = datetime.datetime.strptime(horodatage, _FORMAT).replace(tzinfo=datetime.UTC)
            try:
                taille = chemin.stat().st_size
            except FileNotFoundError:
                continue  # purgée par la rétention, hors file, entre `iterdir` et `stat`
            disponibles.append(
                SauvegardeDisponible(
                    nom=chemin.name,
                    nature=_PREFIXES[prefixe],
                    prise_le=prise_le,
                    taille_octets=taille,
                )
            )
        return disponibles

    def examiner(self, nom: str) -> ExamenSauvegarde:
        try:
            connexion = _ouvrir_en_lecture(self._dossier / nom)
        except sqlite3.DatabaseError:
            return ExamenSauvegarde(integre=False, revision=None)
        try:
            # Un fichier qui n'est pas une base lève dès la première requête, pas à l'ouverture.
            lignes = connexion.execute("PRAGMA integrity_check").fetchall()
        except sqlite3.DatabaseError:
            return ExamenSauvegarde(integre=False, revision=None)
        else:
            return ExamenSauvegarde(integre=lignes == [("ok",)], revision=_revision(connexion))
        finally:
            connexion.close()

    def revision_en_service(self) -> str | None:
        connexion = sqlite3.connect(str(self._base))
        try:
            connexion.execute("PRAGMA busy_timeout = 5000")
            return _revision(connexion)
        finally:
            connexion.close()

    def copier_avant_restauration(self) -> str:
        horodatage = self._horloge.maintenant().strftime(_FORMAT)
        try:
            self._dossier.mkdir(parents=True, exist_ok=True)
            cible = self._dossier / f"avant-restauration-{horodatage}.db"
            rang = 1
            # ⚠️ Jamais d'écrasement : deux restaurations à la même seconde perdraient l'original.
            while cible.exists():
                cible = self._dossier / f"avant-restauration-{horodatage}-{rang}.db"
                rang += 1
            copier_base_atomique(self._base, cible)
        except (sqlite3.Error, OSError) as exc:
            raise RestaurationImpossible(f"Copie de sécurité impossible : {exc}") from exc
        return cible.name

    def restaurer(self, nom: str) -> None:
        try:
            source = _ouvrir_en_lecture(self._dossier / nom)
            try:
                vive = sqlite3.connect(str(self._base))
                try:
                    vive.execute("PRAGMA busy_timeout = 5000")
                    # `backup` vers la base vive : les connexions du pool voient le nouveau
                    # contenu à leur prochaine transaction — ni fichier remplacé, ni engine rouvert.
                    source.backup(vive)
                finally:
                    vive.close()
            finally:
                source.close()
        except sqlite3.Error as exc:
            raise RestaurationImpossible(f"Restauration de {nom} impossible : {exc}") from exc
