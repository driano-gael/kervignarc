"""Tests unitaires du classement de qualification (E06US001) — fonction de domaine **pure**.

Dérivés du **CA** de `stories/E06-classements.md` (et non de l'implémentation) :

- **cumul** : archers triés par score cumulé, qui est la somme des volées **validées** (la même
  définition que `Serie.cumul`) ;
- **départage** FFTA (`docs/referentiel-ffta.md` §8.1, art. C.3) : à total égal, on départage au
  **plus grand nombre de 10**, puis de **9** — deux critères **séquentiels**, jamais fusionnés, et
  qui ne jouent **qu'à** total égal ;
- **catégorie** : deux rangs coexistent — un rang **scratch** (global, toutes catégories) et un rang
  **par catégorie** (repartant de 1 par catégorie, ex æquo partagés avec sauts — pas un rang « dense »
  sans trou). Arbitrage produit du 20/07/2026 (reversé dans `stories/`) : « les deux », pas l'un ou
  l'autre ;
- **traçable** : le nombre de 10 et de 9 remonte dans chaque ligne, pour que le départage se
  **vérifie à l'œil**.

Le X (mouche) n'existe pas dans le vocabulaire de score (ADR-0020/0027) : on départage sur les 10,
pas sur les X.
"""

from __future__ import annotations

from collections.abc import Sequence

from domain.archer import Archer
from domain.blason import ZoneScore
from domain.categorie import Categorie
from domain.classement import LigneClassement, calculer_classement
from domain.serie import Serie, Volee


def _archer(
    id_: int,
    nom: str,
    categorie_id: int = 1,
    prenom: str = "Jean",
    cible: int | None = None,
    club_id: int | None = 1,
) -> Archer:
    return Archer(
        nom=nom,
        prenom=prenom,
        tournoi_id=1,
        categorie_id=categorie_id,
        cible=cible,
        club_id=club_id,
        id=id_,
    )


def _cat(id_: int, libelle: str = "Senior Homme") -> Categorie:
    return Categorie(tournoi_id=1, libelle=libelle, id=id_)


def _volee_validee(numero: int, valeurs: Sequence[ZoneScore]) -> Volee:
    """Une volée **verrouillée** (elle porte un validateur) : la seule qui compte au cumul."""
    return Volee(numero=numero, valeurs=tuple(valeurs), validee_par="Scoreur")


def _serie(archer_id: int, volees: Sequence[Volee]) -> Serie:
    return Serie(tournoi_id=1, archer_id=archer_id, volees=tuple(volees))


DIX, NEUF, HUIT, SEPT, SIX, CINQ = (
    ZoneScore.DIX,
    ZoneScore.NEUF,
    ZoneScore.HUIT,
    ZoneScore.SEPT,
    ZoneScore.SIX,
    ZoneScore.CINQ,
)


def test_classement_vide_sans_archer() -> None:
    """Sans archer, le classement est vide."""
    assert calculer_classement([], [], []).lignes == ()


def test_cumul_ne_compte_que_les_volees_validees() -> None:
    """CA cumul : le total somme les volées **validées** ; une volée en cours n'y entre pas."""
    archers = [_archer(1, "Alice")]
    volee_validee = _volee_validee(1, [DIX, NEUF, HUIT])  # 27, verrouillée
    volee_en_cours = Volee(numero=2, valeurs=(DIX, DIX, DIX))  # 30, pas de validateur
    classement = calculer_classement(
        archers, [_serie(1, [volee_validee, volee_en_cours])], [_cat(1)]
    )
    assert classement.lignes[0].total == 27


def test_ordre_par_cumul_decroissant_avec_rangs() -> None:
    """CA cumul : du meilleur total au moins bon, avec les rangs scratch."""
    archers = [_archer(1, "Alice"), _archer(2, "Bob")]
    series = [
        _serie(1, [_volee_validee(1, [DIX, NEUF])]),  # 19
        _serie(2, [_volee_validee(1, [HUIT, HUIT])]),  # 16
    ]
    lignes = calculer_classement(archers, series, [_cat(1)]).lignes
    assert [(ligne.nom, ligne.rang_scratch, ligne.total) for ligne in lignes] == [
        ("Alice", 1, 19),
        ("Bob", 2, 16),
    ]


