"""Fusion du palmarès quand le déroulé porte **plusieurs qualifications** (E05US025).

Dérivés du **CA** de `stories/E05-moteur-phases.md` § E05US025 — écrits avant l'implémentation, et
non relus depuis elle. L'oracle est l'exemple de référence du commanditaire, arbitré le 09/08/2026 :

```
ordre 1 : Qualification          3x20   ← les 120 inscrits       → classement de 120
ordre 2 : Qualification haute    3x15   ← rangs   1..60 de l'ordre 1  → rangs finaux   1..60
ordre 3 : Qualification basse    3x15   ← rangs  61..120 de l'ordre 1 → rangs finaux  61..120
```

Deux CA sont en jeu, et ils tirent en sens opposé — c'est pour cela qu'ils sont testés ensemble :

- **« le rang vient de la phase, jamais du cumul »** : la *basse* se range **derrière** la *haute*
  parce que la phase amont l'a décidé, quels que soient les scores du second tour. Ce que porte
  `ResultatPhase.rang_premier` (61 pour la basse), déjà calculé par
  `application.prelevement.tranche`.
- **« la qualification ne décerne pas de médaille »** : un rang **exact** issu d'une qualification
  n'est pas un rang **gagné au tir**. `Palmares.podium` n'exige pas moins que `decerne`, sans quoi
  il remettrait l'or sur un classement de qualification, avant le moindre duel — exactement le
  défaut que la docstring de `LignePalmares.decerne` dit avoir corrigé en revue d'E06US004.

Les effectifs sont réduits (4 archers, coupés en deux paires) : la règle de fusion ne dépend pas de
la taille, et 120 lignes rendraient l'oracle illisible sans rien prouver de plus. Les **rangs de
tournoi** restent ceux de l'exemple à l'échelle près.
"""

from __future__ import annotations

from domain.classement import Classement, LigneClassement, StatutClassement
from domain.palmares import (
    LignePalmares,
    OriginePalmares,
    Palmares,
    PositionPhase,
    ResultatPhase,
    calculer_palmares,
)
from domain.podium import PorteePodium, ReglagePodiums


def _ligne(archer_id: int, rang: int, total: int) -> LigneClassement:
    """Une ligne du classement de la **première** qualification (celle des 3x20).

    `total` est explicite ici, contrairement au helper d'E06US004 qui le dérive de l'identifiant :
    c'est précisément le levier des scores croisés ci-dessous.
    """
    return LigneClassement(
        rang_scratch=rang,
        rang_categorie=rang,
        archer_id=archer_id,
        nom=f"Archer{archer_id}",
        prenom="Jean",
        categorie_id=1,
        categorie_libelle="Senior Homme",
        cible=None,
        club_id=1,
        total=total,
        nb_dix=0,
        nb_neuf=0,
        statut=StatutClassement.EN_LICE,
    )


def _premiere_qualification() -> Classement:
    """Quatre archers à l'issue des 3x20 — c'est ce tour qui répartit haute et basse."""
    return Classement(
        lignes=(
            _ligne(archer_id=10, rang=1, total=560),
            _ligne(archer_id=20, rang=2, total=555),
            _ligne(archer_id=30, rang=3, total=400),
            _ligne(archer_id=40, rang=4, total=395),
        )
    )


def _haute() -> ResultatPhase:
    """La *haute* (rangs 1..2 de l'amont) : l'archer 20 y bat l'archer 10.

    `rang_premier=1` — elle dispute le haut du tournoi.
    """
    return ResultatPhase(
        ordre=2,
        positions=(
            PositionPhase(archer_id=20, rang_min=1, rang_max=1),
            PositionPhase(archer_id=10, rang_min=2, rang_max=2),
        ),
        rang_premier=1,
        origine=OriginePalmares.QUALIFICATION,
    )


def _basse() -> ResultatPhase:
    """La *basse* (rangs 3..4 de l'amont) : l'archer 40 y domine l'archer 30.

    `rang_premier=3` — l'équivalent à cette échelle du « 61 » de l'exemple : elle ne dispute que les
    places 3 et 4, quoi qu'il s'y tire.
    """
    return ResultatPhase(
        ordre=3,
        positions=(
            PositionPhase(archer_id=40, rang_min=1, rang_max=1),
            PositionPhase(archer_id=30, rang_min=2, rang_max=2),
        ),
        rang_premier=3,
        origine=OriginePalmares.QUALIFICATION,
    )


def _rangs(palmares: Palmares) -> list[tuple[int, int | None]]:
    """`(archer_id, rang_min)` dans l'ordre du palmarès."""
    return [(ligne.archer_id, ligne.rang_min) for ligne in palmares.lignes]


def _podium(palmares: Palmares, categorie_id: int) -> tuple[LignePalmares, ...]:
    """Le podium d'une catégorie, tel qu'E06US004 le rendait.

    `Palmares.podium(categorie_id)` a été généralisé en `podiums(reglage)` par E16US014, qui rend
    des blocs pour trois portées. Cette aide ramène la forme d'avant pour que **l'oracle de ces
    tests ne bouge pas d'un chiffre** : ce qui est vérifié plus bas est le comportement livré, pas
    la nouvelle interface.
    """
    reglage = ReglagePodiums(portees=frozenset({PorteePodium.CATEGORIE}))
    for bloc in palmares.podiums(reglage):
        if bloc.cle == categorie_id:
            return tuple(place.ligne for place in bloc.places)
    return ()


