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
    assert contrat.plan_de_cibles is PlanDeCibles.PAR_BLOC_DE_COULOIRS


def test_le_classement_dune_poule_est_lisible_par_une_phase_avale() -> None:
    """CA — « la phase avale consomme les qualifiés », livré en fin de tranche E05US023.

    Ce test **a changé de camp** : jusqu'au 6ᵉ commit de l'US, il vérifiait l'inverse et documentait
    ce qui manquait (l'ordre inter-poules n'était pas arrêté, et le branchement
    `ServicePoules` ↔ `ServiceSaisieDuels` était un cycle). Les deux sont désormais écrits —
    `domain/classement_de_poules.py` pour l'ordre, le port `LecteurClassementDePhase` pour le
    cycle — donc le registre peut le déclarer sans mentir.

    ⚠️ L'effet est **mesurable**, et c'est ce qui interdisait de le déclarer plus tôt : le plancher
    d'inscrits (E05US021) est désormais réclamé pour un prélèvement visant une phase de poules. Il
    ne l'est légitimement que parce que le prélèvement est réellement honoré.
    """
    assert TypePhase.POULES in TYPES_CLASSANTS_LUS
    assert {
        TypePhase.QUALIFICATION,
        TypePhase.ELIMINATION_DIRECTE,
        TypePhase.POULES,
        # E05US028 : `ServiceBigShootOff.classement_de_phase` rend le classement des rangs
        # décernés, lu par le port `LecteurClassementDePhase`.
        TypePhase.BIG_SHOOT_OFF,
        # E05US026 : `ServiceSuisse.classement_de_phase` rend le sien par le **même** port — c'est
        # la 3ᵉ occurrence qui a justifié de fondre les ports jumeaux (ADR-0084).
        TypePhase.SUISSE,
        # E05US027 : `ServiceColline.classement_de_phase` rend le sien par ce même port — **4ᵉ
        # occurrence, et aucune duplication à écrire**, ce qui est la preuve à l'usage qu'ADR-0084
        # a fondu les bons ports. `classement_de_colline` est le plus court des quatre : une
        # colline **est** son classement, elle n'a rien à inventer.
        TypePhase.COLLINE,
    } == TYPES_CLASSANTS_LUS


def test_les_cinq_formats_joues_savent_dire_ou_l_archer_tire_ensuite() -> None:
    """⚠️ La capacité qu'il aurait été le plus tentant de mentir (ADR-0083, 5ᵉ question).

    **Ce test a changé de camp deux fois, et chaque fois pour la bonne raison.** Il vérifiait
    d'abord que les poules n'étaient **pas** routées — ce n'était ni au CA d'E05US023 ni à la liste
    de la tranche, et déclarer `route_l_archer=True` « puisque la phase est jouable » aurait
    reproduit `DETTE-028` à l'échelle d'une capacité : une promesse sans appelant.

    Le Big Shoot Off y est entré en **E05US028** (`_routage_big_shoot_off`), puis le suisse **et**
    les poules en **E05US026** (`_routage_par_rencontres`, qui sert les deux : une rencontre de
    ronde comme de groupe *est* un duel, avec deux adversaires et deux couloirs).

    La **colline** y est entrée en **E05US027**, par le même `_routage_par_rencontres` que ses deux
    voisins et sans une ligne de routage neuve — un défi *est* un duel. Elle en avait d'autant plus
    besoin que son régime d'attente n'est pas un cas limite : à portée 1, les deux extrémités de la
    colline se reposent une manche sur deux, **quel que soit** l'effectif.

    Il ne reste donc dehors que ce qui n'est pas joué — et le test le dit en négatif, pour qu'un
    format rendu jouable sans son routage se voie immédiatement.
    """
    assert {
        TypePhase.ELIMINATION_DIRECTE,
        TypePhase.BIG_SHOOT_OFF,
        TypePhase.POULES,
        TypePhase.SUISSE,
        TypePhase.COLLINE,
    } == TYPES_ROUTES
    # Tout type **joué** est routé : c'est l'invariant que les trois US successives ont installé.
    assert {t for t in TYPES_DEROULES if t is not TypePhase.PLACEMENT} <= TYPES_ROUTES


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
    [TypePhase.BARRAGE],
)
def test_les_formats_restants_ne_sont_toujours_pas_joues(type_sans_service: TypePhase) -> None:
    """`DETTE-028` est **refermée sur son volet « moteurs sans appelant »** — et le registre le dit.

    Ceux-là ont un moteur de domaine depuis E05US015 et **aucun appelant de production**. Les
    déclarer jouables parce que d'autres le sont devenus serait exactement la faute qu'ADR-0083 se
    donne pour objet d'empêcher : le signal d'écart de l'atelier cesserait de les viser, et
    l'organisateur composerait un déroulé que rien ne déroulera.

    Ce test **change de camp** à chacune des US `E05US026` à `E05US028`, une ligne à la fois. Le
    **Big Shoot Off en est sorti le 14/08/2026** (E05US028) : `ServiceBigShootOff` le déroule, son
    classement est lu par une phase avale, et le routage sait dire quelle manche vient. Le
    **système suisse en est sorti le 15/08/2026** (E05US026) : `ServiceSuisse` rejoue ses rondes des
    duels validés et `classement_de_suisse` rend son classement de phase. La **colline en est
    sortie le 22/08/2026** (`E05US027`, 4ᵉ et dernière tranche) : `ServiceColline` rejoue ses
    manches et `classement_de_colline` rend son classement de phase.

    ⚠️ **Il ne reste donc que le barrage, et son cas est différent et permanent** : c'est un
    **départage**, pas un format qu'on déroule. Ce test ne se videra jamais — il ne garde plus
    l'avancement d'un chantier, il garde une **distinction de nature**. Le renommer « les formats
    restants » serait désormais trompeur si un jour on croyait devoir le faire disparaître : le
    barrage a un moteur, un appelant (`config.policies.tiebreak` depuis E06US003) et aucun déroulé,
    et c'est exact.
    """
    contrat = contrat_de(type_sans_service)

    assert not contrat.deroule_par_un_service
    assert not contrat.classement_lisible
    assert type_sans_service in TYPES_SIGNALES_EN_ECART


