"""Garde-fou du classement des modules de test en familles (ADR-0110)."""

from __future__ import annotations

import re
from pathlib import Path

from tests.conftest import FAMILLE_PAR_DEFAUT, FAMILLES_DE_TESTS, famille_du_module

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
    return {chemin.stem for chemin in RACINE.glob("test_*.py")}


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
