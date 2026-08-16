"""Lecture du backlog — epics, registre de dette, US spécifiées — sur des fixtures littérales.

Ces trois lecteurs n'étaient éprouvés que contre le dépôt réel, ce qui prouve l'état du jour et
non la règle : une dérive de format y rendrait des tuples vides, et **tous** les contrôles qui en
dépendent deviendraient vrais par vacuité, CI verte comprise. C'est ce que la revue du 16/08/2026
a nommé, et c'est exactement le mode de panne que l'atlas existe pour empêcher ailleurs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from atlas.modele import AtlasSourceInvalide
from atlas.sources import backlog

EPICS = """# Les epics

| ID | Titre | Priorité | Dépend de |
|---|---|---|---|
| EPIC-00 | Socle technique | P0 | — |
| EPIC-03 | Placement | P1 | 00, 01 |
| EPIC-05 | Moteur | P1 | 03 *(depuis le 15/08)* |
| EPIC-07 | Public | P2 | EPIC-05 · EPIC-03 |
"""

DETTE = """# Registre de dette

## Dette ouverte

| ID | Type | Sévérité | Portée | Introduite par | Résorption |
|---|---|---|---|---|---|
| DETTE-001 | conception | majeur | `domain/` | E01US002 | E01US026 |

## Dette résorbée

| ID | Type | Portée | Introduite par | Soldée par |
|---|---|---|---|---|
| DETTE-004 | technique | `frontend/` | E00US009 | E00US013 |

## Détail

Rien ici.
"""


def _poser(racine: Path, epics: str = EPICS, dette: str = DETTE) -> Path:
    (racine / "epics").mkdir(parents=True, exist_ok=True)
    (racine / "docs").mkdir(parents=True, exist_ok=True)
    (racine / "epics" / "README.md").write_text(epics, encoding="utf-8", newline="\n")
    (racine / "docs" / "dette.md").write_text(dette, encoding="utf-8", newline="\n")
    return racine


def test_les_dependances_se_lisent_sans_ramasser_les_gloses(tmp_path: Path) -> None:
    """⚠️ Le vrai piège : `\\b(\\d{2})\\b` sur toute la cellule.

    « 03 *(depuis le 15/08)* » y fabriquait des dépendances vers EPIC-15 et EPIC-08 — qui
    **existent**, donc `epic-inexistant` ne les contredisait pas et le schéma dessinait une arête
    inventée. Un lien faux qu'aucun contrôle ne peut voir est pire qu'un lien manquant.
    """
    epics = {e.identifiant: e.depend_de for e in backlog.lire_epics(_poser(tmp_path))}

    assert epics["00"] == ()
    assert epics["03"] == ("00", "01")
    assert epics["05"] == ("03",)
    assert epics["07"] == ("05", "03")


def test_une_dependance_repetee_ne_compte_qu_une_fois(tmp_path: Path) -> None:
    racine = _poser(tmp_path, epics=EPICS.replace("| 00, 01 |", "| 00, 01, 00 |"))
    epics = {e.identifiant: e.depend_de for e in backlog.lire_epics(racine)}

    assert epics["03"] == ("00", "01")


def test_l_etat_d_une_dette_vient_de_sa_section_et_non_d_une_colonne(tmp_path: Path) -> None:
    """Une dette résorbée **change de table** : c'est le déplacement qui fait foi, pas une colonne.

    Le drapeau se déduisait de la présence d'une colonne `Sévérité`, ce qui marchait par
    coïncidence. Ajouter cette colonne à la table des dettes résorbées — pour garder la sévérité
    historique, geste parfaitement naturel — les aurait toutes basculées en « ouvertes », rendant
    `dette-dans-les-deux-tables` **définitivement** incapable de se déclencher.
    """
    resorbee_avec_severite = DETTE.replace(
        "| ID | Type | Portée | Introduite par | Soldée par |\n|---|---|---|---|---|\n"
        "| DETTE-004 | technique | `frontend/` | E00US009 | E00US013 |",
        "| ID | Type | Sévérité | Portée | Introduite par | Soldée par |\n"
        "|---|---|---|---|---|---|\n"
        "| DETTE-004 | technique | mineur | `frontend/` | E00US009 | E00US013 |",
    )
    dettes = {
        d.identifiant: d.ouverte
        for d in backlog.lire_dettes(_poser(tmp_path, dette=resorbee_avec_severite))
    }

    assert dettes == {"001": True, "004": False}


def test_les_deux_registres_se_lisent(tmp_path: Path) -> None:
    dettes = backlog.lire_dettes(_poser(tmp_path))

    assert [(d.identifiant, d.ouverte) for d in dettes] == [("001", True), ("004", False)]
    assert dettes[0].severite == "majeur"
    assert dettes[0].introduite_par == ("E01US002",)
    assert dettes[0].resorption_us == ("E01US026",)
    assert dettes[1].resorption_us == ("E00US013",)


def test_une_section_de_registre_renommee_fait_echouer_la_lecture(tmp_path: Path) -> None:
    """Sans ce refus, renommer une section rendait sa table invisible — donc les dettes muettes.

    Le registre le plus contrôlé du dépôt serait redevenu vide **en silence**, et tous les
    contrôles qui le lisent seraient passés au vert par vacuité.
    """
    racine = _poser(tmp_path, dette=DETTE.replace("## Dette résorbée", "## Dettes soldées"))

    with pytest.raises(AtlasSourceInvalide, match="Dettes soldées"):
        backlog.lire_dettes(racine)


def test_un_tube_echappe_reste_dans_sa_cellule(tmp_path: Path) -> None:
    """`\\|` est la convention Markdown, déjà employée dans `docs/modele-de-donnees.md`."""
    avec_tube = DETTE.replace(
        "| DETTE-001 | conception | majeur | `domain/` | E01US002 | E01US026 |",
        "| DETTE-001 | conception | majeur | `domain/` (lecture \\| écriture) "
        "| E01US002 | E01US026 |",
    )
    dettes = backlog.lire_dettes(_poser(tmp_path, dette=avec_tube))

    assert [(d.identifiant, d.ouverte, d.severite) for d in dettes] == [
        ("001", True, "majeur"),
        ("004", False, ""),
    ]


def test_les_us_specifiees_se_lisent_avec_leur_titre(tmp_path: Path) -> None:
    (tmp_path / "stories").mkdir(parents=True)
    (tmp_path / "stories" / "E00-socle.md").write_text(
        "# EPIC-00\n\n### E00US001 — Le socle\n- **CA** : rien.\n\n"
        "#### E00US002 \u2013 Un sous-titre au demi-cadratin\n",
        encoding="utf-8",
        newline="\n",
    )
    trouvees = backlog.lire_us_specifiees(tmp_path)

    assert [(u.identifiant, u.titre) for u in trouvees] == [
        ("E00US001", "Le socle"),
        ("E00US002", "Un sous-titre au demi-cadratin"),
    ]
    assert trouvees[0].fichier == "stories/E00-socle.md"
