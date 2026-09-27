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
_CHIFFRES_MAXIMUM = 4

# Codes de division Ianseo (FFTA, puis World Archery) → libellés du catalogue FFTA, que
# `test_lecteur_import_inscrits` aligne sur `application/referentiel_ffta.py`. `TA` (« tous arcs »)
# et l'absence ne contraignent pas l'arme (arbitrage du 26/09/2026) ; un code inconnu passe tel
# quel, pour que le motif de rejet le nomme.
_ARMES = {
    "CL": "Arc Classique",
    "R": "Arc Classique",
    "CO": "Arc à Poulies",
    "C": "Arc à Poulies",
    "BB": "Arc Nu",
    "B": "Arc Nu",
}
_TOUS_ARCS = {"TA", ""}
_GENRES = {"0": SexeCategorie.HOMME, "1": SexeCategorie.FEMME}
_CLASSES = {"H": SexeCategorie.HOMME, "M": SexeCategorie.HOMME, "F": SexeCategorie.FEMME}


def lire(contenu: bytes) -> FichierInscrits:
    try:
        lignes = list(csv.reader(io.StringIO(_decoder(contenu)), delimiter=";"))
    except csv.Error as exc:
        raise FichierInscritsIllisible(f"Fichier CSV illisible : {exc}.") from exc
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
        depart_numero=entier(valeur[1]),
        nom=valeur[10],
        prenom=valeur[11],
        sexe=_GENRES.get(valeur[12]) or _CLASSES.get(valeur[3].upper()),
        date_naissance=naissance,
        club=valeur[14] or None,
        arme=_arme(valeur[2]),
    )


def entier(texte: str) -> int | None:
    """Un petit entier décimal ASCII, sinon `None` — `"²".isdigit()` est vrai, `int("²")` lève."""
    valide = texte.isascii() and texte.isdecimal() and len(texte) <= _CHIFFRES_MAXIMUM
    return int(texte) if valide else None


def _arme(code: str) -> str | None:
    cle = code.strip().upper()
    return None if cle in _TOUS_ARCS else _ARMES.get(cle, code.strip())


def _date(texte: str) -> datetime.date | None:
    if not texte:
        return None
    if "/" in texte:
        return datetime.datetime.strptime(texte, "%d/%m/%Y").date()
    return datetime.date.fromisoformat(texte)
