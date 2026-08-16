"""Les quatre issues de la porte, éprouvées sur un dépôt jetable.

Ces tests manquaient, et leur absence est instructive : le correctif « les écarts bloquants font
rougir la porte » avait été livré **sans rien qui prouve qu'ils rougissent**. C'est le mode de
panne que la règle 9 décrit — un correctif en code de production ne touche aucun fichier de test,
donc n'éveille jamais son propre relecteur. Il a fallu qu'un second passage le cherche.

`principal()` a dû devenir testable pour cela : `racine` était un global du module, ce qui rendait
la fonction structurellement inatteignable depuis un test. Une porte qu'on ne peut pas éprouver
n'est pas une porte, c'est une intention — exactement ce qu'ADR-0075 reproche à un ADR sans lien
vers le code.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from atlas.__main__ import principal

CLAUDE = """# Essai

## Règles non négociables

1. **Isolation du domaine.** <!--regle:isolation-du-domaine--> Le domaine reste pur.

## Workflow

- <!--regle:une-branche-par-us--> **Une branche par US**, jamais de travail direct.
"""

ADR_SAIN = """# ADR-0001 — Une décision d'essai

- **Statut** : Accepté
- **Date** : 2026-01-01

## Décision

On tranche ceci.

## Porté dans le code par

- `backend/present.py` — `ChosePresente`
"""

ADR_QUI_PROMET_DU_VENT = ADR_SAIN.replace(
    "- `backend/present.py` — `ChosePresente`",
    "- `backend/disparu.py` — `ChoseDisparue`",
)


def _git(depot: Path, *arguments: str) -> None:
    """Appelle git en neutralisant la configuration **globale** du poste.

    Sans `commit.gpgsign=false`, un poste où la signature est activée globalement fait échouer le
    test (ou attendre une passphrase) ; sans `core.hooksPath=`, les hooks du projet tournent dans
    le dépôt jetable. La règle 9 exige des tests déterministes : l'environnement n'a pas à entrer
    dans l'équation.
    """
    subprocess.run(
        [
            "git",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=",
            "-C",
            str(depot),
            *arguments,
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )


def _poser_depot(racine: Path, *, adr: str = ADR_SAIN) -> None:
    (racine / "docs" / "adr").mkdir(parents=True)
    (racine / "backend").mkdir(parents=True, exist_ok=True)
    (racine / "CLAUDE.md").write_text(CLAUDE, encoding="utf-8", newline="\n")
    (racine / "docs" / "adr" / "0001-essai.md").write_text(adr, encoding="utf-8", newline="\n")
    (racine / "backend" / "present.py").write_text(
        "class ChosePresente:\n    pass\n", encoding="utf-8", newline="\n"
    )


@pytest.fixture
def depot(tmp_path: Path) -> Path:
    _poser_depot(tmp_path)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "essai@exemple.test")
    _git(tmp_path, "config", "user.name", "Essai")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "docs(claude): poser les règles")
    return tmp_path


def test_des_donnees_a_jour_sortent_en_zero(depot: Path) -> None:
    assert principal([], racine=depot) == 0

    assert principal(["--verifier"], racine=depot) == 0


def test_des_donnees_perimees_sortent_en_un(depot: Path) -> None:
    """Le cœur de la porte : une source qui bouge sans régénération doit rougir."""
    principal([], racine=depot)
    (depot / "CLAUDE.md").write_text(
        CLAUDE.replace("Le domaine reste pur.", "Le domaine reste pur et synchrone."),
        encoding="utf-8",
        newline="\n",
    )

    assert principal(["--verifier"], racine=depot) == 1


def test_un_depot_sans_git_sort_en_deux(tmp_path: Path) -> None:
    """Générer sans git écrivait un historique vide en annonçant « atlas généré »."""
    _poser_depot(tmp_path)

    assert principal([], racine=tmp_path) == 2
    assert not (tmp_path / "atlas" / "donnees").exists(), "rien ne doit être écrit"


def test_un_ecart_bloquant_sort_en_trois(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Un ADR qui nomme un module disparu doit faire rougir la porte, pas seulement une page web."""
    _poser_depot(tmp_path, adr=ADR_QUI_PROMET_DU_VENT)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "essai@exemple.test")
    _git(tmp_path, "config", "user.name", "Essai")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "docs(adr): promettre du vent")
    principal([], racine=tmp_path)
    capsys.readouterr()

    code = principal(["--verifier"], racine=tmp_path)

    assert code == 3
    erreur = capsys.readouterr().err
    assert "ADR-0001" in erreur and "backend/disparu.py" in erreur


def test_la_generation_ecrit_meme_avec_un_ecart_bloquant(tmp_path: Path) -> None:
    """C'est `--verifier` qui refuse, pas la génération.

    La page « Écarts constatés » existe précisément pour montrer ces écarts : refuser d'écrire les
    rendrait invisibles, ce qui serait le contraire du but.
    """
    _poser_depot(tmp_path, adr=ADR_QUI_PROMET_DU_VENT)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "essai@exemple.test")
    _git(tmp_path, "config", "user.name", "Essai")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "docs(adr): promettre du vent")

    assert principal([], racine=tmp_path) == 0
    assert (tmp_path / "atlas" / "donnees" / "controles.js").is_file()
