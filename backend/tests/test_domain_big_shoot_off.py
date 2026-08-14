"""Tests du **Big Shoot Off** (E05US015, règle élargie en E05US028).

**Dérivés du CA** (règle 9), et de deux sources qui se sont succédé :

1. la règle donnée verbatim par le commanditaire le **31/07/2026**, qui ferme la question Q9 du
   cahier des charges (référentiel §10.1) — « le plus faible score est éliminé, jusqu'aux x
   derniers » ;
2. son **élargissement du 14/08/2026**, obtenu au cadrage d'E05US028 : une manche élimine
   **plusieurs** archers, et combien se dit **manche par manche**.

⚠️ **Vocabulaire.** `eliminations` est une **liste écrite par l'organisateur** — une case par
manche, « combien sortent à ce tour » —, jamais une progression déduite. Rien n'impose qu'elle
décroisse ni qu'elle soit régulière : `(2, 2, 2, 2)`, `(4, 2, 1)` et `(1, 5)` sont également
valides. Le mot « suite » a été écarté au cadrage, il faisait entendre une règle imposée.

⚠️ **Le point 2 est un changement de règle, pas une généralisation du code.** Le CA d'E05US028
annonçait « nombre d'éliminés par manche **et restants** » alors que `ConfigurationBigShootOff` ne
portait ni l'un ni l'autre : c'est en essayant d'écrire ces tests que la divergence est apparue
(règle 9 — « ne pas réussir à écrire le test depuis le CA est le signal que le CA est ambigu »).
Quatre arbitrages en sont sortis, tous reversés au référentiel §10.1 et à `stories/` :

- le réglage est une **suite d'éliminations**, une entrée par manche (`[4, 2, 1]`) ;
- **K n'est plus un paramètre** : il se déduit de ce que la suite n'élimine pas ;
- on joue **tant que la manche est possible** — une suite ne se refuse jamais, elle s'écourte ;
- les sortants d'une même manche sont **classés entre eux au score de la manche**, et les départager
  par barrage quand ils sont à égalité est un **paramètre** (`departage_les_sortants`).

Le cas de référence reste celui du classeur réel : la **Grande Finale à 5** de `Tableaux.xlsx` (4
vainqueurs du 8ᵉ tour + 1 repêché), que l'oracle 120 d'E05US010 laisse hors de sa portée. Elle
s'exprime désormais par la suite `(1, 1, 1, 1)`.
"""

from __future__ import annotations

import pytest

from domain.big_shoot_off import (
    ConfigurationBigShootOff,
    demarrer,
    eliminer_apres_barrage,
    jouer_manche,
)
from domain.erreurs import ConfigurationBigShootOffInvalide, ScoreDeMancheManquant
from domain.participant import Participant


def finalistes(nombre: int) -> list[Participant]:
    return [Participant.individuel(rang) for rang in range(1, nombre + 1)]


# --- le réglage : une suite d'éliminations, et rien d'autre ---------------------------------------


def test_defauts_du_format() -> None:
    """Arbitrages du 31/07 conservés : 1 volée de 3 flèches, **remise à zéro** entre manches.

    ⚠️ `eliminations` n'a **pas** de défaut, et c'est délibéré : une suite vide décrirait une phase
    qui n'élimine personne. L'absence de réglage se dit `Phase.big_shoot_off is None` — le patron
    de `ReglageDePoules`, où « pas encore réglé » est un état de la phase, pas une configuration
    dégénérée qu'un moteur devrait interpréter.
    """
    configuration = ConfigurationBigShootOff(eliminations=(1,))
    assert configuration.volees == 1
    assert configuration.fleches_par_volee == 3
    assert configuration.cumul_des_manches is False
    assert configuration.departage_les_sortants is False
    assert configuration.fleches_par_manche == 3


def test_une_suite_vide_est_refusee() -> None:
    """Une phase qui n'élimine personne n'est pas un Big Shoot Off : c'est un échauffement."""
    with pytest.raises(ConfigurationBigShootOffInvalide):
        ConfigurationBigShootOff(eliminations=())


