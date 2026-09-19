"""Garde-fou du classement des modules de test en familles (ADR-0110)."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from porte import PYTEST_RAPIDE, _selection
from tests.conftest import (
    FAMILLE_PAR_DEFAUT,
    FAMILLES_DE_TESTS,
    famille_du_module,
)

RACINE = Path(__file__).parent

# Liste **gelée** au 19/09/2026 : les modules qui ne suivent aucune convention de nommage.
# ⚠️ Un module neuf hors convention fait échouer `test_aucun_nouveau_module_hors_convention`.
# C'est voulu : on le renomme (`test_service_x`, `test_x_api`…) pour qu'il rejoigne une
# famille, ou on l'inscrit ici sciemment. Le silence, lui, priverait la porte rapide d'un
# test sans que personne ne s'en aperçoive.
MODULES_SANS_FAMILLE: frozenset[str] = frozenset(
    {
        "test_acces_public",
        "test_admin_credentials_store",
        "test_agents_de_revue",
        "test_broadcaster",
        "test_catalogue_types_de_phase",
        "test_commentaires_bornes",
        "test_conformite_ports_memoire",
        "test_db_connexion",
        "test_documents_salle_reportlab",
        "test_familles_de_tests",
        "test_feuille_de_marque_reportlab",
        "test_health",
        "test_horloge",
        "test_idempotence",
        "test_listes_impression_csv",
        "test_listes_impression_reportlab",
        "test_pdf_palmares",
        "test_porte_couvre_la_ci",
        "test_portee_deux_creneaux",
        "test_portee_sportive",
        "test_prelevement_phase_source",
        "test_preseance_de_role",
        "test_profondeur_par_phase",
        "test_realtime_ws",
        "test_referentiel_ffta",
        "test_release_chemins",
        "test_release_migrate",
        "test_release_reseau",
        "test_release_run",
        "test_sauvegarde",
        "test_simulation_non_pollution",
        "test_spa",
        "test_tableur_grille",
        "test_tableur_palmares",
        "test_write_queue",
    }
)


def _tiges_des_modules() -> set[str]:
    return {chemin.stem for chemin in RACINE.rglob("test_*.py")}


def test_les_familles_sont_disjointes() -> None:
    chevauchements = {
        tige: [nom for nom, motif in FAMILLES_DE_TESTS if re.search(motif, tige)]
        for tige in _tiges_des_modules()
    }
    multiples = {tige: noms for tige, noms in chevauchements.items() if len(noms) > 1}
    assert not multiples, f"Ces modules relèvent de plusieurs familles : {multiples}"


def test_aucun_nouveau_module_hors_convention() -> None:
    hors_convention = {
        tige for tige in _tiges_des_modules() if famille_du_module(tige) == FAMILLE_PAR_DEFAUT
    }
    nouveaux = hors_convention - MODULES_SANS_FAMILLE
    assert not nouveaux, (
        f"Modules hors convention de nommage : {sorted(nouveaux)}. Renommez-les pour "
        "qu'ils rejoignent une famille, ou inscrivez-les sciemment dans MODULES_SANS_FAMILLE."
    )


def test_le_gel_ne_cite_que_des_modules_encore_hors_convention() -> None:
    tiges = _tiges_des_modules()
    disparus = MODULES_SANS_FAMILLE - tiges
    reclasses = {
        tige
        for tige in MODULES_SANS_FAMILLE & tiges
        if famille_du_module(tige) != FAMILLE_PAR_DEFAUT
    }
    assert not disparus, f"MODULES_SANS_FAMILLE cite des modules absents : {sorted(disparus)}"
    assert (
        not reclasses
    ), f"Ces modules ont rejoint une famille et doivent sortir du gel : {sorted(reclasses)}"


def _familles_connues() -> set[str]:
    return {nom for nom, _ in FAMILLES_DE_TESTS} | {FAMILLE_PAR_DEFAUT}


def test_les_marqueurs_declares_sont_exactement_les_familles() -> None:
    """Deux copies indépendantes : `conftest.py` pose les familles, `pyproject.toml` les déclare.

    ⚠️ Renommer une famille d'un seul côté laisse tout vert et vide l'étage rapide de sa
    sélection — `--strict-markers` ne rattrape que le marqueur **posé**, jamais l'expression `-m`.
    """
    config = tomllib.loads((RACINE.parent / "pyproject.toml").read_text(encoding="utf-8"))
    declares = {
        ligne.split(":", 1)[0].strip()
        for ligne in config["tool"]["pytest"]["ini_options"]["markers"]
    }
    assert declares == _familles_connues(), (
        f"déclarés dans pyproject.toml : {sorted(declares)} ; "
        f"posés par conftest.py : {sorted(_familles_connues())}"
    )


def test_l_etage_rapide_ne_selectionne_que_des_familles_existantes() -> None:
    """Le vrai trou que `--strict-markers` ne ferme pas : une faute dans l'expression `-m`.

    ⚠️ `-m "domaine or servce"` sélectionne les tests `domaine`, sort **0**, et la porte rapide
    se déclare verte avec 40 % des tests en moins. Mesuré : `--strict-markers` ne valide pas
    l'expression, seul un `-m` qui ne sélectionne **rien** est rattrapé (code de sortie 5).
    """
    # ⚠️ Le **dernier** `-m` : le premier est celui de `python -m pytest`.
    jetons = list(PYTEST_RAPIDE.commande)
    expression = jetons[len(jetons) - jetons[::-1].index("-m")]
    nommees = {mot for mot in re.findall(r"[a-z_]+", expression) if mot not in {"or", "and", "not"}}
    inconnues = nommees - _familles_connues()
    assert (
        not inconnues
    ), f"L'étage rapide sélectionne des familles qui n'existent pas : {inconnues}"


def test_l_etage_rapide_joue_bien_des_tests() -> None:
    """Sans ce test, retirer `PYTEST_RAPIDE` de la sélection rend `--rapide` vert sans un test."""
    assert PYTEST_RAPIDE in _selection(rapide=True)["backend"]
