"""Lecture du backlog : les epics, les US spécifiées, et le registre de dette.

Trois fichiers écrits à la main qui se citent les uns les autres — `epics/README.md` déclare des
dépendances entre epics, `stories/` spécifie les US, `docs/dette.md` renvoie à des US de
résorption — sans que rien ne vérifie que ces renvois pointent vers quelque chose.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from atlas import markdown

_EPIC = re.compile(r"EPIC-(\d{2})")
_DETTE = re.compile(r"DETTE-(\d{3})")
_US = re.compile(r"E\d{2}US\d{3}")
# Le séparateur est écrit en échappements Unicode et non en toutes lettres : cadratin, demi-cadratin
# et trait d'union se ressemblent à l'œil et se confondent à la relecture.
_TITRE_US = re.compile(
    r"^#{2,4}\s+(?P<id>E\d{2}US\d{3})\s*[-\u2013\u2014]\s*(?P<titre>.+?)\s*$", re.M
)


@dataclass(frozen=True, slots=True)
class Epic:
    identifiant: str
    titre: str
    priorite: str
    depend_de: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Dette:
    identifiant: str
    ouverte: bool
    severite: str
    introduite_par: tuple[str, ...]
    resorption_us: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UsSpecifiee:
    identifiant: str
    titre: str
    fichier: str


def _cellule(cellules: list[str], index: dict[str, int], nom: str) -> str:
    """La cellule d'une colonne nommée — vide si la colonne ou la cellule manque."""
    rang = index.get(nom)
    return cellules[rang] if rang is not None and rang < len(cellules) else ""


def lire_epics(racine: Path) -> tuple[Epic, ...]:
    """La carte des epics et leurs dépendances, telle que `epics/README.md` la tabule."""
    texte = markdown.lire(racine / "epics" / "README.md")
    trouves: list[Epic] = []
    for entete, lignes in markdown.tableaux(texte):
        index = {nom.strip("* "): rang for rang, nom in enumerate(entete)}
        if "ID" not in index or "Dépend de" not in index:
            continue
        for cellules in lignes:
            identifiant = _EPIC.search(_cellule(cellules, index, "ID"))
            if not identifiant:
                continue
            trouves.append(
                Epic(
                    identifiant=identifiant.group(1),
                    titre=markdown.en_clair(_cellule(cellules, index, "Titre")),
                    priorite=markdown.en_clair(_cellule(cellules, index, "Priorité")),
                    # « 02, 03, 04 » ou « — » : on lit les nombres à deux chiffres, rien d'autre.
                    depend_de=tuple(
                        re.findall(r"\b(\d{2})\b", _cellule(cellules, index, "Dépend de"))
                    ),
                )
            )
    return tuple(trouves)


def lire_dettes(racine: Path) -> tuple[Dette, ...]:
    """Les deux registres de dette — ouverte et résorbée — dans l'ordre du fichier.

    Le drapeau `ouverte` se déduit de la **table** où la ligne se trouve, pas d'une colonne : la
    procédure du projet veut qu'une dette résorbée **change de table**, et c'est ce déplacement
    qui fait foi.
    """
    texte = markdown.lire(racine / "docs" / "dette.md")
    trouves: list[Dette] = []
    for entete, lignes in markdown.tableaux(texte):
        index = {nom.strip("* "): rang for rang, nom in enumerate(entete)}
        if "ID" not in index:
            continue
        ouverte = "Sévérité" in index
        for cellules in lignes:
            identifiant = _DETTE.search(_cellule(cellules, index, "ID"))
            if not identifiant:
                continue
            trouves.append(
                Dette(
                    identifiant=identifiant.group(1),
                    ouverte=ouverte,
                    severite=markdown.en_clair(_cellule(cellules, index, "Sévérité")),
                    introduite_par=tuple(
                        dict.fromkeys(_US.findall(_cellule(cellules, index, "Introduite par")))
                    ),
                    resorption_us=tuple(
                        dict.fromkeys(
                            _US.findall(
                                _cellule(cellules, index, "Résorption")
                                + " "
                                + _cellule(cellules, index, "Soldée par")
                            )
                        )
                    ),
                )
            )
    return tuple(trouves)


def lire_us_specifiees(racine: Path) -> tuple[UsSpecifiee, ...]:
    """Les US telles que `stories/` les spécifie — titre compris.

    C'est le second terme des contrôles de concordance : le tracker dit l'**état** d'une US, les
    stories disent ce qu'elle **est**. Quand les deux titres divergent, l'un des deux ment.
    """
    dossier = racine / "stories"
    trouvees: list[UsSpecifiee] = []
    for fichier in sorted(dossier.glob("*.md")):
        chemin = fichier.relative_to(racine).as_posix()
        for entree in _TITRE_US.finditer(markdown.lire(fichier)):
            trouvees.append(
                UsSpecifiee(
                    identifiant=entree.group("id"),
                    titre=markdown.en_clair(entree.group("titre")),
                    fichier=chemin,
                )
            )
    return tuple(trouvees)
