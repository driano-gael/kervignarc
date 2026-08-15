"""Garde-fous du site statique — ce qui le casserait en silence.

Le site n'a ni build, ni typage, ni test de rendu (DETTE assumée). Ces vérifications couvrent les
trois fautes qui ne se voient **pas** en développement et cassent l'usage réel :

1. un `fetch()` ou un module ES : parfaitement fonctionnel en `localhost`, **mort** au double-clic
   en `file://`, qui est le mode d'usage demandé ;
2. une ressource externe : le projet se déploie le jour J **sans internet** ;
3. l'absence de `viewport` : la page s'affiche alors en 980 px virtuels sur téléphone, et tout le
   travail responsive est annulé d'une ligne manquante.

Elles ne remplacent pas un coup d'œil humain sur le rendu — rien ici ne dit qu'une page est
*jolie* ni qu'elle est lisible à 360 px. Elles disent qu'elle **fonctionne**.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parents[2] / "atlas"
PAGES = sorted(SITE.glob("*.html"))
SCRIPTS = sorted((SITE / "statique").glob("*.js"))


def _lire(chemin: Path) -> str:
    return chemin.read_text(encoding="utf-8")


def test_le_site_a_bien_ses_pages() -> None:
    assert {page.name for page in PAGES} >= {
        "index.html",
        "regle.html",
        "decisions.html",
        "adr.html",
        "errata.html",
        "controles.html",
        "recherche.html",
    }


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_aucune_page_ne_depend_d_un_module_es(page: Path) -> None:
    """`<script type="module">` est soumis au CORS : bloqué sur `file://`."""
    assert 'type="module"' not in _lire(page)


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_aucun_script_ne_recupere_ses_donnees_par_le_reseau(script: Path) -> None:
    """`fetch()` sur `file://` est bloqué par la politique d'origine — d'où les données en `.js`."""
    source = _lire(script)

    assert "fetch(" not in source
    assert "XMLHttpRequest" not in source
    assert not re.search(r"^\s*(import|export)\s", source, re.MULTILINE)


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_aucune_page_ne_charge_de_ressource_externe(page: Path) -> None:
    """Déploiement hors ligne le jour J : aucun CDN, aucune police distante."""
    source = _lire(page)

    assert not re.search(r'(src|href)\s*=\s*"(https?:)?//', source)


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_chaque_page_declare_son_viewport(page: Path) -> None:
    """Sans cette balise, un téléphone rend la page en 980 px virtuels et le responsive tombe."""
    assert 'name="viewport"' in _lire(page)


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_chaque_page_est_branchee_sur_la_coquille(page: Path) -> None:
    source = _lire(page)

    assert "statique/coquille.js" in source
    assert "statique/pages.js" in source
    assert "Atlas.demarrer(" in source


def test_les_donnees_chargees_par_une_page_existent() -> None:
    """Un `<script src>` vers une donnée absente casse la page sans message lisible."""
    manquants = [
        (page.name, cible)
        for page in PAGES
        for cible in re.findall(r'<script src="(donnees/[^"]+)"', _lire(page))
        if not (SITE / cible).is_file()
    ]

    assert manquants == []


def test_tout_tableau_vit_dans_un_conteneur_defilant() -> None:
    """La faute de mise en page la plus fréquente, et la seule qui casse vraiment sur téléphone."""
    source = _lire(SITE / "statique" / "pages.js")

    assert source.count("<table>") <= source.count('"defilable"')


def test_la_feuille_de_style_tient_ses_deux_points_de_rupture() -> None:
    """Deux points de rupture, pas un de plus : une seule dimension de variation à vérifier."""
    ruptures = re.findall(
        r"@media \(min-width: ([\d.]+rem)\)", _lire(SITE / "statique" / "atlas.css")
    )

    assert set(ruptures) == {"48rem", "80rem"}
