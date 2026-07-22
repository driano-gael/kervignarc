"""Détection de doublons d'archers (E02US005) — tests **du domaine**, dérivés du CA.

Écrits **depuis le CA** (`stories/E02-inscriptions.md`, E02US005) avant l'implémentation (règle 9) :
ils spécifient les deux niveaux de rapprochement (doublon **probable** vs **à vérifier**) et le
déterminisme de la liste, sur des agrégats `Archer` purs — ni base, ni service.
"""

from __future__ import annotations

import pytest

from domain.archer import Archer
from domain.doublons import (
    NiveauDoublon,
    detecter_doublons,
    distance_edition,
)

_TOURNOI = 1
_CATEGORIE = 1


def _archer(archer_id: int, nom: str, prenom: str, club_id: int | None = None) -> Archer:
    """Un archer persisté prêt pour la détection (seuls nom, prénom, club et id comptent ici)."""
    return Archer(
        nom=nom,
        prenom=prenom,
        tournoi_id=_TOURNOI,
        categorie_id=_CATEGORIE,
        club_id=club_id,
        id=archer_id,
    )


# --- Doublon probable ---------------------------------------------------------------------------


def test_memes_nom_prenom_club_est_un_doublon_probable() -> None:
    """Mêmes nom, prénom et club : le doublon le plus net (CA « doublon probable »)."""
    paires = detecter_doublons([_archer(1, "Dupont", "Jean", 7), _archer(2, "Dupont", "Jean", 7)])
    assert [p.niveau for p in paires] == [NiveauDoublon.PROBABLE]
    assert (paires[0].a.id, paires[0].b.id) == (1, 2)


def test_casse_et_accents_replies_pour_le_doublon_probable() -> None:
    """« LEFEVRE remi » et « Lefèvre Rémi » sont le même (repli casse/accents, `cle_nom`)."""
    paires = detecter_doublons([_archer(1, "Lefèvre", "Rémi"), _archer(2, "  LEFEVRE ", "remi")])
    assert [p.niveau for p in paires] == [NiveauDoublon.PROBABLE]


def test_pont_avec_club_et_sans_club_est_un_doublon_probable() -> None:
    """Une fiche sans club et une fiche rattachée, mêmes nom/prénom : le **pont** de E02US005.

    C'est le cas que la détection à l'inscription **exclut** (`cle_identite` renvoie ici) : `None`
    = « club inconnu », donc l'archer sans club **peut** être le même que le rattaché.
    """
    paires = detecter_doublons(
        [_archer(1, "Dupont", "Jean", None), _archer(2, "Dupont", "Jean", 7)]
    )
    assert [p.niveau for p in paires] == [NiveauDoublon.PROBABLE]


def test_deux_fiches_sans_club_memes_noms_est_un_doublon_probable() -> None:
    """Deux « Dupont Jean » sans club : clubs compatibles (les deux `None`) → probable."""
    paires = detecter_doublons(
        [_archer(1, "Dupont", "Jean", None), _archer(2, "Dupont", "Jean", None)]
    )
    assert [p.niveau for p in paires] == [NiveauDoublon.PROBABLE]


# --- À vérifier (rapprochement approximatif) ----------------------------------------------------


def test_memes_noms_mais_clubs_differents_est_a_verifier() -> None:
    """Mêmes nom et prénom, **clubs connus différents** : à vérifier, pas un doublon probable.

    Les clubs départagent (comme à l'inscription), mais l'identité est trop proche pour l'ignorer :
    ce peut être un club mal saisi. L'admin confirme.
    """
    paires = detecter_doublons([_archer(1, "Dupont", "Jean", 7), _archer(2, "Dupont", "Jean", 9)])
    assert [p.niveau for p in paires] == [NiveauDoublon.A_VERIFIER]


def test_faute_de_frappe_sur_le_nom_est_a_verifier() -> None:
    """Une lettre fausse dans le nom (« Robain » / « Robin »), même prénom → à vérifier."""
    paires = detecter_doublons([_archer(1, "Robain", "Jean", 7), _archer(2, "Robin", "Jean", 7)])
    assert [p.niveau for p in paires] == [NiveauDoublon.A_VERIFIER]