def test_une_manche_qui_n_elimine_personne_est_refusee() -> None:
    """`[4, 0, 1]` ferait tirer une manche pour rien — l'organisateur voulait `[4, 1]`."""
    with pytest.raises(ConfigurationBigShootOffInvalide):
        ConfigurationBigShootOff(eliminations=(4, 0, 1))


# --- « on joue tant que la manche est possible » (arbitrage du 14/08) -----------------------------


def test_la_projection_montre_ce_que_la_suite_donne_sur_l_effectif() -> None:
    """Le CA « la répartition est montrée » — patron `RepartitionPoules`.

    C'est ce que l'atelier affiche sous la fiche de réglages : l'organisateur voit les paliers
    **avant** de composer, donc il corrige sa suite au lieu de découvrir le résultat en salle.
    """
    configuration = ConfigurationBigShootOff(eliminations=(4, 2, 1))
    assert configuration.paliers_pour(12) == (8, 6, 5)
    assert configuration.restants_pour(12) == 5


def test_une_suite_trop_longue_s_ecourte_au_lieu_d_etre_refusee() -> None:
    """**Le cœur de l'arbitrage du 14/08.** Un format est de la **configuration** (règle 2) : il
    part au patrimoine et se réutilise d'un tournoi à l'autre, sur des effectifs qu'il ne connaît
    pas. Une suite écrite pour 12 archers appliquée à 6 ne doit donc pas bloquer la phase.

    Sur 6 archers, `[4, 2, 1]` sort 4 à la manche 1 (il en reste 2), puis la manche 2 voudrait en
    sortir 2 sur 2 — elle laisserait la lice **vide**. On s'arrête donc là : deux restants.
    """
    configuration = ConfigurationBigShootOff(eliminations=(4, 2, 1))
    assert configuration.paliers_pour(6) == (2,)
    assert configuration.restants_pour(6) == 2


def test_une_suite_trop_courte_laisse_simplement_plus_de_restants() -> None:
    """La suite fait autorité : elle ne se prolonge pas toute seule jusqu'au vainqueur unique.

    20 entrants sur `[4, 2, 1]` laissent **13** rescapés — ce qui n'est probablement pas voulu, et
    c'est exactement pourquoi la projection ci-dessus est affichée à l'atelier. Le moteur ne
    réécrit pas la suite pour rattraper l'organisateur : il montre, il ne décide pas.
    """
    configuration = ConfigurationBigShootOff(eliminations=(4, 2, 1))
    assert configuration.paliers_pour(20) == (16, 14, 13)
    assert configuration.restants_pour(20) == 13


def test_un_bso_est_termine_quand_la_manche_suivante_n_est_plus_possible() -> None:
    a, b, c, d, e, f = finalistes(6)
    etat = demarrer([a, b, c, d, e, f], ConfigurationBigShootOff(eliminations=(4, 2, 1)))
    assert not etat.est_termine
    etat = jouer_manche(etat, {a: 30, b: 29, c: 28, d: 27, e: 26, f: 25}).etat
    assert etat.en_lice == (a, b)
    # La manche 2 sortirait 2 archers sur 2 : elle viderait la lice, donc elle ne se joue pas.
    assert etat.est_termine


def test_on_ne_joue_pas_une_manche_sur_un_bso_termine() -> None:
    a, b = finalistes(2)
    etat = demarrer([a, b], ConfigurationBigShootOff(eliminations=(1,)))
    etat = jouer_manche(etat, {a: 28, b: 20}).etat
    with pytest.raises(ConfigurationBigShootOffInvalide):
        jouer_manche(etat, {a: 28})


# --- « les sortants sont classés entre eux au score de la manche » (arbitrage du 14/08) -----------


def test_une_manche_sort_plusieurs_archers_classes_au_score() -> None:
    """Arbitrage du 14/08 : le plus faible des sortants prend le **rang le plus bas**.

    Sur 12 archers dont 4 sortent, les rangs 12, 11, 10 et 9 sont distribués dans l'ordre des
    scores de la manche — un classement 1→N sans trou, cohérent avec le placement intégral
    d'E05US010.
    """
    archers = finalistes(12)
    etat = demarrer(archers, ConfigurationBigShootOff(eliminations=(4, 2, 1)))
    scores = {archer: 30 - index for index, archer in enumerate(archers)}
    issue = jouer_manche(etat, scores)
    # Les quatre derniers de la manche sortent, le plus faible au rang le plus bas.
    assert issue.elimines == (archers[11], archers[10], archers[9], archers[8])
    assert issue.rangs_attribues == (
        (archers[11], 12),
        (archers[10], 11),
        (archers[9], 10),
        (archers[8], 9),
    )
    assert issue.etat.en_lice == tuple(archers[:8])


