"""Tests du déroulé de vues et de la prise de contrôle (E07US004) — écrits **depuis le CA**.

Deux CA sont en jeu :

- « **déroulé de vues par défaut** paramétré à la préparation du tournoi (classement,
  affectations, tableaux, plans) avec **cadence réglable** […] **plusieurs écrans possibles,
  chacun son déroulé** » ;
- « l'admin […] **impose** soit une **vue figée**, soit une **autre séquence** ; […] **une prise de
  contrôle sait se terminer** — **durée** ou retour explicite très visible ; **jamais un état forcé
  qu'on oublie** ».

Le domaine ne lit pas l'heure (règle 9, déterminisme) : comme `domain.supervision.etat_poste`, il
reçoit un **écart déjà calculé** et rend une règle, pas une lecture d'horloge.
"""

from __future__ import annotations

import pytest

from domain.ecran import (
    CADENCE_MAX_S,
    CADENCE_MIN_S,
    CADENCE_PAGE_MAX_S,
    CADENCE_PAGE_MIN_S,
    NOMS_PAR_PAGE_MAX,
    NOMS_PAR_PAGE_MIN,
    Consigne,
    ReglagePages,
    SequenceVues,
    VueEcran,
    VueProgrammee,
    reste_secondes,
)
from domain.erreurs import (
    CadenceDePageInvalide,
    CadenceEcranInvalide,
    ConsigneEcranInvalide,
    DureePriseDeControleInvalide,
    NombreDeNomsParPageInvalide,
    SequenceVuesVide,
)

# --- Le déroulé de vues --------------------------------------------------------------------------


def test_une_sequence_enchaine_les_vues_dans_l_ordre_donne() -> None:
    sequence = SequenceVues(
        (
            VueProgrammee(VueEcran.CLASSEMENT, 30),
            VueProgrammee(VueEcran.SUIVI_DEROULE, 45),
        )
    )

    assert [v.vue for v in sequence.vues] == [VueEcran.CLASSEMENT, VueEcran.SUIVI_DEROULE]
    assert [v.cadence_s for v in sequence.vues] == [30, 45]


def test_une_meme_vue_peut_revenir_plusieurs_fois_dans_un_deroule() -> None:
    """Le CA parle d'un *déroulé*, pas d'un ensemble : « classement, plan, classement » est légitime
    (la vue qui intéresse le plus revient plus souvent)."""
    sequence = SequenceVues(
        (
            VueProgrammee(VueEcran.CLASSEMENT, 30),
            VueProgrammee(VueEcran.PLAN_CIBLES, 20),
            VueProgrammee(VueEcran.CLASSEMENT, 30),
        )
    )

    assert len(sequence.vues) == 3


def test_une_sequence_vide_est_refusee() -> None:
    """Un écran sans aucune vue n'affiche rien : ce n'est pas un déroulé, c'est une panne muette."""
    with pytest.raises(SequenceVuesVide):
        SequenceVues(())


@pytest.mark.parametrize("cadence", [0, -1, CADENCE_MIN_S - 1, CADENCE_MAX_S + 1])
def test_une_cadence_hors_bornes_est_refusee(cadence: int) -> None:
    """« Cadence réglable » n'est pas « cadence quelconque » : sous le plancher l'écran clignote et
    devient illisible de loin, au-dessus du plafond le déroulé n'en est plus un."""
    with pytest.raises(CadenceEcranInvalide):
        SequenceVues((VueProgrammee(VueEcran.CLASSEMENT, cadence),))


def test_le_deroule_par_defaut_est_utilisable_sans_rien_regler() -> None:
    """« Déroulé de vues **par défaut** » : un écran neuf doit informer sans configuration."""
    defaut = SequenceVues.par_defaut()

    assert defaut.vues
    assert all(CADENCE_MIN_S <= v.cadence_s <= CADENCE_MAX_S for v in defaut.vues)


# --- La prise de contrôle ------------------------------------------------------------------------


