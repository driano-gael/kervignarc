"""Tests unitaires de l'agrégat Tournoi (E00US009, E01US001, E01US002) — domaine pur.

Le tarif n'est plus porté par le tournoi (E02US004, ADR-0017) : il vit sur chaque `Depart` — voir
`test_domain_depart.py`.
"""

from __future__ import annotations

import datetime

import pytest

from domain.erreurs import NomTournoiInvalide
from domain.tournoi import StatutTournoi, Tournoi, TypeTournoi, transitions_possibles

_DATE = datetime.date(2026, 3, 14)


def test_creer_un_tournoi_valide() -> None:
    """Nom + date suffisent : lieu à None, type non officiel, statut brouillon, id à None."""
    tournoi = Tournoi.creer("Salle 18m", _DATE)
    assert tournoi == Tournoi(
        nom="Salle 18m",
        date=_DATE,
        lieu=None,
        type_tournoi=TypeTournoi.NON_OFFICIEL,
        statut=StatutTournoi.BROUILLON,
        id=None,
    )


def test_creer_avec_lieu_et_type() -> None:
    """Lieu et type explicites sont conservés."""
    tournoi = Tournoi.creer("Trophée", _DATE, "Quimper", TypeTournoi.OFFICIEL)
    assert tournoi.lieu == "Quimper"
    assert tournoi.type_tournoi is TypeTournoi.OFFICIEL


def test_creer_normalise_nom_et_lieu() -> None:
    """Le nom et le lieu sont normalisés (espaces de bord retirés)."""
    tournoi = Tournoi.creer("  Trophée  ", _DATE, "  Quimper  ")
    assert tournoi.nom == "Trophée"
    assert tournoi.lieu == "Quimper"


def test_creer_lieu_vide_devient_none() -> None:
    """Un lieu vide ou blanc est facultatif → normalisé à None."""
    assert Tournoi.creer("Trophée", _DATE, "   ").lieu is None


@pytest.mark.parametrize("nom", ["", "   ", "\t\n"])
def test_creer_refuse_un_nom_vide(nom: str) -> None:
    """Un nom vide ou blanc lève une erreur de domaine typée."""
    with pytest.raises(NomTournoiInvalide):
        Tournoi.creer(nom, _DATE)


# --- Édition des métadonnées (E01US002) ---


def test_modifier_met_a_jour_et_preserve_id_et_statut() -> None:
    """`modifier` change nom/date/lieu/type mais conserve `id` et `statut`."""
    tournoi = Tournoi(
        nom="Ancien",
        date=_DATE,
        lieu=None,
        type_tournoi=TypeTournoi.NON_OFFICIEL,
        statut=StatutTournoi.EN_COURS,
        id=7,
    )
    modifie = tournoi.modifier("Nouveau", _DATE, "Quimper", TypeTournoi.OFFICIEL)
    assert modifie == Tournoi(
        nom="Nouveau",
        date=_DATE,
        lieu="Quimper",
        type_tournoi=TypeTournoi.OFFICIEL,
        statut=StatutTournoi.EN_COURS,
        id=7,
    )


def test_modifier_normalise_et_valide_le_nom() -> None:
    """`modifier` applique les mêmes règles que `creer` (normalisation, nom non vide)."""
    tournoi = Tournoi.creer("Trophée", _DATE)
    assert tournoi.modifier("  Renommé  ", _DATE, "  ").nom == "Renommé"
    with pytest.raises(NomTournoiInvalide):
        tournoi.modifier("   ", _DATE)


# --- Cycle de vie (E01US002) : les transitions renvoient une copie ---


def test_demarrer_passe_en_cours() -> None:
    """`demarrer` renvoie une copie au statut `en_cours` (le reste inchangé)."""
    tournoi = Tournoi.creer("Trophée", _DATE)
    demarre = tournoi.demarrer()
    assert demarre.statut is StatutTournoi.EN_COURS
    assert demarre.nom == tournoi.nom


def test_terminer_passe_termine() -> None:
    """`terminer` renvoie une copie au statut `termine`."""
    tournoi = Tournoi.creer("Trophée", _DATE).vers_pret().demarrer()
    assert tournoi.terminer().statut is StatutTournoi.TERMINE


# --- Cycle de vie enrichi (E01US017, ADR-0026 §4) : transitions pures ---
# Chaque transition ne fait que porter la nouvelle valeur (l'enchaînement légal et les gardes
# vivent dans le service — ADR-0007/0026 §4). On vérifie ici la cible de chaque arête du graphe.