# --- CA « le rang vient de la phase, jamais du cumul » --------------------------------------------


def test_la_basse_se_range_derriere_la_haute() -> None:
    """CA : le classement final va de 1 à N, la haute devant, la basse derrière.

    C'est l'énoncé nu de l'exemple : `rang_premier` situe chaque phase dans l'espace de rangs du
    tournoi, et la fusion respecte ce découpage.
    """
    palmares = calculer_palmares(_premiere_qualification(), (_haute(), _basse()))

    assert _rangs(palmares) == [(20, 1), (10, 2), (40, 3), (30, 4)]


def test_le_vainqueur_de_la_basse_ne_double_pas_la_haute_meme_en_tirant_mieux() -> None:
    """CA : le dernier de la haute précède le premier de la basse, même s'il a mieux tiré.

    Le levier est le **score du second tour**, que le palmarès ne voit pas — il ne reçoit que des
    positions. Ce test verrouille donc l'autre bout : quel que soit ce qui s'est joué dans la basse,
    son vainqueur ne peut pas remonter au-dessus de `rang_premier`. Une implémentation qui
    ordonnerait les phases par `ordre` (« la plus tardive l'emporte », le défaut DETTE-034) rendrait
    ici l'archer 40 premier du tournoi.
    """
    palmares = calculer_palmares(_premiere_qualification(), (_haute(), _basse()))

    rang_par_archer = {ligne.archer_id: ligne.rang_min for ligne in palmares.lignes}
    assert rang_par_archer[40] == 3, "Le vainqueur de la basse dispute la 3ᵉ place, pas la 1ʳᵉ."
    assert rang_par_archer[10] == 2, "Le battu de la haute reste devant toute la basse."


def test_le_classement_final_n_est_pas_un_tri_par_total() -> None:
    """CA : « un classement obtenu en triant toutes les séries par total est faux ».

    Les totaux de la **première** qualification sont ici volontairement croisés avec le résultat du
    second tour : l'archer 10 est le meilleur total du plateau (560) et finit pourtant 2ᵉ, l'archer
    20 le suit de peu (555) et finit 1ᵉʳ. Un palmarès qui retomberait sur `LigneClassement.total`
    — la donnée est à portée de main dans le classement reçu — les inverserait.
    """
    palmares = calculer_palmares(_premiere_qualification(), (_haute(), _basse()))

    ordre_final = [ligne.archer_id for ligne in palmares.lignes]
    ordre_par_total = [10, 20, 30, 40]
    assert ordre_final != ordre_par_total
    assert ordre_final == [20, 10, 40, 30]


# --- CA « la qualification ne décerne pas de médaille » -------------------------------------------


def test_un_rang_de_qualification_n_est_jamais_decerne() -> None:
    """Un rang exact issu d'une qualification n'a été gagné par aucun match.

    `decerne` est ce qui vaut la médaille (`Palmares.podium`). Le confondre avec « rang exact »
    donnerait l'or au vainqueur de la haute alors qu'aucun duel n'a eu lieu.
    """
    palmares = calculer_palmares(_premiere_qualification(), (_haute(), _basse()))

    assert [ligne.decerne for ligne in palmares.lignes] == [False, False, False, False]


def test_le_podium_reste_vide_sans_le_moindre_duel() -> None:
    """Conséquence directe : trois qualifications d'affilée ne remettent aucune médaille.

    Le tournoi de l'exemple n'a **pas** de phase à tableau. Le podium doit donc rester vide plutôt
    que de sacrer les deux premiers de la haute.
    """
    palmares = calculer_palmares(_premiere_qualification(), (_haute(), _basse()))

    assert _podium(palmares, 1) == ()


def test_l_origine_distingue_la_phase_du_repli_sur_la_qualification() -> None:
    """L'écran doit pouvoir dire d'où vient le rang (`OriginePalmares`).

    Un archer classé par la haute et un archer resté à la première qualification portent tous deux
    un rang de qualification, mais l'étiqueter `DUELS` — ce que fait la fusion pour toute position
    acquise — ferait lire « éliminé en duels » sur un tournoi qui n'en compte aucun.
    """
    palmares = calculer_palmares(_premiere_qualification(), (_haute(), _basse()))

    assert {ligne.origine for ligne in palmares.lignes} == {OriginePalmares.QUALIFICATION}


def test_une_phase_a_tableau_reste_decernee_et_etiquetee_duels() -> None:
    """Non-régression E06US004 : le défaut de `ResultatPhase.origine` est `DUELS`.

    Les producteurs existants (`application/palmares.py`) ne passent pas d'origine ; leurs rangs
    doivent continuer de valoir médaille. Sans ce défaut, l'US retirerait le podium à tous les
    tournois à tableau — une régression bien plus grave que le trou qu'elle vient combler.
    """
    tableau = ResultatPhase(
        ordre=2,
        positions=(
            PositionPhase(archer_id=20, rang_min=1, rang_max=1),
            PositionPhase(archer_id=10, rang_min=2, rang_max=2),
            PositionPhase(archer_id=30, rang_min=3, rang_max=3),
            PositionPhase(archer_id=40, rang_min=4, rang_max=4),
        ),
    )

    palmares = calculer_palmares(_premiere_qualification(), (tableau,))

    assert all(ligne.decerne for ligne in palmares.lignes)
    assert {ligne.origine for ligne in palmares.lignes} == {OriginePalmares.DUELS}
    assert [ligne.archer_id for ligne in _podium(palmares, 1)] == [20, 10, 30, 40]