def test_le_big_shoot_off_est_joue_lu_et_route() -> None:
    """CA d'E05US028, les trois capacités d'un coup — et le signal d'écart cesse de le viser.

    ⚠️ **Le `plan_de_cibles` reste `AUCUN`, et ce n'est pas un oubli.** Les finalistes tirent bien
    en parallèle, donc ils occupent des couloirs — mais aucun service ne les leur attribue : ce sont
    des inscrits du créneau, et le moteur du format ne relit pas leur couloir de qualification. Le
    routage le **nomme** au lieu de le taire (`DETTE-059`). Déclarer un plan ici mentirait
    exactement comme `deroule_par_un_service` aurait menti avant que le service existe.
    """
    contrat = contrat_de(TypePhase.BIG_SHOOT_OFF)

    assert contrat.deroule_par_un_service
    assert contrat.classement_lisible
    assert contrat.route_l_archer
    assert contrat.decor is DecorDeSaisie.VOLEE_COLLECTIVE
    assert contrat.plan_de_cibles is PlanDeCibles.AUCUN
    assert TypePhase.BIG_SHOOT_OFF not in TYPES_SIGNALES_EN_ECART
    # Il n'entre **pas** au palmarès par reconstruction d'arbre : il n'en a pas. Son entrée passe
    # par `ServicePalmares._resultat_big_shoot_off`, un résultat propre au format.
    assert TypePhase.BIG_SHOOT_OFF not in TYPES_RECONSTRUCTIBLES


def test_le_registre_est_le_miroir_des_filtres_de_service() -> None:
    """Le verrou dans le sens **dangereux** : les tables et les services doivent coïncider.

    Un registre juste et des services qui filtrent encore à la main ne vaut rien. On vérifie donc
    ici que les trois filtres ponctuels d'origine (`ServiceSaisieDuels`, `ServicePlacementDuels`,
    `ServicePalmares` — tous trois `phase.type is not ELIMINATION_DIRECTE`) rendent bien
    l'élimination directe **seule**. Si un type y entrait par le registre sans que le service sache
    le traiter, c'est ici qu'on le verrait — pas en salle.
    """
    assert {TypePhase.ELIMINATION_DIRECTE} == TYPES_EN_TABLEAU_JOUE


def test_le_bot_de_simulation_ne_pretend_pas_jouer_ce_qu_il_ne_sait_pas() -> None:
    """⚠️ **Le seul garde-fou de `_TYPES_DEROULABLES` était un commentaire** (correctif de revue).

    `application/simulation_format.py` part de `TYPES_JOUES` — table **dérivée** — et lui retranche
    **à la main** les formats que `fabriquer_harnais_simulation` ne construit pas. Les deux
    répondent à des questions différentes : « un service de production déroule-t-il ce type ? »
    contre « le **bot** sait-il le jouer ? ».

    L'oubli s'est produit **trois fois** (poules, Big Shoot Off, système suisse), et à chaque fois
    l'atelier annonçait `joue=True, 0 tour, 0 duel` — des zéros lus comme un constat — en perdant le
    bandeau « le moteur ne sait pas encore dérouler ce type ».

    ✅ **Le garde-fou a servi dès l'US suivante, et exactement comme prévu** : il est tombé en
    E05US027 à la seconde où le registre a déclaré la colline jouable, **avant** qu'une ligne de
    `simulation_format.py` ait été touchée. Le 4ᵉ retrait a donc été posé en connaissance de cause
    plutôt que découvert en salle. C'est la valeur d'un test qui garde une **divergence entre deux
    tables** : il ne dit pas que le code est faux, il dit qu'une décision est due.

    Ce test est le garde-fou qui manquait : il tombe à chaque oubli, que `DETTE-066` annonçait pour
    la colline. Il vit ici et non dans les tests de simulation parce que ce qu'il garde est la
    **divergence entre deux tables**, pas le comportement de l'atelier.
    """
    from application.simulation_format import _TYPES_DEROULABLES

    # Ce que le bot sait réellement jouer aujourd'hui : le harnais ne construit que la
    # qualification et les duels de tableau.
    assert {TypePhase.QUALIFICATION, TypePhase.ELIMINATION_DIRECTE} == _TYPES_DEROULABLES
    # Et tout format **joué en production** mais absent de cette liste doit l'être *explicitement* :
    # c'est le retrait à la main que DETTE-066 tracera jusqu'à sa résorption.
    assert {
        TypePhase.POULES,
        TypePhase.BIG_SHOOT_OFF,
        TypePhase.SUISSE,
        # E05US027 — 4ᵉ retrait, posé le jour où ce test est tombé (voir la docstring).
        TypePhase.COLLINE,
    } == TYPES_JOUES - _TYPES_DEROULABLES
