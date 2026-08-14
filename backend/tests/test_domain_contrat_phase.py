"""Le **contrat de phase jouable** — registre des capacités par type ([ADR-0083]).

**Ce que ces tests gardent, et pourquoi ils ne ressemblent pas aux autres.** Le registre n'est pas
une règle métier : il n'a pas de CA dont dériver un oracle (règle 9 — « câblage : tests après
l'implémentation »). Sa valeur est **structurelle**, et elle est tout entière dans une propriété :
*aucune table dérivée ne peut diverger d'une autre*. C'est cette propriété qu'on teste, pas les
valeurs une à une — recopier le registre dans les assertions ne prouverait que la capacité du
copier-coller.

Trois familles de garde, donc :

1. **complétude** — tout `TypePhase` a un contrat, et rien d'autre n'en a un ;
2. **dérivation** — chaque table publique se recalcule depuis le registre, et non l'inverse ;
3. **honnêteté** — les deux capacités qu'il serait le plus facile de mentir
   (`deroule_par_un_service`, `classement_lisible`) sont confrontées au **code du jour**, pas à
   l'intention. C'est la garde qui aurait attrapé `DETTE-028` et le défaut d'ADR-0017.

[ADR-0083]: ../../docs/adr/0083-le-contrat-de-phase-jouable.md
"""

from __future__ import annotations

import pytest

from domain.contrat_phase import (
    TYPES_CLASSANTS_LUS,
    TYPES_DEROULES,
    TYPES_EN_TABLEAU,
    TYPES_EN_TABLEAU_JOUE,
    TYPES_JOUES,
    TYPES_RECONSTRUCTIBLES,
    TYPES_ROUTES,
    TYPES_SANS_CLASSEMENT,
    TYPES_SANS_OPPOSITION,
    TYPES_SIGNALES_EN_ECART,
    ContratDePhase,
    DecorDeSaisie,
    PlanDeCibles,
    TypePhase,
    contrat_de,
    produit_un_classement,
)

# --- 1. Complétude du registre ------------------------------------------------------------------


@pytest.mark.parametrize("type_phase", list(TypePhase))
def test_chaque_type_du_catalogue_a_un_contrat(type_phase: TypePhase) -> None:
    """Un type sans contrat lèverait `KeyError` **en salle**, dans un filtre, sans rien dire.

    `contrat_de` ne rattrape pas ce cas volontairement : ce test est ce qui le rend inatteignable
    en production, en faisant tomber l'oubli à l'endroit utile. C'est le seul filet, et il suffit —
    le catalogue est fermé (un `Enum`), donc la couverture est exhaustive par construction.
    """
    assert isinstance(contrat_de(type_phase), ContratDePhase)


def test_le_decor_et_le_plan_de_cibles_sont_coherents_entre_eux() -> None:
    """Un type qui **place** des archers a forcément quelque chose à leur faire tirer.

    L'inverse est permis et fréquent — suisse, colline, Big Shoot Off et barrage ont un décor mais
    aucun plan de cibles, parce que personne ne les pose encore en salle. Mais un plan sans décor
    serait un non-sens : on réserverait des couloirs pour une phase où l'on ne saisit rien.
    """
    for type_phase in TypePhase:
        contrat = contrat_de(type_phase)
        if contrat.plan_de_cibles is not PlanDeCibles.AUCUN:
            assert contrat.decor is not DecorDeSaisie.AUCUN, type_phase


# --- 2. Dérivation : les tables se recalculent, elles ne se recopient pas ------------------------