def test_le_bso_classe_tout_le_monde() -> None:
    """La Grande Finale du classeur : cinq archers, suite `(1, 1, 1, 1)`, cinq rangs.

    Le déroulé historique reste exprimable — c'est ce qui garantit que l'élargissement du 14/08
    **ajoute** une capacité au lieu d'en remplacer une.
    """
    a, b, c, d, e = finalistes(5)
    etat = demarrer([a, b, c, d, e], ConfigurationBigShootOff(eliminations=(1, 1, 1, 1)))
    for scores in (
        {a: 30, b: 29, c: 28, d: 27, e: 26},
        {a: 30, b: 29, c: 28, d: 27},
        {a: 30, b: 29, c: 28},
        {a: 30, b: 29},
    ):
        etat = jouer_manche(etat, scores).etat
    assert etat.est_termine
    assert etat.classement() == ((a, 1), (b, 2), (c, 3), (d, 4), (e, 5))


def test_les_restants_partagent_le_rang_un() -> None:
    """Règle du 31/07, **inchangée** : « les x derniers » n'ont pas de critère pour se départager.

    Ici la suite `(1,)` laisse deux archers sur trois : leur en inventer un ordre (le score de la
    dernière manche ?) serait ajouter à la règle.
    """
    a, b, c = finalistes(3)
    etat = demarrer([a, b, c], ConfigurationBigShootOff(eliminations=(1,)))
    etat = jouer_manche(etat, {a: 28, b: 27, c: 20}).etat
    assert etat.est_termine
    assert etat.classement() == ((a, 1), (b, 1), (c, 3))


def test_des_sortants_a_egalite_restent_ex_aequo_sans_le_parametre() -> None:
    """Sans `departage_les_sortants`, deux sortants au même score **partagent** leur rang.

    Rang partagé au sens usuel (« 1224 ») : sur 12 archers dont 4 sortent à 18, 21, 21 et 24, le
    18 est 12ᵉ, les deux 21 sont **11ᵉ ex æquo**, le 24 est 9ᵉ. Le rang 10 reste vacant — c'est la
    trace du départage qui n'a pas eu lieu, et il vaut mieux qu'elle se voie.
    """
    archers = finalistes(12)
    etat = demarrer(archers, ConfigurationBigShootOff(eliminations=(4,)))
    scores = {archer: 30 for archer in archers}
    scores[archers[11]] = 18
    scores[archers[10]] = 21
    scores[archers[9]] = 21
    scores[archers[8]] = 24
    issue = jouer_manche(etat, scores)
    assert dict(issue.rangs_attribues) == {
        archers[11]: 12,
        archers[10]: 11,
        archers[9]: 11,
        archers[8]: 9,
    }


# --- cumul ou remise à zéro : le paramètre demandé le 31/07 --------------------------------------


def test_le_cumul_est_un_parametre_et_change_le_sortant() -> None:
    """Le paramètre du 31/07 porte une décision de **fond**, pas un détail d'affichage : la même
    série de scores élimine deux archers différents selon le mode.

    Manche 1 (A 30, B 10, C 20, D 5) : D sort dans les deux modes.
    Manche 2 (A 10, B 25, C 20) :
    - **remise à zéro** (défaut) → A tire la plus faible manche (10) et sort. Son excellent premier
      tour ne le protège pas : c'est ce qui garde l'enjeu jusqu'à la dernière flèche.
    - **cumul** → A totalise 40, B 35, C 40 : c'est B qui sort, coulé par sa manche 1 à 10.
    """
    a, b, c, d = finalistes(4)
    scores_1 = {a: 30, b: 10, c: 20, d: 5}
    scores_2 = {a: 10, b: 25, c: 20}
    suite = ConfigurationBigShootOff(eliminations=(1, 1))

    a_la_manche = jouer_manche(demarrer([a, b, c, d], suite), scores_1)
    assert a_la_manche.elimines == (d,)
    assert jouer_manche(a_la_manche.etat, scores_2).elimines == (a,)

    au_cumul = jouer_manche(
        demarrer(
            [a, b, c, d], ConfigurationBigShootOff(eliminations=(1, 1), cumul_des_manches=True)
        ),
        scores_1,
    )
    assert au_cumul.elimines == (d,)
    assert jouer_manche(au_cumul.etat, scores_2).elimines == (b,)


