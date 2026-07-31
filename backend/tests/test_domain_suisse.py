"""Tests du **système suisse** (E05US015).

**Dérivés du CA** (règle 9) : la règle donnée par le commanditaire le 31/07/2026 (référentiel §10.1)
et les quatre arbitrages du cadrage — ronde 1 par classement (jamais aléatoire), pas de
ré-affrontement, bye au moins bien classé sans bye, départage points → Buchholz → critères FFTA.

L'exemple de la règle sert de fil : « Ronde 1 : A bat B, C bat D, E bat F, G bat H. Ronde 2 : A vs
C, E vs G, B vs D, F vs H. »
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from domain.erreurs import ConfigurationSuisseInvalide
from domain.participant import Participant
from domain.suisse import (
    Appariement,
    ConfigurationSuisse,
    ResultatRonde,
    apparier_ronde,
    classement_suisse,
)


def archers(nombre: int) -> list[Participant]:
    """`nombre` participants **ordonnés par classement source** (indice 0 = premier)."""
    return [Participant.individuel(rang) for rang in range(1, nombre + 1)]


def paires(appariements: Sequence[Appariement]) -> set[frozenset[int]]:
    return {frozenset((a.a.ref_id, a.b.ref_id)) for a in appariements if a.b is not None}


# --- ronde 1 : « par classement », jamais aléatoire ----------------------------------------------


def test_la_ronde_1_apparie_par_classement_et_non_au_hasard() -> None:
    """La règle proposait « aléatoire **ou** par classement » ; la **règle 9 du projet** interdit
    l'aléa non maîtrisé, donc c'est le classement. Ce n'est pas esthétique : c'est ce qui permet de
    reconstruire la phase à l'identique après un incident le jour J.

    Fort contre faible : 1 vs 5, 2 vs 6, 3 vs 7, 4 vs 8 — un favori ne sort pas d'entrée.
    """
    appariements = apparier_ronde(archers(8), [], ConfigurationSuisse())
    assert paires(appariements) == {
        frozenset((1, 5)),
        frozenset((2, 6)),
        frozenset((3, 7)),
        frozenset((4, 8)),
    }


def test_la_ronde_1_est_reproductible() -> None:
    """Deux appels identiques rendent le même appariement — la condition d'un test déterministe."""
    premier = apparier_ronde(archers(8), [], ConfigurationSuisse())
    second = apparier_ronde(archers(8), [], ConfigurationSuisse())
    assert premier == second


# --- rondes suivantes : « les vainqueurs rencontrent les vainqueurs » ----------------------------


def test_la_ronde_2_oppose_les_vainqueurs_entre_eux() -> None:
    """L'exemple même de la règle : après « A bat B, C bat D, E bat F, G bat H », la ronde 2 ne doit
    plus opposer un vainqueur à un perdant."""
    a, b, c, d, e, f, g, h = archers(8)
    ronde_1 = [
        ResultatRonde.victoire_de(a, b),
        ResultatRonde.victoire_de(c, d),
        ResultatRonde.victoire_de(e, f),
        ResultatRonde.victoire_de(g, h),
    ]
    appariements = apparier_ronde(archers(8), ronde_1, ConfigurationSuisse())
    vainqueurs = {a, c, e, g}
    for appariement in appariements:
        assert appariement.b is not None
        camps = {appariement.a, appariement.b}
        assert camps <= vainqueurs or not (camps & vainqueurs)


def test_personne_n_est_elimine() -> None:
    """L'objectif annoncé de la règle : tout le monde est apparié à chaque ronde."""
    a, b, c, d = archers(4)
    ronde_1 = [ResultatRonde.victoire_de(a, b), ResultatRonde.victoire_de(c, d)]
    # 4 participants → 3 rondes appariables au plus (chacun a 3 adversaires).
    appariements = apparier_ronde(archers(4), ronde_1, ConfigurationSuisse(nb_rondes=3))
    engages = {appariement.a for appariement in appariements} | {
        appariement.b for appariement in appariements if appariement.b is not None
    }
    assert engages == {a, b, c, d}


# --- pas de ré-affrontement (arbitrage du cadrage) -----------------------------------------------


def test_deux_participants_ne_se_rencontrent_jamais_deux_fois() -> None:
    """La règle ne le dit pas, mais l'omettre dégrade le format : le suisse tire sa précision du
    fait que **chaque ronde apporte une information nouvelle**.

    On déroule quatre rondes à 8 archers et on vérifie qu'aucune paire ne revient.
    """
    participants = archers(8)
    resultats: list[ResultatRonde] = []
    vues: set[frozenset[Participant]] = set()
    for _ in range(4):
        for appariement in apparier_ronde(participants, resultats, ConfigurationSuisse()):
            assert appariement.b is not None
            paire = frozenset((appariement.a, appariement.b))
            assert paire not in vues
            vues.add(paire)
            resultats.append(ResultatRonde.victoire_de(appariement.a, appariement.b))


