"""Tests du **Big Shoot Off** (E05US015).

**Dérivés du CA** (règle 9) : la règle donnée verbatim par le commanditaire le 31/07/2026, qui ferme
la question Q9 du cahier des charges (`stories/E05-moteur-phases.md`, CA « Big Shoot Off » ;
référentiel §10.1), et les arbitrages du cadrage — cumul **paramétrable**, égalité au plus faible →
barrage, rangs en ordre inverse de sortie, K = 1 par défaut.

Le cas de référence est celui du classeur réel : la **Grande Finale à 5** de `Tableaux.xlsx` (4
vainqueurs du 8ᵉ tour + 1 repêché), que l'oracle 120 d'E05US010 laisse explicitement hors de sa
portée faute de moteur pour la dérouler. C'est cette US qui la lui donne.
"""

from __future__ import annotations

import pytest

from domain.big_shoot_off import (
    ConfigurationBigShootOff,
    demarrer,
    eliminer_apres_barrage,
    jouer_manche,
)
from domain.erreurs import ConfigurationBigShootOffInvalide
from domain.participant import Participant


def finalistes(nombre: int) -> list[Participant]:
    return [Participant.individuel(rang) for rang in range(1, nombre + 1)]


# --- les quatre paramètres que la règle confond en un seul `x` -----------------------------------


def test_defauts_du_format() -> None:
    """Arbitrages du 31/07 : 1 volée de 3 flèches, K = 1, et **remise à zéro** entre manches."""
    configuration = ConfigurationBigShootOff()
    assert configuration.volees == 1
    assert configuration.fleches_par_volee == 3
    assert configuration.restants == 1
    assert configuration.cumul_des_manches is False
    assert configuration.fleches_par_manche == 3


def test_k_egal_a_l_effectif_est_refuse() -> None:
    """« Jusqu'aux x derniers restants » suppose qu'on élimine : à K = N, la phase ne finit jamais.

    Le contrôle vit au démarrage et non sur la configuration, parce qu'un format de bibliothèque
    s'écrit avant de savoir combien d'archers arriveront.
    """
    with pytest.raises(ConfigurationBigShootOffInvalide):
        demarrer(finalistes(5), ConfigurationBigShootOff(restants=5))


# --- « le plus faible score est éliminé » --------------------------------------------------------


def test_le_plus_faible_sort_et_prend_le_dernier_rang() -> None:
    """Ordre **inverse** de sortie : dans un BSO à 5, le premier sorti prend le rang 5."""
    a, b, c, d, e = finalistes(5)
    etat = demarrer([a, b, c, d, e], ConfigurationBigShootOff())
    issue = jouer_manche(etat, {a: 28, b: 27, c: 26, d: 25, e: 24})
    assert issue.elimine == e
    assert issue.rang_attribue == 5
    assert issue.etat.en_lice == (a, b, c, d)


def test_le_bso_classe_tout_le_monde() -> None:
    """Cohérent avec le placement 1→N d'E05US010 : une finale à 5 rend cinq rangs, pas un podium.

    Déroulé complet de la Grande Finale du classeur : quatre manches, quatre éliminés, un vainqueur.
    """
    a, b, c, d, e = finalistes(5)
    etat = demarrer([a, b, c, d, e], ConfigurationBigShootOff())
    for scores in (
        {a: 30, b: 29, c: 28, d: 27, e: 26},
        {a: 30, b: 29, c: 28, d: 27},
        {a: 30, b: 29, c: 28},
        {a: 30, b: 29},
    ):
        etat = jouer_manche(etat, scores).etat
    assert etat.est_termine
    assert etat.classement() == ((a, 1), (b, 2), (c, 3), (d, 4), (e, 5))


def test_k_superieur_a_un_fait_partager_le_rang_un() -> None:
    """La règle ne donne aucun critère pour départager « les x derniers » entre eux : leur en
    inventer un (le score de la dernière manche ?) serait ajouter à la règle."""
    a, b, c = finalistes(3)
    etat = demarrer([a, b, c], ConfigurationBigShootOff(restants=2))
    etat = jouer_manche(etat, {a: 28, b: 27, c: 20}).etat
    assert etat.est_termine
    assert etat.classement() == ((a, 1), (b, 1), (c, 3))