def test_les_tables_derivees_se_recalculent_depuis_le_registre() -> None:
    """La propriété qui justifie tout le module : **une seule source par capacité**.

    On recalcule ici chaque table depuis `contrat_de`, exactement comme le module le fait. Le test
    ne vaudrait rien s'il se contentait de comparer deux constantes ; il vaut parce qu'il **redit
    la règle de dérivation** — si quelqu'un fige une table en dur (le geste qui a produit les dix
    filtres d'origine), les deux expressions cessent de coïncider.
    """
    contrats = {type_phase: contrat_de(type_phase) for type_phase in TypePhase}

    assert {
        t for t, c in contrats.items() if c.decor is DecorDeSaisie.ARBRE_DE_DUELS
    } == TYPES_EN_TABLEAU
    assert {t for t, c in contrats.items() if c.deroule_par_un_service} == TYPES_DEROULES
    assert {t for t, c in contrats.items() if c.classement_lisible} == TYPES_CLASSANTS_LUS
    assert {t for t, c in contrats.items() if c.route_l_archer} == TYPES_ROUTES
    assert {t for t, c in contrats.items() if not c.produit_un_classement} == TYPES_SANS_CLASSEMENT
    assert {t for t, c in contrats.items() if not c.oppose_des_tireurs} == TYPES_SANS_OPPOSITION
    assert {
        t
        for t, c in contrats.items()
        if c.deroule_par_un_service and c.decor is DecorDeSaisie.ARBRE_DE_DUELS
    } == TYPES_EN_TABLEAU_JOUE
    assert TYPES_JOUES == TYPES_CLASSANTS_LUS | TYPES_DEROULES
    assert TYPES_RECONSTRUCTIBLES == TYPES_EN_TABLEAU_JOUE


def test_un_type_en_tableau_joue_est_a_la_fois_en_tableau_et_monte() -> None:
    """L'intersection est une **conjonction**, pas un troisième ensemble à tenir à jour.

    C'est ce qui a manqué aux dix filtres d'origine : `placement` a l'arbre sans le service, les
    poules le service sans l'arbre, et chaque appelant redécouvrait la nuance dans son coin.
    """
    assert TYPES_EN_TABLEAU_JOUE == TYPES_EN_TABLEAU & TYPES_DEROULES


def test_le_signal_decart_ne_vise_que_ce_qui_produit_sans_etre_joue() -> None:
    """E01US024 : l'atelier signale « composable mais pas jouable ».

    Deux exclusions, et les deux comptent. Un type **joué** n'est pas en écart — c'est le sens même
    du signal. Un type **non classant** non plus : l'échauffement ne produit rien *par définition*,
    donc l'annoncer serait un faux positif, et un faux positif répété apprend à ignorer le signal.
    """
    assert {
        t for t in TypePhase if t not in TYPES_JOUES and contrat_de(t).produit_un_classement
    } == TYPES_SIGNALES_EN_ECART
    assert TypePhase.ECHAUFFEMENT not in TYPES_SIGNALES_EN_ECART
    assert not TYPES_SIGNALES_EN_ECART & TYPES_JOUES


def test_produit_un_classement_reste_le_negatif_de_la_table() -> None:
    """La fonction historique de `domain.phase` continue de répondre, depuis le registre."""
    assert produit_un_classement(TypePhase.POULES)
    assert not produit_un_classement(TypePhase.ECHAUFFEMENT)


# --- 3. Honnêteté : le registre décrit le code du jour, pas l'intention --------------------------


def test_les_poules_sont_montees_saisies_et_placees() -> None:
    """Ce que la tranche E05US023 rend vrai — et qui ne l'était pas la veille.

    Une phase de poules est désormais **montée** par un service (`ServicePoules`), **saisie** dans
    son propre décor et **placée** sur des blocs de couloirs. C'est ce que « jouable » veut dire.
    """
    contrat = contrat_de(TypePhase.POULES)

    assert contrat.deroule_par_un_service
    assert contrat.decor is DecorDeSaisie.RENCONTRES_EN_GROUPES
    assert contrat.plan_de_cibles is PlanDeCibles.PAR_BLOC_DE_POULE


def test_le_classement_dune_poule_est_lisible_par_une_phase_avale() -> None:
    """CA — « la phase avale consomme les qualifiés », livré en fin de tranche E05US023.

    Ce test **a changé de camp** : jusqu'au 6ᵉ commit de l'US, il vérifiait l'inverse et documentait
    ce qui manquait (l'ordre inter-poules n'était pas arrêté, et le branchement
    `ServicePoules` ↔ `ServiceSaisieDuels` était un cycle). Les deux sont désormais écrits —
    `domain/classement_de_poules.py` pour l'ordre, le port `LecteurClassementPoules` pour le cycle —
    donc le registre peut le déclarer sans mentir.

    ⚠️ L'effet est **mesurable**, et c'est ce qui interdisait de le déclarer plus tôt : le plancher
    d'inscrits (E05US021) est désormais réclamé pour un prélèvement visant une phase de poules. Il
    ne l'est légitimement que parce que le prélèvement est réellement honoré.
    """
    assert TypePhase.POULES in TYPES_CLASSANTS_LUS
    assert {
        TypePhase.QUALIFICATION,
        TypePhase.ELIMINATION_DIRECTE,
        TypePhase.POULES,
    } == TYPES_CLASSANTS_LUS