def test_prenom_abrege_est_a_verifier() -> None:
    """Un prénom abrégé (« J » / « Jean ») sur un même nom → à vérifier (CA)."""
    paires = detecter_doublons([_archer(1, "Dupont", "J", 7), _archer(2, "Dupont", "Jean", 7)])
    assert [p.niveau for p in paires] == [NiveauDoublon.A_VERIFIER]


def test_deux_fautes_reparties_restent_dans_le_seuil() -> None:
    """Une faute dans le nom **et** une dans le prénom (distance cumulée 2) → à vérifier."""
    paires = detecter_doublons([_archer(1, "Robain", "Jeanne", 7), _archer(2, "Robin", "Jeane", 7)])
    assert [p.niveau for p in paires] == [NiveauDoublon.A_VERIFIER]


# --- Aucun rapprochement ------------------------------------------------------------------------


def test_deux_archers_differents_ne_sont_pas_rapproches() -> None:
    """Des noms sans ressemblance ne produisent aucune paire."""
    assert detecter_doublons([_archer(1, "Dupont", "Jean"), _archer(2, "Martin", "Alice")]) == []


def test_distance_trop_grande_n_est_pas_rapprochee() -> None:
    """Au-delà du seuil (ici 3 substitutions), les fiches ne sont pas rapprochées."""
    assert detecter_doublons([_archer(1, "Dupont", "Jean"), _archer(2, "Duravd", "Jean")]) == []


def test_un_archer_seul_ne_se_rapproche_pas_de_lui_meme() -> None:
    """Aucune paire à partir d'un seul inscrit (pas de rapprochement réflexif)."""
    assert detecter_doublons([_archer(1, "Dupont", "Jean", 7)]) == []


# --- Structure de la liste ----------------------------------------------------------------------


def test_chaque_paire_apparait_une_seule_fois() -> None:
    """Trois fiches identiques donnent 3 paires (1-2, 1-3, 2-3), pas 6 : paires non orientées."""
    paires = detecter_doublons(
        [
            _archer(1, "Dupont", "Jean", 7),
            _archer(2, "Dupont", "Jean", 7),
            _archer(3, "Dupont", "Jean", 7),
        ]
    )
    couples = [(p.a.id, p.b.id) for p in paires]
    assert couples == [(1, 2), (1, 3), (2, 3)]


def test_les_doublons_probables_precedent_les_a_verifier() -> None:
    """Le tri met les **probables** avant les **à vérifier** : le plus sûr d'abord."""
    paires = detecter_doublons(
        [
            _archer(1, "Dupont", "Jean", 7),
            _archer(2, "Dupont", "Jean", 7),  # probable avec 1
            _archer(3, "Dupond", "Jean", 7),  # à vérifier (faute de frappe) avec 1 et 2
        ]
    )
    niveaux = [p.niveau for p in paires]
    assert niveaux[0] is NiveauDoublon.PROBABLE
    assert all(n is NiveauDoublon.A_VERIFIER for n in niveaux[1:])


def test_la_paire_est_ordonnee_par_identifiant_croissant() -> None:
    """Quel que soit l'ordre d'entrée, `a.id < b.id` dans chaque paire (déterminisme)."""
    paires = detecter_doublons([_archer(5, "Dupont", "Jean", 7), _archer(2, "Dupont", "Jean", 7)])
    assert (paires[0].a.id, paires[0].b.id) == (2, 5)


# --- Distance d'édition (brique) ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("a", "b", "attendu"),
    [
        ("robin", "robin", 0),
        ("robin", "robain", 1),  # une insertion
        ("robin", "ropin", 1),  # une substitution
        ("", "jean", 4),  # tout à insérer
        ("jean", "", 4),  # tout à supprimer
        ("chat", "chien", 3),
    ],
)
def test_distance_edition(a: str, b: str, attendu: int) -> None:
    """La distance de Levenshtein maison donne les valeurs de référence (symétrique)."""
    assert distance_edition(a, b) == attendu
    assert distance_edition(b, a) == attendu