def test_une_consigne_peut_figer_une_vue() -> None:
    """CA : l'admin « impose soit une **vue figée** (ex. podium) »."""
    consigne = Consigne(vue=VueEcran.CLASSEMENT, sequence=None, duree_s=600)

    assert consigne.vue is VueEcran.CLASSEMENT
    assert consigne.sequence is None


def test_une_consigne_peut_imposer_une_autre_sequence() -> None:
    """CA : « soit une **autre séquence** »."""
    autre = SequenceVues((VueProgrammee(VueEcran.PLAN_CIBLES, 15),))
    consigne = Consigne(vue=None, sequence=autre, duree_s=None)

    assert consigne.sequence is autre
    assert consigne.vue is None


def test_une_consigne_sans_contenu_est_refusee() -> None:
    """Imposer « rien » n'est pas une prise de contrôle — c'est rendre la main, un autre geste."""
    with pytest.raises(ConsigneEcranInvalide):
        Consigne(vue=None, sequence=None, duree_s=60)


def test_une_consigne_ne_peut_pas_imposer_les_deux_a_la_fois() -> None:
    """Une vue figée *et* une séquence : l'écran ne saurait pas laquelle honorer."""
    with pytest.raises(ConsigneEcranInvalide):
        Consigne(
            vue=VueEcran.CLASSEMENT,
            sequence=SequenceVues((VueProgrammee(VueEcran.PLAN_CIBLES, 15),)),
            duree_s=60,
        )


@pytest.mark.parametrize("duree", [0, -60])
def test_une_duree_non_positive_est_refusee(duree: int) -> None:
    """« Podium 0 minute » n'est pas une prise de contrôle : la borner est le sens même du CA."""
    with pytest.raises(DureePriseDeControleInvalide):
        Consigne(vue=VueEcran.CLASSEMENT, sequence=None, duree_s=duree)


def test_une_consigne_a_duree_expire_toute_seule() -> None:
    """CA « durée » : « podium 10 min **puis reprise du déroulé** » — l'écran se libère seul."""
    consigne = Consigne(vue=VueEcran.CLASSEMENT, sequence=None, duree_s=600)

    assert not consigne.expiree(secondes_ecoulees=599)
    assert consigne.expiree(secondes_ecoulees=600)
    assert consigne.expiree(secondes_ecoulees=601)


def test_une_consigne_sans_duree_ne_expire_jamais_seule() -> None:
    """CA « **ou** retour explicite » : l'admin garde la main jusqu'à ce qu'il la rende."""
    consigne = Consigne(vue=VueEcran.CLASSEMENT, sequence=None, duree_s=None)

    assert not consigne.expiree(secondes_ecoulees=0)
    assert not consigne.expiree(secondes_ecoulees=86_400)


def test_une_consigne_sans_duree_exige_un_rappel() -> None:
    """CA « **jamais un état forcé qu'on oublie** » — arbitrage du 01/08/2026 (Q-UX7 : durée **et**
    retour explicite).

    Le domaine ne peut pas empêcher l'oubli, mais il peut le **nommer** : une consigne sans échéance
    porte l'obligation d'un rappel très visible côté console. C'est ce drapeau que la supervision
    consomme — sans quoi « jamais oublié » resterait une intention de rédaction.
    """
    assert Consigne(vue=VueEcran.CLASSEMENT, sequence=None, duree_s=None).exige_rappel
    assert not Consigne(vue=VueEcran.CLASSEMENT, sequence=None, duree_s=600).exige_rappel


def test_le_reste_permet_d_afficher_un_compte_a_rebours() -> None:
    """« Podium 10 min puis reprise » se rend visible : la console et l'écran comptent à rebours."""
    consigne = Consigne(vue=VueEcran.CLASSEMENT, sequence=None, duree_s=600)

    assert reste_secondes(consigne, secondes_ecoulees=0) == 600
    assert reste_secondes(consigne, secondes_ecoulees=590) == 10
    assert reste_secondes(consigne, secondes_ecoulees=700) == 0