# --- « égalité au plus faible se départage au barrage » (§8.2) ------------------------------------


def test_l_egalite_a_la_barre_suspend_la_manche() -> None:
    """Le moteur **ne devine pas** les sortants : il nomme les ex æquo et attend le barrage.

    Généralisation du 14/08 : l'égalité qui bloque n'est plus « au plus faible » mais **à la
    barre** — la frontière entre sortants et rescapés. Deux places à prendre, trois candidats à 22 :
    le 18 sort de toute façon, et le barrage désigne lequel des trois l'accompagne.
    """
    a, b, c, d, e, f = finalistes(6)
    etat = demarrer([a, b, c, d, e, f], ConfigurationBigShootOff(eliminations=(2,)))
    issue = jouer_manche(etat, {a: 31, b: 30, c: 22, d: 22, e: 22, f: 18})
    assert issue.elimines == ()
    assert set(issue.barrage_entre) == {c, d, e}
    assert issue.places_au_barrage == 1
    assert issue.etat.en_lice == (a, b, c, d, e, f)  # rien n'a bougé


def test_un_archer_clairement_condamne_ne_tire_pas_le_barrage_de_la_barre() -> None:
    """`places_au_barrage` ne compte que ce qui reste à trancher **après** les sortants certains.

    C'est ce qui économise le pas de tir : on ne fait retirer que ceux dont l'égalité décide.
    """
    a, b, c, d, e, f = finalistes(6)
    etat = demarrer([a, b, c, d, e, f], ConfigurationBigShootOff(eliminations=(2,)))
    issue = jouer_manche(etat, {a: 31, b: 30, c: 22, d: 22, e: 22, f: 18})
    assert f not in issue.barrage_entre


def test_le_verdict_du_barrage_conclut_la_manche() -> None:
    """Le BSO **applique** le verdict de `domain/barrage.py`, il ne le rejoue pas — c'est ce qui
    permet au barrage de servir aussi aux poules et aux duels nuls.

    L'ordre reçu va du **plus faible au plus fort** : sur trois ex æquo pour une seule place
    d'élimination, seul le premier sort.
    """
    a, b, c, d, e, f = finalistes(6)
    etat = demarrer([a, b, c, d, e, f], ConfigurationBigShootOff(eliminations=(2,)))
    suspendue = jouer_manche(etat, {a: 31, b: 30, c: 22, d: 22, e: 22, f: 18})
    issue = eliminer_apres_barrage(suspendue.etat, ordre=(e, c, d))
    # `f` (18) sortait de toute façon ; `e`, désigné plus faible du barrage, l'accompagne.
    assert set(issue.elimines) == {f, e}
    assert dict(issue.rangs_attribues) == {f: 6, e: 5}
    assert issue.etat.en_lice == (a, b, c, d)
    assert issue.etat.barrage_en_cours == ()


def test_on_n_elimine_pas_par_barrage_sans_manche_suspendue() -> None:
    """Sans cette garde, un service pourrait éliminer n'importe qui, hors de toute manche, et lui
    décerner un rang — la couture BSO ↔ barrage laisserait une liberté qu'aucune règle ne donne."""
    a, b, c = finalistes(3)
    etat = demarrer([a, b, c], ConfigurationBigShootOff(eliminations=(1,)))
    with pytest.raises(ConfigurationBigShootOffInvalide):
        eliminer_apres_barrage(etat, ordre=(c,))