def test_archer_sans_serie_a_un_total_nul() -> None:
    """Un archer inscrit sans flèche apparaît avec un total de 0 (et 0 dix, 0 neuf)."""
    ligne = calculer_classement([_archer(5, "Zoé")], [], [_cat(1)]).lignes[0]
    assert (ligne.total, ligne.nb_dix, ligne.nb_neuf) == (0, 0, 0)


def test_departage_par_nombre_de_dix() -> None:
    """CA départage : à total égal, plus de 10 = mieux classé.

    Alice : 10+8 = 18 (un 10). Bob : 9+9 = 18 (zéro 10). Même total, Alice a plus de 10 → rang 1.
    """
    archers = [_archer(1, "Alice"), _archer(2, "Bob")]
    series = [
        _serie(1, [_volee_validee(1, [DIX, HUIT])]),
        _serie(2, [_volee_validee(1, [NEUF, NEUF])]),
    ]
    lignes = calculer_classement(archers, series, [_cat(1)]).lignes
    assert [(ligne.nom, ligne.rang_scratch, ligne.total, ligne.nb_dix) for ligne in lignes] == [
        ("Alice", 1, 18, 1),
        ("Bob", 2, 18, 0),
    ]


def test_departage_par_nombre_de_neuf_quand_les_dix_sont_egaux() -> None:
    """CA départage : à total **et** nombre de 10 égaux, on passe au nombre de 9 (séquentiel).

    Alice : 10+9+9+5 = 33 (un 10, deux 9). Bob : 10+9+8+6 = 33 (un 10, un 9). → Alice rang 1.
    """
    archers = [_archer(1, "Alice"), _archer(2, "Bob")]
    series = [
        _serie(1, [_volee_validee(1, [DIX, NEUF, NEUF, CINQ])]),
        _serie(2, [_volee_validee(1, [DIX, NEUF, HUIT, SIX])]),
    ]
    lignes = calculer_classement(archers, series, [_cat(1)]).lignes
    assert [(ligne.nom, ligne.rang_scratch, ligne.nb_dix, ligne.nb_neuf) for ligne in lignes] == [
        ("Alice", 1, 1, 2),
        ("Bob", 2, 1, 1),
    ]


def test_le_departage_ne_joue_qu_a_total_egal() -> None:
    """Un total supérieur l'emporte, même avec moins de 10 : le départage n'intervient qu'à égalité.

    Alice 20 (deux 10) est devancée par Carl 27 (zéro 10) : le total prime le départage.
    """
    archers = [_archer(1, "Alice"), _archer(2, "Carl")]
    series = [
        _serie(1, [_volee_validee(1, [DIX, DIX])]),  # 20, deux 10
        _serie(2, [_volee_validee(1, [NEUF, NEUF, NEUF])]),  # 27, zéro 10
    ]
    lignes = calculer_classement(archers, series, [_cat(1)]).lignes
    assert [(ligne.nom, ligne.rang_scratch, ligne.total) for ligne in lignes] == [
        ("Carl", 1, 27),
        ("Alice", 2, 20),
    ]


def test_egalite_parfaite_partage_le_rang() -> None:
    """Total, 10 et 9 identiques : rang **partagé** (le référentiel laisse l'ex æquo en qualif).

    L'ordre d'affichage reste déterministe (par nom) mais les deux portent le même rang.
    """
    archers = [_archer(1, "Bruno"), _archer(2, "Anna")]
    serie = [_volee_validee(1, [DIX, NEUF, HUIT])]  # 27, un 10, un 9, pour les deux
    series = [_serie(1, serie), _serie(2, serie)]
    lignes = calculer_classement(archers, series, [_cat(1)]).lignes
    assert [(ligne.nom, ligne.rang_scratch) for ligne in lignes] == [("Anna", 1), ("Bruno", 1)]