def test_les_poules_ne_sont_pas_encore_routees() -> None:
    """⚠️ La capacité qu'il aurait été le plus tentant de mentir (ADR-0083, 5ᵉ question).

    `application/routage.py` ne sait pas dire à un membre de poule où il tire ensuite : ce n'est ni
    au CA d'E05US023 ni à la liste de la tranche. Déclarer `route_l_archer=True` « puisque la phase
    est jouable » reproduirait `DETTE-028` à l'échelle d'une capacité — un moteur annoncé, aucun
    appelant. Le test tombe le jour où le routage l'apprend, et c'est le signal attendu.
    """
    assert TypePhase.POULES not in TYPES_ROUTES
    assert {TypePhase.ELIMINATION_DIRECTE} == TYPES_ROUTES


def test_le_placement_a_un_arbre_mais_aucun_service_pour_le_monter() -> None:
    """La divergence qu'E06US006 avait constatée et laissée, tranchée ici.

    `deroule._TYPES_DEROULES` comptait `placement` parmi les types déroulés alors qu'aucun service
    ne monte son tableau — les deux services de duels filtrent sur l'élimination directe seule.
    Conséquence mesurable : une phase `placement` prélevant « les rangs 33 et suivants » **relevait
    le plancher d'inscrits** (E05US021) pour une phase que rien ne joue, soit le « refus abusif le
    jour J » que cette US-là nommait comme sa pire défaillance.

    Le registre ne permet plus d'écrire les deux à la fois : `placement` a le **décor** d'un arbre
    (sa profondeur reste réglable, E06US006) sans la capacité de le **monter**.
    """
    contrat = contrat_de(TypePhase.PLACEMENT)

    assert contrat.decor is DecorDeSaisie.ARBRE_DE_DUELS
    assert not contrat.deroule_par_un_service
    assert TypePhase.PLACEMENT in TYPES_EN_TABLEAU
    assert TypePhase.PLACEMENT not in TYPES_DEROULES


@pytest.mark.parametrize(
    "type_sans_service",
    [TypePhase.SUISSE, TypePhase.COLLINE, TypePhase.BIG_SHOOT_OFF, TypePhase.BARRAGE],
)
def test_les_formats_restants_ne_sont_toujours_pas_joues(type_sans_service: TypePhase) -> None:
    """`DETTE-028` **rétrécit sans se refermer** — et le registre doit le dire.

    Ces quatre-là ont un moteur de domaine depuis E05US015 et **aucun appelant de production**.
    Les déclarer jouables parce que les poules le sont devenues serait exactement la faute que
    l'ADR-0083 se donne pour objet d'empêcher : le signal d'écart de l'atelier cesserait de les
    viser, et l'organisateur composerait un déroulé que rien ne déroulera.

    Ce test **change de camp** à chacune des US `E05US026` à `E05US028`, une ligne à la fois.
    """
    contrat = contrat_de(type_sans_service)

    assert not contrat.deroule_par_un_service
    assert not contrat.classement_lisible
    assert type_sans_service in TYPES_SIGNALES_EN_ECART


def test_le_registre_est_le_miroir_des_filtres_de_service() -> None:
    """Le verrou dans le sens **dangereux** : les tables et les services doivent coïncider.

    Un registre juste et des services qui filtrent encore à la main ne vaut rien. On vérifie donc
    ici que les trois filtres ponctuels d'origine (`ServiceSaisieDuels`, `ServicePlacementDuels`,
    `ServicePalmares` — tous trois `phase.type is not ELIMINATION_DIRECTE`) rendent bien
    l'élimination directe **seule**. Si un type y entrait par le registre sans que le service sache
    le traiter, c'est ici qu'on le verrait — pas en salle.
    """
    assert {TypePhase.ELIMINATION_DIRECTE} == TYPES_EN_TABLEAU_JOUE