def test_le_verdict_doit_porter_exactement_les_ex_aequo_du_barrage() -> None:
    """Le verdict d'un barrage ne sert pas à éliminer un tiers, ni à en oublier un."""
    a, b, c, d = finalistes(4)
    etat = demarrer([a, b, c, d], ConfigurationBigShootOff(eliminations=(1,)))
    suspendue = jouer_manche(etat, {a: 28, b: 27, c: 20, d: 20})
    with pytest.raises(ConfigurationBigShootOffInvalide):
        eliminer_apres_barrage(suspendue.etat, ordre=(a, c))
    with pytest.raises(ConfigurationBigShootOffInvalide):
        eliminer_apres_barrage(suspendue.etat, ordre=(c,))


def test_on_ne_joue_pas_une_manche_par_dessus_un_barrage_en_attente() -> None:
    """⚠️ **Le garde-fou n'avait été posé que d'un côté de la couture.**

    `eliminer_apres_barrage` vérifiait qu'une manche est suspendue ; `jouer_manche` ne vérifiait
    rien. On pouvait donc enjamber un barrage en cours : le **leader** s'y faisait éliminer,
    l'égalité était oubliée sans trace, et les scores de la manche suspendue — déjà repliés dans les
    cumuls — étaient comptés deux fois. Fermer une porte et laisser l'autre ouverte ne ferme rien.
    """
    a, b, c = finalistes(3)
    etat = demarrer(
        [a, b, c], ConfigurationBigShootOff(eliminations=(1, 1), cumul_des_manches=True)
    )
    suspendue = jouer_manche(etat, {a: 28, b: 20, c: 20})
    assert suspendue.etat.barrage_en_cours == (b, c)
    with pytest.raises(ConfigurationBigShootOffInvalide):
        jouer_manche(suspendue.etat, {a: 10, b: 30, c: 30})


# --- « départager les sortants » : le paramètre demandé le 14/08 ----------------------------------


def test_le_departage_des_sortants_declenche_un_barrage_entre_elimines() -> None:
    """Paramètre demandé par le commanditaire le 14/08 : le classement final sans ex æquo se paie
    en barrages, donc c'est un **choix d'organisateur** — jumeau de `departage_inter_poules`.

    Ici les deux plus faibles sortent tous les deux et sont à 18 : leur égalité ne change **rien**
    à qui continue, elle ne décide que du 12ᵉ et du 11ᵉ. Sans le paramètre, on ne les fait pas
    retirer ; avec, on les départage.
    """
    archers = finalistes(12)
    scores = {archer: 30 for archer in archers}
    scores[archers[11]] = 18
    scores[archers[10]] = 18

    sans = jouer_manche(demarrer(archers, ConfigurationBigShootOff(eliminations=(2,))), scores)
    assert sans.barrage_entre == ()
    assert dict(sans.rangs_attribues) == {archers[11]: 12, archers[10]: 12}

    avec = jouer_manche(
        demarrer(archers, ConfigurationBigShootOff(eliminations=(2,), departage_les_sortants=True)),
        scores,
    )
    assert set(avec.barrage_entre) == {archers[11], archers[10]}
    assert avec.places_au_barrage == 2
    assert avec.elimines == ()


def test_le_departage_des_sortants_n_invente_pas_de_barrage_quand_les_scores_different() -> None:
    """Le paramètre ne fait tirer que ce qui est réellement à égalité."""
    archers = finalistes(12)
    scores = {archer: 30 for archer in archers}
    scores[archers[11]] = 18
    scores[archers[10]] = 21
    issue = jouer_manche(
        demarrer(archers, ConfigurationBigShootOff(eliminations=(2,), departage_les_sortants=True)),
        scores,
    )
    assert issue.barrage_entre == ()
    assert dict(issue.rangs_attribues) == {archers[11]: 12, archers[10]: 11}


# --- garde-fous de saisie ------------------------------------------------------------------------


def test_un_score_manquant_n_est_pas_un_zero() -> None:
    """Traiter l'absence comme un zéro éliminerait un archer sur une donnée non saisie — l'erreur
    typique qu'on ne voit qu'après coup, le jour J."""
    a, b, c = finalistes(3)
    etat = demarrer([a, b, c], ConfigurationBigShootOff(eliminations=(1,)))
    with pytest.raises(ScoreDeMancheManquant):
        jouer_manche(etat, {a: 28, b: 27})