def test_vers_pret_passe_pret_et_preserve_le_reste() -> None:
    """`vers_pret` renvoie une copie au statut `prêt`, le reste inchangé (immuabilité)."""
    tournoi = Tournoi.creer("Trophée", _DATE, "Quimper", TypeTournoi.OFFICIEL)
    pret = tournoi.vers_pret()
    assert pret.statut is StatutTournoi.PRET
    assert (pret.nom, pret.date, pret.lieu, pret.type_tournoi) == (
        tournoi.nom,
        tournoi.date,
        tournoi.lieu,
        tournoi.type_tournoi,
    )
    assert tournoi.statut is StatutTournoi.BROUILLON  # l'original n'est pas muté


def test_revenir_brouillon_repasse_brouillon() -> None:
    """`revenir_brouillon` rétrograde un `prêt` en `brouillon`."""
    pret = Tournoi.creer("Trophée", _DATE).vers_pret()
    assert pret.revenir_brouillon().statut is StatutTournoi.BROUILLON


def test_demarrer_passe_de_pret_a_en_cours() -> None:
    """`demarrer` renvoie une copie `en_cours` (depuis `prêt` — ADR-0026)."""
    pret = Tournoi.creer("Trophée", _DATE).vers_pret()
    assert pret.demarrer().statut is StatutTournoi.EN_COURS


def test_mettre_en_pause_puis_reprendre() -> None:
    """`mettre_en_pause` gèle en `en_pause` ; `reprendre` revient à `en_cours` (réversible)."""
    en_cours = Tournoi.creer("Trophée", _DATE).vers_pret().demarrer()
    en_pause = en_cours.mettre_en_pause()
    assert en_pause.statut is StatutTournoi.EN_PAUSE
    assert en_pause.reprendre().statut is StatutTournoi.EN_COURS


def test_archiver_passe_archive() -> None:
    """`archiver` verrouille un `terminé` en `archivé`."""
    termine = Tournoi.creer("Trophée", _DATE).vers_pret().demarrer().terminer()
    assert termine.archiver().statut is StatutTournoi.ARCHIVE


def test_annuler_passe_annule() -> None:
    """`annuler` renvoie une copie au statut terminal `annulé` (conserve la trace)."""
    tournoi = Tournoi.creer("Trophée", _DATE)
    assert tournoi.annuler().statut is StatutTournoi.ANNULE


# --- Topologie du cycle de vie (E14US001, ADR-0026 §2) : transitions offertes par statut ---
# Source unique de lecture pour l'accueil admin (frise à boutons, E14US001). Dérivé du **CA**
# (ADR-0026 §2, le graphe d'états), PAS du code du service : `transitions_possibles(statut)` doit
# rendre exactement les arêtes du graphe pour que la frise propose les bonnes actions. La *garde*
# de chaque arête reste dans le service (ADR-0026 §4) et est recoupée par le test de cohérence de
# `test_service_tournois.py` (topologie ↔ légalité effective).


def _noms_transitions(statut: StatutTournoi) -> set[str]:
    """Noms d'action offerts depuis `statut` (alignés sur les suffixes d'endpoint)."""
    return {transition.nom for transition in transitions_possibles(statut)}


def test_transitions_offertes_par_statut() -> None:
    """Chaque statut offre exactement les arêtes d'ADR-0026 §2 (par nom d'action)."""
    assert _noms_transitions(StatutTournoi.BROUILLON) == {"vers-pret", "annuler"}
    assert _noms_transitions(StatutTournoi.PRET) == {"demarrer", "revenir-brouillon", "annuler"}
    assert _noms_transitions(StatutTournoi.EN_COURS) == {"mettre-en-pause", "terminer", "annuler"}
    assert _noms_transitions(StatutTournoi.EN_PAUSE) == {"reprendre", "annuler"}
    assert _noms_transitions(StatutTournoi.TERMINE) == {"archiver"}


def test_statuts_terminaux_n_offrent_aucune_transition() -> None:
    """`archivé` et `annulé` sont terminaux : aucune transition sortante (ADR-0026 §2)."""
    assert transitions_possibles(StatutTournoi.ARCHIVE) == ()
    assert transitions_possibles(StatutTournoi.ANNULE) == ()


def test_chaque_transition_porte_libelle_et_cible() -> None:
    """Une transition offerte porte un libellé non vide et le statut cible attendu (feu vert)."""
    par_nom = {t.nom: t for t in transitions_possibles(StatutTournoi.PRET)}
    assert par_nom["demarrer"].vers is StatutTournoi.EN_COURS
    assert par_nom["revenir-brouillon"].vers is StatutTournoi.BROUILLON
    assert par_nom["annuler"].vers is StatutTournoi.ANNULE
    assert all(t.libelle.strip() for t in transitions_possibles(StatutTournoi.EN_COURS))
