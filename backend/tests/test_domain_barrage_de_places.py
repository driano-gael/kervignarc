"""Tests du **barrage de places décisives** (E06US003).

**Dérivés du CA** (règle 9), CA cadré le 02/08/2026 dans `stories/E06-classements.md`. Ils portent
sur ce qu'E06US003 ajoute — le **déclenchement** (seuil configurable), la **répétition** en manches
et le **verdict** —, jamais sur la règle du barrage elle-même : celle-ci est livrée et testée par
E05US015 (`test_domain_barrage.py`), et cette US ne la retouche pas.

Trois points du CA méritaient leur test nommé, parce qu'ils sont contre-intuitifs :

- le seuil porte sur le **rang du groupe**, donc un barrage déclenché au rang 8 tranche aussi la 9ᵉ
  place — sans quoi la dernière place qualificative serait indépartageable ;
- l'ordre acquis à la **manche 1** survit aux manches suivantes (le groupe à 10 reste devant le
  groupe à 8, quoi qu'il arrive au retir) ;
- une manche qui fait retirer quelqu'un de **déjà départagé** est refusée, pas ignorée.
"""

from __future__ import annotations

import dataclasses as _dataclasses
import datetime

import pytest

from domain.barrage import (
    BarrageDePlaces,
    EgaliteADepartager,
    PorteeBarrage,
    TirBarrage,
    VerdictBarrage,
    egalites_a_departager,
    partitionner_barrage,
    resoudre_barrage_en_manches,
)
from domain.erreurs import ConfigurationBarrageInvalide
from domain.participant import Participant
from domain.politiques import (
    DecompteDepartage,
    TiebreakAvecBarrage,
    TiebreakFftaDefaut,
    TiebreakPoules,
)

A = Participant.individuel(1)
B = Participant.individuel(2)
C = Participant.individuel(3)
D = Participant.individuel(4)


# --- la partition ordonnée : ce que la manche 1 a acquis ----------------------------------------


def test_la_partition_rend_les_groupes_dans_l_ordre_du_classement() -> None:
    """Quatre tireurs, deux à 10 et deux à 8 : **deux** égalités distinctes, et celle à 10 devant.

    `resoudre_barrage` ne pouvait pas dire cela — il rend `groupes_a_rejouer` sans l'ordre relatif
    des groupes, parce que son contrat interdit l'ordre partiel. La partition est la même règle
    rendue **structurée**, et c'est elle que la répétition en manches consomme.
    """
    partition = partitionner_barrage(
        [TirBarrage(A, 10), TirBarrage(B, 8), TirBarrage(C, 10), TirBarrage(D, 8)]
    )
    assert partition == ((A, C), (B, D))


def test_un_groupe_departage_est_un_singleton() -> None:
    partition = partitionner_barrage([TirBarrage(A, 10), TirBarrage(B, 9), TirBarrage(C, 8)])
    assert partition == ((A,), (B,), (C,))


def test_les_absents_ferment_la_partition_et_restent_groupes_entre_eux() -> None:
    """B.6.5.2.4 : l'absent est déclaré perdant. Deux absents ne s'ordonnent pas entre eux — ils
    n'ont pas tiré —, donc ils ferment la partition **ensemble**."""
    partition = partitionner_barrage(
        [TirBarrage(A, None), TirBarrage(B, 9), TirBarrage(C, None), TirBarrage(D, 10)]
    )
    assert partition == ((D,), (B,), (A, C))


# --- « on répète jusqu'à résolution » (§8.2) -----------------------------------------------------


def test_une_seule_manche_se_comporte_comme_le_moteur_d_origine() -> None:
    resultat = resoudre_barrage_en_manches([[TirBarrage(A, 10), TirBarrage(B, 9)]])
    assert resultat.est_resolu
    assert resultat.ordre == (A, B)


def test_la_manche_suivante_departage_le_groupe_reste_a_egalite() -> None:
    resultat = resoudre_barrage_en_manches(
        [
            [TirBarrage(A, 9), TirBarrage(B, 9)],
            [TirBarrage(A, 8), TirBarrage(B, 10)],
        ]
    )
    assert resultat.est_resolu
    assert resultat.ordre == (B, A)


def test_l_ordre_acquis_a_la_premiere_manche_survit_au_retir() -> None:
    """Le point le plus facile à casser. A et C ont fait 10, B et D ont fait 8 : quoi que donne le
    retir, **aucun** tireur à 8 ne peut passer devant un tireur à 10 que la manche 1 avait déjà
    départagé. C'est exactement ce que la mise à plat des groupes ferait perdre."""
    resultat = resoudre_barrage_en_manches(
        [
            [TirBarrage(A, 10), TirBarrage(B, 8), TirBarrage(C, 10), TirBarrage(D, 8)],
            [TirBarrage(A, 7), TirBarrage(C, 9), TirBarrage(B, 10), TirBarrage(D, 6)],
        ]
    )
    assert resultat.est_resolu
    assert resultat.ordre == (C, A, B, D)


