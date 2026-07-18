"""Tests unitaires du calcul de classement (E00US011) — fonction de domaine pure."""

from __future__ import annotations

from domain.archer import Archer
from domain.classement import LigneClassement, calculer_classement
from domain.score import Score


def _archer(
    id_: int,
    nom: str,
    cible: int | None = None,
    prenom: str = "Jean",
    club_id: int | None = 1,
) -> Archer:
    # `categorie_id` est sans effet sur le classement (E00US011 ordonne au total puis au nom) ;
    # obligatoire depuis E02US002, d'où une valeur fixe qui ne dit rien de plus. `prenom` et
    # `club_id`, eux, sont **restitués** par le classement — cf. les deux tests dédiés.
    return Archer(
        nom=nom, prenom=prenom, tournoi_id=1, categorie_id=1, cible=cible, club_id=club_id, id=id_
    )


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
        LigneClassement(
            rang=1, archer_id=1, nom="Alice", prenom="Jean", cible=2, club_id=1, total=19
        ),
        LigneClassement(rang=2, archer_id=2, nom="Bob", prenom="Jean", cible=2, club_id=1, total=8),
    )


def test_archer_sans_score_a_un_total_nul() -> None:
    """Un archer inscrit mais sans flèche apparaît avec un total de 0."""
    classement = calculer_classement([_archer(5, "Zoé")], [])
    assert classement.lignes == (
        LigneClassement(
            rang=1, archer_id=5, nom="Zoé", prenom="Jean", cible=None, club_id=1, total=0
        ),
    )


def test_le_classement_restitue_le_prenom() -> None:
    """Deux homonymes confirmés (E02US002) doivent rester distinguables : le prénom remonte."""
    archers = [_archer(1, "Dupont", prenom="Jean"), _archer(2, "Dupont", prenom="Pierre")]
    prenoms = {ligne.archer_id: ligne.prenom for ligne in calculer_classement(archers, []).lignes}
    assert prenoms == {1: "Jean", 2: "Pierre"}


def test_le_classement_signale_un_club_inconnu() -> None:
    """`club_id` remonte tel quel : c'est le classement qui **signale** l'anomalie (ADR-0014).

    Sans ce report, un archer inscrit sans club serait invisible — et « on complétera plus tard »
    n'aurait aucun support à l'écran.
    """
    archers = [_archer(1, "Martin", club_id=None), _archer(2, "Durand", club_id=7)]
    clubs = {ligne.archer_id: ligne.club_id for ligne in calculer_classement(archers, []).lignes}
    assert clubs == {1: None, 2: 7}


def test_egalite_de_total_partage_le_rang() -> None:
    """Deux archers à égalité partagent le rang ; départage par nom (déterministe)."""
    archers = [_archer(1, "Bruno"), _archer(2, "Anna"), _archer(3, "Carl")]
    scores = [Score(1, 5, id=1), Score(2, 5, id=2), Score(3, 10, id=3)]
    classement = calculer_classement(archers, scores)
    rangs = [(ligne.nom, ligne.rang, ligne.total) for ligne in classement.lignes]
    assert rangs == [("Carl", 1, 10), ("Anna", 2, 5), ("Bruno", 2, 5)]


def test_deux_homonymes_a_total_egal_sont_ordonnes_de_facon_stable() -> None:
    """Deux homonymes (E02US002) à total égal ont un ordre **déterministe**, quel que soit
    l'ordre d'entrée.

    Sans départage au-delà du nom, l'ordre retombait sur celui de `par_tournoi` (un `SELECT`
    sans `ORDER BY`) : les deux lignes permutaient d'une lecture à l'autre, sur l'écran même où
    on doit les distinguer. Le rang reste partagé (même total) ; c'est **l'ordre des lignes** qui
    doit être stable. On le prouve en inversant l'ordre d'entrée : le classement doit rendre la
    même séquence d'`archer_id`.
    """
    pere = _archer(1, "Dupont", prenom="Jean")
    fils = _archer(2, "Dupont", prenom="Jean")
    scores = [Score(1, 5, id=1), Score(2, 5, id=2)]
    ordre_a = [ligne.archer_id for ligne in calculer_classement([pere, fils], scores).lignes]
    ordre_b = [ligne.archer_id for ligne in calculer_classement([fils, pere], scores).lignes]
    assert ordre_a == ordre_b == [1, 2]
    rangs = {
        ligne.archer_id: ligne.rang for ligne in calculer_classement([pere, fils], scores).lignes
    }
    assert rangs == {1: 1, 2: 1}  # même total ⇒ même rang partagé


def test_scores_d_archers_inconnus_sont_ignores() -> None:
    """Un score dont l'archer n'est pas dans le lot n'affecte pas le classement."""
    classement = calculer_classement([_archer(1, "Alice")], [Score(999, 10, id=1)])
    assert classement.lignes[0].total == 0