def test_le_reste_est_inconnu_sans_duree() -> None:
    consigne = Consigne(vue=VueEcran.CLASSEMENT, sequence=None, duree_s=None)

    assert reste_secondes(consigne, secondes_ecoulees=42) is None


# --- Le réglage des pages projetées (E16US009) ---------------------------------------------------
#
# CA : « la **cadence d'une page de noms** se règle **par écran**, à côté du déroulé de vues déjà
# configurable » et « `NOMS_PAR_PAGE = 40` est un choix à confirmer sur le vidéoprojecteur réel ;
# **le rendre réglable** ou le mesurer ».
#
# Le second CA offre une alternative — régler ou mesurer. Mesurer suppose un vidéoprojecteur, une
# salle et une distance ; c'est un geste d'exploitation, pas de code. C'est donc « réglable » qui
# est implémenté, et la mesure devient ce que l'organisateur fait **avec** le réglage.


def test_un_reglage_de_pages_porte_les_deux_valeurs_du_ca() -> None:
    reglage = ReglagePages(noms_par_page=25, cadence_page_s=15)

    assert reglage.noms_par_page == 25
    assert reglage.cadence_page_s == 15


def test_le_reglage_de_pages_par_defaut_est_utilisable_sans_rien_regler() -> None:
    """Même exigence que `SequenceVues.par_defaut` : un écran neuf doit informer sans configuration.

    Les valeurs du défaut sont celles que le front tenait en dur jusqu'ici (`DETTE-039`) — 40 noms,
    20 s —, pour qu'aucun écran déjà installé ne change de comportement au déploiement de cette US.
    """
    defaut = ReglagePages.par_defaut()

    assert defaut.noms_par_page == 40
    assert defaut.cadence_page_s == 20


@pytest.mark.parametrize("noms", [0, -1, NOMS_PAR_PAGE_MIN - 1, NOMS_PAR_PAGE_MAX + 1])
def test_un_nombre_de_noms_par_page_hors_bornes_est_refuse(noms: int) -> None:
    """« Réglable » n'est pas « quelconque » — même parti que la cadence de vue.

    Sous le plancher, le nombre de pages explose : à 2 noms par page, 200 archers font 100 pages,
    soit plus d'une demi-heure avant de revoir la sienne. Au-dessus du plafond, la hauteur de ligne
    tombe sous ce qui se lit **à dix mètres**, ce qui est la raison d'être de la pagination.
    """
    with pytest.raises(NombreDeNomsParPageInvalide):
        ReglagePages(noms_par_page=noms, cadence_page_s=20)


@pytest.mark.parametrize("cadence", [0, -1, CADENCE_PAGE_MIN_S - 1, CADENCE_PAGE_MAX_S + 1])
def test_une_cadence_de_page_hors_bornes_est_refusee(cadence: int) -> None:
    """Sous le plancher la page clignote (même jugement que `CADENCE_MIN_S`) ; au-dessus du plafond
    la pagination cesse d'être un défilement — cinq minutes par page, c'est une vue figée."""
    with pytest.raises(CadenceDePageInvalide):
        ReglagePages(noms_par_page=40, cadence_page_s=cadence)


def test_le_reglage_de_pages_est_independant_de_la_cadence_de_vue() -> None:
    """Deux durées **distinctes**, et c'est le point d'attention de l'US.

    `cadence_s` d'une `VueProgrammee` dit combien de temps l'écran reste sur *la vue* ; le réglage
    de pages dit à quel rythme la *liste* tourne **à l'intérieur** de la vue. Une page peut donc
    durer plus longtemps que la vue : la séquence de pages reprend où elle s'était arrêtée au
    passage suivant (cf. `pagination.ts`, `secondes_ecoulees` cumulé). Rien n'exige que l'une divise
    l'autre, et le domaine ne l'impose pas.
    """
    vue = VueProgrammee(VueEcran.CLASSEMENT, 30)
    pages = ReglagePages(noms_par_page=40, cadence_page_s=45)

    assert pages.cadence_page_s > vue.cadence_s
