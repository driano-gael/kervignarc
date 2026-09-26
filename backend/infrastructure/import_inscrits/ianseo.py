"""Export Ianseo : CSV `;`, sans en-tête, Latin-1 — format d'import de participants.

Colonnes (0-indexées, lues sur `docs/sources/import inscription/`) : 0 licence · 1 session (= n° de
départ) · 2 division (= arme) · 3 classe · 4 cible · 5-9 drapeaux · 10 nom · 11 prénom · 12 genre
(`0` homme, `1` femme) · 13 code club · 14 nom du club · 15 date de naissance (`AAAA-MM-JJ`).
"""

from __future__ import annotations

import csv
import datetime
import io

from domain.categorie import SexeCategorie
from domain.erreurs import FichierInscritsIllisible
from domain.import_inscrits import FichierInscrits, LigneFichier, SourceImport

_COLONNES_MINIMUM = 16
_GENRES = {"0": SexeCategorie.HOMME, "1": SexeCategorie.FEMME}
_CLASSES = {"H": SexeCategorie.HOMME, "M": SexeCategorie.HOMME, "F": SexeCategorie.FEMME}


def lire(contenu: bytes) -> FichierInscrits:
    lignes = list(csv.reader(io.StringIO(_decoder(contenu)), delimiter=";"))
    if not any(len(cellules) >= _COLONNES_MINIMUM for cellules in lignes):
        raise FichierInscritsIllisible(
            "Fichier non reconnu : ni un export Ianseo (CSV « ; » d'au moins "
            f"{_COLONNES_MINIMUM} colonnes), ni un classeur Résult'Arc (.xls)."
        )
    return FichierInscrits(
        source=SourceImport.IANSEO,
        lignes=tuple(
            _ligne(numero, cellules)
            for numero, cellules in enumerate(lignes, start=1)
            if any(cellule.strip() for cellule in cellules)
        ),
    )


def _decoder(contenu: bytes) -> str:
    """UTF-8 d'abord (un export ré-enregistré) ; sinon Latin-1, qui décode tout octet."""
    try:
        return contenu.decode("utf-8-sig")
    except UnicodeDecodeError:
        return contenu.decode("latin-1")


def _ligne(numero: int, cellules: list[str]) -> LigneFichier:
    if len(cellules) < _COLONNES_MINIMUM:
        return LigneFichier(
            numero=numero,
            licence=None,
            depart_numero=None,
            anomalie=f"{len(cellules)} colonnes au lieu de {_COLONNES_MINIMUM} au moins",
        )
    valeur = [cellule.strip() for cellule in cellules]
    try:
        naissance = _date(valeur[15])
    except ValueError:
        return LigneFichier(
            numero=numero,
            licence=valeur[0] or None,
            depart_numero=None,
            anomalie=f"date de naissance illisible « {valeur[15]} »",
        )
    return LigneFichier(
        numero=numero,
        licence=valeur[0] or None,
        depart_numero=int(valeur[1]) if valeur[1].isdigit() else None,
        nom=valeur[10],
        prenom=valeur[11],
        sexe=_GENRES.get(valeur[12]) or _CLASSES.get(valeur[3].upper()),
        date_naissance=naissance,
        club=valeur[14] or None,
        arme=valeur[2] or None,
    )


def _date(texte: str) -> datetime.date | None:
    if not texte:
        return None
    if "/" in texte:
        return datetime.datetime.strptime(texte, "%d/%m/%Y").date()
    return datetime.date.fromisoformat(texte)
