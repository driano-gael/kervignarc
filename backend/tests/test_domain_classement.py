"""Tests unitaires du calcul de classement (E00US011) — fonction de domaine pure."""

from __future__ import annotations

from domain.archer import Archer
from domain.classement import LigneClassement, calculer_classement
from domain.score import Score


def _archer(id_: int, nom: str, cible: int | None = None) -> Archer:
    # `prenom` et `categorie_id` sont sans effet sur le classement (E00US011 classe au nom) ;
    # ils sont obligatoires depuis E02US002, d'où des valeurs fixes qui ne disent rien de plus.
    return Archer(nom=nom, prenom="Jean", tournoi_id=1, categorie_id=1, cible=cible, id=id_)


def test_classement_vide_sans_archer() -> None:
    """Sans archer, le classement est vide."""
    assert calculer_classement([], []) == calculer_classement([], [])
    assert calculer_classement([], []).lignes == ()


def test_ordre_par_total_decroissant() -> None:
    """Les archers sont ordonnés du meilleur total au moins bon, avec les rangs."""
    archers = [_archer(1, "Alice", cible=2), _archer(2, "Bob", cible=2)]
    scores = [Score(1, 9, id=1), Score(1, 10, id=2), Score(2, 8, id=3)]
    classement = calculer_classement(archers, scores)
    assert classement.lignes == (
        LigneClassement(rang=1, archer_id=1, nom="Alice", cible=2, total=19),
        LigneClassement(rang=2, archer_id=2, nom="Bob", cible=2, total=8),
    )


def test_archer_sans_score_a_un_total_nul() -> None:
    """Un archer inscrit mais sans flèche apparaît avec un total de 0."""
    classement = calculer_classement([_archer(5, "Zoé")], [])
    assert classement.lignes == (
        LigneClassement(rang=1, archer_id=5, nom="Zoé", cible=None, total=0),
    )


def test_egalite_de_total_partage_le_rang() -> None:
    """Deux archers à égalité partagent le rang ; départage par nom (déterministe)."""
    archers = [_archer(1, "Bruno"), _archer(2, "Anna"), _archer(3, "Carl")]
    scores = [Score(1, 5, id=1), Score(2, 5, id=2), Score(3, 10, id=3)]
    classement = calculer_classement(archers, scores)
    rangs = [(ligne.nom, ligne.rang, ligne.total) for ligne in classement.lignes]
    assert rangs == [("Carl", 1, 10), ("Anna", 2, 5), ("Bruno", 2, 5)]


def test_scores_d_archers_inconnus_sont_ignores() -> None:
    """Un score dont l'archer n'est pas dans le lot n'affecte pas le classement."""
    classement = calculer_classement([_archer(1, "Alice")], [Score(999, 10, id=1)])
    assert classement.lignes[0].total == 0