def test_on_peut_faire_retirer_un_seul_groupe_a_la_fois() -> None:
    """Le jour J, un juge fait retirer une égalité puis l'autre — pas les deux en même temps. Un
    groupe absent de la manche **reste** à égalité au lieu d'être considéré comme résolu."""
    resultat = resoudre_barrage_en_manches(
        [
            [TirBarrage(A, 10), TirBarrage(B, 8), TirBarrage(C, 10), TirBarrage(D, 8)],
            [TirBarrage(A, 9), TirBarrage(C, 7)],
        ]
    )
    assert not resultat.est_resolu
    assert resultat.groupes_a_rejouer == ((B, D),)


def test_la_repetition_va_jusqu_a_la_resolution() -> None:
    resultat = resoudre_barrage_en_manches(
        [
            [TirBarrage(A, 9), TirBarrage(B, 9)],
            [TirBarrage(A, 10), TirBarrage(B, 10)],
            [TirBarrage(A, 8), TirBarrage(B, 9)],
        ]
    )
    assert resultat.est_resolu
    assert resultat.ordre == (B, A)


def test_une_egalite_persistante_reste_non_resolue() -> None:
    resultat = resoudre_barrage_en_manches(
        [
            [TirBarrage(A, 9), TirBarrage(B, 9)],
            [TirBarrage(A, 10), TirBarrage(B, 10)],
        ]
    )
    assert not resultat.est_resolu
    assert resultat.groupes_a_rejouer == ((A, B),)


def test_faire_retirer_quelqu_un_de_deja_departage_est_refuse() -> None:
    """Pas une saisie à ignorer poliment : c'est une **erreur de saisie** qui, si on la laissait
    passer, réordonnerait des places que le premier tir avait déjà tranchées."""
    with pytest.raises(ConfigurationBarrageInvalide):
        resoudre_barrage_en_manches(
            [
                [TirBarrage(A, 10), TirBarrage(B, 9), TirBarrage(C, 9)],
                [TirBarrage(B, 8), TirBarrage(C, 10), TirBarrage(A, 7)],
            ]
        )


def test_un_barrage_sans_aucune_manche_est_refuse() -> None:
    with pytest.raises(ConfigurationBarrageInvalide):
        resoudre_barrage_en_manches([])


def test_une_manche_de_retir_incomplete_est_refusee() -> None:
    """Un groupe se retire **en entier** ou pas du tout : deux ex æquo dont un seul a retiré ne se
    départagent sur rien. Le laisser passer ferait gagner celui qui a tiré, sans adversaire."""
    with pytest.raises(ConfigurationBarrageInvalide):
        resoudre_barrage_en_manches(
            [
                [TirBarrage(A, 9), TirBarrage(B, 9), TirBarrage(C, 9)],
                [TirBarrage(A, 10)],
            ]
        )


# --- le déclenchement : seuil configurable porté par la politique `tiebreak` ---------------------


def test_le_defaut_ffta_ne_declenche_aucun_barrage() -> None:
    """E06US001 est inchangée tant que rien n'est réglé : l'ex æquo **reste** le défaut."""
    rangs = [(1, A), (2, B), (2, C), (4, D)]
    assert egalites_a_departager(rangs, TiebreakFftaDefaut()) == ()


def test_le_defaut_des_poules_ne_declenche_pas_davantage() -> None:
    rangs = [(1, A), (2, B), (2, C)]
    assert egalites_a_departager(rangs, TiebreakPoules()) == ()


def test_une_egalite_sous_le_seuil_demande_un_barrage() -> None:
    politique = TiebreakAvecBarrage(sous_jacent=TiebreakFftaDefaut(), jusqu_au=8)
    rangs = [(1, A), (2, B), (2, C), (4, D)]
    assert egalites_a_departager(rangs, politique) == (
        EgaliteADepartager(rang=2, participants=(B, C)),
    )


def test_une_egalite_au_dela_du_seuil_reste_partagee() -> None:
    politique = TiebreakAvecBarrage(sous_jacent=TiebreakFftaDefaut(), jusqu_au=8)
    rangs = [(9, A), (9, B)]
    assert egalites_a_departager(rangs, politique) == ()


