"""Lecture du backlog : les epics, les US spécifiées, et le registre de dette.

Trois fichiers écrits à la main qui se citent les uns les autres — `epics/README.md` déclare des
dépendances entre epics, `stories/` spécifie les US, `docs/dette.md` renvoie à des US de
résorption — sans que rien ne vérifie que ces renvois pointent vers quelque chose.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from atlas import markdown, normalisation
from atlas.modele import AtlasSourceInvalide

_EPIC = re.compile(r"EPIC-(\d{2})")
_DETTE = re.compile(r"DETTE-(\d{3})")
_US = re.compile(r"E\d{2}US\d{3}")
# Les deux sections du registre, et ce qu'elles disent de la ligne qu'elles portent.
_ETAT_DE_DETTE = {"dette ouverte": True, "dette resorbee": False}
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


def _dependances(cellule: str) -> tuple[str, ...]:
    """« 02, 03, 04 », « EPIC-02 · EPIC-03 » ou « — » — et rien d'autre.

    ⚠️ La version précédente cherchait `\\b(\\d{2})\\b` **dans toute la cellule** : une glose datée
    (« 03 *(depuis le 15/08)* ») y fabriquait des dépendances vers EPIC-15 et EPIC-08 — qui
    existent, donc aucun contrôle ne les contredisait, et le schéma dessinait une arête inventée.
    On découpe donc d'abord la liste, puis on n'accepte qu'un jeton **entièrement** conforme.
    """
    trouves = [
        entier.group(1)
        for jeton in re.split(r"[,;·]", cellule)
        # En **tête** de jeton, jamais au milieu : « 03 *(depuis le 15/08)* » vaut bien une
        # dépendance vers 03 — une annotation ne l'annule pas — mais « 15 » et « 08 » ne sont
        # pas des dépendances. Exiger le jeton entier aurait perdu la dépendance légitime ;
        # accepter n'importe où en fabriquait deux fausses.
        if (entier := re.match(r"\s*`?(?:EPIC-)?(\d{2})\b", jeton))
    ]
    return tuple(dict.fromkeys(trouves))


def lire_epics(racine: Path) -> tuple[Epic, ...]:
    """La carte des epics et leurs dépendances, telle que `epics/README.md` la tabule."""
    texte = markdown.lire(racine / "epics" / "README.md")
    trouves: list[Epic] = []
    for _, entete, lignes in markdown.tableaux(texte):
        index = markdown.index_colonnes(entete)
        if "ID" not in index or "Dépend de" not in index:
            continue
        for cellules in lignes:
            identifiant = _EPIC.search(markdown.cellule(cellules, index, "ID"))
            if not identifiant:
                continue
            trouves.append(
                Epic(
                    identifiant=identifiant.group(1),
                    titre=markdown.en_clair(markdown.cellule(cellules, index, "Titre")),
                    priorite=markdown.en_clair(markdown.cellule(cellules, index, "Priorité")),
                    depend_de=_dependances(markdown.cellule(cellules, index, "Dépend de")),
                )
            )
    return tuple(trouves)


def lire_dettes(racine: Path) -> tuple[Dette, ...]:
    """Les deux registres de dette — ouverte et résorbée — dans l'ordre du fichier.

    Le drapeau `ouverte` se déduit de la **section** où la table se trouve — « Dette ouverte » ou
    « Dette résorbée » — parce que la procédure du projet veut qu'une dette résorbée **change de
    table**, et que c'est ce déplacement qui fait foi.

    ⚠️ Il se déduisait auparavant de la **présence d'une colonne `Sévérité`**, ce qui marchait par
    coïncidence et contredisait cette docstring. Ajouter une colonne `Sévérité` à la table des
    dettes résorbées — pour garder la sévérité historique, geste parfaitement naturel — les aurait
    toutes basculées en « ouvertes », rendant `dette-dans-les-deux-tables` définitivement incapable
    de se déclencher. Un lecteur silencieusement faux vaut moins que pas de lecteur.
    """
    texte = markdown.lire(racine / "docs" / "dette.md")
    trouves: list[Dette] = []
    for section, entete, lignes in markdown.tableaux(texte):
        index = markdown.index_colonnes(entete)
        if "ID" not in index:
            continue
        etat = _ETAT_DE_DETTE.get(normalisation.cle(section))
        if etat is None:
            # ⚠️ Une table qui porte des `DETTE-nnn` **sous une section inconnue** ne peut pas être
            # lue : rien ne dit si ses lignes sont ouvertes ou résorbées. Sans ce refus, renommer
            # une section rendait sa table invisible — le registre le plus contrôlé du dépôt
            # redevenait muet **en silence**, et les contrôles qui le lisent passaient au vert par
            # vacuité. On ne réclame pas que les deux sections existent : seulement qu'aucune table
            # de dettes ne se retrouve orpheline.
            orphelines = [c for c in lignes if _DETTE.search(markdown.cellule(c, index, "ID"))]
            if orphelines:
                raise AtlasSourceInvalide(
                    f"docs/dette.md : la section « {section} » porte {len(orphelines)} dette(s) "
                    f"mais n'est ni « Dette ouverte » ni « Dette résorbée ».\n"
                    f"C'est la section qui dit si une dette est ouverte ou résorbée — une table "
                    f"rangée ailleurs ne peut pas être lue, et la taire serait pire."
                )
            continue
        for cellules in lignes:
            identifiant = _DETTE.search(markdown.cellule(cellules, index, "ID"))
            if not identifiant:
                continue
            trouves.append(
                Dette(
                    identifiant=identifiant.group(1),
                    ouverte=etat,
                    severite=markdown.en_clair(markdown.cellule(cellules, index, "Sévérité")),
                    introduite_par=tuple(
                        dict.fromkeys(
                            _US.findall(markdown.cellule(cellules, index, "Introduite par"))
                        )
                    ),
                    resorption_us=tuple(
                        dict.fromkeys(
                            _US.findall(
                                markdown.cellule(cellules, index, "Résorption")
                                + " "
                                + markdown.cellule(cellules, index, "Soldée par")
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
