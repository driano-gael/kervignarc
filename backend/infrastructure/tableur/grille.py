"""Socle des rendus tableur : une **grille** composée une fois, rendue en CSV ou en xlsx (E16US016).

Pourquoi un socle et non un adapter par document et par format : ADR-0101 §6.

⚠️ Le type s'appelle `Grille` et **non `Tableau`** : ce dernier est un terme FFTA du glossaire —
l'arbre de matchs à élimination (`domain/tableau.py`). Même parti que le paquet, qui ne s'appelle
pas `csv` pour ne pas heurter le module stdlib qu'il importe.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from typing import Protocol

from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.worksheet.worksheet import Worksheet

from infrastructure.erreurs import InfrastructureError

_SEPARATEUR = ";"

# Caractères par lesquels un tableur reconnaît une **formule**. Une cellule qui commence par l'un
# d'eux est exécutée à l'ouverture (CWE-1236) — or les noms d'archers et de clubs viennent de la
# saisie et de l'import FFTA, et le fichier est fait pour partir chez la trésorière.
_AMORCES_DE_FORMULE = ("=", "+", "-", "@", "\t", "\r")

_FORMAT_MONTANT_XLSX = "0.00"

# Ce qu'Excel refuse dans un nom d'onglet, et la longueur qu'il tolère. ⚠️ openpyxl ne lève que
# sur les caractères interdits : au-delà de 31 il se contente d'un avertissement, et un caractère
# de contrôle produit un `workbook.xml` **mal formé**, donc un classeur illisible servi en 200.
_TITRE_INTERDIT = re.compile(r"[\/*?:\[\]]")
_TITRE_MAX = 31


@dataclass(frozen=True)
class Montant:
    """Une somme, en centimes. Marque la cellule comme **nombre**, jamais comme texte.

    ⚠️ C'est ce marquage, et lui seul, qui rend la colonne sommable : un montant suffixé ou
    neutralisé redevient du texte, ce qu'ADR-0101 §4 interdit — l'usage de l'export *est* la somme.
    """

    centimes: int


Cellule = str | int | Montant
"""Ce qu'une case peut porter. `str` est du texte (donc neutralisable), le reste est numérique."""


@dataclass(frozen=True)
class Grille:
    """Un document tabulaire prêt à rendre : un titre de feuille, une ligne d'en-tête, les données.

    ⚠️ Aucun total, aucun bloc, aucun titre **dans** la grille (ADR-0101 §4) : ce qui fait un beau
    PDF casse le tri et le filtre d'un tableur. `titre` nomme l'onglet du classeur, rien de plus —
    le CSV l'ignore, n'ayant pas d'onglet.
    """

    entetes: tuple[str, ...]
    lignes: tuple[tuple[Cellule, ...], ...]
    titre: str = "Export"


class RenduTableur(Protocol):
    """Port interne : transforme une `Grille` en octets téléchargeables."""

    def __call__(self, grille: Grille) -> bytes:
        """Rend la grille ; lève `InfrastructureError` si l'écriture échoue."""
        ...


def rendre_csv(grille: Grille) -> bytes:
    """Rend en CSV lisible par un tableur français (ADR-0101 §4 : BOM, point-virgule, virgule)."""
    try:
        tampon = io.StringIO(newline="")
        # `\r\n` : fin de ligne attendue par la RFC 4180 et par Excel sous Windows.
        redacteur = csv.writer(tampon, delimiter=_SEPARATEUR, lineterminator="\r\n")
        for ligne in (grille.entetes, *grille.lignes):
            redacteur.writerow(tuple(_cellule_csv(cellule) for cellule in ligne))
        return tampon.getvalue().encode("utf-8-sig")
    except Exception as echec:  # pragma: no cover - défense, `csv` n'échoue pas sur du `str`
        raise InfrastructureError("Échec du rendu CSV du document.") from echec


def rendre_xlsx(grille: Grille) -> bytes:
    """Rend en classeur Excel — une feuille nommée, l'en-tête figé."""
    try:
        classeur = Workbook()
        feuille = classeur.active
        feuille.title = _titre_sur(grille.titre)
        for numero, ligne in enumerate((grille.entetes, *grille.lignes), start=1):
            _ecrire_ligne_xlsx(feuille, numero, ligne)
        # Fige l'en-tête : un journal de mille lignes se lit en défilant, sans perdre ses colonnes.
        feuille.freeze_panes = "A2"
        tampon = io.BytesIO()
        classeur.save(tampon)
        return tampon.getvalue()
    except Exception as echec:  # pragma: no cover - défense ; les entrées fautives sont assainies
        raise InfrastructureError("Échec du rendu xlsx du document.") from echec


def _ecrire_ligne_xlsx(feuille: Worksheet, numero: int, ligne: tuple[Cellule, ...]) -> None:
    """Écrit une ligne, en **forçant le type** de chaque case de texte.

    ⚠️ openpyxl interprète toute chaîne commençant par `=` comme une formule (`data_type` vaut
    alors `f`) : sans ce forçage, un nom d'archer importé exécuterait du calcul à l'ouverture.
    Le `data_type` se pose **après** l'affectation, qui le recalcule. ⚠️ **L'en-tête passe par ici
    comme les données** : l'en exempter rouvrait le trou au premier document à colonnes calculées.
    """
    for colonne, valeur in enumerate(ligne, start=1):
        if isinstance(valeur, Montant):
            case = feuille.cell(row=numero, column=colonne, value=valeur.centimes / 100)
            case.number_format = _FORMAT_MONTANT_XLSX
            continue
        if isinstance(valeur, str):
            valeur = ILLEGAL_CHARACTERS_RE.sub("", valeur)
        case = feuille.cell(row=numero, column=colonne, value=valeur)
        if isinstance(valeur, str):
            case.data_type = "s"


def _cellule_csv(cellule: Cellule) -> str:
    """Rend une case en texte CSV : montants à la française, texte neutralisé."""
    if isinstance(cellule, Montant):
        # Virgule décimale et **sans symbole** — pour rester sommable au tableur.
        return f"{cellule.centimes / 100:.2f}".replace(".", ",")
    if isinstance(cellule, int):
        return str(cellule)
    return f"'{cellule}" if cellule.startswith(_AMORCES_DE_FORMULE) else cellule


def _titre_sur(titre: str) -> str:
    """Rend un nom d'onglet qu'Excel accepte : sans caractère interdit ni de contrôle, borné à 31.

    ⚠️ **Assainir plutôt que laisser lever** : un `/` dans un libellé de catégorie ferait échouer
    **tout** l'export, et un caractère de contrôle produirait un classeur illisible servi en 200.
    La donnée vient de la saisie et de l'import FFTA — un onglet renommé coûte moins qu'un export
    perdu le jour J.
    """
    propre = _TITRE_INTERDIT.sub(" ", ILLEGAL_CHARACTERS_RE.sub("", titre)).strip()
    return propre[:_TITRE_MAX] or "Export"