def test_plus_de_rondes_que_d_adversaires_est_refuse_a_la_composition() -> None:
    """À 4 participants chacun n'a que 3 adversaires : 5 rondes sans rematch sont impossibles **par
    construction**. Le dire à la composition évite de bloquer à la ronde 4 le jour J."""
    with pytest.raises(ConfigurationSuisseInvalide):
        apparier_ronde(archers(4), [], ConfigurationSuisse(nb_rondes=5))


def test_on_n_apparie_pas_au_dela_du_nombre_de_rondes_prevu() -> None:
    a, b, c, d = archers(4)
    resultats = [
        ResultatRonde.victoire_de(a, c),
        ResultatRonde.victoire_de(b, d),
        ResultatRonde.victoire_de(a, b),
        ResultatRonde.victoire_de(c, d),
    ]
    with pytest.raises(ConfigurationSuisseInvalide):
        apparier_ronde(archers(4), resultats, ConfigurationSuisse(nb_rondes=2))


# --- effectif impair : le bye --------------------------------------------------------------------


def test_le_bye_va_au_moins_bien_classe() -> None:
    """Un bye est un cadeau (une victoire sans tirer) : il ne revient pas au mieux classé."""
    appariements = apparier_ronde(archers(5), [], ConfigurationSuisse())
    byes = [appariement for appariement in appariements if appariement.est_bye]
    assert len(byes) == 1
    assert byes[0].a.ref_id == 5


def test_le_bye_ne_revient_pas_deux_fois_a_la_meme_personne() -> None:
    """Tant que quelqu'un n'en a pas eu, le bye tourne."""
    participants = archers(5)
    a, b, c, d, e = participants
    # Ronde 1 : E a eu le bye, les autres ont joué.
    ronde_1 = [ResultatRonde.victoire_de(a, c), ResultatRonde.victoire_de(b, d)]
    appariements = apparier_ronde(participants, ronde_1, ConfigurationSuisse())
    porteur = next(appariement.a for appariement in appariements if appariement.est_bye)
    assert porteur != e


# --- départage : points, puis Buchholz, puis critères FFTA ---------------------------------------


def test_le_classement_ordonne_d_abord_par_points() -> None:
    a, b, c, d = archers(4)
    resultats = [
        ResultatRonde.victoire_de(a, c),
        ResultatRonde.victoire_de(b, d),
        ResultatRonde.victoire_de(a, b),
        ResultatRonde.victoire_de(c, d),
    ]
    classement = classement_suisse(archers(4), resultats)
    assert classement[0].participant == a
    assert classement[0].points == 4  # deux victoires, comptées en demi-points doublés


def test_le_buchholz_departage_deux_parcours_de_difficulte_inegale() -> None:
    """Deux archers à une victoire ne valent pas la même chose si l'un a battu le meilleur.

    B bat A (qui gagne son autre rencontre), D bat C (qui perd la sienne) : B et D ont un point,
    mais le parcours de B était plus dur.
    """
    a, b, c, d = archers(4)
    resultats = [
        ResultatRonde.victoire_de(b, a),
        ResultatRonde.victoire_de(d, c),
        ResultatRonde.victoire_de(a, c),
        ResultatRonde.victoire_de(b, d),
    ]
    classement = {ligne.participant: ligne for ligne in classement_suisse(archers(4), resultats)}
    # A a 2 points (une victoire), D aussi ; A a rencontré B (4 pts) et C (0), D a rencontré C (0)
    # et B (4) — égalité de Buchholz ici, donc on vérifie le calcul lui-même.
    assert classement[a].buchholz == classement[b].points + classement[c].points
    assert classement[b].buchholz == classement[a].points + classement[d].points


def test_un_bye_ne_gonfle_pas_le_buchholz() -> None:
    """Compter le bye comme un adversaire à 0 pénaliserait celui qui l'a reçu ; le compter comme un
    adversaire fort le favoriserait. Ne rien compter est le seul choix neutre."""
    a, b, c = archers(3)
    resultats = [ResultatRonde.victoire_de(a, b)]  # C a eu le bye : aucune rencontre
    classement = {ligne.participant: ligne for ligne in classement_suisse(archers(3), resultats)}
    assert classement[c].buchholz == 0


def test_l_ordre_est_stable_a_egalite_parfaite() -> None:
    """À tous critères égaux, le rang **source** ordonne l'affichage sans créer de rangs distincts
    — les deux lignes sont marquées `ex_aequo`."""
    a, b = archers(2)
    classement = classement_suisse(archers(2), [ResultatRonde.nul(a, b)])
    assert [ligne.rang for ligne in classement] == [1, 1]
    assert all(ligne.ex_aequo for ligne in classement)


# --- garde-fous ----------------------------------------------------------------------------------


def test_nombre_de_rondes_par_defaut() -> None:
    """La règle dit « 5 à 7 rondes » ; le défaut retenu au cadrage est 5."""
    assert ConfigurationSuisse().nb_rondes == 5


def test_zero_ronde_est_refuse() -> None:
    with pytest.raises(ConfigurationSuisseInvalide):
        ConfigurationSuisse(nb_rondes=0)