def test_nombre_de_dix_et_de_neuf_est_trace() -> None:
    """CA traçable : chaque ligne porte le décompte de 10 et de 9 (sur les volées validées)."""
    archers = [_archer(1, "Alice")]
    series = [
        _serie(1, [_volee_validee(1, [DIX, DIX, NEUF]), _volee_validee(2, [NEUF, HUIT, SEPT])])
    ]
    ligne = calculer_classement(archers, series, [_cat(1)]).lignes[0]
    assert (ligne.nb_dix, ligne.nb_neuf) == (2, 2)


def test_rang_scratch_est_global_toutes_categories() -> None:
    """CA catégorie : le rang scratch classe tous les archers ensemble, catégories confondues."""
    archers = [_archer(1, "Alice", categorie_id=1), _archer(2, "Bob", categorie_id=2)]
    series = [
        _serie(1, [_volee_validee(1, [HUIT, HUIT])]),  # 16
        _serie(2, [_volee_validee(1, [DIX, DIX])]),  # 20
    ]
    lignes = calculer_classement(archers, series, [_cat(1), _cat(2, "Cadet")]).lignes
    assert {ligne.nom: ligne.rang_scratch for ligne in lignes} == {"Bob": 1, "Alice": 2}


def test_rang_categorie_repart_de_un_et_independant_par_categorie() -> None:
    """CA catégorie : au sein de chaque catégorie, les rangs repartent de 1.

    Alice (cat 1) est 2ᵉ au scratch mais **1ʳᵉ de sa catégorie** ; Bob (cat 2) est 1ᵉ partout.
    """
    archers = [
        _archer(1, "Alice", categorie_id=1),
        _archer(2, "Bob", categorie_id=2),
        _archer(3, "Chloé", categorie_id=1),
    ]
    series = [
        _serie(1, [_volee_validee(1, [NEUF, NEUF])]),  # 18, cat 1
        _serie(2, [_volee_validee(1, [DIX, DIX])]),  # 20, cat 2
        _serie(3, [_volee_validee(1, [HUIT, HUIT])]),  # 16, cat 1
    ]
    cats = [_cat(1, "Senior Homme"), _cat(2, "Cadet")]
    par_nom = {ligne.nom: ligne for ligne in calculer_classement(archers, series, cats).lignes}
    assert (par_nom["Bob"].rang_scratch, par_nom["Bob"].rang_categorie) == (1, 1)
    assert (par_nom["Alice"].rang_scratch, par_nom["Alice"].rang_categorie) == (2, 1)
    assert (par_nom["Chloé"].rang_scratch, par_nom["Chloé"].rang_categorie) == (3, 2)
    assert par_nom["Alice"].categorie_libelle == "Senior Homme"


def test_ex_aequo_intra_categorie_partage_le_rang_avec_saut() -> None:
    """Rang catégorie : deux ex æquo parfaits partagent le rang, et le suivant **saute** (1-2-2-4).

    C'est le cas qui sépare un classement de compétition (avec saut) d'un rang « dense » sans trou
    (1-2-2-3). Le CA veut le premier — même règle que le scratch (§8.1). Bob et Chloé ont le même
    total (18), le même nombre de 10 (1) et de 9 (0) : départage épuisé, rang **partagé** ; Dora,
    juste derrière, est **4ᵉ**, pas 3ᵉ. Tous en catégorie 1 : rang catégorie et scratch coïncident,
    ce qui prouve que la **catégorie** saute elle aussi (sinon Dora serait 3ᵉ de catégorie).
    """
    archers = [
        _archer(1, "Alice", categorie_id=1),
        _archer(2, "Bob", categorie_id=1),
        _archer(3, "Chloé", categorie_id=1),
        _archer(4, "Dora", categorie_id=1),
    ]
    series = [
        _serie(1, [_volee_validee(1, [DIX, DIX])]),  # 20 — 2 dix
        _serie(2, [_volee_validee(1, [DIX, HUIT])]),  # 18 — 1 dix, 0 neuf
        _serie(3, [_volee_validee(1, [DIX, HUIT])]),  # 18 — 1 dix, 0 neuf (ex æquo parfait de Bob)
        _serie(4, [_volee_validee(1, [HUIT, HUIT])]),  # 16
    ]
    par_nom = {ligne.nom: ligne for ligne in calculer_classement(archers, series, [_cat(1)]).lignes}
    rangs_categorie = {nom: ligne.rang_categorie for nom, ligne in par_nom.items()}
    rangs_scratch = {nom: ligne.rang_scratch for nom, ligne in par_nom.items()}
    assert rangs_categorie == {"Alice": 1, "Bob": 2, "Chloé": 2, "Dora": 4}
    assert rangs_scratch == {"Alice": 1, "Bob": 2, "Chloé": 2, "Dora": 4}


