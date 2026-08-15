"""L'historique d'une règle, éprouvé sur un dépôt git jetable.

`git log -L` est le seul mécanisme de l'US qui **suit un bloc qui bouge** — c'est toute la raison
de l'avoir choisi plutôt qu'un `git log` sur le fichier. Ce n'était prouvé nulle part : le module
n'était traversé qu'incidemment par le test de déterminisme, qui n'assert rien sur son contenu.

Or `_git` **avale tout** (`return ""` sur exception comme sur code retour non nul) : une invocation
qui casserait sur une autre version de git ne produirait aucun message. C'est un chemin de panne
muet, donc exactement celui qu'un test doit garder.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from atlas.modele import Regle
from atlas.sources import historique


def _git(depot: Path, *arguments: str) -> None:
    subprocess.run(["git", "-C", str(depot), *arguments], check=True, capture_output=True)


def _regle(ligne: int, ligne_fin: int) -> Regle:
    return Regle(
        identifiant="essai",
        section="Règles non négociables",
        rang=1,
        titre="Essai",
        corps="",
        fichier="CLAUDE.md",
        ligne=ligne,
        ligne_fin=ligne_fin,
        amendements=(),
        adr=(),
        us=(),
    )


@pytest.fixture
def depot(tmp_path: Path) -> Path:
    """Quatre commits, dont un qui **déplace** le bloc sans le modifier.

    C'est le scénario qui prouve la propriété recherchée : après le déplacement, l'historique doit
    encore contenir les commits **antérieurs** au déplacement. Un `git log` sur le fichier les
    donnerait aussi ; ce que `-L` apporte, c'est de ne **pas** donner les commits qui n'ont pas
    touché ce bloc-là.
    """
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "essai@exemple.test")
    _git(tmp_path, "config", "user.name", "Essai")

    fichier = tmp_path / "CLAUDE.md"

    def commit(contenu: str, sujet: str) -> None:
        fichier.write_text(contenu, encoding="utf-8", newline="\n")
        _git(tmp_path, "add", "CLAUDE.md")
        _git(tmp_path, "commit", "-q", "-m", sujet)

    commit("# Titre\n\nrègle : version un\nautre : intacte\n", "docs(claude): poser la règle")
    commit(
        "# Titre\n\nrègle : version deux\nautre : intacte\n",
        "feat(e01us001): resserrer la règle",
    )
    # Le bloc descend de deux lignes sans changer de contenu.
    commit(
        "# Titre\n\n## Préambule ajouté\n\nrègle : version deux\nautre : intacte\n",
        "docs(claude): ajouter un préambule",
    )
    commit(
        "# Titre\n\n## Préambule ajouté\n\nrègle : version trois\nautre : intacte\n",
        "fix(e01us002): corriger la règle",
    )
    # Un commit qui ne touche **pas** le bloc suivi : il ne doit pas apparaître.
    commit(
        "# Titre\n\n## Préambule ajouté\n\nrègle : version trois\nautre : modifiée\n",
        "chore: toucher une autre ligne",
    )
    return tmp_path


def test_git_indisponible_ne_fait_pas_echouer(tmp_path: Path) -> None:
    """L'atlas doit rester générable hors dépôt — la dégradation est silencieuse et voulue."""
    assert historique.disponible(tmp_path) is False
    assert historique.historique(tmp_path, (_regle(1, 3),)) == {}


def test_l_historique_traverse_un_deplacement_du_bloc(depot: Path) -> None:
    """La règle est en ligne 5 aujourd'hui ; elle était en ligne 3 avant le préambule.

    Les trois commits qui l'ont **modifiée** doivent être retrouvés, y compris ceux d'avant le
    déplacement — c'est la propriété pour laquelle `-L` a été choisi.
    """
    entrees = historique.historique(depot, (_regle(5, 5),))["essai"]

    assert [e.motif for e in entrees] == [
        "fix(e01us002): corriger la règle",
        "feat(e01us001): resserrer la règle",
        "docs(claude): poser la règle",
    ]


def test_un_commit_qui_ne_touche_pas_le_bloc_n_y_apparait_pas(depot: Path) -> None:
    """Sans cela `git log` sur le fichier suffirait, et chaque règle porterait toute l'histoire."""
    motifs = [e.motif for e in historique.historique(depot, (_regle(5, 5),))["essai"]]

    assert "chore: toucher une autre ligne" not in motifs
    assert "docs(claude): ajouter un préambule" not in motifs


def test_l_us_se_lit_dans_le_sujet_du_commit(depot: Path) -> None:
    """Le lien règle → US se déduit du scope conventionnel, sans heuristique."""
    par_motif = {e.motif: e for e in historique.historique(depot, (_regle(5, 5),))["essai"]}

    assert par_motif["feat(e01us001): resserrer la règle"].us == ("E01US001",)
    assert par_motif["docs(claude): poser la règle"].us == ()


def test_chaque_entree_porte_une_empreinte_et_une_date(depot: Path) -> None:
    """L'empreinte est la clé de la comparaison par tolérance d'ajout (`rendu.ecarts`)."""
    entrees = historique.historique(depot, (_regle(5, 5),))["essai"]

    assert all(len(e.reference) == 10 for e in entrees)
    assert len({e.reference for e in entrees}) == len(entrees)
    assert all(e.date.count("-") == 2 for e in entrees)
    assert all(e.origine == "git" for e in entrees)


def test_une_borne_de_depart_hors_fichier_degrade_sans_bruit(depot: Path) -> None:
    """Le vrai cas limite, mesuré plutôt que supposé.

    Une borne de **fin** trop grande est tolérée par git, qui la ramène à la taille du fichier —
    contrairement à ce qu'on pourrait craindre de l'élément vide que `split("\\n")` ajoute. C'est
    une borne de **départ** au-delà de la fin qui fait sortir git en erreur (`fatal: file has only
    N lines`), erreur que `_git` avale. La dégradation est voulue ; ce test la fige, pour qu'on ne
    croie pas le cas impossible.
    """
    assert historique.historique(depot, (_regle(1, 99),))["essai"] != ()
    assert historique.historique(depot, (_regle(99, 99),))["essai"] == ()
