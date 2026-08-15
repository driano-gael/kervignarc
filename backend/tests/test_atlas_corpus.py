"""Garde-fous de l'atlas sur le **dépôt réel**.

C'est ici que se trouve le vrai livrable de l'US : pas le dessin du registre, mais la confrontation
de ce que l'écrit promet à ce que le dépôt contient. Ces tests-là échouent le jour où un ADR nomme
un module supprimé, où une décision renvoie à un ADR inexistant, ou où une règle perd son ancre —
c'est-à-dire le jour où la documentation commence à mentir, et non six mois plus tard.

Ils sont volontairement **complémentaires** de `test_atlas_parseurs.py` : celui-ci décrit ce que
les parseurs savent faire, ceux-là décrivent l'état du dépôt d'aujourd'hui.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from atlas import controles as controles_module
from atlas.modele import Decision, Regle, Severite, TypeLien
from atlas.sources import adr, reglement

RACINE = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def decisions() -> tuple[Decision, ...]:
    return adr.lire_decisions(RACINE)


@pytest.fixture(scope="module")
def regles() -> tuple[Regle, ...]:
    return reglement.lire_regles(RACINE)


def test_tous_les_adr_se_parsent(decisions: tuple[Decision, ...]) -> None:
    """Aucun ADR ne doit résister au lecteur — un ADR muet est un ADR invisible.

    Le simple fait que la fixture se construise prouve déjà qu'aucun libellé de relation n'est
    inconnu, qu'aucun statut n'est illisible et qu'aucune date ne manque : ces trois cas lèvent.
    """
    fichiers = [f for f in (RACINE / "docs" / "adr").iterdir() if adr.FICHIER_ADR.match(f.name)]

    assert len(decisions) == len(fichiers)
    assert all(d.titre and d.date and d.fichier for d in decisions)


def test_toute_relation_vise_un_adr_existant(decisions: tuple[Decision, ...]) -> None:
    connus = {d.identifiant for d in decisions}
    orphelines = [
        (d.identifiant, lien.libelle, lien.cible)
        for d in decisions
        for lien in d.liens
        if lien.type is not TypeLien.US and lien.cible not in connus
    ]

    assert orphelines == []


def test_tout_module_porte_dans_le_code_existe(decisions: tuple[Decision, ...]) -> None:
    """La leçon d'ADR-0075, mécanisée : un ADR qui nomme un module disparu n'est plus tenu."""
    disparus = [
        (d.identifiant, portage.chemin)
        for d in decisions
        for portage in d.portage
        if not portage.existe
    ]

    assert disparus == []


def test_le_controle_de_portage_n_est_pas_creux(decisions: tuple[Decision, ...]) -> None:
    """Un contrôle qui ne vérifie rien passerait au vert sans rien garantir.

    On exige donc qu'il ait réellement de la matière à vérifier : sans ce test, une régression de
    l'extraction (un format de section qui change) rendrait tous les contrôles verts en silence.
    """
    portages = [p for d in decisions for p in d.portage]

    assert len(portages) >= 50
    assert sum(len(p.symboles) for p in portages) >= 100


def test_le_registre_est_bien_un_graphe_date(decisions: tuple[Decision, ...]) -> None:
    """Le statut ne discrimine pas : la péremption réelle vit dans les arêtes d'amendement.

    82 ADR sur 83 sont « Accepté » et un seul est marqué « Remplacé ». Ce qui répond à « cette
    décision tient-elle encore ? », c'est `amende_par` — une information qui ne figure sur aucune
    des deux fiches concernées, et que seul le croisement fait apparaître.
    """
    amendes = [d for d in decisions if d.amende_par]

    connus = {d.identifiant for d in decisions}

    assert amendes, "aucun ADR amendé : le graphe d'amendement ne se construit plus"
    assert all(cible in connus for d in amendes for cible in d.amende_par)


def test_les_regles_sont_toutes_ancrees(regles: tuple[Regle, ...]) -> None:
    """Sans ancre, l'historique d'une règle se détache d'elle au premier réordonnancement."""
    assert len(regles) >= 25
    assert all(r.identifiant and r.titre for r in regles)
    assert len({r.identifiant for r in regles}) == len(regles)


def test_les_quatre_sections_du_reglement_sont_couvertes(regles: tuple[Regle, ...]) -> None:
    assert {r.section for r in regles} == set(reglement.SECTIONS)


def test_toute_regle_citant_un_adr_le_cite_correctement(
    regles: tuple[Regle, ...], decisions: tuple[Decision, ...]
) -> None:
    connus = {d.identifiant for d in decisions}
    fantomes = [(r.identifiant, cite) for r in regles for cite in r.adr if cite not in connus]

    assert fantomes == []


def test_aucun_ecart_bloquant_dans_le_depot(
    regles: tuple[Regle, ...], decisions: tuple[Decision, ...]
) -> None:
    """La porte proprement dite : le dépôt ne doit porter aucun écart de sévérité bloquante.

    Les **signaux** (symbole introuvable, date hors format canonique) ne sont volontairement pas
    couverts ici : ils reposent sur de l'heuristique ou sur un choix de forme, et faire rougir la
    CI dessus reviendrait à la faire désactiver — on perdrait alors aussi les contrôles justes.
    """
    bloquants = controles_module.bloquants(controles_module.verifier(RACINE, regles, decisions))

    assert [f"{c.sujet} {c.message}" for c in bloquants] == []


def test_les_signaux_restent_visibles(
    regles: tuple[Regle, ...], decisions: tuple[Decision, ...]
) -> None:
    """Non bloquants, mais jamais silencieux : leur disparition serait une régression."""
    verdicts = controles_module.verifier(RACINE, regles, decisions)

    assert any(c.severite is Severite.SIGNAL for c in verdicts)