# --- cumul ou remise à zéro : le paramètre demandé le 31/07 --------------------------------------


def test_le_cumul_est_un_parametre_et_change_le_sortant() -> None:
    """Le paramètre demandé le 31/07 porte une décision de **fond**, pas un détail d'affichage :
    la même série de scores élimine deux archers différents selon le mode.

    Manche 1 (A 30, B 10, C 20, D 5) : D sort dans les deux modes.
    Manche 2 (A 10, B 25, C 20) :
    - **remise à zéro** (défaut) → A tire la plus faible manche (10) et sort. Son excellent premier
      tour ne le protège pas : c'est ce qui garde l'enjeu jusqu'à la dernière flèche.
    - **cumul** → A totalise 40, B 35, C 40 : c'est B qui sort, coulé par sa manche 1 à 10.
    """
    a, b, c, d = finalistes(4)
    scores_1 = {a: 30, b: 10, c: 20, d: 5}
    scores_2 = {a: 10, b: 25, c: 20}

    a_la_manche = jouer_manche(demarrer([a, b, c, d], ConfigurationBigShootOff()), scores_1)
    assert a_la_manche.elimine == d
    assert jouer_manche(a_la_manche.etat, scores_2).elimine == a

    configuration = ConfigurationBigShootOff(cumul_des_manches=True)
    au_cumul = jouer_manche(demarrer([a, b, c, d], configuration), scores_1)
    assert au_cumul.elimine == d
    assert jouer_manche(au_cumul.etat, scores_2).elimine == b


# --- « égalité au plus faible se départage au barrage » (§8.2) ------------------------------------


def test_egalite_au_plus_faible_suspend_la_manche() -> None:
    """Le moteur **ne devine pas** l'éliminé : il nomme les ex æquo et attend le barrage."""
    a, b, c = finalistes(3)
    etat = demarrer([a, b, c], ConfigurationBigShootOff())
    issue = jouer_manche(etat, {a: 28, b: 20, c: 20})
    assert issue.elimine is None
    assert set(issue.barrage_entre) == {b, c}
    assert issue.etat.en_lice == (a, b, c)  # rien n'a bougé


def test_le_verdict_du_barrage_conclut_la_manche() -> None:
    """Le BSO **applique** le verdict de `domain/barrage.py`, il ne le rejoue pas — c'est ce qui
    permet au barrage de servir aussi aux poules et aux duels nuls."""
    a, b, c = finalistes(3)
    etat = demarrer([a, b, c], ConfigurationBigShootOff())
    suspendue = jouer_manche(etat, {a: 28, b: 20, c: 20})
    issue = eliminer_apres_barrage(suspendue.etat, perdant_du_barrage=c)
    assert issue.elimine == c
    assert issue.rang_attribue == 3
    assert issue.etat.en_lice == (a, b)


# --- garde-fous de saisie ------------------------------------------------------------------------


def test_un_score_manquant_n_est_pas_un_zero() -> None:
    """Traiter l'absence comme un zéro éliminerait un archer sur une donnée non saisie — l'erreur
    typique qu'on ne voit qu'après coup, le jour J."""
    a, b, c = finalistes(3)
    etat = demarrer([a, b, c], ConfigurationBigShootOff())
    with pytest.raises(ConfigurationBigShootOffInvalide):
        jouer_manche(etat, {a: 28, b: 27})


def test_on_ne_joue_pas_une_manche_sur_un_bso_termine() -> None:
    a, b = finalistes(2)
    etat = demarrer([a, b], ConfigurationBigShootOff())
    etat = jouer_manche(etat, {a: 28, b: 20}).etat
    with pytest.raises(ConfigurationBigShootOffInvalide):
        jouer_manche(etat, {a: 28})
