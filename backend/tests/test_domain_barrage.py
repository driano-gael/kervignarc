"""Tests du **tir de barrage** (E05US015).

**Dérivés du CA** (règle 9), et ici le CA renvoie à une règle **écrite** : art. B.6.5.2, référentiel
§8.2. Le CA de l'US insiste sur deux points « qui surprennent et qu'il ne faut pas rater » — pas de
recompte des 10/9, et l'absent déclaré perdant : ils ont chacun leur test.
"""

from __future__ import annotations

import pytest

from domain.barrage import (
    ConfigurationBarrage,
    ResultatBarrage,
    TirBarrage,
    resoudre_barrage,
)
from domain.erreurs import ConfigurationBarrageInvalide
from domain.participant import Participant

A = Participant.individuel(1)
B = Participant.individuel(2)
C = Participant.individuel(3)
D = Participant.individuel(4)


# --- format : 1 flèche en individuel, 3 en équipe (B.6.5.2 / B.6.5.2.2) --------------------------


def test_formats_reglementaires() -> None:
    assert ConfigurationBarrage.individuel().fleches == 1
    assert ConfigurationBarrage.par_equipe().fleches == 3


def test_un_nombre_de_fleches_hors_reglement_est_refuse() -> None:
    """Le règlement **fixe** ce nombre : un barrage à 2 flèches n'est pas un barrage mal réglé, mais
    une autre épreuve. Contraste voulu avec le barème de poule ou le BSO, que le club choisit."""
    with pytest.raises(ConfigurationBarrageInvalide):
        ConfigurationBarrage(fleches=2, equipe=False)
    with pytest.raises(ConfigurationBarrageInvalide):
        ConfigurationBarrage(fleches=1, equipe=True)


# --- « 1 flèche, le plus haut score gagne » ------------------------------------------------------


def test_le_plus_haut_score_gagne() -> None:
    resultat = resoudre_barrage([TirBarrage(A, 9), TirBarrage(B, 10)])
    assert resultat.est_resolu
    assert resultat.vainqueur == B
    assert resultat.perdant == A


def test_le_perdant_est_exploitable_car_tous_les_barrages_ne_designent_pas_un_vainqueur() -> None:
    """Le Big Shoot Off attend l'**éliminé** de la manche, pas le gagnant : un barrage sert aussi à
    départager une dernière place."""
    resultat = resoudre_barrage([TirBarrage(A, 8), TirBarrage(B, 10), TirBarrage(C, 9)])
    assert resultat.ordre == (B, C, A)
    assert resultat.perdant == A


# --- « si l'égalité subsiste, on répète au plus près du centre » (critère séquentiel) -------------


def test_a_score_egal_le_plus_pres_du_centre_l_emporte() -> None:
    """Second critère, appliqué **seulement** après le score — les deux ne sont pas fusionnés."""
    resultat = resoudre_barrage(
        [TirBarrage(A, 10, distance_au_centre=180), TirBarrage(B, 10, distance_au_centre=40)]
    )
    assert resultat.vainqueur == B


def test_egalite_persistante_demande_de_repeter_le_barrage() -> None:
    """Le règlement dit de répéter : le moteur **ne tranche pas** et nomme les ex æquo."""
    resultat = resoudre_barrage([TirBarrage(A, 10), TirBarrage(B, 10)])
    assert not resultat.est_resolu
    assert set(resultat.a_rejouer) == {A, B}
    assert resultat.ordre == ()


def test_un_ordre_partiel_n_est_jamais_rendu() -> None:
    """Un classement à moitié vrai est plus dangereux qu'un refus : il s'affiche sans avertir.

    C est nettement devant, mais A et B restent à égalité : rien n'est rendu.
    """
    resultat = resoudre_barrage([TirBarrage(A, 8), TirBarrage(B, 8), TirBarrage(C, 10)])
    assert resultat == ResultatBarrage(groupes_a_rejouer=((A, B),))


