"""Classeur Résult'Arc : `.xls` OLE2, une feuille, une ligne d'en-tête. Ni nom, ni prénom.

Colonnes repérées **par leur en-tête** (casse et accents repliés), pas par leur rang.
"""

from __future__ import annotations

import io

import xlrd

from domain.club import cle_nom
from domain.erreurs import FichierInscritsIllisible
from domain.import_inscrits import FichierInscrits, LigneFichier, SourceImport

_LICENCE = "licence"
_DEPART = "numero depart"


def lire(contenu: bytes) -> FichierInscrits:
    try:
        # ⚠️ `ignore_workbook_corruption` : Résult'Arc écrit une table d'allocation OLE2 que xlrd
        # juge corrompue (`seen[2] == 4`) — sans ce drapeau, aucun vrai fichier ne s'ouvre.
        classeur = xlrd.open_workbook(
            file_contents=contenu, ignore_workbook_corruption=True, logfile=io.StringIO()
        )
        feuille = classeur.sheet_by_index(0)
        rangees = [feuille.row_values(i) for i in range(feuille.nrows)]
    except Exception as exc:  # xlrd lève des types variés sur un binaire quelconque
        raise FichierInscritsIllisible("Classeur .xls illisible.") from exc
    if not rangees:
        raise FichierInscritsIllisible("Le classeur Résult'Arc est vide.")
    en_tete = [cle_nom(str(cellule)) for cellule in rangees[0]]
    if _LICENCE not in en_tete or _DEPART not in en_tete:
        raise FichierInscritsIllisible(
            "Classeur non reconnu : les colonnes « Licence » et « Numéro Départ » sont exigées."
        )
    col_licence, col_depart = en_tete.index(_LICENCE), en_tete.index(_DEPART)
    return FichierInscrits(
        source=SourceImport.RESULTARC,
        lignes=tuple(
            LigneFichier(
                numero=numero,
                licence=_texte(rangee[col_licence]),
                depart_numero=_entier(rangee[col_depart]),
            )
            for numero, rangee in enumerate(rangees[1:], start=2)
            if any(_texte(cellule) for cellule in rangee)
        ),
        colonnes_ignorees=tuple(
            str(cellule).strip()
            for rang, cellule in enumerate(rangees[0])
            if rang not in (col_licence, col_depart) and str(cellule).strip()
        ),
    )


def _texte(cellule: object) -> str | None:
    if isinstance(cellule, float) and cellule.is_integer():
        cellule = int(cellule)
    texte = str(cellule).strip()
    return texte or None


def _entier(cellule: object) -> int | None:
    texte = _texte(cellule)
    return int(texte) if texte is not None and texte.isdigit() else None