def test_le_seuil_porte_sur_le_rang_du_groupe_pas_sur_chacune_de_ses_places() -> None:
    """Deux ex æquo au rang 8 avec un seuil à 8 : le barrage a lieu, et il tranche donc **aussi**
    la 9ᵉ place, qui est au-delà du seuil.

    Ce n'est pas un effet de bord toléré, c'est le cas d'usage : « départager la dernière place
    qualificative » est précisément une égalité qui **chevauche** le seuil. Le lire place par place
    rendrait l'option inutile là où on la demande.
    """
    politique = TiebreakAvecBarrage(sous_jacent=TiebreakFftaDefaut(), jusqu_au=8)
    rangs = [(8, A), (8, B), (10, C)]
    assert egalites_a_departager(rangs, politique) == (
        EgaliteADepartager(rang=8, participants=(A, B)),
    )


def test_un_rang_non_partage_n_est_jamais_une_egalite() -> None:
    politique = TiebreakAvecBarrage(sous_jacent=TiebreakFftaDefaut(), jusqu_au=8)
    rangs = [(1, A), (2, B), (3, C)]
    assert egalites_a_departager(rangs, politique) == ()


def test_plusieurs_egalites_sont_toutes_signalees() -> None:
    politique = TiebreakAvecBarrage(sous_jacent=TiebreakFftaDefaut(), jusqu_au=8)
    rangs = [(1, A), (1, B), (3, C), (3, D)]
    assert egalites_a_departager(rangs, politique) == (
        EgaliteADepartager(rang=1, participants=(A, B)),
        EgaliteADepartager(rang=3, participants=(C, D)),
    )


def test_le_seuil_ne_change_pas_le_comparateur_qu_il_enveloppe() -> None:
    """`TiebreakAvecBarrage` est un **composite** : il ajoute le déclenchement, il ne touche pas au
    départage. Un seuil réglé sur un comparateur de poule doit départager comme une poule."""
    a = DecompteDepartage(nb_dix=0, nb_neuf=0, points_match=6)
    b = DecompteDepartage(nb_dix=9, nb_neuf=9, points_match=3)
    assert TiebreakAvecBarrage(sous_jacent=TiebreakPoules(), jusqu_au=8).departager(a, b) < 0
    assert TiebreakAvecBarrage(sous_jacent=TiebreakFftaDefaut(), jusqu_au=8).departager(a, b) > 0


# --- le verdict, prêt à être appliqué au classement ----------------------------------------------


def test_un_barrage_resolu_donne_un_verdict_a_rangs_consecutifs() -> None:
    verdict = VerdictBarrage(rang=8, ordre=(B, A, C))
    assert verdict.rangs() == {B: 8, A: 9, C: 10}


def test_un_verdict_vide_ne_range_personne() -> None:
    """Un barrage non résolu ne publie rien : le rang **reste partagé**. Publier un ordre à moitié
    vrai serait pire qu'un refus, parce qu'il s'affiche sans avertir (contrat de `ResultatBarrage`).
    """
    assert VerdictBarrage(rang=8, ordre=()).rangs() == {}


# --- couverture de la manche 1 (correctif de revue, bloquant) ------------------------------------


def _annonce(participants: tuple[Participant, ...]) -> BarrageDePlaces:
    return BarrageDePlaces(
        depart_id=1,
        portee=PorteeBarrage.QUALIFICATION,
        participants=participants,
        cree_le=datetime.datetime(2026, 8, 2, 12, 0, tzinfo=datetime.UTC),
        rang_dispute=8,
    )


def test_la_premiere_manche_doit_faire_tirer_tous_les_participants() -> None:
    """Le pendant, pour la manche 1, de « un groupe se retire en entier ou pas du tout ».

    C'est le trou qui rendait le reste inopérant : `_rejouer` ne traite que les manches ≥ 2, et
    `partitionner_barrage` ne connaît que les tirs qu'on lui donne — il ne peut pas remarquer qu'il
    en manque. Un barrage annoncé à trois dont on ne saisit que deux tirs rendait `est_resolu=True`
    en **oubliant** le troisième, lequel passait ensuite devant les tireurs au classement.
    """
    barrage = _annonce((A, B, C))
    with pytest.raises(ConfigurationBarrageInvalide, match="tous les participants"):
        _dataclasses.replace(barrage, manches=((TirBarrage(A, 10), TirBarrage(B, 9)),)).resultat()


def test_un_absent_se_saisit_il_ne_s_omet_pas() -> None:
    """La bonne façon de ne pas noter quelqu'un : un score nul (absent), pas une ligne manquante."""
    barrage = _dataclasses.replace(
        _annonce((A, B, C)),
        manches=((TirBarrage(A, 10), TirBarrage(B, 9), TirBarrage(C, None)),),
    )
    assert barrage.resultat().ordre == (A, B, C)


def test_un_barrage_sans_manche_reste_a_tirer() -> None:
    assert not _annonce((A, B)).resultat().est_resolu