def test_deux_egalites_distinctes_forment_deux_groupes() -> None:
    """⚠️ Les aplatir ferait retirer les quatre ensemble — et un tireur à 8 pourrait alors passer
    devant un tireur à 10 que le premier tir avait **déjà** départagé.

    Le service doit pouvoir organiser deux barrages séparés ; une liste plate ne le lui dit pas.
    """
    resultat = resoudre_barrage(
        [TirBarrage(A, 10), TirBarrage(B, 10), TirBarrage(C, 8), TirBarrage(D, 8)]
    )
    assert resultat.groupes_a_rejouer == ((A, B), (C, D))


def test_une_distance_non_mesuree_ne_gagne_pas_le_barrage() -> None:
    """⚠️ **Une mesure absente est une inconnue, pas un zéro.**

    Un premier jet repliait `None` sur `0`, c'est-à-dire sur le **centre parfait** : le tir non
    mesuré battait un tir mesuré, et le barrage était déclaré *résolu*. C'est le cas le plus
    probable du jour J — le juge mesure la flèche litigieuse, rarement les deux. Le verdict rendu
    était faux **et silencieux**. Le test précédent ne l'attrapait pas : il mesurait les deux.
    """
    resultat = resoudre_barrage(
        [TirBarrage(A, 10, distance_au_centre=None), TirBarrage(B, 10, distance_au_centre=120)]
    )
    assert not resultat.est_resolu
    assert set(resultat.a_rejouer) == {A, B}


# --- le piège n°1 du CA : le barrage ne recompte pas les 10/9 (B.6.5.2) --------------------------


def test_le_nombre_de_dix_ne_departage_pas_un_barrage() -> None:
    """**Seul endroit du produit** où ce critère est écarté (§8.1 et les poules s'en servent).

    Deux archers à 10 : `TirBarrage` ne porte volontairement **aucun** compte de 10/9, donc aucun
    appelant ne peut le glisser dans le départage. L'égalité tient et il faut retirer — c'est la
    réponse réglementaire, même si elle coûte une flèche de plus.
    """
    assert not hasattr(TirBarrage(A, 10), "nb_dix")
    assert not resoudre_barrage([TirBarrage(A, 10), TirBarrage(B, 10)]).est_resolu


# --- le piège n°2 du CA : « un archer absent est déclaré perdant » (B.6.5.2.4) -------------------


def test_l_absent_est_declare_perdant() -> None:
    """L'absence **tranche** immédiatement : ce n'est pas un forfait à instruire."""
    resultat = resoudre_barrage([TirBarrage(A, None), TirBarrage(B, 6)])
    assert resultat.vainqueur == B
    assert resultat.perdant == A


def test_l_absent_perd_meme_contre_un_score_derisoire() -> None:
    """Aucune comparaison de score n'a lieu : la relégation précède le barème."""
    assert resoudre_barrage([TirBarrage(A, None), TirBarrage(B, 1)]).vainqueur == B


def test_deux_absents_restent_ex_aequo_entre_eux() -> None:
    """Le règlement les déclare tous deux perdants sans les ordonner — et rien ne le permettrait :
    ils n'ont pas tiré. Inventer un ordre serait ajouter à la règle."""
    resultat = resoudre_barrage([TirBarrage(A, None), TirBarrage(B, None), TirBarrage(C, 7)])
    assert not resultat.est_resolu
    assert set(resultat.a_rejouer) == {A, B}


# --- garde-fous ----------------------------------------------------------------------------------


def test_un_barrage_a_un_seul_tireur_n_a_pas_d_objet() -> None:
    with pytest.raises(ConfigurationBarrageInvalide):
        resoudre_barrage([TirBarrage(A, 10)])


def test_un_participant_ne_figure_pas_deux_fois() -> None:
    with pytest.raises(ConfigurationBarrageInvalide):
        resoudre_barrage([TirBarrage(A, 10), TirBarrage(A, 9)])