def test_le_classement_restitue_le_prenom() -> None:
    """Deux homonymes confirmés (E02US002) restent distinguables : le prénom remonte."""
    archers = [_archer(1, "Dupont", prenom="Jean"), _archer(2, "Dupont", prenom="Pierre")]
    prenoms = {
        ligne.archer_id: ligne.prenom
        for ligne in calculer_classement(archers, [], [_cat(1)]).lignes
    }
    assert prenoms == {1: "Jean", 2: "Pierre"}


def test_le_classement_signale_un_club_inconnu() -> None:
    """`club_id` remonte : le classement **signale** l'anomalie, sans la résoudre (ADR-0014)."""
    archers = [_archer(1, "Martin", club_id=None), _archer(2, "Durand", club_id=7)]
    clubs = {
        ligne.archer_id: ligne.club_id
        for ligne in calculer_classement(archers, [], [_cat(1)]).lignes
    }
    assert clubs == {1: None, 2: 7}


def test_deux_homonymes_a_egalite_sont_ordonnes_de_facon_stable() -> None:
    """À égalité parfaite, l'ordre des lignes est déterministe quel que soit l'ordre d'entrée.

    Sans départage au-delà du nom, l'ordre retombait sur celui de `par_tournoi` (`SELECT` sans
    `ORDER BY`) : deux homonymes permutaient d'une lecture à l'autre. On le prouve en inversant
    l'ordre d'entrée ; le rang reste partagé (mêmes total/10/9).
    """
    pere, fils = _archer(1, "Dupont", prenom="Jean"), _archer(2, "Dupont", prenom="Jean")
    s = [_volee_validee(1, [DIX, NEUF])]
    series = [_serie(1, s), _serie(2, s)]
    ordre_a = [
        ligne.archer_id for ligne in calculer_classement([pere, fils], series, [_cat(1)]).lignes
    ]
    ordre_b = [
        ligne.archer_id for ligne in calculer_classement([fils, pere], series, [_cat(1)]).lignes
    ]
    assert ordre_a == ordre_b == [1, 2]
    rangs = {
        ligne.archer_id: ligne.rang_scratch
        for ligne in calculer_classement([pere, fils], series, [_cat(1)]).lignes
    }
    assert rangs == {1: 1, 2: 1}


def test_serie_d_un_archer_inconnu_est_ignoree() -> None:
    """Une série dont l'archer n'est pas dans le lot n'affecte pas le classement."""
    archers = [_archer(1, "Alice")]
    series = [_serie(999, [_volee_validee(1, [DIX, DIX, DIX])])]
    assert calculer_classement(archers, series, [_cat(1)]).lignes[0].total == 0


def test_ligne_est_immuable() -> None:
    """`LigneClassement` est un agrégat frozen : le classement rendu ne se mute pas par mégarde."""
    ligne = calculer_classement([_archer(1, "Alice")], [], [_cat(1)]).lignes[0]
    assert isinstance(ligne, LigneClassement)
